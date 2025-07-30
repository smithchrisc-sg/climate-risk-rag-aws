#!/usr/bin/env python3
"""
Deploy Updated Pipeline Test Lambda
Script to deploy the updated pipeline test Lambda function with strict database requirements
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

def deploy_updated_pipeline_test():
    """Deploy updated pipeline test Lambda function"""
    
    logger.info("🚀 Deploying Updated Pipeline Test Lambda")
    logger.info("=" * 50)
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    source_dir = 'lambda/pipeline_test_function'
    zip_path = '/tmp/pipeline_test_function_updated.zip'
    
    create_deployment_package(source_dir, zip_path)
    
    # Get function name
    function_name = 'solve-global-kr-pipeline-test-function'
    
    try:
        # Update function code
        with open(zip_path, 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
        
        logger.info(f"✅ Updated function code: {response['LastModified']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error deploying updated pipeline test Lambda: {str(e)}")
        return False
    
    finally:
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    logger.info(f"🚀 Updated Pipeline Test Lambda Deployment")
    logger.info("=" * 50)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("")
    
    success = deploy_updated_pipeline_test()
    
    if success:
        logger.info("🎉 Updated Pipeline Test Lambda deployment complete!")
        logger.info("   The pipeline test Lambda will now treat database connectivity as a hard requirement.")
    else:
        logger.error("⚠️ Updated Pipeline Test Lambda deployment failed!")
