#!/usr/bin/env python3
"""
Database Configuration Utilities
Standard configuration and validation for database connections
"""

import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

def validate_database_environment() -> Dict[str, str]:
    """
    Validate required database environment variables
    Returns validated configuration dictionary
    """
    required_vars = [
        'DATABASE_SECRET_NAME',
        'DB_HOST',
        'DB_NAME',
        'DB_PORT'
    ]
    
    config = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            config[var] = value
    
    if missing_vars:
        error_msg = f"Missing required database environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate port is numeric
    try:
        int(config['DB_PORT'])
    except ValueError:
        raise ValueError(f"DB_PORT must be numeric, got: {config['DB_PORT']}")
    
    logger.info("Database environment variables validated successfully")
    return config

def get_standard_database_tables() -> List[str]:
    """Return list of standard database tables used by pipeline"""
    return [
        'documents',
        'processing_status',
        'text_extraction_status',
        'chunking_status',
        'nlp_processing_status',
        'vector_processing_status'
    ]

def get_database_health_check_query() -> str:
    """Return standard database health check query"""
    return "SELECT 1 as health_check"

def log_database_configuration():
    """Log current database configuration (without sensitive data)"""
    try:
        config = validate_database_environment()
        logger.info("Database Configuration:")
        logger.info(f"  Host: {config['DB_HOST']}")
        logger.info(f"  Database: {config['DB_NAME']}")
        logger.info(f"  Port: {config['DB_PORT']}")
        logger.info(f"  Secret: {config['DATABASE_SECRET_NAME']}")
        logger.info("  Connection Method: Secrets Manager")
    except Exception as e:
        logger.error(f"Failed to log database configuration: {e}")

# Standard environment variable names
STANDARD_DB_ENV_VARS = {
    'DATABASE_SECRET_NAME': 'AWS Secrets Manager secret name for database credentials',
    'DB_HOST': 'Database hostname',
    'DB_NAME': 'Database name',
    'DB_PORT': 'Database port (default: 5432)',
    'DATABASE_CONNECTION_METHOD': 'Connection method (should be: secrets_manager)'
}
