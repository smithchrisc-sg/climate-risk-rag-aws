#!/usr/bin/env python3
"""
Database Schema Diagnostic Script
Uses existing Lambda function to check database schema and authentication
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_database_via_lambda():
    """Use Lambda function to diagnose database issues"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create a diagnostic payload that will check database schema
    diagnostic_code = '''
import psycopg2
import os
import json
from datetime import datetime

def diagnose_database():
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return {"error": "DATABASE_URL not found in environment"}
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        
        results = {
            "connection": "SUCCESS",
            "database_url_present": True,
            "tables": {},
            "authentication": "SUCCESS"
        }
        
        with conn.cursor() as cursor:
            # Check if text_chunking_status table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'text_chunking_status'
                );
            """)
            table_exists = cursor.fetchone()[0]
            results["tables"]["text_chunking_status_exists"] = table_exists
            
            if table_exists:
                # Get table schema
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'text_chunking_status'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                results["tables"]["text_chunking_status_columns"] = [
                    {
                        "name": col[0],
                        "type": col[1], 
                        "nullable": col[2],
                        "default": col[3]
                    } for col in columns
                ]
                
                # Check specifically for chunks_count column
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'text_chunking_status' 
                        AND column_name = 'chunks_count'
                    );
                """)
                chunks_count_exists = cursor.fetchone()[0]
                results["tables"]["chunks_count_column_exists"] = chunks_count_exists
            
            # Check other relevant tables
            for table in ['documents', 'textract_jobs', 'processing_status']:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """)
                exists = cursor.fetchone()[0]
                results["tables"][f"{table}_exists"] = exists
        
        conn.close()
        return results
        
    except Exception as e:
        return {
            "error": str(e),
            "connection": "FAILED",
            "authentication": "FAILED" if "authentication failed" in str(e) else "UNKNOWN"
        }

# Execute diagnosis
result = diagnose_database()
print(json.dumps(result, indent=2))
'''
    
    # Create a Lambda function payload that executes this diagnostic
    payload = {
        "diagnostic_code": diagnostic_code,
        "action": "database_diagnosis"
    }
    
    try:
        logger.info("Executing database diagnosis via Lambda...")
        
        # Use a function that has database access
        response = lambda_client.invoke(
            FunctionName="nlp-processor",  # This function has database access
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Database diagnosis result: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to execute database diagnosis: {e}")
        raise

if __name__ == "__main__":
    diagnose_database_via_lambda()
