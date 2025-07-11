#!/usr/bin/env python3
"""
Deploy Source Documents Bucket
Quick deployment script to add the source documents bucket to existing infrastructure
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
    """Deploy the source documents bucket"""
    try:
        logger.info("🚀 DEPLOYING SOURCE DOCUMENTS BUCKET")
        logger.info("=" * 50)
        
        # Change to CDK directory
        os.chdir("/Users/chris/climate-risk-rag-aws/cdk")
        
        # Set AWS environment variables
        os.environ['CDK_DEFAULT_ACCOUNT'] = '861276078413'
        os.environ['CDK_DEFAULT_REGION'] = 'us-east-1'
        
        # Bootstrap CDK if needed (safe to run multiple times)
        logger.info("1. Bootstrapping CDK...")
        if not run_command(
            "cdk bootstrap aws://861276078413/us-east-1",
            "Bootstrap CDK environment"
        ):
            logger.error("CDK bootstrap failed")
            return False
        
        # Synthesize the stack to check for errors
        logger.info("2. Synthesizing CDK stack...")
        if not run_command(
            "cdk synth solve-global-kr-rag-data-lake",
            "Synthesize data lake stack"
        ):
            logger.error("CDK synthesis failed")
            return False
        
        # Deploy the data lake stack (which includes the new source bucket)
        logger.info("3. Deploying data lake stack...")
        if not run_command(
            "cdk deploy solve-global-kr-rag-data-lake --require-approval never",
            "Deploy data lake stack with source documents bucket"
        ):
            logger.error("CDK deployment failed")
            return False
        
        # Deploy the notifications stack to add S3 event triggers
        logger.info("4. Deploying notifications stack...")
        if not run_command(
            "cdk deploy solve-global-kr-rag-notifications --require-approval never",
            "Deploy notifications stack with source bucket triggers"
        ):
            logger.error("Notifications stack deployment failed")
            return False
        
        logger.info("=" * 50)
        logger.info("✅ SOURCE DOCUMENTS BUCKET DEPLOYMENT COMPLETE")
        logger.info("=" * 50)
        logger.info("New bucket: solve-global-kr-dl-source-documents-861276078413-us-east-1")
        logger.info("S3 event triggers configured for text extraction")
        logger.info("Lambda permissions updated")
        
        return True
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
