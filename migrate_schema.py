#!/usr/bin/env python3
"""
Database Schema Migration Script
Add missing columns to document_processing_status table
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_schema():
    """Migrate database schema by invoking a Lambda function that can execute SQL"""
    
    # Create a simple Lambda payload that will trigger database connection
    # and hopefully show us the current schema
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # First, let's see what the current table structure looks like
    logger.info("🔍 Checking current table structure...")
    
    # Use cleanup service to see what columns it expects vs what exists
    cleanup_payload = {
        "cleanup_scope": {
            "databases": {
                "postgresql": {
                    "enabled": True,
                    "tables": ["document_processing_status"],
                    "document_ids": []
                }
            }
        },
        "safety_checks": {
            "require_confirmation": False,
            "dry_run": True,  # Just check, don't actually delete
            "max_documents_to_delete": 1
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(cleanup_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== CLEANUP SERVICE SCHEMA CHECK ===")
        logger.info(json.dumps(result, indent=2))
        
        # The error will tell us what columns are missing
        if not result.get('success'):
            error = result.get('error', '')
            if 'column' in error and 'does not exist' in error:
                logger.info("✅ Found schema issue in cleanup service too")
            
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def create_migration_lambda():
    """Create a simple Lambda function to execute schema migration"""
    
    # Instead of creating a new Lambda, let's use the existing pipeline test function
    # and see if we can get it to show us the table structure
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Try to get table info
    payload = {
        "action": "health_check"  # This should connect to database
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== PIPELINE TEST DATABASE CONNECTION ===")
        logger.info(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    logger.info("🔧 Database Schema Migration")
    logger.info("Checking for missing columns in document_processing_status table")
    
    logger.info("\\n1. Checking cleanup service...")
    cleanup_result = migrate_schema()
    
    logger.info("\\n2. Checking pipeline test function...")
    pipeline_result = create_migration_lambda()
    
    logger.info("\\n📋 ANALYSIS:")
    logger.info("The text extraction functions expect these columns in document_processing_status:")
    logger.info("- textract_job_id (VARCHAR)")
    logger.info("- text_extraction_completed_at (TIMESTAMP)")
    logger.info("- text_s3_key (VARCHAR)")
    logger.info("- error_message (TEXT)")
    logger.info("\\nThese columns need to be added to the database schema.")
    logger.info("\\n🔧 SOLUTION:")
    logger.info("Run this SQL against the database:")
    logger.info("""
    ALTER TABLE document_processing_status 
    ADD COLUMN IF NOT EXISTS textract_job_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS text_extraction_completed_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS text_s3_key VARCHAR(500),
    ADD COLUMN IF NOT EXISTS error_message TEXT;
    """)
