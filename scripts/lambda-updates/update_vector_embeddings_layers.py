#!/usr/bin/env python3
"""
Update Vector Embeddings Lambda Functions with Latest Layers
Fixes the import issues by updating to the latest layer versions
"""

import boto3
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to update vector embeddings Lambda functions"""
    logger.info("🔧 Updating Vector Embeddings Lambda Functions with Latest Layers")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Update vector embeddings processor
        logger.info("Step 1: Updating vector embeddings processor")
        update_processor_layers(lambda_client)
        
        # Step 2: Update vector embeddings worker
        logger.info("Step 2: Updating vector embeddings worker")
        update_worker_layers(lambda_client)
        
        logger.info("✅ Successfully updated vector embeddings Lambda functions")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating vector embeddings functions: {str(e)}")
        return 1

def update_processor_layers(lambda_client):
    """Update the vector embeddings processor layers"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA"
    
    # Get current layer version
    logger.info("Getting current layer version...")
    response = lambda_client.list_layer_versions(
        LayerName='climate-risk-core-utilities',
        MaxItems=1
    )
    
    latest_core_layer_version = response['LayerVersions'][0]['Version']
    logger.info(f"Latest core layer version: {latest_core_layer_version}")
    
    # Get database layer version
    response = lambda_client.list_layer_versions(
        LayerName='database-dependencies-pipeline',
        MaxItems=1
    )
    
    latest_db_layer_version = response['LayerVersions'][0]['Version']
    logger.info(f"Latest database layer version: {latest_db_layer_version}")
    
    # Update function configuration
    new_layers = [
        f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{latest_core_layer_version}",
        f"arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:{latest_db_layer_version}"
    ]
    
    logger.info(f"Updating processor with layers: {new_layers}")
    
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Layers=new_layers
    )
    
    logger.info(f"✅ Successfully updated processor layers")

def update_worker_layers(lambda_client):
    """Update the vector embeddings worker layers"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi"
    
    # Get current layer versions
    logger.info("Getting current layer versions...")
    
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
    
    # Check if numpy layer exists
    try:
        response = lambda_client.list_layer_versions(
            LayerName='numpy-dependencies-lambda',
            MaxItems=1
        )
        latest_numpy_layer_version = response['LayerVersions'][0]['Version']
        numpy_layer = f"arn:aws:lambda:us-east-1:861276078413:layer:numpy-dependencies-lambda:{latest_numpy_layer_version}"
        logger.info(f"Latest numpy layer version: {latest_numpy_layer_version}")
    except:
        numpy_layer = None
        logger.warning("No numpy layer found - worker may need additional dependencies")
    
    # Update function configuration
    new_layers = [
        f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{latest_core_layer_version}",
        f"arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:{latest_db_layer_version}"
    ]
    
    if numpy_layer:
        new_layers.append(numpy_layer)
    
    logger.info(f"Updating worker with layers: {new_layers}")
    
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Layers=new_layers
    )
    
    logger.info(f"✅ Successfully updated worker layers")

if __name__ == "__main__":
    sys.exit(main())
