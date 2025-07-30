"""
PostgreSQL Database Cleanup Module
Handles cleanup of document processing status and related database records
"""

import logging
import os
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Import DatabaseManager from layer
try:
    from utils.DatabaseManager import DatabaseManager
except ImportError:
    # Fallback for local testing
    import sys
    sys.path.append('/opt/python')
    from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add debug logging if in Lambda environment
if os.environ.get('LAMBDA_ENVIRONMENT'):
    logger.setLevel(logging.DEBUG)

class DatabaseCleanup:
    """Handles PostgreSQL database cleanup operations"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def cleanup_postgresql(self, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up PostgreSQL database records
        
        Args:
            config: PostgreSQL cleanup configuration
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dict containing cleanup results
        """
        logger.info(f"Starting PostgreSQL cleanup. Dry run: {dry_run}")
        
        results = {
            'success': True,
            'operations_performed': [],
            'records_affected': {},
            'errors': []
        }
        
        try:
            # Default to all tables if none specified
            default_tables = [
                'documents',
                'document_processing_status'
            ]
            
            tables = config.get('tables', default_tables)
            document_ids = config.get('document_ids', [])
            
            # Connect to database using DatabaseManager
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    
                    # Clean up each specified table
                    for table in tables:
                        try:
                            logger.info(f"Starting cleanup for table: {table}")
                            affected_count = self._cleanup_table(
                                cursor, table, document_ids, dry_run
                            )
                            
                            results['records_affected'][table] = affected_count
                            results['operations_performed'].append({
                                'operation': 'delete_records',
                                'table': table,
                                'document_ids': document_ids if document_ids else 'all',
                                'records_affected': affected_count,
                                'dry_run': dry_run
                            })
                            
                            logger.info(f"Table {table}: {affected_count} records {'would be' if dry_run else ''} deleted")
                            
                        except Exception as e:
                            error_msg = f"Failed to clean table {table}: {str(e)}"
                            logger.error(error_msg, exc_info=True)
                            results['errors'].append(error_msg)
                            results['success'] = False
                            # Continue with other tables even if one fails
                    
                    # Commit changes if not dry run
                    if not dry_run and results['success']:
                        conn.commit()
                        logger.info("Database cleanup committed successfully")
                    elif dry_run:
                        conn.rollback()
                        logger.info("Dry run completed - no changes committed")
                    else:
                        conn.rollback()
                        logger.error("Cleanup failed - changes rolled back")
        
        except Exception as e:
            error_msg = f"Database connection or operation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _cleanup_table(self, cursor, table_name: str, document_ids: List[str], dry_run: bool) -> int:
        """
        Clean up a specific table
        
        Args:
            cursor: Database cursor
            table_name: Name of table to clean
            document_ids: List of specific document IDs to delete (empty = all)
            dry_run: If True, only count records
            
        Returns:
            Number of records affected
        """
        
        try:
            # Build query based on whether specific document IDs are provided
            if document_ids:
                # Clean specific documents
                if dry_run:
                    query = f"SELECT COUNT(*) as count FROM {table_name} WHERE doc_id = ANY(%s)"
                    logger.debug(f"Executing count query: {query} with params: {document_ids}")
                    cursor.execute(query, (document_ids,))
                    result = cursor.fetchone()
                    count = result['count'] if result else 0
                    logger.info(f"Found {count} records in {table_name} for specific documents")
                    return count
                else:
                    query = f"DELETE FROM {table_name} WHERE doc_id = ANY(%s)"
                    logger.debug(f"Executing delete query: {query} with params: {document_ids}")
                    cursor.execute(query, (document_ids,))
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} records from {table_name}")
                    return deleted
            else:
                # Clean all records
                if dry_run:
                    query = f"SELECT COUNT(*) as count FROM {table_name}"
                    logger.debug(f"Executing count query: {query}")
                    cursor.execute(query)
                    result = cursor.fetchone()
                    count = result['count'] if result else 0
                    logger.info(f"Found {count} total records in {table_name}")
                    return count
                else:
                    query = f"DELETE FROM {table_name}"
                    logger.debug(f"Executing delete query: {query}")
                    cursor.execute(query)
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} records from {table_name}")
                    return deleted
                    
        except Exception as e:
            error_msg = f"Error executing query on {table_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
    
    def get_database_status(self) -> Dict[str, Any]:
        """
        Get current database status for reporting
        
        Returns:
            Dict containing database status information
        """
        status = {
            'connection_status': 'unknown',
            'table_counts': {},
            'errors': []
        }
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    status['connection_status'] = 'connected'
                    
                    # Get record counts for key tables
                    tables = [
                        'documents',
                        'document_processing_status'
                    ]
                    
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cursor.fetchone()[0]
                            status['table_counts'][table] = count
                        except Exception as e:
                            # Table might not exist, which is okay
                            status['table_counts'][table] = f"Error: {str(e)}"
                    
        except Exception as e:
            status['connection_status'] = 'failed'
            status['errors'].append(f"Database connection failed: {str(e)}")
        
        return status
    
    def vacuum_tables(self, tables: List[str] = None) -> Dict[str, Any]:
        """
        Vacuum specified tables to reclaim space after cleanup
        
        Args:
            tables: List of tables to vacuum (default: all main tables)
            
        Returns:
            Dict containing vacuum results
        """
        if tables is None:
            tables = [
                'documents',
                'document_processing_status'
            ]
        
        results = {
            'success': True,
            'tables_vacuumed': [],
            'errors': []
        }
        
        try:
            # Note: VACUUM cannot be run inside a transaction block
            conn = self.db_manager.get_raw_connection()
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                for table in tables:
                    try:
                        logger.info(f"Vacuuming table {table}")
                        cursor.execute(f"VACUUM ANALYZE {table}")
                        results['tables_vacuumed'].append(table)
                    except Exception as e:
                        error_msg = f"Failed to vacuum table {table}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['success'] = False
            
            conn.close()
            
        except Exception as e:
            error_msg = f"Vacuum operation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
