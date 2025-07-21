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
    
    
    def get_document_exists(self, doc_id: str) -> bool:
        """
        Check if document exists in the database
        """
        try:
            query = """
                SELECT EXISTS(SELECT 1 FROM documents WHERE doc_id = %s)
            """

            results = self.execute_query(query, (doc_id,))
            return results[0][0]

        except Exception as e:
            logger.error(f"Failed to check if document exists: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by doc_id
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary containing document or None if not found
        """

        try:
            query = """
                SELECT doc_id, source_url, original_filename, file_size_bytes, file_hash, created_at, updated_at
                FROM documents 
                WHERE doc_id = %s
            """
            
            results = self.execute_query(query, (doc_id,))
            
            if results:
                row = results[0]
                document = {
                    'doc_id': row[0],
                    'source_url': row[1],
                    'original_filename': row[2],
                    'file_size_bytes': row[3],
                    'file_hash': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
                logger.debug(f"Retrieved document: {doc_id}")
                return document
            else:
                logger.debug(f"No document found for {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise

    def add_or_update_document(self, doc_id: str, source_url: str, original_filename: str, file_size_bytes: int, file_hash: str):
        """
        Add new document or update existing document based on file hash comparison.
        
        For repository rescans:
        - If document doesn't exist: INSERT new document
        - If document exists with same hash: UPDATE only updated_at (document seen again)
        - If document exists with different hash: UPDATE all fields (content changed)
        
        This preserves the original created_at timestamp while tracking rescan activity.
        """
        try:
            # Check if document already exists
            existing_doc = self.get_document(doc_id)
            
            if existing_doc:
                # Document exists - check if content has changed
                if existing_doc['file_hash'] == file_hash:
                    # Same content - just update rescan timestamp
                    query = """
                        UPDATE documents 
                        SET updated_at = CURRENT_TIMESTAMP 
                        WHERE doc_id = %s
                    """
                    self.execute_query(query, (doc_id,), fetch_results=False)
                    logger.info(f"Document rescan - no changes: {doc_id}")
                else:
                    # Content changed - update all fields but preserve created_at
                    query = """
                        UPDATE documents 
                        SET source_url = %s, 
                            original_filename = %s, 
                            file_size_bytes = %s, 
                            file_hash = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE doc_id = %s
                    """
                    self.execute_query(query, (source_url, original_filename, file_size_bytes, file_hash, doc_id), fetch_results=False)
                    logger.info(f"Document updated - content changed: {doc_id}")
            else:
                # New document - insert normally
                query = """
                    INSERT INTO documents (doc_id, source_url, original_filename, file_size_bytes, file_hash)   
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.execute_query(query, (doc_id, source_url, original_filename, file_size_bytes, file_hash), fetch_results=False)
                logger.info(f"Added new document: {doc_id}")

        except Exception as e:
            logger.error(f"Failed to add or update document: {e}")
            raise   
    
    def set_processing_status(self, doc_id: str, stage: str, status: str, error_message: str = None, system_id: str = None, retry_count: int = 0, metadata: Dict[str, Any] = None):
        """
        Set document processing status

        Args:
            doc_id: Document ID
            stage: Processing stage
            status: Processing status
            error_message: Optional error message
            system_id: Optional system ID
            retry_count: Optional retry count


        This is an insert only operation. Multiple rows can be inserted for the same doc_id.

        CREATE TABLE document_processing_status (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(32) REFERENCES documents(doc_id) ON DELETE CASCADE,
            stage VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT,
            system_id VARCHAR(100),
            retry_count INTEGER DEFAULT 0,
            metadata JSONB,

        """
        try:
            query = """
                INSERT INTO document_processing_status (doc_id, stage, status, error_message, system_id, retry_count, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            self.execute_query(
                query, 
                (doc_id, stage, status, error_message, system_id, retry_count, metadata),
                fetch_results=False
            )
            
            logger.info(f"Set document processing status: {doc_id} -> {stage} -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to set document processing status: {e}")
            raise

