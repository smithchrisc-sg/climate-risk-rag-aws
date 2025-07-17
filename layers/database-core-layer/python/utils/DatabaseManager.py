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
