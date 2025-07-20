#!/usr/bin/env python3
"""
Deploy Text Extractor Processor
Deploy the updated processor with DatabaseManager integration
"""

import boto3
import tempfile
import zipfile
import os
import shutil

def main():
    """Deploy the text extractor processor"""
    print("🚀 Deploying Text Extractor Processor")
    print("=====================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy processor files
        processor_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
        
        # Copy Python files (excluding backups)
        for file in os.listdir(processor_dir):
            if file.endswith('.py') and not file.startswith('text_extractor_processor_'):
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
        
        print(f"✅ Deployed processor: {response['CodeSha256']}")

if __name__ == "__main__":
    main()
