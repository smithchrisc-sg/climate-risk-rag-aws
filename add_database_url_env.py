#!/usr/bin/env python3
"""
Add DATABASE_URL Environment Variable to Vector Embeddings Functions
Constructs DATABASE_URL from existing DB_HOST, DB_NAME, DB_PORT configuration
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to add DATABASE_URL environment variable"""
    logger.info("🔧 Adding DATABASE_URL Environment Variable")
    logger.info("==========================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Update processor environment
        logger.info("Step 1: Updating processor environment")
        update_processor_env(lambda_client)
        
        # Step 2: Update worker environment
        logger.info("Step 2: Updating worker environment")
        update_worker_env(lambda_client)
        
        logger.info("✅ Successfully added DATABASE_URL environment variable")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error adding DATABASE_URL: {str(e)}")
        return 1

def update_processor_env(lambda_client):
    """Update processor environment variables"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA"
    
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
    
    logger.info(f"✅ Updated processor environment with DATABASE_URL")

def update_worker_env(lambda_client):
    """Update worker environment variables"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi"
    
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
    
    logger.info(f"✅ Updated worker environment with DATABASE_URL")

if __name__ == "__main__":
    sys.exit(main())
