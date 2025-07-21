"""
Configuration module for Text Extraction Processor
Centralizes environment variable handling and configuration
"""

import os
from typing import Optional

class Config:
    """Configuration class for Text Extraction Processor"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        
        # Required environment variables
        self.output_bucket = self._get_required_env('OUTPUT_BUCKET')
        
        # Database configuration (handled by DatabaseManager layer)
        self.database_secret_name = self._get_required_env('DATABASE_SECRET_NAME')
        self.db_host = self._get_required_env('DB_HOST')
        self.db_name = self._get_required_env('DB_NAME')
        self.db_port = os.environ.get('DB_PORT', '5432')
        self.database_connection_method = os.environ.get('DATABASE_CONNECTION_METHOD', 'secrets_manager')
        
        # SNS Topics
        self.text_extraction_complete_topic_arn = os.environ.get(
            'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN',
            'arn:aws:sns:us-east-1:861276078413:text-extraction-complete'
        )
        
        # Optional buckets
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET')
        self.chunks_ready_topic_arn = os.environ.get('CHUNKS_READY_TOPIC_ARN')
        
        # Processing configuration
        self.max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        self.timeout_seconds = int(os.environ.get('TIMEOUT_SECONDS', '300'))
        
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def get_s3_config(self) -> dict:
        """Get S3-related configuration"""
        return {
            'output_bucket': self.output_bucket,
            'text_bucket': self.text_bucket,
            'chunks_bucket': self.chunks_bucket
        }
    
    def get_messaging_config(self) -> dict:
        """Get messaging-related configuration"""
        return {
            'text_extraction_complete_topic_arn': self.text_extraction_complete_topic_arn,
            'chunks_ready_topic_arn': self.chunks_ready_topic_arn
        }
    
    def get_database_config(self) -> dict:
        """Get database-related configuration"""
        return {
            'secret_name': self.database_secret_name,
            'host': self.db_host,
            'name': self.db_name,
            'port': self.db_port,
            'connection_method': self.database_connection_method
        }
