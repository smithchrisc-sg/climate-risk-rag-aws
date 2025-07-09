#!/usr/bin/env python3
"""
Updated NLP Deployment Script - STANDARDIZED MESSAGING VERSION
Uses nlp_processor_updated.py and nlp_worker_updated.py with standardized messaging
"""

import boto3
import zipfile
import tempfile
import os

def deploy_nlp_processor_standardized():
    """Deploy NLP processor with standardized messaging"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("🚀 Deploying NLP Processor with Standardized Messaging...")
    
    # Configuration
    account_id = "861276078413"
    region = "us-east-1"
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'nlp_processor_standardized.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/nlp_processor"
    
    files_to_include = [
        "nlp_processor_updated.py",  # UPDATED VERSION
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
                FunctionName='nlp-processor',
                ZipFile=f.read()
            )
        
        print("✅ NLP Processor code updated")
        
        # Update function configuration
        config_response = lambda_client.update_function_configuration(
            FunctionName='nlp-processor',
            Handler="nlp_processor_updated.lambda_handler",  # UPDATED HANDLER
            Environment={
                'Variables': {
                    'NLP_WORKER_TOPIC_ARN': f'arn:aws:sns:{region}:{account_id}:nlp-worker',
                    'STANDARDIZED_MESSAGING_ENABLED': 'true',
                    'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
                    'NLP_PROVIDER': 'comprehend',
                    'COMPREHEND_REGION': region
                }
            },
            Layers=[
                f'arn:aws:lambda:{region}:{account_id}:layer:climate-risk-core-utilities-pipeline:2',
                f'arn:aws:lambda:{region}:{account_id}:layer:database-dependencies-pipeline:2'
            ]
        )
        
        print("✅ NLP Processor configuration updated")
        
        # Cleanup
        os.remove(package_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying NLP processor: {e}")
        return False

def deploy_nlp_worker_standardized():
    """Deploy NLP worker with standardized messaging"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("🚀 Deploying NLP Worker with Standardized Messaging...")
    
    # Configuration
    account_id = "861276078413"
    region = "us-east-1"
    
    # Create deployment package
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'nlp_worker_standardized.zip')
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/nlp_worker"
    
    files_to_include = [
        "nlp_worker_updated.py",  # UPDATED VERSION
        "standardized_messaging.py",
        "nlp_interface.py",
        "offset_mapper.py",
        "s3_data_lake_manager.py",
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
                FunctionName='nlp-worker',
                ZipFile=f.read()
            )
        
        print("✅ NLP Worker code updated")
        
        # Update function configuration
        config_response = lambda_client.update_function_configuration(
            FunctionName='nlp-worker',
            Handler="nlp_worker_updated.lambda_handler",  # UPDATED HANDLER
            Environment={
                'Variables': {
                    'NLP_COMPLETION_TOPIC_ARN': f'arn:aws:sns:{region}:{account_id}:nlp-processing-complete',
                    'STANDARDIZED_MESSAGING_ENABLED': 'true',
                    'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
                    'NLP_PROVIDER': 'comprehend',
                    'COMPREHEND_REGION': region,
                    'NER_RESULTS_BUCKET': f'solve-global-kr-ner-results-{account_id}-{region}'
                }
            },
            Layers=[
                f'arn:aws:lambda:{region}:{account_id}:layer:climate-risk-core-utilities-pipeline:2',
                f'arn:aws:lambda:{region}:{account_id}:layer:database-dependencies-pipeline:2'
            ]
        )
        
        print("✅ NLP Worker configuration updated")
        
        # Cleanup
        os.remove(package_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying NLP worker: {e}")
        return False

def main():
    """Deploy both NLP functions with standardized messaging"""
    
    print("🚀 DEPLOYING NLP FUNCTIONS WITH STANDARDIZED MESSAGING")
    print("=" * 60)
    
    success_count = 0
    
    # Deploy NLP Processor
    if deploy_nlp_processor_standardized():
        success_count += 1
        print("✅ NLP Processor deployment successful")
    else:
        print("❌ NLP Processor deployment failed")
    
    print("\n" + "=" * 60)
    
    # Deploy NLP Worker
    if deploy_nlp_worker_standardized():
        success_count += 1
        print("✅ NLP Worker deployment successful")
    else:
        print("❌ NLP Worker deployment failed")
    
    print("\n" + "=" * 60)
    print(f"📊 Deployment Summary: {success_count}/2 successful")
    
    if success_count == 2:
        print("🎉 All NLP functions deployed with standardized messaging!")
        return True
    else:
        print("⚠️  Some NLP deployments failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
