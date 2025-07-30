#!/usr/bin/env python3
"""
Deploy Pipeline Test Lambda
Script to deploy the pipeline test Lambda function
"""

import subprocess
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(command, description):
    """Run a shell command and handle errors"""
    try:
        logger.info(f"Running: {description}")
        logger.info(f"Command: {command}")
        
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd="/Users/chris/climate-risk-rag-aws/cdk"
        )
        
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False

def main():
    """Deploy the pipeline test Lambda function"""
    try:
        logger.info("🚀 DEPLOYING PIPELINE TEST LAMBDA")
        logger.info("=" * 50)
        
        # Change to CDK directory
        os.chdir("/Users/chris/climate-risk-rag-aws/cdk")
        
        # Set AWS environment variables
        os.environ['CDK_DEFAULT_ACCOUNT'] = '861276078413'
        os.environ['CDK_DEFAULT_REGION'] = 'us-east-1'
        
        # Deploy the pipeline test Lambda stack
        logger.info("1. Deploying pipeline test Lambda...")
        if not run_command(
            "cdk deploy solve-global-kr-pipeline-test-lambda --app 'python3 app_pipeline_test_lambda.py' --require-approval never",
            "Deploy pipeline test Lambda function"
        ):
            logger.error("Pipeline test Lambda deployment failed")
            return False
        
        logger.info("=" * 50)
        logger.info("✅ PIPELINE TEST LAMBDA DEPLOYMENT COMPLETE")
        logger.info("=" * 50)
        logger.info("Function: solve-global-kr-pipeline-test-function")
        logger.info("You can now invoke it using: python3 invoke_pipeline_test.py")
        
        return True
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
