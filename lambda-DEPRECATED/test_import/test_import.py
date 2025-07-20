#!/usr/bin/env python3
"""
Test Lambda function to check database schema
"""

import json
import sys
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda handler for checking database schema"""
    
    logger.info("Test import Lambda invoked")
    
    # Get DATABASE_URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "DATABASE_URL environment variable not set"
            })
        }
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get schema for documents table
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        # Close connection
        cursor.close()
        conn.close()
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "table": "documents",
                "columns": [dict(col) for col in columns]
            })
        }
        
    except Exception as e:
        logger.error(f"Error checking database schema: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
