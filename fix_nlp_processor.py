#!/usr/bin/env python3
"""
Fix and redeploy NLP processor with typing import
"""

import boto3
import zipfile
import tempfile
import os

def update_nlp_processor():
    """Update NLP processor with fixed typing import"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'nlp_processor_fixed.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/nlp_processor"
    
    files_to_include = [
        "nlp_processor_updated.py",
        "standardized_messaging.py",
        "requirements.txt"
    ]
    
    try:
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_include:
                full_path = os.path.join(source_dir, file_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, file_path)
                    print(f"Added {file_path} to package")
                else:
                    print(f"Warning: {file_path} not found")
        
        # Update function code
        with open(package_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='nlp-processor',
                ZipFile=f.read()
            )
        
        print("✅ NLP processor updated successfully")
        print(f"   Last modified: {response['LastModified']}")
        
        # Cleanup
        os.remove(package_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating NLP processor: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing NLP Processor typing import...")
    success = update_nlp_processor()
    
    if success:
        print("🎉 NLP processor fixed and deployed!")
    else:
        print("❌ Failed to fix NLP processor")
    
    exit(0 if success else 1)
