#!/usr/bin/env python3
"""
Update Lambda Layer and Function with Simplified Smart Chunker
Updates the climate-risk-core-utilities layer and text-chunker-pipeline function
"""

import boto3
import logging
import sys
import os
import zipfile
import tempfile
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to update Lambda layer and function"""
    logger.info("🔧 Updating Lambda Layer and Function with Simplified Smart Chunker")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Step 1: Update the Lambda layer
        logger.info("Step 1: Updating Lambda layer with simplified smart chunker")
        layer_version = update_lambda_layer()
        
        # Step 2: Update the Lambda function
        logger.info("Step 2: Updating Lambda function with new processor")
        update_lambda_function(layer_version)
        
        logger.info("✅ Successfully updated Lambda layer and function")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda layer and function: {str(e)}")
        return 1

def update_lambda_layer():
    """Update the Lambda layer with the simplified smart chunker"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Get current layer version
    logger.info("Getting current layer version...")
    response = lambda_client.list_layer_versions(
        LayerName='climate-risk-core-utilities',
        MaxItems=1
    )
    
    current_version = response['LayerVersions'][0]['Version']
    logger.info(f"Current layer version: {current_version}")
    
    # Download current layer
    logger.info(f"Downloading current layer version {current_version}...")
    response = lambda_client.get_layer_version(
        LayerName='climate-risk-core-utilities',
        VersionNumber=current_version
    )
    
    layer_url = response['Content']['Location']
    
    # Download layer zip
    import urllib.request
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
        urllib.request.urlretrieve(layer_url, temp_file.name)
        layer_zip = temp_file.name
    
    # Create a temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the zip file
        logger.info(f"Extracting layer to {temp_dir}...")
        with zipfile.ZipFile(layer_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Copy the simplified smart chunker to the layer
        logger.info("Adding simplified smart chunker to layer...")
        src_file = '/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python/simplified_smart_chunker.py'
        dst_file = os.path.join(temp_dir, 'python', 'simplified_smart_chunker.py')
        
        with open(src_file, 'r') as src:
            with open(dst_file, 'w') as dst:
                dst.write(src.read())
        
        # Create a new zip file
        new_layer_zip = os.path.join(temp_dir, 'new_layer.zip')
        
        # Create the zip file
        logger.info("Creating new layer zip...")
        shutil.make_archive(os.path.join(temp_dir, 'new_layer'), 'zip', temp_dir)
        
        # Publish new layer version
        logger.info("Publishing new layer version...")
        with open(new_layer_zip, 'rb') as f:
            response = lambda_client.publish_layer_version(
                LayerName='climate-risk-core-utilities',
                Description=f'Added SimplifiedSmartChunker (v{current_version+1})',
                Content={
                    'ZipFile': f.read()
                },
                CompatibleRuntimes=['python3.11'],
                LicenseInfo='MIT'
            )
        
        new_version = response['Version']
        logger.info(f"✅ Successfully published new layer version: {new_version}")
    
    # Clean up
    os.unlink(layer_zip)
    
    return new_version

def update_lambda_function(layer_version):
    """Update the Lambda function with the new processor"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Function name
    function_name = 'text-chunker-pipeline'
    
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
        
        # Copy the new processor file
        logger.info("Copying new text_chunker_processor.py file...")
        src_file = '/Users/chris/climate-risk-rag-aws/text_chunker_processor_with_simplified_chunker.py'
        dst_file = os.path.join(temp_dir, 'text_chunker_processor.py')
        
        with open(src_file, 'r') as src:
            with open(dst_file, 'w') as dst:
                dst.write(src.read())
        
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
        
        # Update the function configuration to use the new layer version
        logger.info(f"Updating Lambda function configuration...")
        
        # Get current function configuration
        function_response = lambda_client.get_function(
            FunctionName=function_name
        )
        
        current_layers = function_response['Configuration'].get('Layers', [])
        
        # Replace the climate-risk-core-utilities layer with the new version
        new_layers = []
        for layer in current_layers:
            if 'climate-risk-core-utilities:' in layer['Arn'] and 'climate-risk-core-utilities-db:' not in layer['Arn']:
                # Replace with new version
                new_layer_arn = f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{layer_version}"
                new_layers.append(new_layer_arn)
            else:
                # Keep the same layer
                new_layers.append(layer['Arn'])
        
        # Update the function configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Layers=new_layers
        )
        
        logger.info(f"✅ Successfully updated code and configuration for {function_name}")
    
    # Clean up
    os.unlink(current_code_zip)

if __name__ == "__main__":
    sys.exit(main())
