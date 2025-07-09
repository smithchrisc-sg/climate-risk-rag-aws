#!/usr/bin/env python3
"""
Updated Text Chunker Deployment Script - STANDARDIZED MESSAGING VERSION
Uses text_chunker_processor_updated.py with standardized messaging
"""

import boto3
import zipfile
import tempfile
import os

def deploy_text_chunker_standardized():
    """Deploy text chunker with standardized messaging configuration"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("🚀 Deploying Text Chunker with Standardized Messaging...")
    
    # Configuration
    function_name = 'text-chunker-pipeline'
    account_id = "861276078413"
    region = "us-east-1"
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'text_chunker_standardized.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker"
    
    files_to_include = [
        "text_chunker_processor_updated.py",  # UPDATED VERSION
        "standardized_messaging.py"
    ]
    
    try:
        # Create ZIP package
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_include:
                full_path = os.path.join(source_dir, file_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, file_path)
                    print(f"✅ Added {file_path}")
                else:
                    print(f"⚠️  Warning: {file_path} not found")
        
        # Update function code
        with open(package_path, 'rb') as f:
            code_response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        print("✅ Code updated successfully")
        
        # Update function configuration with standardized messaging
        config_response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Handler="text_chunker_processor_updated.lambda_handler",  # UPDATED HANDLER
            Environment={
                'Variables': {
                    'CHUNKS_READY_TOPIC_ARN': f'arn:aws:sns:{region}:{account_id}:chunks-ready',
                    'STANDARDIZED_MESSAGING_ENABLED': 'true',
                    'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
                    'TEXT_BUCKET': f'solve-global-kr-text-new-{account_id}-{region}',
                    'CHUNKS_BUCKET': f'solve-global-kr-chunks-{account_id}-{region}',
                    'PHASE': 'PRODUCTION_PIPELINE'
                }
            },
            Layers=[
                f'arn:aws:lambda:{region}:{account_id}:layer:climate-risk-core-utilities-pipeline:2',
                f'arn:aws:lambda:{region}:{account_id}:layer:database-dependencies-pipeline:2'
            ],
            Timeout=900,
            MemorySize=1024
        )
        
        print("✅ Configuration updated successfully")
        print(f"📝 Handler: text_chunker_processor_updated.lambda_handler")
        print(f"🔗 Layers: 2 configured")
        print(f"🌍 Environment: Standardized messaging enabled")
        
        # Cleanup
        os.remove(package_path)
        
        print("\n🎉 Text Chunker Standardized Deployment Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying text chunker: {e}")
        return False

if __name__ == "__main__":
    success = deploy_text_chunker_standardized()
    exit(0 if success else 1)
