#!/usr/bin/env python3
"""
Comprehensive NLP Stage Fix
Fixes all identified issues in the NLP stage
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to fix NLP stage issues"""
    logger.info("🔧 Comprehensive NLP Stage Fix")
    logger.info("==============================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Update layer versions
        logger.info("Step 1: Updating layer versions to latest")
        update_layer_versions(lambda_client)
        
        # Step 2: Add DATABASE_URL environment variable
        logger.info("Step 2: Adding DATABASE_URL environment variable")
        add_database_url(lambda_client)
        
        # Step 3: Update function configurations
        logger.info("Step 3: Optimizing function configurations")
        optimize_configurations(lambda_client)
        
        logger.info("✅ Successfully fixed NLP stage issues")
        logger.info("\n📋 Next Steps:")
        logger.info("1. Database schema may need updates for nlp_processing_status table")
        logger.info("2. S3 path handling in worker code may need review")
        logger.info("3. Run integration tests to verify functionality")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error fixing NLP stage: {str(e)}")
        return 1

def update_layer_versions(lambda_client):
    """Update both functions to use latest layer versions"""
    
    # Get latest layer versions
    logger.info("Getting latest layer versions...")
    
    # Core utilities layer
    response = lambda_client.list_layer_versions(
        LayerName='climate-risk-core-utilities',
        MaxItems=1
    )
    latest_core_layer_version = response['LayerVersions'][0]['Version']
    
    # Database layer
    response = lambda_client.list_layer_versions(
        LayerName='database-dependencies-pipeline',
        MaxItems=1
    )
    latest_db_layer_version = response['LayerVersions'][0]['Version']
    
    logger.info(f"Latest core layer version: {latest_core_layer_version}")
    logger.info(f"Latest database layer version: {latest_db_layer_version}")
    
    # Update layers for both functions
    new_layers = [
        f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{latest_core_layer_version}",
        f"arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:{latest_db_layer_version}"
    ]
    
    # Update NLP processor
    logger.info("Updating NLP processor layers...")
    lambda_client.update_function_configuration(
        FunctionName="nlp-processor",
        Layers=new_layers
    )
    
    # Update NLP worker
    logger.info("Updating NLP worker layers...")
    lambda_client.update_function_configuration(
        FunctionName="nlp-worker",
        Layers=new_layers
    )
    
    logger.info("✅ Successfully updated layer versions")

def add_database_url(lambda_client):
    """Add DATABASE_URL environment variable to both functions"""
    
    # Update NLP processor
    logger.info("Adding DATABASE_URL to NLP processor...")
    response = lambda_client.get_function(FunctionName="nlp-processor")
    current_env = response['Configuration']['Environment']['Variables']
    
    # Construct DATABASE_URL
    db_host = current_env['DB_HOST']
    db_name = current_env['DB_NAME']
    db_port = current_env['DB_PORT']
    database_url = f"postgresql://postgres:{{secret}}@{db_host}:{db_port}/{db_name}"
    
    # Add DATABASE_URL
    updated_env = current_env.copy()
    updated_env['DATABASE_URL'] = database_url
    
    lambda_client.update_function_configuration(
        FunctionName="nlp-processor",
        Environment={'Variables': updated_env}
    )
    
    # Update NLP worker
    logger.info("Adding DATABASE_URL to NLP worker...")
    response = lambda_client.get_function(FunctionName="nlp-worker")
    current_env = response['Configuration']['Environment']['Variables']
    
    # Construct DATABASE_URL
    db_host = current_env['DB_HOST']
    db_name = current_env['DB_NAME']
    db_port = current_env['DB_PORT']
    database_url = f"postgresql://postgres:{{secret}}@{db_host}:{db_port}/{db_name}"
    
    # Add DATABASE_URL
    updated_env = current_env.copy()
    updated_env['DATABASE_URL'] = database_url
    
    lambda_client.update_function_configuration(
        FunctionName="nlp-worker",
        Environment={'Variables': updated_env}
    )
    
    logger.info("✅ Successfully added DATABASE_URL to both functions")

def optimize_configurations(lambda_client):
    """Optimize function configurations for better performance"""
    
    # Update NLP processor timeout and memory
    logger.info("Optimizing NLP processor configuration...")
    lambda_client.update_function_configuration(
        FunctionName="nlp-processor",
        Timeout=60,  # Increase timeout for database operations
        MemorySize=512  # Increase memory for better performance
    )
    
    # Update NLP worker timeout and memory
    logger.info("Optimizing NLP worker configuration...")
    lambda_client.update_function_configuration(
        FunctionName="nlp-worker",
        Timeout=900,  # Max timeout for NLP processing
        MemorySize=2048  # More memory for NLP operations
    )
    
    logger.info("✅ Successfully optimized function configurations")

if __name__ == "__main__":
    sys.exit(main())
