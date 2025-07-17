#!/usr/bin/env python3
"""
Add DATABASE_URL to NLP Functions
Specifically for NLP processor and worker
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to add DATABASE_URL to NLP functions"""
    logger.info("🔧 Adding DATABASE_URL to NLP Functions")
    logger.info("======================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Add DATABASE_URL to NLP processor
        logger.info("Step 1: Adding DATABASE_URL to NLP processor")
        add_database_url_processor(lambda_client)
        
        # Add DATABASE_URL to NLP worker
        logger.info("Step 2: Adding DATABASE_URL to NLP worker")
        add_database_url_worker(lambda_client)
        
        logger.info("✅ Successfully added DATABASE_URL to NLP functions")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error adding DATABASE_URL to NLP functions: {str(e)}")
        return 1

def add_database_url_processor(lambda_client):
    """Add DATABASE_URL to NLP processor"""
    function_name = "nlp-processor"
    
    # Get current environment variables
    response = lambda_client.get_function(FunctionName=function_name)
    current_env = response['Configuration']['Environment']['Variables']
    
    # Construct DATABASE_URL from existing variables
    db_host = current_env['DB_HOST']
    db_name = current_env['DB_NAME']
    db_port = current_env['DB_PORT']
    
    # Use secrets manager for password
    database_url = f"postgresql://postgres:{{secret}}@{db_host}:{db_port}/{db_name}"
    
    # Add DATABASE_URL to environment
    updated_env = current_env.copy()
    updated_env['DATABASE_URL'] = database_url
    
    # Update function configuration
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={'Variables': updated_env}
    )
    
    logger.info(f"✅ Updated {function_name} environment with DATABASE_URL")

def add_database_url_worker(lambda_client):
    """Add DATABASE_URL to NLP worker"""
    function_name = "nlp-worker"
    
    # Get current environment variables
    response = lambda_client.get_function(FunctionName=function_name)
    current_env = response['Configuration']['Environment']['Variables']
    
    # Construct DATABASE_URL from existing variables
    db_host = current_env['DB_HOST']
    db_name = current_env['DB_NAME']
    db_port = current_env['DB_PORT']
    
    # Use secrets manager for password
    database_url = f"postgresql://postgres:{{secret}}@{db_host}:{db_port}/{db_name}"
    
    # Add DATABASE_URL to environment
    updated_env = current_env.copy()
    updated_env['DATABASE_URL'] = database_url
    
    # Update function configuration
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={'Variables': updated_env}
    )
    
    logger.info(f"✅ Updated {function_name} environment with DATABASE_URL")

if __name__ == "__main__":
    sys.exit(main())
