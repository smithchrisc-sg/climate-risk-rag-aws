#!/usr/bin/env python3
"""
Deploy Clean Text Extractor Processor
Deploy the clean version with proper DatabaseManager pattern
"""

import boto3
import tempfile
import zipfile
import os
import shutil

def main():
    """Deploy the clean text extractor processor"""
    print("🚀 Deploying Clean Text Extractor Processor")
    print("===========================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy all processor files
        processor_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
        
        # Copy all Python files (excluding corrupted backup)
        for file in os.listdir(processor_dir):
            if file.endswith('.py') and not file.startswith('DEPRECATED') and 'corrupted' not in file:
                shutil.copy(os.path.join(processor_dir, file), temp_dir)
                print(f"  📄 Included: {file}")
        
        # Create deployment zip
        zip_path = os.path.join(temp_dir, 'processor.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(temp_dir):
                if file.endswith('.py'):
                    zipf.write(os.path.join(temp_dir, file), file)
        
        # Deploy function code
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-textextractor-processor',
                ZipFile=f.read()
            )
        
        print(f"✅ Deployed clean processor: {response['CodeSha256']}")
        print("🔧 Key improvements:")
        print("  - Uses proper DatabaseManager.get_connection_string()")
        print("  - No duplicated Secrets Manager code")
        print("  - Clean separation of concerns")
        print("  - Proper error handling")

if __name__ == "__main__":
    main()
