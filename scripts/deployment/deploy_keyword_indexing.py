#!/usr/bin/env python3
"""
Deploy Keyword Indexing Functions
Deploy both processor and worker with DatabaseManager integration
"""

import boto3
import tempfile
import zipfile
import os
import shutil

def deploy_keyword_indexer_processor():
    """Deploy the keyword indexer processor"""
    print("🚀 Deploying Keyword Indexer Processor")
    print("======================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy processor files
        processor_dir = "/Users/chris/climate-risk-rag-aws/lambda/keyword_indexer"
        
        # Copy Python files (excluding backups)
        for file in os.listdir(processor_dir):
            if file.endswith('.py') and not file.startswith('keyword_indexer_processor_'):
                shutil.copy(os.path.join(processor_dir, file), temp_dir)
                print(f"  📄 Included: {file}")
        
        # Create deployment zip
        zip_path = os.path.join(temp_dir, 'processor.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(temp_dir):
                if file.endswith('.py'):
                    zipf.write(os.path.join(temp_dir, file), file)
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName='solve-global-kr-keyword-indexer-processor')
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
        
        if function_exists:
            # Update existing function
            with open(zip_path, 'rb') as f:
                response = lambda_client.update_function_code(
                    FunctionName='solve-global-kr-keyword-indexer-processor',
                    ZipFile=f.read()
                )
            
            # Update layers
            lambda_client.update_function_configuration(
                FunctionName='solve-global-kr-keyword-indexer-processor',
                Layers=[
                    'arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:12',
                    'arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:5'
                ]
            )
            
            print(f"✅ Updated processor: {response['CodeSha256']}")
        else:
            print("⚠️ Function does not exist - would need to create via CDK")

def deploy_keyword_indexer_worker():
    """Deploy the keyword indexer worker"""
    print("\n🚀 Deploying Keyword Indexer Worker")
    print("===================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy worker files
        worker_dir = "/Users/chris/climate-risk-rag-aws/lambda/keyword_indexer_worker"
        
        # Copy Python files (excluding backups)
        for file in os.listdir(worker_dir):
            if file.endswith('.py') and not file.startswith('keyword_indexer_worker_'):
                shutil.copy(os.path.join(worker_dir, file), temp_dir)
                print(f"  📄 Included: {file}")
        
        # Create deployment zip
        zip_path = os.path.join(temp_dir, 'worker.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(temp_dir):
                if file.endswith('.py'):
                    zipf.write(os.path.join(temp_dir, file), file)
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName='solve-global-kr-keyword-indexer-worker')
            function_exists = True
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
        
        if function_exists:
            # Update existing function
            with open(zip_path, 'rb') as f:
                response = lambda_client.update_function_code(
                    FunctionName='solve-global-kr-keyword-indexer-worker',
                    ZipFile=f.read()
                )
            
            # Update layers
            lambda_client.update_function_configuration(
                FunctionName='solve-global-kr-keyword-indexer-worker',
                Layers=[
                    'arn:aws:lambda:us-east-1:861276078413:layer:climate-risk-core-utilities:12',
                    'arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies-pipeline:5'
                ]
            )
            
            print(f"✅ Updated worker: {response['CodeSha256']}")
        else:
            print("⚠️ Function does not exist - would need to create via CDK")

def main():
    """Deploy both keyword indexing functions"""
    print("🔧 Deploying Keyword Indexing Functions with DatabaseManager Integration")
    print("=======================================================================")
    
    deploy_keyword_indexer_processor()
    deploy_keyword_indexer_worker()
    
    print("\n✅ Keyword indexing deployment complete!")
    print("Both functions now use DatabaseManager methods instead of direct SQL")

if __name__ == "__main__":
    main()
