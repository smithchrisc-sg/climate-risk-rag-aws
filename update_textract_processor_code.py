#!/usr/bin/env python3
"""
Update Textract processor code only
"""

import boto3
import zipfile
import tempfile
import os

def update_textract_processor_code():
    """Update just the code for Textract processor"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'textract_processor_fixed.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
    
    files_to_include = [
        "text_extractor_processor_updated.py",
        "standardized_messaging.py",
        "requirements.txt"
    ]
    
    try:
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_include:
                full_path = os.path.join(source_dir, file_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, file_path)
                    print(f"✅ Added {file_path}")
        
        # Update function code only
        with open(package_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-textextractor-processor',
                ZipFile=f.read()
            )
        
        print("✅ Textract processor code updated successfully")
        
        # Cleanup
        os.remove(package_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Textract processor: {e}")
        return False

if __name__ == "__main__":
    success = update_textract_processor_code()
    exit(0 if success else 1)
