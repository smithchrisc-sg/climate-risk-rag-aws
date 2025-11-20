#!/usr/bin/env python3
import boto3
import zipfile
import os
from pathlib import Path

def update_code_only():
    """Update just the Lambda code"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package from lambda/search directory
    search_dir = Path('/Users/chris/climate-risk-rag-aws/lambda/search')
    zip_path = 'search_code.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in search_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                arcname = file_path.relative_to(search_dir)
                zf.write(file_path, arcname)
    
    # Update just the code
    try:
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='gaip-search-lambda',
                ZipFile=f.read()
            )
        
        print("✅ Updated Lambda code")
        print(f"📦 Code size: {response['CodeSize']} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Code update failed: {e}")
        return False
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == '__main__':
    print("📦 Updating Lambda code from lambda/search directory...")
    update_code_only()
