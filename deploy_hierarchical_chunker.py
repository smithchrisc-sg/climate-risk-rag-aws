#!/usr/bin/env python3
"""
Deploy Hierarchical Layout-Based Chunker
Updates the text-chunker-processor Lambda with new hierarchical chunking capability
"""

import boto3
import zipfile
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_lambda_package():
    """Create deployment package for text-chunker-processor with hierarchical chunker"""
    
    logger.info("Creating Lambda deployment package...")
    
    # Paths
    lambda_dir = Path("lambda/text-chunker-processor")
    src_dir = lambda_dir / "src"
    zip_path = lambda_dir / "text-chunker-processor-hierarchical.zip"
    
    # Remove existing zip
    if zip_path.exists():
        zip_path.unlink()
    
    # Create zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add handler.py from lambda directory
        handler_file = lambda_dir / "handler.py"
        if handler_file.exists():
            zipf.write(handler_file, "handler.py")
            logger.info("Added handler.py")
        
        # Add all Python files from src directory
        for py_file in src_dir.glob("*.py"):
            zipf.write(py_file, py_file.name)
            logger.info(f"Added {py_file.name}")
        
        # Add utils directory
        utils_dir = src_dir / "utils"
        if utils_dir.exists():
            for py_file in utils_dir.glob("*.py"):
                zipf.write(py_file, f"utils/{py_file.name}")
                logger.info(f"Added utils/{py_file.name}")
    
    logger.info(f"Created deployment package: {zip_path}")
    return zip_path

def update_lambda_function(zip_path: Path):
    """Update the Lambda function with new code"""
    
    function_name = "text-chunker-processor"
    
    logger.info(f"Updating Lambda function: {function_name}")
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Read zip file
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        logger.info(f"✅ Successfully updated {function_name}")
        logger.info(f"   Function ARN: {response['FunctionArn']}")
        logger.info(f"   Runtime: {response['Runtime']}")
        logger.info(f"   Last Modified: {response['LastModified']}")
        logger.info(f"   Code Size: {response['CodeSize']} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update {function_name}: {str(e)}")
        return False

def verify_deployment():
    """Verify the deployment by checking function configuration"""
    
    function_name = "text-chunker-processor"
    
    logger.info(f"Verifying deployment of {function_name}...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Get function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        logger.info("Function configuration:")
        logger.info(f"  Function Name: {response['FunctionName']}")
        logger.info(f"  Runtime: {response['Runtime']}")
        logger.info(f"  Handler: {response['Handler']}")
        logger.info(f"  Timeout: {response['Timeout']} seconds")
        logger.info(f"  Memory: {response['MemorySize']} MB")
        logger.info(f"  Last Modified: {response['LastModified']}")
        
        # Check environment variables
        env_vars = response.get('Environment', {}).get('Variables', {})
        logger.info("Environment variables:")
        for key, value in env_vars.items():
            if 'BUCKET' in key or 'TOPIC' in key:
                logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to verify deployment: {str(e)}")
        return False

def main():
    """Main deployment process"""
    
    logger.info("🚀 Starting hierarchical chunker deployment")
    
    try:
        # Step 1: Create deployment package
        zip_path = create_lambda_package()
        
        # Step 2: Update Lambda function
        if not update_lambda_function(zip_path):
            sys.exit(1)
        
        # Step 3: Verify deployment
        if not verify_deployment():
            sys.exit(1)
        
        logger.info("✅ Hierarchical chunker deployment completed successfully!")
        logger.info("")
        logger.info("🔍 Key Features Added:")
        logger.info("  • Hierarchical document tree structure")
        logger.info("  • Parent-child chunk relationships")
        logger.info("  • Respect for LAYOUT block boundaries")
        logger.info("  • Sentence-based paragraph splitting")
        logger.info("  • No artificial context brackets")
        logger.info("  • Fallback to legacy chunker if no LAYOUT blocks")
        logger.info("")
        logger.info("📊 New Chunk Fields:")
        logger.info("  • parent_chunk_id: ID of parent chunk")
        logger.info("  • child_chunk_ids: List of child chunk IDs")
        logger.info("  • sibling_chunk_ids: List of sibling chunk IDs")
        logger.info("  • is_split_paragraph: Boolean for split paragraphs")
        logger.info("  • split_part: Part number if split")
        logger.info("  • total_splits: Total parts if split")
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
