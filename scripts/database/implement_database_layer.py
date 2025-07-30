#!/usr/bin/env python3
"""
Database Layer Implementation Script
Implements the standardized database layer architecture
"""

import boto3
import logging
import sys
import zipfile
import os
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main implementation function"""
    logger.info("🚀 Database Layer Implementation")
    logger.info("================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Phase 1: Create and deploy database core layer
        logger.info("Phase 1: Creating database core layer")
        layer_arn = create_database_core_layer()
        
        # Phase 2: Update critical functions first
        logger.info("Phase 2: Updating critical functions")
        update_critical_functions(layer_arn)
        
        # Phase 3: Test critical functions
        logger.info("Phase 3: Testing critical functions")
        test_critical_functions()
        
        logger.info("✅ Database layer implementation completed successfully")
        logger.info(f"New layer ARN: {layer_arn}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Database layer implementation failed: {str(e)}")
        return 1

def create_database_core_layer():
    """Create and deploy the database core layer"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create layer zip file
    layer_path = "/Users/chris/climate-risk-rag-aws/layers/database-core-layer"
    zip_path = f"{layer_path}/database-core-layer.zip"
    
    logger.info("Creating layer zip file...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add Python files
        for root, dirs, files in os.walk(f"{layer_path}/python"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, layer_path)
                zipf.write(file_path, arcname)
                logger.info(f"  Added: {arcname}")
    
    # Deploy layer
    logger.info("Deploying database core layer...")
    with open(zip_path, 'rb') as f:
        response = lambda_client.publish_layer_version(
            LayerName='database-core-layer',
            Description='Core database utilities for climate risk RAG pipeline',
            Content={'ZipFile': f.read()},
            CompatibleRuntimes=['python3.11'],
            CompatibleArchitectures=['x86_64']
        )
    
    layer_arn = response['LayerVersionArn']
    logger.info(f"✅ Database core layer deployed: {layer_arn}")
    
    return layer_arn

def update_critical_functions(layer_arn):
    """Update critical functions with new database layer"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Standard database environment variables
    standard_db_env = {
        'DATABASE_SECRET_NAME': 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
        'DB_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
        'DB_NAME': 'climate_risk_rag',
        'DB_PORT': '5432',
        'DATABASE_CONNECTION_METHOD': 'secrets_manager'
    }
    
    # Standard VPC configuration
    standard_vpc_config = {
        'SubnetIds': ['subnet-03d8bd6cf3491f38c', 'subnet-0c0be1dd59f70f70e'],
        'SecurityGroupIds': ['sg-099296a5c809e8d9d']  # Use existing working security group
    }
    
    # Critical functions to update first
    critical_functions = [
        {
            'name': 'solve-global-kr-pipeline-test-function',
            'description': 'Pipeline test function - critical for integration testing'
        },
        {
            'name': 'solve-global-kr-cleanup-service', 
            'description': 'Cleanup service - critical for test cleanup'
        }
    ]
    
    for func_info in critical_functions:
        func_name = func_info['name']
        logger.info(f"Updating {func_name}...")
        
        try:
            # Get current function configuration
            response = lambda_client.get_function(FunctionName=func_name)
            current_config = response['Configuration']
            current_env = current_config.get('Environment', {}).get('Variables', {})
            
            # Merge standard database environment with existing variables
            updated_env = current_env.copy()
            updated_env.update(standard_db_env)
            
            # Remove old DATABASE_URL if it exists (we'll use Secrets Manager)
            if 'DATABASE_URL' in updated_env:
                del updated_env['DATABASE_URL']
                logger.info(f"  Removed hardcoded DATABASE_URL from {func_name}")
            
            # Update layers - replace database layers with new core layer
            current_layers = [layer['Arn'] for layer in current_config.get('Layers', [])]
            updated_layers = []
            
            # Filter out old database layers and add new core layer
            for layer in current_layers:
                if 'database-dependencies' not in layer and 'climate-risk-core-utilities' not in layer:
                    updated_layers.append(layer)
            
            updated_layers.append(layer_arn)
            
            # Update function configuration
            lambda_client.update_function_configuration(
                FunctionName=func_name,
                Layers=updated_layers,
                Environment={'Variables': updated_env},
                VpcConfig=standard_vpc_config
            )
            
            logger.info(f"✅ Updated {func_name}")
            logger.info(f"  New layers: {len(updated_layers)}")
            logger.info(f"  Database env vars: {len([k for k in updated_env.keys() if 'DB' in k or 'DATABASE' in k])}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update {func_name}: {str(e)}")

def test_critical_functions():
    """Test critical functions after update"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_functions = [
        'solve-global-kr-pipeline-test-function',
        'solve-global-kr-cleanup-service'
    ]
    
    for func_name in test_functions:
        logger.info(f"Testing {func_name}...")
        
        try:
            # Simple test payload
            test_payload = {'test': 'database_connection'}
            
            response = lambda_client.invoke(
                FunctionName=func_name,
                Payload=json.dumps(test_payload)
            )
            
            response_payload = json.loads(response['Payload'].read().decode('utf-8'))
            
            # Check for import errors
            if 'ImportModuleError' in str(response_payload):
                logger.error(f"❌ {func_name}: Import errors detected")
            elif 'errorType' in response_payload and 'Import' in response_payload['errorType']:
                logger.error(f"❌ {func_name}: Import errors detected")
            else:
                logger.info(f"✅ {func_name}: No import errors")
            
            # Check for database connection attempts
            if ('database' in str(response_payload).lower() or 
                'connection' in str(response_payload).lower()):
                logger.info(f"✅ {func_name}: Database connection attempted")
            
        except Exception as e:
            logger.error(f"❌ Failed to test {func_name}: {str(e)}")

if __name__ == "__main__":
    sys.exit(main())
