#!/usr/bin/env python3
"""
Environment Configuration for Solution Ingestion
Manages environment variables and configuration settings.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Environment:
    """Environment configuration manager."""
    
    def __init__(self):
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables."""
        
        # Database configuration
        self.database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require'
        )
        
        # OpenSearch configuration
        self.opensearch_endpoint = os.getenv(
            'OPENSEARCH_ENDPOINT',
            'https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com'
        )
        self.opensearch_username = os.getenv('OPENSEARCH_USERNAME', 'admin')
        self.opensearch_password = os.getenv('OPENSEARCH_PASSWORD', 'veqpat-kegba2-zapbyZ')
        
        # Neptune configuration
        self.neptune_endpoint = os.getenv(
            'NEPTUNE_ENDPOINT',
            'solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com'
        )
        self.neptune_port = os.getenv('NEPTUNE_PORT', '8182')
        
        # AWS configuration
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # S3 bucket configuration (for data lake simulation)
        self.text_bucket = os.getenv('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        self.chunks_bucket = os.getenv('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.ttl_bucket = os.getenv('TTL_BUCKET', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
        
        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        logger.info("Environment configuration loaded")
        self._log_config()
    
    def _log_config(self):
        """Log configuration (without sensitive data)."""
        logger.debug("Configuration:")
        logger.debug(f"  Database: {self._mask_url(self.database_url)}")
        logger.debug(f"  OpenSearch: {self.opensearch_endpoint}")
        logger.debug(f"  Neptune: {self.neptune_endpoint}:{self.neptune_port}")
        logger.debug(f"  AWS Region: {self.aws_region}")
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive parts of URLs for logging."""
        if '://' in url and '@' in url:
            protocol, rest = url.split('://', 1)
            if '@' in rest:
                creds, host_part = rest.split('@', 1)
                return f"{protocol}://***:***@{host_part}"
        return url
    
    def get_neptune_sparql_endpoint(self) -> str:
        """Get Neptune SPARQL endpoint URL."""
        return f"https://{self.neptune_endpoint}:{self.neptune_port}/sparql"
    
    def validate_config(self) -> bool:
        """Validate that required configuration is present."""
        required_vars = [
            ('DATABASE_URL', self.database_url),
            ('OPENSEARCH_ENDPOINT', self.opensearch_endpoint),
            ('NEPTUNE_ENDPOINT', self.neptune_endpoint)
        ]
        
        missing = []
        for var_name, value in required_vars:
            if not value or value.strip() == '':
                missing.append(var_name)
        
        if missing:
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return False
        
        logger.info("Configuration validation passed")
        return True