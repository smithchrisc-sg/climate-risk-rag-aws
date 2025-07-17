#!/usr/bin/env python3
"""
Update Text Chunker Pipeline Lambda Code
Fixes the method call to SmartStructuredChunker.chunk_document
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
    """Main function to update Lambda code"""
    logger.info("🔧 Updating Text Chunker Pipeline Lambda Code")
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
            
            # Read the updated file
            logger.info("Reading updated text_chunker_processor.py...")
            with open('/tmp/text_chunker_pipeline/text_chunker_processor_updated.py', 'r') as f:
                updated_chunk_method = f.read()
            
            # Read the original file
            original_file_path = os.path.join(temp_dir, 'text_chunker_processor.py')
            with open(original_file_path, 'r') as f:
                original_content = f.read()
            
            # Find the create_chunks method in the original file
            start_marker = "    def create_chunks(self, full_text: str, textract_structure: Optional[Dict], doc_id: str) -> List[Dict]:"
            end_marker = "            # Add metadata to chunks"
            
            # Split the content
            parts = original_content.split(start_marker)
            if len(parts) != 2:
                raise ValueError("Could not find create_chunks method in the original file")
            
            before_method = parts[0]
            
            parts = parts[1].split(end_marker)
            if len(parts) != 2:
                raise ValueError("Could not find end of create_chunks method in the original file")
            
            after_method = end_marker + parts[1]
            
            # Create the updated content
            updated_content = before_method + updated_chunk_method + after_method
            
            # Write the updated content back to the file
            with open(original_file_path, 'w') as f:
                f.write(updated_content)
            
            # Create a new zip file
            updated_zip_path = os.path.join(temp_dir, 'updated_function.zip')
            with zipfile.ZipFile(updated_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file != 'updated_function.zip':
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
            
            # Update the Lambda function
            logger.info(f"Updating Lambda function {function_name}...")
            with open(updated_zip_path, 'rb') as f:
                lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=f.read()
                )
        
        logger.info(f"✅ Successfully updated code for {function_name}")
        logger.info(f"Fixed method call: chunk_with_structure -> chunk_document")
        
        # Clean up
        os.unlink(current_code_zip)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda code: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
