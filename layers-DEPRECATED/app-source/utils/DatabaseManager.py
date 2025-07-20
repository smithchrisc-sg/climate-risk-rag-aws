#!/usr/bin/env python3
"""
DatabaseManager - Core Database Layer
Clean, focused database connection and operations manager
Uses ONLY Secrets Manager for authentication
"""

import os
import json
import logging
import psycopg2
import psycopg2.pool
import boto3
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Core database manager for PostgreSQL connections
    Uses AWS Secrets Manager for authentication
    Thread-safe connection pooling
    """
    
    _connection_pool = None
    _instance = None
    
    def __init__(self):
        """Initialize DatabaseManager with Secrets Manager authentication"""
        self.secret_name = os.environ.get('DATABASE_SECRET_NAME')
        self.db_host = os.environ.get('DB_HOST')
        self.db_name = os.environ.get('DB_NAME')
        self.db_port = os.environ.get('DB_PORT', '5432')
        
        if not all([self.secret_name, self.db_host, self.db_name]):
            raise ValueError("Missing required database environment variables")
        
        self._secrets_client = boto3.client('secretsmanager')
        self._credentials = None
        
        logger.info("DatabaseManager initialized with Secrets Manager authentication")
    
    def _get_database_credentials(self) -> Dict[str, str]:
        """Get database credentials from AWS Secrets Manager"""
        if self._credentials is None:
            try:
                response = self._secrets_client.get_secret_value(SecretId=self.secret_name)
                secret_data = json.loads(response['SecretString'])
                self._credentials = {
                    'username': secret_data.get('username', 'postgres'),
                    'password': secret_data['password']
                }
                logger.info("Database credentials retrieved from Secrets Manager")
            except Exception as e:
                logger.error(f"Failed to retrieve database credentials: {e}")
                raise
        
        return self._credentials
    
    def get_connection_string(self) -> str:
        """Build PostgreSQL connection string using Secrets Manager credentials"""
        creds = self._get_database_credentials()
        return (
            f"postgresql://{creds['username']}:{creds['password']}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?sslmode=require"
        )
    
    def _ensure_connection_pool(self):
        """Ensure connection pool is initialized"""
        if DatabaseManager._connection_pool is None:
            try:
                connection_string = self.get_connection_string()
                DatabaseManager._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=connection_string
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection from pool (context manager)"""
        self._ensure_connection_pool()
        connection = None
        try:
            connection = DatabaseManager._connection_pool.getconn()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                DatabaseManager._connection_pool.putconn(connection)
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
    
    def execute_batch(self, query: str, params_list: list) -> int:
        """Execute batch INSERT/UPDATE operations"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    logger.info("Database connection test successful")
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def close_pool(self):
        """Close connection pool"""
        if DatabaseManager._connection_pool:
            DatabaseManager._connection_pool.closeall()
            DatabaseManager._connection_pool = None
            logger.info("Database connection pool closed")
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ========================================
    # Textract-related Database Operations
    # ========================================
    
    def store_textract_job_metadata(self, job_id: str, doc_id: str, source_bucket: str, 
                                   source_key: str, output_bucket: str) -> bool:
        """
        Store Textract job metadata using existing schema
        
        Args:
            job_id: Textract job ID
            doc_id: Document ID (consistent with DocumentIDManager)
            source_bucket: S3 source bucket name
            source_key: S3 source key
            output_bucket: S3 output bucket name
            
        Returns:
            bool: True if successful
        """
        try:
            query = """
                INSERT INTO textract_jobs (
                    job_id, doc_id, source_bucket, source_key, output_bucket, 
                    status, started_at, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    doc_id = EXCLUDED.doc_id,
                    source_bucket = EXCLUDED.source_bucket,
                    source_key = EXCLUDED.source_key,
                    output_bucket = EXCLUDED.output_bucket,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """
            
            now = datetime.utcnow()
            params = (job_id, doc_id, source_bucket, source_key, output_bucket, 
                     'IN_PROGRESS', now, now, now)
            
            rows_affected = self.execute_update(query, params)
            logger.info(f"Stored Textract job metadata: {job_id} -> {doc_id}")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Failed to store Textract job metadata: {e}")
            raise
    
    def update_document_processing_status(self, doc_id: str, filename: str, source_bucket: str, 
                                        source_key: str, text_extraction_status: str = 'IN_PROGRESS', 
                                        text_extraction_job_id: str = None) -> bool:
        """
        Update document processing status using existing schema
        
        Args:
            doc_id: Document ID (consistent with DocumentIDManager)
            filename: Original filename
            source_bucket: S3 source bucket name
            source_key: S3 source key
            text_extraction_status: Status of text extraction
            text_extraction_job_id: Associated Textract job ID
            
        Returns:
            bool: True if successful
        """
        try:
            query = """
                INSERT INTO document_processing_status (
                    doc_id, filename, source_bucket, source_key, 
                    text_extraction_status, text_extraction_job_id, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    source_bucket = EXCLUDED.source_bucket,
                    source_key = EXCLUDED.source_key,
                    text_extraction_status = EXCLUDED.text_extraction_status,
                    text_extraction_job_id = EXCLUDED.text_extraction_job_id,
                    updated_at = EXCLUDED.updated_at
            """
            
            now = datetime.utcnow()
            params = (doc_id, filename, source_bucket, source_key, 
                     text_extraction_status, text_extraction_job_id, now, now)
            
            rows_affected = self.execute_update(query, params)
            logger.info(f"Updated document processing status: {doc_id} -> {text_extraction_status}")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Failed to update document processing status: {e}")
            raise
    
    def get_text_extraction_status(self, doc_id: str) -> Optional[str]:
        """
        Get current text extraction status for a document
        
        Args:
            doc_id: Document ID (consistent with DocumentIDManager)
            
        Returns:
            Optional[str]: Current text extraction status or None if not found
        """
        try:
            query = """
                SELECT text_extraction_status 
                FROM document_processing_status 
                WHERE doc_id = %s
            """
            
            results = self.execute_query(query, (doc_id,))
            
            if results:
                status = results[0][0]
                logger.debug(f"Text extraction status for {doc_id}: {status}")
                return status
            else:
                logger.debug(f"No text extraction status found for {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get text extraction status: {e}")
            raise
    
    def update_textract_job_completion(self, job_id: str, status: str, 
                                     pages_processed: int = None, blocks_extracted: int = None,
                                     error_message: str = None, files_created: dict = None) -> bool:
        """
        Update Textract job completion status
        
        Args:
            job_id: Textract job ID
            status: Final job status (COMPLETED, FAILED, etc.)
            pages_processed: Number of pages processed
            blocks_extracted: Number of text blocks extracted
            error_message: Error message if failed
            files_created: JSON object of created files
            
        Returns:
            bool: True if successful
        """
        try:
            query = """
                UPDATE textract_jobs 
                SET status = %s, completed_at = %s, pages_processed = %s, 
                    blocks_extracted = %s, error_message = %s, files_created = %s,
                    updated_at = %s
                WHERE job_id = %s
            """
            
            now = datetime.utcnow()
            files_json = json.dumps(files_created) if files_created else None
            
            params = (status, now, pages_processed, blocks_extracted, 
                     error_message, files_json, now, job_id)
            
            rows_affected = self.execute_update(query, params)
            logger.info(f"Updated Textract job completion: {job_id} -> {status}")
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Failed to update Textract job completion: {e}")
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
                    'doc_id': row[1],  # Updated from doc_hash to doc_id
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
