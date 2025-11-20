#!/usr/bin/env python3
import boto3
import zipfile
import os
from pathlib import Path

def deploy_proper_search_lambda():
    """Deploy the complete search Lambda from lambda/search directory"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package from lambda/search directory
    search_dir = Path('/Users/chris/climate-risk-rag-aws/lambda/search')
    zip_path = 'proper_search_lambda.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in search_dir.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                arcname = file_path.relative_to(search_dir)
                zf.write(file_path, arcname)
    
    # Update the existing Lambda function
    try:
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='gaip-search-lambda',
                ZipFile=f.read()
            )
        
        # Update handler to use the proper handler
        lambda_client.update_function_configuration(
            FunctionName='gaip-search-lambda',
            Handler='handler.lambda_handler',
            Timeout=60,
            MemorySize=1024
        )
        
        print("✅ Deployed proper search Lambda")
        print(f"📦 Function ARN: {response['FunctionArn']}")
        print(f"🔧 Handler: handler.lambda_handler")
        print(f"📁 Source: {search_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == '__main__':
    print("🚀 Deploying proper search Lambda from lambda/search directory...")
    if deploy_proper_search_lambda():
        print("\n✅ Proper search Lambda deployed!")
        print("🌐 Test: http://gaip-api-test-webapp-1758042975.s3-website-us-east-1.amazonaws.com")
    else:
        print("\n❌ Deployment failed")
