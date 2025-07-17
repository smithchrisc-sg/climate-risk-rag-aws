#!/usr/bin/env python3
"""
Update SmartStructuredChunker Regex in Lambda Layer
Fixes the regex pattern in the _split_into_sentences method
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to update Lambda layer"""
    logger.info("🔧 Updating SmartStructuredChunker Regex in Lambda Layer")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
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
            
            # Path to the structured_chunking_smart_complete.py file
            chunker_file = os.path.join(temp_dir, 'python', 'structured_chunking_smart_complete.py')
            
            # Read the file
            with open(chunker_file, 'r') as f:
                content = f.read()
            
            # Read the fixed _split_into_sentences method from local file
            with open('/Users/chris/climate-risk-rag-aws/fixed_split_into_sentences.py', 'r') as f:
                fixed_method = f.read()
            
            # Replace the method in the content
            import re
            pattern = r'    def _split_into_sentences\(self, text: str\) -> List\[str\]:.*?return sentences'
            
            new_content = re.sub(pattern, fixed_method, content, flags=re.DOTALL)
            
            # Write the updated content back to the file
            with open(chunker_file, 'w') as f:
                f.write(new_content)
            
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
                    Description=f'Fixed regex pattern in SmartStructuredChunker._split_into_sentences (v{current_version+1})',
                    Content={
                        'ZipFile': f.read()
                    },
                    CompatibleRuntimes=['python3.11'],
                    LicenseInfo='MIT'
                )
            
            new_version = response['Version']
            logger.info(f"✅ Successfully published new layer version: {new_version}")
            
            # Update Lambda functions that use this layer
            functions_to_update = ['text-chunker-pipeline', 'solve-global-kr-text-chunker-phase1']
            
            for function_name in functions_to_update:
                logger.info(f"Updating {function_name} to use the new layer version...")
                
                # Get current function configuration
                function_response = lambda_client.get_function(
                    FunctionName=function_name
                )
                
                current_layers = function_response['Configuration'].get('Layers', [])
                
                # Replace the climate-risk-core-utilities layer with the new version
                new_layers = []
                for layer in current_layers:
                    if 'climate-risk-core-utilities:' in layer['Arn'] and not 'climate-risk-core-utilities-db:' in layer['Arn']:
                        # Replace with new version
                        new_arn = f"arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:{new_version}"
                        new_layers.append(new_arn)
                    else:
                        # Keep the same layer
                        new_layers.append(layer['Arn'])
                
                # Update the function
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Layers=new_layers
                )
                
                logger.info(f"✅ Successfully updated {function_name} to use the new layer version")
        
        # Clean up
        os.unlink(layer_zip)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda layer: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
