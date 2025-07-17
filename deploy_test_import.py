#!/usr/bin/env python3
"""
Deploy Test Import Lambda Function
Script to deploy a test Lambda function for debugging import issues
"""

import boto3
import zipfile
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_deployment_package(source_dir, zip_path):
    """Create deployment package for Lambda function"""
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all Python files from source directory
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    logger.info(f"Added {arcname} to deployment package")

def deploy_test_import_lambda():
    """Deploy test import Lambda function"""
    
    logger.info("🚀 Deploying Test Import Lambda")
    logger.info("=" * 50)
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    source_dir = 'lambda/test_import'
    zip_path = '/tmp/test_import.zip'
    
    create_deployment_package(source_dir, zip_path)
    
    # Function name
    function_name = 'solve-global-kr-test-import'
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
        
        if function_exists:
            # Update function code
            with open(zip_path, 'rb') as zip_file:
                response = lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_file.read()
                )
            
            logger.info(f"✅ Updated function code: {response['LastModified']}")
            
            # Update function configuration
            response = lambda_client.update_function_configuration(
                FunctionName=function_name,
                Layers=[
                    'arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities-pipeline:16',
                    'arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:3'
                ],
                VpcConfig={
                    'SubnetIds': [
                        'subnet-0e9efc5fdf29e9da0',
                        'subnet-00efdcc220a613ae3'
                    ],
                    'SecurityGroupIds': [
                        'sg-0709acdc3f0cccd7f'
                    ]
                },
                Environment={
                    'Variables': {
                        'DATABASE_SECRET_NAME': 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
                        'DB_PORT': '5432',
                        'DB_NAME': 'climate_risk_rag',
                        'DB_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com'
                    }
                }
            )
            
            logger.info(f"✅ Updated function configuration")
        else:
            # Create function
            with open(zip_path, 'rb') as zip_file:
                response = lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.11',
                    Role='arn:aws:iam::861276078413:role/solve-global-kr-pipeline--PipelineTestLambdaRoleB69-1FJLHYD6c62Z',
                    Handler='test_import.lambda_handler',
                    Code={
                        'ZipFile': zip_file.read()
                    },
                    Description='Test Lambda function for debugging import issues',
                    Timeout=30,
                    MemorySize=256,
                    Publish=True,
                    Layers=[
                        'arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities-pipeline:16',
                        'arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:3'
                    ],
                    VpcConfig={
                        'SubnetIds': [
                            'subnet-0e9efc5fdf29e9da0',
                            'subnet-00efdcc220a613ae3'
                        ],
                        'SecurityGroupIds': [
                            'sg-0709acdc3f0cccd7f'
                        ]
                    },
                    Environment={
                        'Variables': {
                            'DATABASE_SECRET_NAME': 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
                            'DB_PORT': '5432',
                            'DB_NAME': 'climate_risk_rag',
                            'DB_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com'
                        }
                    }
                )
            
            logger.info(f"✅ Created function: {response['FunctionArn']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deploying test import Lambda: {str(e)}")
        return False
    
    finally:
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    logger.info(f"🚀 Test Import Lambda Deployment")
    logger.info("=" * 50)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("")
    
    success = deploy_test_import_lambda()
    
    if success:
        logger.info("🎉 Test Import Lambda deployment complete!")
        logger.info("   You can now invoke it to debug import issues.")
    else:
        logger.error("⚠️ Test Import Lambda deployment failed!")
