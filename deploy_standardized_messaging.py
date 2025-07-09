#!/usr/bin/env python3
"""
Deployment Script for Standardized Messaging
Updates Lambda functions with standardized message handling
"""

import boto3
import json
import os
import zipfile
import tempfile
import shutil
from datetime import datetime

def create_lambda_deployment_package(source_dir, files_to_include):
    """Create a deployment package for Lambda function"""
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    package_path = os.path.join(temp_dir, 'deployment_package.zip')
    
    try:
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add specified files
            for file_path in files_to_include:
                full_path = os.path.join(source_dir, file_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, file_path)
                    print(f"Added {file_path} to package")
                else:
                    print(f"Warning: {file_path} not found")
        
        return package_path
        
    except Exception as e:
        print(f"Error creating deployment package: {e}")
        return None

def update_lambda_function(function_name, package_path, environment_updates=None):
    """Update Lambda function with new code and environment variables"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Update function code
        with open(package_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        print(f"✅ Updated code for {function_name}")
        
        # Update environment variables if provided
        if environment_updates:
            # Get current environment
            current_config = lambda_client.get_function_configuration(FunctionName=function_name)
            current_env = current_config.get('Environment', {}).get('Variables', {})
            
            # Merge with updates
            updated_env = {**current_env, **environment_updates}
            
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': updated_env}
            )
            
            print(f"✅ Updated environment variables for {function_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating {function_name}: {e}")
        return False

def deploy_textract_processor():
    """Deploy updated Textract processor with standardized messaging"""
    
    print("🚀 Deploying Textract Processor with standardized messaging...")
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor"
    
    files_to_include = [
        "text_extractor_processor_updated.py",
        "standardized_messaging.py",
        "requirements.txt"
    ]
    
    # Create deployment package
    package_path = create_lambda_deployment_package(source_dir, files_to_include)
    if not package_path:
        return False
    
    # Environment updates
    environment_updates = {
        'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:text-extraction-complete',
        'STANDARDIZED_MESSAGING_ENABLED': 'true'
    }
    
    # Update Lambda function
    success = update_lambda_function(
        'solve-global-kr-textextractor-processor',
        package_path,
        environment_updates
    )
    
    # Cleanup
    os.remove(package_path)
    
    return success

def deploy_text_chunker():
    """Deploy updated Text Chunker with standardized messaging"""
    
    print("🚀 Deploying Text Chunker with standardized messaging...")
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/text_chunker"
    
    files_to_include = [
        "text_chunker_processor_updated.py",
        "standardized_messaging.py",
        "requirements.txt"
    ]
    
    # Create deployment package
    package_path = create_lambda_deployment_package(source_dir, files_to_include)
    if not package_path:
        return False
    
    # Environment updates
    environment_updates = {
        'CHUNKS_READY_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:chunks-ready',
        'STANDARDIZED_MESSAGING_ENABLED': 'true'
    }
    
    # Update Lambda function
    success = update_lambda_function(
        'text-chunker-pipeline',
        package_path,
        environment_updates
    )
    
    # Cleanup
    os.remove(package_path)
    
    return success

def deploy_nlp_processor():
    """Deploy updated NLP Processor with standardized messaging"""
    
    print("🚀 Deploying NLP Processor with standardized messaging...")
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/nlp_processor"
    
    files_to_include = [
        "nlp_processor_updated.py",
        "standardized_messaging.py",
        "requirements.txt"
    ]
    
    # Create deployment package
    package_path = create_lambda_deployment_package(source_dir, files_to_include)
    if not package_path:
        return False
    
    # Environment updates
    environment_updates = {
        'NLP_WORKER_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:nlp-worker',
        'STANDARDIZED_MESSAGING_ENABLED': 'true'
    }
    
    # Update Lambda function
    success = update_lambda_function(
        'nlp-processor',
        package_path,
        environment_updates
    )
    
    # Cleanup
    os.remove(package_path)
    
    return success

def deploy_nlp_worker():
    """Deploy updated NLP Worker with standardized messaging"""
    
    print("🚀 Deploying NLP Worker with standardized messaging...")
    
    source_dir = "/Users/chris/climate-risk-rag-aws/lambda/nlp_worker"
    
    files_to_include = [
        "nlp_worker_updated.py",
        "standardized_messaging.py",
        "nlp_interface.py",
        "offset_mapper.py",
        "s3_data_lake_manager.py",
        "requirements.txt"
    ]
    
    # Create deployment package
    package_path = create_lambda_deployment_package(source_dir, files_to_include)
    if not package_path:
        return False
    
    # Environment updates
    environment_updates = {
        'NLP_COMPLETION_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:nlp-processing-complete',
        'STANDARDIZED_MESSAGING_ENABLED': 'true'
    }
    
    # Update Lambda function
    success = update_lambda_function(
        'nlp-worker',
        package_path,
        environment_updates
    )
    
    # Cleanup
    os.remove(package_path)
    
    return success

def create_missing_sns_topics():
    """Create any missing SNS topics for standardized messaging"""
    
    print("🔧 Creating missing SNS topics...")
    
    sns = boto3.client('sns', region_name='us-east-1')
    
    required_topics = [
        'text-extraction-complete',
        'nlp-processing-complete',
        'vector-embeddings-complete',
        'keyword-indexing-complete'
    ]
    
    # List existing topics
    existing_topics = []
    try:
        response = sns.list_topics()
        for topic in response['Topics']:
            topic_name = topic['TopicArn'].split(':')[-1]
            existing_topics.append(topic_name)
    except Exception as e:
        print(f"Error listing topics: {e}")
        return False
    
    # Create missing topics
    created_topics = []
    for topic_name in required_topics:
        if topic_name not in existing_topics:
            try:
                response = sns.create_topic(Name=topic_name)
                created_topics.append(topic_name)
                print(f"✅ Created SNS topic: {topic_name}")
            except Exception as e:
                print(f"❌ Error creating topic {topic_name}: {e}")
                return False
        else:
            print(f"✅ SNS topic already exists: {topic_name}")
    
    if created_topics:
        print(f"Created {len(created_topics)} new SNS topics")
    
    return True

def update_lambda_handler_references():
    """Update Lambda function handler references to use updated files"""
    
    print("🔧 Updating Lambda handler references...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    handler_updates = [
        {
            'function_name': 'solve-global-kr-textextractor-processor',
            'handler': 'text_extractor_processor_updated.lambda_handler'
        },
        {
            'function_name': 'text-chunker-pipeline',
            'handler': 'text_chunker_processor_updated.lambda_handler'
        },
        {
            'function_name': 'nlp-processor',
            'handler': 'nlp_processor_updated.lambda_handler'
        },
        {
            'function_name': 'nlp-worker',
            'handler': 'nlp_worker_updated.lambda_handler'
        }
    ]
    
    for update in handler_updates:
        try:
            lambda_client.update_function_configuration(
                FunctionName=update['function_name'],
                Handler=update['handler']
            )
            print(f"✅ Updated handler for {update['function_name']}")
        except Exception as e:
            print(f"❌ Error updating handler for {update['function_name']}: {e}")
            return False
    
    return True

def main():
    """Main deployment function"""
    
    print("🚀 Starting Standardized Messaging Deployment")
    print("=" * 60)
    
    # Step 1: Create missing SNS topics
    if not create_missing_sns_topics():
        print("❌ Failed to create SNS topics")
        return False
    
    print("\n" + "=" * 60)
    
    # Step 2: Deploy Lambda functions
    deployments = [
        ("Textract Processor", deploy_textract_processor),
        ("Text Chunker", deploy_text_chunker),
        ("NLP Processor", deploy_nlp_processor),
        ("NLP Worker", deploy_nlp_worker)
    ]
    
    successful_deployments = 0
    
    for name, deploy_func in deployments:
        print(f"\n📦 Deploying {name}...")
        if deploy_func():
            print(f"✅ {name} deployed successfully")
            successful_deployments += 1
        else:
            print(f"❌ {name} deployment failed")
    
    print("\n" + "=" * 60)
    
    # Step 3: Update handler references
    if not update_lambda_handler_references():
        print("❌ Failed to update Lambda handler references")
        return False
    
    print("\n" + "=" * 60)
    print("📊 Deployment Summary:")
    print(f"✅ Successful deployments: {successful_deployments}/{len(deployments)}")
    print(f"✅ SNS topics configured")
    print(f"✅ Lambda handlers updated")
    
    if successful_deployments == len(deployments):
        print("\n🎉 Standardized Messaging Deployment Complete!")
        print("🔄 The pipeline now uses standardized message formats")
        print("📋 Ready for end-to-end testing")
        return True
    else:
        print(f"\n⚠️  Partial deployment: {successful_deployments}/{len(deployments)} functions updated")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
