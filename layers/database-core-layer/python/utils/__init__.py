"""
Database Core Layer Utilities
Clean, focused database access for climate risk RAG pipeline
"""

from .DatabaseManager import DatabaseManager
from .DocumentIDManager import DocumentIDManager
from .database_config import (
    validate_database_environment,
    get_standard_database_tables,
    get_database_health_check_query,
    log_database_configuration,
    STANDARD_DB_ENV_VARS
)

__version__ = "1.0.0"
__all__ = [
    'DatabaseManager',
    'DocumentIDManager',
    'validate_database_environment',
    'get_standard_database_tables', 
    'get_database_health_check_query',
    'log_database_configuration',
    'STANDARD_DB_ENV_VARS'
]
