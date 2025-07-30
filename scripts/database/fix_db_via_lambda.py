#!/usr/bin/env python3
"""
Fix Database Schema via Lambda Function
Uses existing Lambda function to execute database fixes
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_via_lambda():
    """Use an existing Lambda function to fix the database schema"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Use the text chunker function to execute database fix
    function_name = "text-chunker-pipeline"
    
    # Create a payload that will trigger the database fix
    payload = {
        "action": "fix_database_schema",
        "sql_commands": [
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'text_chunking_status') THEN
                    IF NOT EXISTS (SELECT FROM information_schema.columns 
                                  WHERE table_name = 'text_chunking_status' 
                                  AND column_name = 'chunks_count') THEN
                        ALTER TABLE text_chunking_status ADD COLUMN chunks_count INTEGER DEFAULT 0;
                        RAISE NOTICE 'Added chunks_count column';
                    ELSE
                        RAISE NOTICE 'chunks_count column already exists';
                    END IF;
                ELSE
                    CREATE TABLE text_chunking_status (
                        doc_id VARCHAR(255) PRIMARY KEY,
                        status VARCHAR(50) NOT NULL,
                        chunks_count INTEGER DEFAULT 0,
                        message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    RAISE NOTICE 'Created text_chunking_status table';
                END IF;
            END
            $$;
            """
        ]
    }
    
    try:
        logger.info(f"Invoking {function_name} to fix database schema...")
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Lambda response: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to fix database via Lambda: {e}")
        raise

if __name__ == "__main__":
    fix_database_via_lambda()
