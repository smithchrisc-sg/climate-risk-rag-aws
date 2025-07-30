#!/usr/bin/env python3
"""
Fix Vector Embeddings Function Syntax Errors
Fixes the indentation issues in the updated functions
"""

import boto3
import logging
import sys
import zipfile
import tempfile
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to fix vector embeddings function syntax errors"""
    logger.info("🔧 Fixing Vector Embeddings Function Syntax Errors")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Fix vector embeddings processor syntax
        logger.info("Step 1: Fixing vector embeddings processor syntax")
        fix_processor_syntax(lambda_client)
        
        # Step 2: Fix vector embeddings worker syntax
        logger.info("Step 2: Fixing vector embeddings worker syntax")
        fix_worker_syntax(lambda_client)
        
        logger.info("✅ Successfully fixed vector embeddings function syntax")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error fixing vector embeddings functions: {str(e)}")
        return 1

def fix_processor_syntax(lambda_client):
    """Fix the vector embeddings processor syntax"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA"
    
    # Get current function code
    logger.info("Getting current processor code...")
    response = lambda_client.get_function(FunctionName=function_name)
    code_location = response['Code']['Location']
    
    # Download current code
    logger.info(f"Downloading code from {code_location}...")
    import urllib.request
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
        urllib.request.urlretrieve(code_location, temp_file.name)
        current_code_zip = temp_file.name
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        logger.info(f"Extracting code to {temp_dir}...")
        with zipfile.ZipFile(current_code_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Read the current processor file
        processor_file = os.path.join(temp_dir, 'vector_embeddings_processor.py')
        with open(processor_file, 'r') as f:
            content = f.read()
        
        # Fix the syntax error - proper indentation
        fixed_content = content.replace(
            """if DatabaseManager is None:
            raise ValueError("DatabaseManager not available - layer import failed")
        db_manager = DatabaseManager()""",
            """        if DatabaseManager is None:
            raise ValueError("DatabaseManager not available - layer import failed")
        db_manager = DatabaseManager()"""
        )
        
        # Write the fixed content
        with open(processor_file, 'w') as f:
            f.write(fixed_content)
        
        # Create a new zip file
        new_zip_path = os.path.join(temp_dir, 'updated_processor.zip')
        
        # Create the zip file
        logger.info("Creating updated processor zip...")
        with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'updated_processor.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Update the Lambda function
        logger.info(f"Updating processor function...")
        with open(new_zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Successfully updated processor code")
    
    # Clean up
    os.unlink(current_code_zip)

def fix_worker_syntax(lambda_client):
    """Fix the vector embeddings worker syntax"""
    function_name = "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi"
    
    # Get current function code
    logger.info("Getting current worker code...")
    response = lambda_client.get_function(FunctionName=function_name)
    code_location = response['Code']['Location']
    
    # Download current code
    logger.info(f"Downloading code from {code_location}...")
    import urllib.request
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
        urllib.request.urlretrieve(code_location, temp_file.name)
        current_code_zip = temp_file.name
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        logger.info(f"Extracting code to {temp_dir}...")
        with zipfile.ZipFile(current_code_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Read the current worker file
        worker_file = os.path.join(temp_dir, 'vector_embeddings_worker.py')
        with open(worker_file, 'r') as f:
            content = f.read()
        
        # Fix the syntax error - proper indentation
        fixed_content = content.replace(
            """if DatabaseManager is None:
            raise ValueError("DatabaseManager not available - layer import failed")
        db_manager = DatabaseManager()""",
            """        if DatabaseManager is None:
            raise ValueError("DatabaseManager not available - layer import failed")
        db_manager = DatabaseManager()"""
        )
        
        # Write the fixed content
        with open(worker_file, 'w') as f:
            f.write(fixed_content)
        
        # Create a new zip file
        new_zip_path = os.path.join(temp_dir, 'updated_worker.zip')
        
        # Create the zip file
        logger.info("Creating updated worker zip...")
        with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'updated_worker.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Update the Lambda function
        logger.info(f"Updating worker function...")
        with open(new_zip_path, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        logger.info(f"✅ Successfully updated worker code")
    
    # Clean up
    os.unlink(current_code_zip)

if __name__ == "__main__":
    sys.exit(main())
