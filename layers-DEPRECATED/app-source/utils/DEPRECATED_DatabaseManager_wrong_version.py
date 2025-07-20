"""
PostgreSQL DatabaseManager for Climate Risk RAG System
Lambda-optimized with connection pooling and error handling
"""

import os
import sys
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import time

# REQUIRED IMPORTS - FAIL HARD IF MISSING
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

class DatabaseManager:
    """
    PostgreSQL database manager optimized for AWS Lambda execution.
    Provides connection pooling, error handling, and Lambda-specific optimizations.
    """
    
    # Class-level connection pool for Lambda container reuse
    _connection_pool = None
    _pool_initialized = False
    
    def __init__(self, connection_string: str = None):
        """
        Initialize database manager with PostgreSQL connection.
        
        Args:
            connection_string: PostgreSQL connection string (defaults to DATABASE_URL env var)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Get connection string from parameter or environment
        self.connection_string = connection_string or os.environ.get('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("Database connection string required (DATABASE_URL environment variable or parameter)")
        
        # Configuration from environment
        self.pool_min_conn = int(os.environ.get('DB_POOL_MIN_CONN', '1'))
        self.pool_max_conn = int(os.environ.get('DB_POOL_MAX_CONN', '10'))
        self.connection_timeout = int(os.environ.get('DB_CONNECTION_TIMEOUT', '30'))
        self.retry_attempts = int(os.environ.get('DB_RETRY_ATTEMPTS', '3'))
        self.retry_delay = float(os.environ.get('DB_RETRY_DELAY', '1.0'))
        
        # Initialize connection pool
        self._ensure_connection_pool()
        
        # Initialize schema if needed
        self._init_db()
        
        self.logger.info("PostgreSQL DatabaseManager initialized successfully")

    @classmethod
    def _ensure_connection_pool(cls):
        """Ensure connection pool is initialized (thread-safe)"""
        if not cls._pool_initialized:
            try:
                connection_string = os.environ.get('DATABASE_URL')
                if not connection_string:
                    raise ValueError("DATABASE_URL environment variable required")
                
                pool_min = int(os.environ.get('DB_POOL_MIN_CONN', '1'))
                pool_max = int(os.environ.get('DB_POOL_MAX_CONN', '10'))
                
                cls._connection_pool = ThreadedConnectionPool(
                    minconn=pool_min,
                    maxconn=pool_max,
                    dsn=connection_string
                )
                cls._pool_initialized = True
                
                # Test connection
                conn = cls._connection_pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                finally:
                    cls._connection_pool.putconn(conn)
                    
            except Exception as e:
                logging.error(f"Failed to initialize connection pool: {str(e)}")
                raise

    def get_connection(self):
        """Get a connection from the pool with retry logic"""
        if not self._connection_pool:
            self._ensure_connection_pool()
        
        for attempt in range(self.retry_attempts):
            try:
                conn = self._connection_pool.getconn()
                if conn:
                    # Test connection
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                    return conn
            except Exception as e:
                self.logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise
        
        raise Exception("Failed to get database connection after all retry attempts")

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self._connection_pool and conn:
            try:
                self._connection_pool.putconn(conn)
            except Exception as e:
                self.logger.error(f"Error returning connection to pool: {str(e)}")

    def _init_db(self) -> None:
        """Initialize database with schema if needed (idempotent)"""
        try:
            self.logger.debug("Checking database schema")
            
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # Check if core tables exist
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                    """)
                    existing_tables = {row[0] for row in cursor.fetchall()}
                    
                    expected_tables = {
                        'documents', 'chunks', 'document_metadata', 'system_ids',
                        'textract_jobs', 'document_processing_status'
                    }
                    
                    missing_tables = expected_tables - existing_tables
                    
                    if not missing_tables:
                        # All tables exist - schema is already initialized
                        self.logger.debug(f"Database schema already exists. Tables: {', '.join(sorted(existing_tables))}")
                        return
                    
                    # Some tables are missing - need to initialize schema
                    self.logger.info(f"Missing tables detected: {missing_tables}. Initializing schema...")
                    
                    # Get schema from embedded string (Lambda-friendly)
                    schema = self._get_embedded_schema()
                    
                    # Execute schema (should be idempotent with CREATE TABLE IF NOT EXISTS)
                    cursor.execute(schema)
                    conn.commit()
                    
                    # Verify all expected tables now exist
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                    """)
                    final_tables = {row[0] for row in cursor.fetchall()}
                    
                    still_missing = expected_tables - final_tables
                    if still_missing:
                        raise RuntimeError(f"Failed to create tables: {still_missing}")
                    
                    self.logger.info(f"Database schema initialization complete. Tables: {', '.join(sorted(final_tables))}")
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            # Don't raise the exception if tables already exist
            if "already exists" in str(e).lower():
                self.logger.info("Schema already exists - continuing with existing database")
            else:
                raise

    def _get_embedded_schema(self) -> str:
        """Get embedded PostgreSQL schema (Lambda-friendly approach)"""
        # Try to load from file first (development)
        schema_path = os.path.join(os.path.dirname(__file__), 'schema', 'postgresql_schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                return f.read()
        
        # Fallback to embedded schema for Lambda
        return """
        -- Minimal embedded schema for Lambda deployment
        CREATE TABLE IF NOT EXISTS documents (
            doc_id VARCHAR(255) PRIMARY KEY,
            url TEXT UNIQUE,
            original_filename TEXT,
            pdf_path TEXT,
            text_path TEXT,
            download_date TIMESTAMP WITH TIME ZONE,
            status VARCHAR(50) DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS document_metadata (
            doc_id VARCHAR(255) PRIMARY KEY,
            title TEXT,
            title_confidence DECIMAL(5,4),
            title_source VARCHAR(100),
            author TEXT,
            author_confidence DECIMAL(5,4),
            author_source VARCHAR(100),
            language VARCHAR(10),
            language_confidence DECIMAL(5,4),
            structural_metadata JSONB,
            processing_info JSONB,
            raw_metadata JSONB,
            metadata_quality DECIMAL(5,4),
            metadata_source VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
        );
        
        CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
        CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at);
        """

    def validate_schema(self) -> bool:
        """Validate existing database schema matches expected structure"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # Check tables exist
                    cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                    """)
                    tables = set(row[0] for row in cursor.fetchall())
                    
                    expected_tables = {'documents', 'document_metadata'}
                    missing_tables = expected_tables - tables
                    
                    if missing_tables:
                        self.logger.error(f"Missing tables: {missing_tables}")
                        return False
                    
                    # Check documents table structure
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'documents' AND table_schema = 'public'
                    """)
                    columns = set(row[0] for row in cursor.fetchall())
                    
                    expected_columns = {
                        'doc_id', 'url', 'original_filename', 'pdf_path', 
                        'text_path', 'download_date', 'status', 'error_message', 
                        'created_at', 'updated_at'
                    }
                    
                    missing_columns = expected_columns - columns
                    if missing_columns:
                        self.logger.error(f"Missing columns in documents table: {missing_columns}")
                        return False
                    
                    return True
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error validating schema: {str(e)}")
            return False

    def add_or_update_document(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """Add or update document and its metadata"""
        try:
            metadata['doc_id'] = doc_id
            structured_metadata = self.structure_document_metadata(metadata)
            
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # Update documents table with basic info
                    doc_fields = {
                        "doc_id": doc_id,
                        "url": structured_metadata.get("url"),
                        "original_filename": structured_metadata.get("original_filename"),
                        "pdf_path": structured_metadata.get("pdf_path"),
                        "text_path": structured_metadata.get("text_path"),
                        "download_date": structured_metadata.get("download_date", datetime.now()),
                        "status": structured_metadata.get("status", "pending"),
                        "updated_at": datetime.now()
                    }
                    
                    # PostgreSQL UPSERT syntax
                    cursor.execute("""
                        INSERT INTO documents (doc_id, url, original_filename, pdf_path, text_path, 
                                             download_date, status, updated_at)
                        VALUES (%(doc_id)s, %(url)s, %(original_filename)s, %(pdf_path)s, %(text_path)s,
                                %(download_date)s, %(status)s, %(updated_at)s)
                        ON CONFLICT (doc_id) DO UPDATE SET
                            url = EXCLUDED.url,
                            original_filename = EXCLUDED.original_filename,
                            pdf_path = EXCLUDED.pdf_path,
                            text_path = EXCLUDED.text_path,
                            download_date = EXCLUDED.download_date,
                            status = EXCLUDED.status,
                            updated_at = EXCLUDED.updated_at
                    """, doc_fields)
                    
                    # Update document_metadata table
                    title_data = structured_metadata.get("title", {})
                    author_data = structured_metadata.get("author", {})
                    language_data = structured_metadata.get("language", {})
                    
                    meta_fields = {
                        "doc_id": doc_id,
                        "title": title_data.get("value") if isinstance(title_data, dict) else title_data,
                        "title_confidence": title_data.get("confidence", 0.1) if isinstance(title_data, dict) else 0.1,
                        "title_source": title_data.get("source", "default") if isinstance(title_data, dict) else "default",
                        "author": author_data.get("value") if isinstance(author_data, dict) else author_data,
                        "author_confidence": author_data.get("confidence", 0.1) if isinstance(author_data, dict) else 0.1,
                        "author_source": author_data.get("source", "default") if isinstance(author_data, dict) else "default",
                        "language": language_data.get("value") if isinstance(language_data, dict) else language_data,
                        "language_confidence": language_data.get("confidence", 0.1) if isinstance(language_data, dict) else 0.1,
                        "structural_metadata": json.dumps(structured_metadata.get("structural", {})),
                        "processing_info": json.dumps(structured_metadata.get("processing_info", {})),
                        "raw_metadata": json.dumps(structured_metadata.get("raw_metadata", {})),
                        "metadata_quality": structured_metadata.get("metadata_quality", 0.1),
                        "metadata_source": structured_metadata.get("metadata_source", "initial"),
                        "updated_at": datetime.now()
                    }
                    
                    cursor.execute("""
                        INSERT INTO document_metadata (
                            doc_id, title, title_confidence, title_source, author, author_confidence, 
                            author_source, language, language_confidence, structural_metadata, 
                            processing_info, raw_metadata, metadata_quality, metadata_source, updated_at
                        ) VALUES (
                            %(doc_id)s, %(title)s, %(title_confidence)s, %(title_source)s, %(author)s, 
                            %(author_confidence)s, %(author_source)s, %(language)s, %(language_confidence)s, 
                            %(structural_metadata)s, %(processing_info)s, %(raw_metadata)s, 
                            %(metadata_quality)s, %(metadata_source)s, %(updated_at)s
                        )
                        ON CONFLICT (doc_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            title_confidence = EXCLUDED.title_confidence,
                            title_source = EXCLUDED.title_source,
                            author = EXCLUDED.author,
                            author_confidence = EXCLUDED.author_confidence,
                            author_source = EXCLUDED.author_source,
                            language = EXCLUDED.language,
                            language_confidence = EXCLUDED.language_confidence,
                            structural_metadata = EXCLUDED.structural_metadata,
                            processing_info = EXCLUDED.processing_info,
                            raw_metadata = EXCLUDED.raw_metadata,
                            metadata_quality = EXCLUDED.metadata_quality,
                            metadata_source = EXCLUDED.metadata_source,
                            updated_at = EXCLUDED.updated_at
                    """, meta_fields)
                    
                    conn.commit()
                    self.logger.debug(f"Document {doc_id} updated successfully")
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error updating document {doc_id}: {str(e)}")
            raise

    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata by ID"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT d.*, m.title, m.title_confidence, m.title_source,
                               m.author, m.author_confidence, m.author_source,
                               m.language, m.language_confidence,
                               m.structural_metadata, m.processing_info, m.raw_metadata,
                               m.metadata_quality, m.metadata_source
                        FROM documents d
                        LEFT JOIN document_metadata m ON d.doc_id = m.doc_id
                        WHERE d.doc_id = %s
                    """, (doc_id,))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error getting document metadata for {doc_id}: {str(e)}")
            return None

    def update_system_id(self, doc_id: str, system_name: str, system_id: str, 
                        status: str = 'complete', timestamp: Optional[str] = None) -> bool:
        """Update or insert system ID with indexing metadata"""
        try:
            timestamp = timestamp or datetime.now()
            
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO system_ids 
                            (doc_id, system_name, system_id, last_indexed, indexing_status)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (doc_id, system_name) DO UPDATE SET
                            system_id = EXCLUDED.system_id,
                            last_indexed = EXCLUDED.last_indexed,
                            indexing_status = EXCLUDED.indexing_status,
                            updated_at = NOW()
                    """, (doc_id, system_name, system_id, timestamp, status))
                    
                    conn.commit()
                    return True
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error updating system ID for document {doc_id}: {str(e)}")
            return False

    def get_documents_by_index_status(self, system_name: str, 
                                    status: Optional[str] = None, 
                                    since: Optional[datetime] = None) -> List[str]:
        """Get documents filtered by indexing status"""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    query = """
                        SELECT d.doc_id 
                        FROM documents d
                        LEFT JOIN system_ids s ON d.doc_id = s.doc_id 
                            AND s.system_name = %s
                        WHERE 1=1
                    """
                    params = [system_name]
                    
                    if status:
                        query += " AND (s.indexing_status IS NULL OR s.indexing_status = %s)"
                        params.append(status)
                        
                    if since:
                        query += """ AND (s.last_indexed IS NULL 
                                        OR s.last_indexed < %s 
                                        OR d.updated_at > s.last_indexed)"""
                        params.append(since)
                    
                    cursor.execute(query, params)
                    return [row[0] for row in cursor.fetchall()]
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error getting documents by index status: {str(e)}")
            return []

    def structure_document_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Structure document metadata for database storage"""
        # This method maintains compatibility with the original interface
        # while ensuring proper data structure for PostgreSQL
        
        structured = {}
        
        # Basic fields
        for field in ['doc_id', 'url', 'original_filename', 'pdf_path', 'text_path', 
                     'download_date', 'status', 'error_message']:
            if field in metadata:
                structured[field] = metadata[field]
        
        # Complex fields with confidence scores
        for field in ['title', 'author', 'language']:
            if field in metadata:
                if isinstance(metadata[field], dict):
                    structured[field] = metadata[field]
                else:
                    structured[field] = {
                        'value': metadata[field],
                        'confidence': 0.1,
                        'source': 'default'
                    }
        
        # JSON fields
        for field in ['structural', 'processing_info', 'raw_metadata']:
            if field in metadata:
                structured[field] = metadata[field]
        
        # Quality and source
        structured['metadata_quality'] = metadata.get('metadata_quality', 0.1)
        structured['metadata_source'] = metadata.get('metadata_source', 'initial')
        
        return structured

    def close_all_connections(self):
        """Close all connections in the pool (for cleanup)"""
        if self._connection_pool:
            try:
                self._connection_pool.closeall()
                self.__class__._connection_pool = None
                self.__class__._pool_initialized = False
                self.logger.info("All database connections closed")
            except Exception as e:
                self.logger.error(f"Error closing connections: {str(e)}")

    def __del__(self):
        """Cleanup on destruction"""
        # Note: In Lambda, this may not be called reliably
        pass
