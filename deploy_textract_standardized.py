#!/usr/bin/env python3
"""
Updated Textract Deployment Script - STANDARDIZED MESSAGING VERSION
Uses text_extractor_processor_updated.py with standardized messaging
"""

import boto3
import zipfile
import tempfile
import os

def deploy_textract_processor_standardized():
    """Deploy Textract processor with standardized messaging"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("🚀 Deploying Textract Processor with Standardized Messaging...")
    
    # Configuration
    function_name = 'solve-global-kr-textextractor-processor'
    account_id = "861276078413"
    region = "us-east-1"
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'textract_processor_standardized.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
    
    files_to_include = [
        "text_extractor_processor_updated.py",  # UPDATED VERSION
        "standardized_messaging.py",
        "requirements.txt"
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
            Handler="text_extractor_processor_updated.lambda_handler",  # UPDATED HANDLER
            Environment={
                'Variables': {
                    'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN': f'arn:aws:sns:{region}:{account_id}:text-extraction-complete',
                    'STANDARDIZED_MESSAGING_ENABLED': 'true',
                    'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
                    'OUTPUT_BUCKET': f'solve-global-kr-text-new-{account_id}-{region}',
                    'NEXT_STAGE_QUEUE_URL': f'https://sqs.{region}.amazonaws.com/{account_id}/text-chunker-queue'
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
        print(f"📝 Handler: text_extractor_processor_updated.lambda_handler")
        print(f"🔗 Layers: 2 configured")
        print(f"🌍 Environment: Standardized messaging enabled")
        
        # Cleanup
        os.remove(package_path)
        
        print("\n🎉 Textract Processor Standardized Deployment Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error deploying Textract processor: {e}")
        return False

def deploy_textract_initiator_check():
    """Check and optionally update Textract initiator"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("\n🔍 Checking Textract Initiator...")
    
    try:
        response = lambda_client.get_function_configuration(
            FunctionName='solve-global-kr-textextractor-initiator'
        )
        
        print(f"✅ Textract Initiator found")
        print(f"📝 Current handler: {response['Handler']}")
        print(f"🔗 Layers: {len(response.get('Layers', []))} configured")
        
        # Check if it needs standardized messaging updates
        env_vars = response.get('Environment', {}).get('Variables', {})
        if 'STANDARDIZED_MESSAGING_ENABLED' not in env_vars:
            print("⚠️  Textract Initiator may need standardized messaging updates")
        else:
            print("✅ Textract Initiator has standardized messaging")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Textract initiator: {e}")
        return False

def main():
    """Deploy Textract functions with standardized messaging"""
    
    print("🚀 DEPLOYING TEXTRACT FUNCTIONS WITH STANDARDIZED MESSAGING")
    print("=" * 70)
    
    success_count = 0
    
    # Deploy Textract Processor
    if deploy_textract_processor_standardized():
        success_count += 1
        print("✅ Textract Processor deployment successful")
    else:
        print("❌ Textract Processor deployment failed")
    
    # Check Textract Initiator
    if deploy_textract_initiator_check():
        print("✅ Textract Initiator check completed")
    else:
        print("⚠️  Textract Initiator check had issues")
    
    print("\n" + "=" * 70)
    print(f"📊 Deployment Summary: {success_count}/1 processor deployments successful")
    
    if success_count >= 1:
        print("🎉 Textract Processor deployed with standardized messaging!")
        print("📋 Textract Initiator checked and ready")
        return True
    else:
        print("⚠️  Textract deployment needs attention")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
