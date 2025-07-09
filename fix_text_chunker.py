#!/usr/bin/env python3
"""
Fix and redeploy text chunker with corrected SmartStructuredChunker parameters
"""

import boto3
import zipfile
import tempfile
import os

def update_text_chunker():
    """Update text chunker with fixed code"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'text_chunker_fixed.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker"
    
    files_to_include = [
        "text_chunker_processor_updated.py",
        "standardized_messaging.py"
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
                FunctionName='text-chunker-pipeline',
                ZipFile=f.read()
            )
        
        print("✅ Text chunker updated successfully")
        print(f"   Last modified: {response['LastModified']}")
        
        # Cleanup
        os.remove(package_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating text chunker: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing Text Chunker SmartStructuredChunker parameters...")
    success = update_text_chunker()
    
    if success:
        print("🎉 Text chunker fixed and deployed!")
    else:
        print("❌ Failed to fix text chunker")
    
    exit(0 if success else 1)
