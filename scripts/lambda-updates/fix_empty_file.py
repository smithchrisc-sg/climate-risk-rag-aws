#!/usr/bin/env python3
"""
Fix Empty File Issue in Lambda Layer
Restores the structured_chunking_smart_complete.py file and fixes the regex pattern
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
    """Main function to fix the empty file issue"""
    logger.info("🔧 Fixing Empty File Issue in Lambda Layer")
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
            
            # Path to the structured_chunking_smart_complete.py file and its backup
            chunker_file = os.path.join(temp_dir, 'python', 'structured_chunking_smart_complete.py')
            chunker_backup = os.path.join(temp_dir, 'python', 'structured_chunking_smart_complete.py.bak')
            
            # Check if the backup file exists
            if os.path.exists(chunker_backup) and os.path.getsize(chunker_backup) > 0:
                logger.info("Backup file exists and has content. Restoring from backup...")
                
                # Read the backup file
                with open(chunker_backup, 'r') as f:
                    content = f.read()
                
                # Create the fixed _split_into_sentences method
                fixed_method = '''    def _split_into_sentences(self, text: str) -> List[str]:
        """Enhanced sentence splitting with regex that works in Python 3.11"""
        import re
        
        # Instead of using a variable-width look-behind assertion, we'll use a different approach
        # First, split on potential sentence boundaries
        potential_sentences = re.split(r'\\s*[.!?]+\\s+(?=[A-Z])', text)
        
        # Then filter out false positives (where the split happened after an abbreviation)
        sentences = []
        abbreviations = ['Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr', 'vs', 'etc', 'Inc', 'Corp', 'Ltd', 'Co', 
                         'St', 'Ave', 'Blvd', 'Rd', 'Fig', 'Table', 'Ch', 'Sec', 'Vol', 'No', 'pp', 'cf', 'i.e', 'e.g', 'et al']
        
        for i, s in enumerate(potential_sentences):
            if i == 0:
                # First segment is always included
                sentences.append(s.strip())
            else:
                # Check if the previous segment ends with an abbreviation
                prev_segment = potential_sentences[i-1]
                is_abbreviation = False
                
                for abbr in abbreviations:
                    if prev_segment.strip().endswith(abbr):
                        is_abbreviation = True
                        # Combine with previous segment
                        sentences[-1] = sentences[-1] + '.' + s.strip()
                        break
                
                if not is_abbreviation:
                    sentences.append(s.strip())
        
        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Handle edge cases where splitting failed
        if len(sentences) == 1 and len(text) > self.max_chunk_size:
            # Fallback to simpler splitting
            sentences = re.split(r'[.!?]+\\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences'''
                
                # Replace the method in the content
                import re
                pattern = r'    def _split_into_sentences\(self, text: str\) -> List\[str\]:.*?return sentences'
                
                new_content = re.sub(pattern, fixed_method, content, flags=re.DOTALL)
                
                # Write the updated content to the file
                with open(chunker_file, 'w') as f:
                    f.write(new_content)
                
                logger.info("Successfully restored and updated the file.")
            else:
                logger.error("Backup file does not exist or is empty. Cannot restore.")
                return 1
            
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
                    Description=f'Fixed empty file issue in SmartStructuredChunker (v{current_version+1})',
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
                    if 'climate-risk-core-utilities:' in layer['Arn'] and 'climate-risk-core-utilities-db:' not in layer['Arn']:
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
        logger.error(f"❌ Error fixing empty file issue: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
