#!/usr/bin/env python3
"""
Verify and Fix Database Schema
Ensure text_chunking_status table exists with correct columns
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_and_fix_database_schema():
    """Use Lambda to verify and fix database schema"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create SQL to check and fix schema
    schema_fix_sql = """
    -- Check if text_chunking_status table exists and create/fix it
    DO $$
    BEGIN
        -- Check if table exists
        IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'text_chunking_status') THEN
            -- Create table with correct schema (matching original working version)
            CREATE TABLE text_chunking_status (
                doc_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50) NOT NULL,
                chunks_created INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            RAISE NOTICE 'Created text_chunking_status table with chunks_created column';
        ELSE
            -- Table exists, check if it has the correct columns
            IF NOT EXISTS (SELECT FROM information_schema.columns 
                          WHERE table_name = 'text_chunking_status' 
                          AND column_name = 'chunks_created') THEN
                -- Add missing chunks_created column
                ALTER TABLE text_chunking_status ADD COLUMN chunks_created INTEGER DEFAULT 0;
                RAISE NOTICE 'Added chunks_created column to existing table';
            END IF;
            
            -- Check if it has notes column (from original schema)
            IF NOT EXISTS (SELECT FROM information_schema.columns 
                          WHERE table_name = 'text_chunking_status' 
                          AND column_name = 'notes') THEN
                -- Add missing notes column
                ALTER TABLE text_chunking_status ADD COLUMN notes TEXT;
                RAISE NOTICE 'Added notes column to existing table';
            END IF;
            
            RAISE NOTICE 'text_chunking_status table schema verified and updated';
        END IF;
    END
    $$;
    
    -- Verify final schema
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'text_chunking_status'
    ORDER BY ordinal_position;
    """
    
    # Create a simple Lambda function that can execute SQL
    payload = {
        "sql_query": schema_fix_sql,
        "action": "execute_sql"
    }
    
    try:
        logger.info("Executing database schema verification and fix...")
        
        # Use text chunker function since it has database access
        response = lambda_client.invoke(
            FunctionName="text-chunker-pipeline",
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Schema fix result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to verify/fix database schema: {e}")
        raise

if __name__ == "__main__":
    verify_and_fix_database_schema()
