#!/usr/bin/env python3
"""
Update Lambda Function with New File
Updates the text-chunker-pipeline Lambda function with a new text_chunker_processor.py file
"""

import boto3
import logging
import sys
import os
import zipfile
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to update Lambda function"""
    logger.info("🔧 Updating Lambda Function with New File")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Function name
    function_name = 'text-chunker-pipeline'
    
    try:
        # Get current function code
        logger.info(f"Getting current code for {function_name}...")
        response = lambda_client.get_function(FunctionName=function_name)
        code_location = response['Code']['Location']
        
        # Download current code
        logger.info(f"Downloading current code from {code_location}...")
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
            
            # Copy the new file
            logger.info("Copying new text_chunker_processor.py file...")
            new_file_path = '/Users/chris/climate-risk-rag-aws/text_chunker_processor_modified.py'
            target_file_path = os.path.join(temp_dir, 'text_chunker_processor.py')
            
            with open(new_file_path, 'r') as src_file:
                with open(target_file_path, 'w') as dst_file:
                    dst_file.write(src_file.read())
            
            # Create a new zip file
            new_zip_path = os.path.join(temp_dir, 'updated_function.zip')
            
            # Create the zip file
            logger.info("Creating new function zip...")
            with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            # Update the Lambda function
            logger.info(f"Updating Lambda function {function_name}...")
            with open(new_zip_path, 'rb') as f:
                lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=f.read()
                )
            
            logger.info(f"✅ Successfully updated code for {function_name}")
            logger.info(f"Replaced text_chunker_processor.py with new version")
        
        # Clean up
        os.unlink(current_code_zip)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
