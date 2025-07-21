#!/usr/bin/env python3
"""
Schema Migration Lambda Function
Add missing columns to document_processing_status table
"""

import json
import logging
from utils.DatabaseManager import DatabaseManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda handler to execute schema migration
    """
    try:
        logger.info("🔧 Starting schema migration...")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # SQL to add missing columns
        migration_sql = """
        ALTER TABLE document_processing_status 
        ADD COLUMN IF NOT EXISTS textract_job_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS text_extraction_completed_at TIMESTAMP,
        ADD COLUMN IF NOT EXISTS text_s3_key VARCHAR(500),
        ADD COLUMN IF NOT EXISTS error_message TEXT;
        """
        
        # Execute migration
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                logger.info("Executing schema migration SQL...")
                cursor.execute(migration_sql)
                conn.commit()
                logger.info("✅ Schema migration completed successfully")
        
        # Verify the migration by checking table structure
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'document_processing_status'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                column_info = [{'name': col[0], 'type': col[1]} for col in columns]
                
                logger.info("✅ Current table structure:")
                for col in column_info:
                    logger.info(f"   {col['name']}: {col['type']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'message': 'Schema migration completed successfully',
                'columns_added': [
                    'textract_job_id',
                    'text_extraction_completed_at', 
                    'text_s3_key',
                    'error_message'
                ],
                'table_structure': column_info
            })
        }
        
    except Exception as e:
        logger.error(f"❌ Schema migration failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
