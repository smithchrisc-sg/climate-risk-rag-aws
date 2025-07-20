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
            # Default to all major tables if none specified
            default_tables = [
                'documents',
                'document_metadata', 
                'document_processing_status',
                'nlp_processing_status',
                'vector_embeddings_status',
                'keyword_indexing_status',
                'text_chunking_status',
                'textract_jobs',
                'chunks'
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
        # Map table names to their actual names and document ID columns
        table_mappings = {
            'document_processing_status': ('document_processing_status', 'doc_hash'),  # Uses doc_hash, not doc_id
            'nlp_processing_status': ('nlp_processing_status', 'doc_id'),
            'vector_processing_status': ('vector_embeddings_status', 'doc_id'),  # Actual table name
            'keyword_processing_status': ('keyword_indexing_status', 'doc_id'),  # Actual table name
            'kg_processing_status': ('text_chunking_status', 'doc_id'),  # Closest equivalent
            # Additional tables found in database
            'documents': ('documents', 'doc_id'),
            'document_metadata': ('document_metadata', 'doc_id'),
            'textract_jobs': ('textract_jobs', 'doc_hash'),
            'chunks': ('chunks', 'doc_id'),
            # Direct table name mappings (for when user specifies actual table names)
            'vector_embeddings_status': ('vector_embeddings_status', 'doc_id'),
            'keyword_indexing_status': ('keyword_indexing_status', 'doc_id'),
            'text_chunking_status': ('text_chunking_status', 'doc_id')
        }
        
        # Get actual table name and column
        if table_name in table_mappings:
            actual_table, doc_column = table_mappings[table_name]
        else:
            # Default assumption - use table name as-is with doc_id column
            actual_table = table_name
            doc_column = 'doc_id'
            logger.warning(f"Table {table_name} not in mappings, using default: {actual_table}.{doc_column}")
        
        logger.info(f"Cleaning table {actual_table} using column {doc_column}, dry_run={dry_run}")
        
        try:
            # Build query based on whether specific document IDs are provided
            if document_ids:
                # Clean specific documents
                if dry_run:
                    query = f"SELECT COUNT(*) as count FROM {actual_table} WHERE {doc_column} = ANY(%s)"
                    logger.debug(f"Executing count query: {query} with params: {document_ids}")
                    cursor.execute(query, (document_ids,))
                    result = cursor.fetchone()
                    count = result['count'] if result else 0
                    logger.info(f"Found {count} records in {actual_table} for specific documents")
                    return count
                else:
                    query = f"DELETE FROM {actual_table} WHERE {doc_column} = ANY(%s)"
                    logger.debug(f"Executing delete query: {query} with params: {document_ids}")
                    cursor.execute(query, (document_ids,))
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} records from {actual_table}")
                    return deleted
            else:
                # Clean all records
                if dry_run:
                    query = f"SELECT COUNT(*) as count FROM {actual_table}"
                    logger.debug(f"Executing count query: {query}")
                    cursor.execute(query)
                    result = cursor.fetchone()
                    count = result['count'] if result else 0
                    logger.info(f"Found {count} total records in {actual_table}")
                    return count
                else:
                    query = f"DELETE FROM {actual_table}"
                    logger.debug(f"Executing delete query: {query}")
                    cursor.execute(query)
                    deleted = cursor.rowcount
                    logger.info(f"Deleted {deleted} records from {actual_table}")
                    return deleted
                    
        except Exception as e:
            error_msg = f"Error executing query on {actual_table}: {str(e)}"
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
