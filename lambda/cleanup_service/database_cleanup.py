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

logger = logging.getLogger(__name__)

class DatabaseCleanup:
    """Handles PostgreSQL database cleanup operations"""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
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
            # Get configuration
            tables = config.get('tables', ['document_processing_status', 'nlp_processing_status'])
            document_ids = config.get('document_ids', [])
            
            # Connect to database
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    
                    # Clean up each specified table
                    for table in tables:
                        try:
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
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                            results['success'] = False
                    
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
        # Validate table name to prevent SQL injection
        allowed_tables = [
            'document_processing_status',
            'nlp_processing_status',
            'vector_processing_status',
            'keyword_processing_status',
            'kg_processing_status'
        ]
        
        if table_name not in allowed_tables:
            raise ValueError(f"Table {table_name} is not allowed for cleanup")
        
        # Build query based on whether specific document IDs are provided
        if document_ids:
            # Clean specific documents
            if dry_run:
                query = f"SELECT COUNT(*) FROM {table_name} WHERE document_id = ANY(%s)"
                cursor.execute(query, (document_ids,))
                return cursor.fetchone()[0]
            else:
                query = f"DELETE FROM {table_name} WHERE document_id = ANY(%s)"
                cursor.execute(query, (document_ids,))
                return cursor.rowcount
        else:
            # Clean all records
            if dry_run:
                query = f"SELECT COUNT(*) FROM {table_name}"
                cursor.execute(query)
                return cursor.fetchone()[0]
            else:
                query = f"DELETE FROM {table_name}"
                cursor.execute(query)
                return cursor.rowcount
    
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
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    status['connection_status'] = 'connected'
                    
                    # Get record counts for key tables
                    tables = [
                        'document_processing_status',
                        'nlp_processing_status',
                        'vector_processing_status',
                        'keyword_processing_status',
                        'kg_processing_status'
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
                'document_processing_status',
                'nlp_processing_status',
                'vector_processing_status',
                'keyword_processing_status',
                'kg_processing_status'
            ]
        
        results = {
            'success': True,
            'tables_vacuumed': [],
            'errors': []
        }
        
        try:
            # Note: VACUUM cannot be run inside a transaction block
            conn = psycopg2.connect(self.database_url)
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
