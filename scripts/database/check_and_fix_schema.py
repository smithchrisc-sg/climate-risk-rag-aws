#!/usr/bin/env python3
"""
Check database schema and fix missing columns
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_schema():
    """Check current database schema"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use pipeline test function to check database
    payload = {
        "action": "test",
        "test_config": {
            "test_name": "schema_check",
            "check_schema": True
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info("=== SCHEMA CHECK RESULT ===")
        logger.info(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def fix_schema():
    """Add missing columns to document_processing_status table"""
    logger.info("🔧 Adding missing columns to document_processing_status table...")
    
    # We need to add the missing columns. Let me create a simple Lambda function call
    # that executes the ALTER TABLE statements
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use the pipeline test function to execute SQL
    payload = {
        "action": "test", 
        "test_config": {
            "test_name": "schema_migration",
            "sql_commands": [
                """
                ALTER TABLE document_processing_status 
                ADD COLUMN IF NOT EXISTS textract_job_id VARCHAR(255),
                ADD COLUMN IF NOT EXISTS text_extraction_completed_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS text_s3_key VARCHAR(500),
                ADD COLUMN IF NOT EXISTS error_message TEXT
                """
            ]
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info("=== SCHEMA MIGRATION RESULT ===")
        logger.info(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    logger.info("🔍 Checking database schema...")
    check_result = check_schema()
    
    logger.info("\\n🔧 Attempting to fix schema...")
    fix_result = fix_schema()
    
    if fix_result:
        logger.info("\\n✅ Schema migration attempted")
    else:
        logger.error("\\n❌ Schema migration failed")
