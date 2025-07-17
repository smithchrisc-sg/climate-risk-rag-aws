#!/usr/bin/env python3
"""
Update Text Chunker Pipeline Lambda Function
Adds error handling for the regex pattern issue
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
    """Main function to update Lambda function"""
    logger.info("🔧 Updating Text Chunker Pipeline Lambda Function")
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
            
            # Path to the text_chunker_processor.py file
            processor_file = os.path.join(temp_dir, 'text_chunker_processor.py')
            
            # Read the file
            with open(processor_file, 'r') as f:
                content = f.read()
            
            # Add our own implementation of _split_into_sentences method
            new_method = '''
    def _split_into_sentences_safe(self, text: str) -> List[str]:
        """Safe sentence splitting that works in Python 3.11"""
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
            
            # Update the create_chunks method to use our safe method
            updated_create_chunks = '''
    def create_chunks(self, full_text: str, textract_structure: Optional[Dict], doc_id: str) -> List[Dict]:
        """Create structured chunks from text"""
        
        try:
            if self.structured_chunker and textract_structure:
                # Use smart structured chunker with Textract data
                logger.info("Using smart structured chunker with Textract structure")
                try:
                    chunks = self.structured_chunker.chunk_document(textract_structure)
                except Exception as e:
                    logger.error(f"Error in smart structured chunking: {e}")
                    logger.warning("Falling back to simple chunking")
                    chunks = self.basic_chunk_text(full_text)
            elif self.structured_chunker:
                # Use smart chunker without structure
                logger.info("Using smart structured chunker (text-only)")
                try:
                    # Add our own _split_into_sentences method to the chunker
                    self.structured_chunker._original_split_into_sentences = self.structured_chunker._split_into_sentences
                    self.structured_chunker._split_into_sentences = self._split_into_sentences_safe
                    chunks = self.structured_chunker.chunk_text(full_text)
                except Exception as e:
                    logger.error(f"Error in smart text-only chunking: {e}")
                    logger.warning("Falling back to simple chunking")
                    chunks = self.basic_chunk_text(full_text)
            else:
                # Fallback to basic chunking
                logger.info("Using basic chunking")
                chunks = self.basic_chunk_text(full_text)'''
            
            # Replace the create_chunks method in the content
            import re
            pattern = r'    def create_chunks\(self, full_text: str, textract_structure: Optional\[Dict\], doc_id: str\) -> List\[Dict\]:[^}]*?try:'
            replacement = updated_create_chunks
            
            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            # Add our new method
            new_content = new_content.replace('class TextChunkerProcessor:', 'class TextChunkerProcessor:' + new_method)
            
            # Write the updated content back to the file
            with open(processor_file, 'w') as f:
                f.write(new_content)
            
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
            logger.info(f"Added safe sentence splitting method and error handling")
        
        # Clean up
        os.unlink(current_code_zip)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error updating Lambda function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
