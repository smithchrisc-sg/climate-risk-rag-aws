#!/usr/bin/env python3
"""
Enhanced Database Manager for Climate Risk RAG System
Provides centralized database operations with connection pooling and error handling
"""

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from typing import Dict, List, Any, Optional, Tuple
import boto3
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Centralized database manager with connection pooling and standardized operations
    """
    
    def __init__(self):
        """Initialize database manager with connection pooling"""
        self._connection_pool = None
        self._secrets_client = boto3.client('secretsmanager')
        self._connection_params = None
        
        # Initialize connection pool
        self._initialize_connection_pool()
        
        logger.info("DatabaseManager initialized with connection pooling")
    
    def _initialize_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            # Get connection parameters
            self._connection_params = self._get_connection_params()
            
            # Create connection pool
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **self._connection_params
            )
            
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Get database connection parameters from environment and secrets"""
        try:
            # Check for direct connection method first
            connection_method = os.environ.get('DATABASE_CONNECTION_METHOD', 'secrets_manager')
            
            if connection_method == 'direct':
                # Direct connection using environment variables
                return {
                    'host': os.environ['DB_HOST'],
                    'port': int(os.environ.get('DB_PORT', 5432)),
                    'database': os.environ['DB_NAME'],
                    'user': os.environ['DB_USER'],
                    'password': os.environ['DB_PASSWORD']
                }
            else:
                # Secrets Manager connection (default)
                secret_name = os.environ.get('DATABASE_SECRET_NAME')
                if not secret_name:
                    raise ValueError("DATABASE_SECRET_NAME environment variable required")
                
                # Get secret from AWS Secrets Manager
                response = self._secrets_client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response['SecretString'])
                
                return {
                    'host': os.environ.get('DB_HOST', secret.get('host')),
                    'port': int(os.environ.get('DB_PORT', secret.get('port', 5432))),
                    'database': os.environ.get('DB_NAME', secret.get('dbname')),
                    'user': secret.get('username'),
                    'password': secret.get('password')
                }
                
        except Exception as e:
            logger.error(f"Failed to get connection parameters: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            if not self._connection_pool:
                self._initialize_connection_pool()
            
            connection = self._connection_pool.getconn()
            if connection:
                return connection
            else:
                raise Exception("Failed to get connection from pool")
                
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise
    
    def return_connection(self, connection):
        """Return a connection to the pool"""
        try:
            if self._connection_pool and connection:
                self._connection_pool.putconn(connection)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
    def get_connection_string(self) -> str:
        """Get database connection string for external libraries"""
        try:
            params = self._connection_params or self._get_connection_params()
            return f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['database']}"
        except Exception as e:
            logger.error(f"Failed to build connection string: {e}")
            raise
    
    def execute_query(self, query: str, params: Tuple = None, fetch_results: bool = True) -> List[Tuple]:
        """
        Execute a database query with connection pooling
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_results: Whether to fetch and return results
            
        Returns:
            List of result tuples if fetch_results=True, empty list otherwise
        """
        connection = None
        try:
            connection = self.get_connection()
            
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch_results:
                    results = cursor.fetchall()
                    logger.debug(f"Query executed successfully, returned {len(results)} rows")
                    return results
                else:
                    connection.commit()
                    logger.debug("Query executed successfully (no results fetched)")
                    return []
                    
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        finally:
            if connection:
                self.return_connection(connection)
    
    def execute_dict_query(self, query: str, params: Tuple = None) -> List[Dict]:
        """
        Execute a query and return results as dictionaries
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        connection = None
        try:
            connection = self.get_connection()
            
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # Convert RealDictRow to regular dict
                dict_results = [dict(row) for row in results]
                logger.debug(f"Dict query executed successfully, returned {len(dict_results)} rows")
                return dict_results
                
        except Exception as e:
            logger.error(f"Database dict query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        finally:
            if connection:
                self.return_connection(connection)
    
    def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata by doc_id
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary containing document metadata or None if not found
        """
        try:
            query = """
                SELECT doc_id, url, original_filename, pdf_path, text_path, 
                       chunking_complete, download_date, status, error_message,
                       created_at, updated_at
                FROM documents 
                WHERE doc_id = %s
            """
            
            results = self.execute_query(query, (doc_id,))
            
            if results:
                row = results[0]
                metadata = {
                    'doc_id': row[0],
                    'url': row[1],
                    'original_filename': row[2],
                    'pdf_path': row[3],
                    'text_path': row[4],
                    'chunking_complete': row[5],
                    'download_date': row[6],
                    'status': row[7],
                    'error_message': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }
                logger.debug(f"Retrieved document metadata: {doc_id}")
                return metadata
            else:
                logger.debug(f"No document metadata found for {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get document metadata: {e}")
            raise
    
    def update_document_status(self, doc_id: str, status: str, error_message: str = None):
        """
        Update document processing status
        
        Args:
            doc_id: Document ID
            status: New status
            error_message: Optional error message
        """
        try:
            query = """
                UPDATE documents 
                SET status = %s, error_message = %s, updated_at = %s
                WHERE doc_id = %s
            """
            
            self.execute_query(
                query, 
                (status, error_message, datetime.utcnow(), doc_id),
                fetch_results=False
            )
            
            logger.info(f"Updated document status: {doc_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to update document status: {e}")
            raise
    
    def store_textract_job_metadata(self, job_id: str, doc_id: str, source_bucket: str, 
                                  source_key: str, output_bucket: str = None) -> bool:
        """
        Store Textract job metadata
        
        Args:
            job_id: Textract job ID
            doc_id: Document ID
            source_bucket: S3 source bucket
            source_key: S3 source key
            output_bucket: S3 output bucket
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
                INSERT INTO textract_jobs (job_id, doc_id, source_bucket, source_key, output_bucket, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) 
                DO UPDATE SET 
                    doc_id = EXCLUDED.doc_id,
                    source_bucket = EXCLUDED.source_bucket,
                    source_key = EXCLUDED.source_key,
                    output_bucket = EXCLUDED.output_bucket,
                    updated_at = NOW()
            """
            
            self.execute_query(
                query, 
                (job_id, doc_id, source_bucket, source_key, output_bucket, 'IN_PROGRESS'),
                fetch_results=False
            )
            
            logger.info(f"Stored Textract job metadata: {job_id} -> {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store Textract job metadata: {e}")
            raise
    
    def update_textract_job_completion(self, job_id: str, status: str, 
                                     pages_processed: int = None, 
                                     blocks_extracted: int = None,
                                     files_created: Dict = None,
                                     error_message: str = None):
        """
        Update Textract job completion status
        
        Args:
            job_id: Textract job ID
            status: Job status (COMPLETED, FAILED, etc.)
            pages_processed: Number of pages processed
            blocks_extracted: Number of blocks extracted
            files_created: Dictionary of created files
            error_message: Error message if failed
        """
        try:
            query = """
                UPDATE textract_jobs 
                SET status = %s, completed_at = %s, pages_processed = %s, 
                    blocks_extracted = %s, files_created = %s, error_message = %s,
                    updated_at = %s
                WHERE job_id = %s
            """
            
            files_json = json.dumps(files_created) if files_created else None
            
            self.execute_query(
                query, 
                (status, datetime.utcnow(), pages_processed, blocks_extracted, 
                 files_json, error_message, datetime.utcnow(), job_id),
                fetch_results=False
            )
            
            logger.info(f"Updated Textract job completion: {job_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to update Textract job completion: {e}")
            raise
    
    def update_document_processing_status(self, doc_id: str, stage: str, status: str, 
                                        job_id: str = None):
        """
        Update document processing pipeline status
        
        Args:
            doc_id: Document ID (using doc_hash for compatibility)
            stage: Processing stage (text_extraction, chunking, embedding, ner)
            status: Status (PENDING, IN_PROGRESS, COMPLETED, FAILED)
            job_id: Optional job ID for text extraction
        """
        try:
            # Map stage to column names
            stage_columns = {
                'text_extraction': ('text_extraction_status', 'text_extraction_completed_at', 'text_extraction_job_id'),
                'chunking': ('chunking_status', 'chunking_completed_at', None),
                'embedding': ('embedding_status', 'embedding_completed_at', None),
                'ner': ('ner_status', 'ner_completed_at', None)
            }
            
            if stage not in stage_columns:
                raise ValueError(f"Invalid stage: {stage}")
            
            status_col, completed_col, job_col = stage_columns[stage]
            
            # Build dynamic query
            if status == 'COMPLETED':
                if job_col and job_id:
                    query = f"""
                        INSERT INTO document_processing_status (doc_hash, {status_col}, {completed_col}, {job_col})
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (doc_hash) 
                        DO UPDATE SET 
                            {status_col} = EXCLUDED.{status_col},
                            {completed_col} = EXCLUDED.{completed_col},
                            {job_col} = EXCLUDED.{job_col},
                            updated_at = NOW()
                    """
                    params = (doc_id, status, datetime.utcnow(), job_id)
                else:
                    query = f"""
                        INSERT INTO document_processing_status (doc_hash, {status_col}, {completed_col})
                        VALUES (%s, %s, %s)
                        ON CONFLICT (doc_hash) 
                        DO UPDATE SET 
                            {status_col} = EXCLUDED.{status_col},
                            {completed_col} = EXCLUDED.{completed_col},
                            updated_at = NOW()
                    """
                    params = (doc_id, status, datetime.utcnow())
            else:
                if job_col and job_id:
                    query = f"""
                        INSERT INTO document_processing_status (doc_hash, {status_col}, {job_col})
                        VALUES (%s, %s, %s)
                        ON CONFLICT (doc_hash) 
                        DO UPDATE SET 
                            {status_col} = EXCLUDED.{status_col},
                            {job_col} = EXCLUDED.{job_col},
                            updated_at = NOW()
                    """
                    params = (doc_id, status, job_id)
                else:
                    query = f"""
                        INSERT INTO document_processing_status (doc_hash, {status_col})
                        VALUES (%s, %s)
                        ON CONFLICT (doc_hash) 
                        DO UPDATE SET 
                            {status_col} = EXCLUDED.{status_col},
                            updated_at = NOW()
                    """
                    params = (doc_id, status)
            
            self.execute_query(query, params, fetch_results=False)
            
            logger.info(f"Updated document processing status: {doc_id} {stage} -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to update document processing status: {e}")
            raise
    
    def get_textract_job_metadata(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Textract job metadata
        
        Args:
            job_id: Textract job ID
            
        Returns:
            Optional[Dict]: Job metadata or None if not found
        """
        try:
            query = """
                SELECT job_id, doc_id, source_bucket, source_key, output_bucket,
                       status, started_at, completed_at, error_message,
                       pages_processed, blocks_extracted, files_created
                FROM textract_jobs 
                WHERE job_id = %s
            """
            
            results = self.execute_query(query, (job_id,))
            
            if results:
                row = results[0]
                metadata = {
                    'job_id': row[0],
                    'doc_id': row[1],
                    'source_bucket': row[2],
                    'source_key': row[3],
                    'output_bucket': row[4],
                    'status': row[5],
                    'started_at': row[6],
                    'completed_at': row[7],
                    'error_message': row[8],
                    'pages_processed': row[9],
                    'blocks_extracted': row[10],
                    'files_created': json.loads(row[11]) if row[11] else None
                }
                logger.debug(f"Retrieved Textract job metadata: {job_id}")
                return metadata
            else:
                logger.debug(f"No Textract job metadata found for {job_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get Textract job metadata: {e}")
            raise
    
    # ========================================
    # KEYWORD INDEXING METHODS
    # ========================================
    
    def update_keyword_indexing_status(self, doc_id: str, status: str, 
                                     notes: str = None, 
                                     keywords_count: int = None,
                                     opensearch_index_name: str = None,
                                     error_message: str = None) -> bool:
        """
        Update keyword indexing status for a document
        
        Args:
            doc_id: Document ID
            status: Processing status (PENDING, PROCESSING, COMPLETED, FAILED)
            notes: Optional processing notes
            keywords_count: Number of keywords extracted
            opensearch_index_name: OpenSearch index name
            error_message: Error message if failed
            
        Returns:
            True if successful
        """
        try:
            # Determine if this is a completion update
            if status == 'COMPLETED':
                query = """
                    INSERT INTO keyword_indexing_status 
                    (doc_id, status, notes, keywords_extracted, opensearch_index_name, 
                     processing_completed_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) 
                    DO UPDATE SET 
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        keywords_extracted = EXCLUDED.keywords_extracted,
                        opensearch_index_name = EXCLUDED.opensearch_index_name,
                        processing_completed_at = EXCLUDED.processing_completed_at,
                        updated_at = EXCLUDED.updated_at
                """
                params = (doc_id, status, notes, keywords_count, opensearch_index_name, 
                         datetime.utcnow(), datetime.utcnow())
            elif status == 'FAILED':
                query = """
                    INSERT INTO keyword_indexing_status 
                    (doc_id, status, notes, error_message, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) 
                    DO UPDATE SET 
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        error_message = EXCLUDED.error_message,
                        updated_at = EXCLUDED.updated_at
                """
                params = (doc_id, status, notes, error_message, datetime.utcnow())
            else:
                # PENDING or PROCESSING status
                query = """
                    INSERT INTO keyword_indexing_status 
                    (doc_id, status, notes, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (doc_id) 
                    DO UPDATE SET 
                        status = EXCLUDED.status,
                        notes = EXCLUDED.notes,
                        updated_at = EXCLUDED.updated_at
                """
                params = (doc_id, status, notes, datetime.utcnow())
            
            self.execute_query(query, params, fetch_results=False)
            
            logger.info(f"Updated keyword indexing status: {doc_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update keyword indexing status: {e}")
            raise
    
    def get_keyword_indexing_status(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get keyword indexing status for a document
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary containing keyword indexing status or None if not found
        """
        try:
            query = """
                SELECT doc_id, status, notes, opensearch_index_name, keywords_extracted,
                       processing_started_at, processing_completed_at, error_message,
                       created_at, updated_at
                FROM keyword_indexing_status 
                WHERE doc_id = %s
            """
            
            results = self.execute_query(query, (doc_id,))
            
            if results:
                row = results[0]
                status_info = {
                    'doc_id': row[0],
                    'status': row[1],
                    'notes': row[2],
                    'opensearch_index_name': row[3],
                    'keywords_extracted': row[4],
                    'processing_started_at': row[5],
                    'processing_completed_at': row[6],
                    'error_message': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                }
                logger.debug(f"Retrieved keyword indexing status: {doc_id}")
                return status_info
            else:
                logger.debug(f"No keyword indexing status found for {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get keyword indexing status: {e}")
            raise
    
    def get_documents_for_keyword_indexing(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get documents that are ready for keyword indexing (text extraction completed)
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            List of document dictionaries ready for keyword indexing
        """
        try:
            query = """
                SELECT DISTINCT dps.doc_hash as doc_id, dps.filename, 
                       dps.source_bucket, dps.source_key,
                       dps.text_extraction_completed_at
                FROM document_processing_status dps
                LEFT JOIN keyword_indexing_status kis ON dps.doc_hash = kis.doc_id
                WHERE dps.text_extraction_status = 'COMPLETED'
                  AND (kis.status IS NULL OR kis.status IN ('PENDING', 'FAILED'))
                ORDER BY dps.text_extraction_completed_at ASC
                LIMIT %s
            """
            
            results = self.execute_query(query, (limit,))
            
            documents = []
            for row in results:
                doc_info = {
                    'doc_id': row[0],
                    'filename': row[1],
                    'source_bucket': row[2],
                    'source_key': row[3],
                    'text_extraction_completed_at': row[4]
                }
                documents.append(doc_info)
            
            logger.info(f"Found {len(documents)} documents ready for keyword indexing")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get documents for keyword indexing: {e}")
            raise
    
    def get_keyword_indexing_statistics(self) -> Dict[str, Any]:
        """
        Get keyword indexing processing statistics
        
        Returns:
            Dictionary containing processing statistics
        """
        try:
            query = """
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(keywords_extracted) as avg_keywords,
                    AVG(EXTRACT(EPOCH FROM (processing_completed_at - processing_started_at))/60) as avg_processing_time_minutes
                FROM keyword_indexing_status 
                WHERE processing_started_at IS NOT NULL
                GROUP BY status
            """
            
            results = self.execute_query(query)
            
            stats = {}
            for row in results:
                stats[row[0]] = {
                    'count': row[1],
                    'avg_keywords': float(row[2]) if row[2] else 0,
                    'avg_processing_time_minutes': float(row[3]) if row[3] else 0
                }
            
            logger.debug("Retrieved keyword indexing statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get keyword indexing statistics: {e}")
            raise
