#!/usr/bin/env python3
"""
Manual deployment script for KG components
"""
import boto3
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def create_lambda_zip(lambda_dir, zip_name):
    """Create a zip file for Lambda deployment"""
    print(f"\n📦 Creating zip file for {lambda_dir}")
    
    zip_path = f"/tmp/{zip_name}"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        lambda_path = Path(lambda_dir)
        for file_path in lambda_path.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                arcname = file_path.relative_to(lambda_path)
                zipf.write(file_path, arcname)
    
    print(f"✅ Created {zip_path}")
    return zip_path

def deploy_lambda_function(function_name, zip_path, handler, description, timeout=300, memory=512, env_vars=None):
    """Deploy or update a Lambda function"""
    print(f"\n🚀 Deploying Lambda function: {function_name}")
    
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda')
    
    # Check if function exists
    try:
        lambda_client.get_function(FunctionName=function_name)
        function_exists = True
        print(f"Function {function_name} exists, updating...")
    except lambda_client.exceptions.ResourceNotFoundException:
        function_exists = False
        print(f"Function {function_name} does not exist, creating...")
    
    # Read zip file
    with open(zip_path, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    if function_exists:
        # Update function code
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # Update function configuration
        if env_vars:
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Timeout=timeout,
                MemorySize=memory,
                Environment={'Variables': env_vars}
            )
    else:
        # Create function
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role='arn:aws:iam::861276078413:role/document-processing-lambda-role',
            Handler=handler,
            Code={'ZipFile': zip_content},
            Description=description,
            Timeout=timeout,
            MemorySize=memory,
            Layers=[
                'arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16'
            ],
            Environment={'Variables': env_vars or {}},
            VpcConfig={
                'SubnetIds': ['subnet-03d8bd6cf3491f38c', 'subnet-0c0be1dd59f70f70e'],
                'SecurityGroupIds': ['sg-0c9e10b9cfb4c9eb0']
            }
        )
    
    print(f"✅ Lambda function {function_name} deployed successfully")

def create_sns_topic(topic_name, display_name):
    """Create SNS topic if it doesn't exist"""
    print(f"\n📢 Creating SNS topic: {topic_name}")
    
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns')
    
    try:
        response = sns_client.create_topic(
            Name=topic_name,
            Attributes={
                'DisplayName': display_name
            }
        )
        topic_arn = response['TopicArn']
        print(f"✅ SNS topic created: {topic_arn}")
        return topic_arn
    except Exception as e:
        print(f"❌ Failed to create SNS topic: {e}")
        return None

def subscribe_lambda_to_sns(topic_arn, function_name):
    """Subscribe Lambda function to SNS topic"""
    print(f"\n🔗 Subscribing {function_name} to SNS topic")
    
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns')
    lambda_client = session.client('lambda')
    
    # Get function ARN
    function_response = lambda_client.get_function(FunctionName=function_name)
    function_arn = function_response['Configuration']['FunctionArn']
    
    # Subscribe to topic
    subscription_response = sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='lambda',
        Endpoint=function_arn
    )
    
    # Add permission for SNS to invoke Lambda
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=f'AllowSNSInvoke-{topic_arn.split(":")[-1]}',
            Action='lambda:InvokeFunction',
            Principal='sns.amazonaws.com',
            SourceArn=topic_arn
        )
    except lambda_client.exceptions.ResourceConflictException:
        print("Permission already exists")
    
    print(f"✅ Subscription created: {subscription_response['SubscriptionArn']}")

def main():
    """Deploy KG components"""
    print("🚀 Deploying KG Integration Components")
    print("=" * 60)
    
    # Standard environment variables
    standard_env = {
        "DATABASE_SECRET_NAME": "rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863",
        "DB_PORT": "5432",
        "DB_NAME": "climate_risk_rag",
        "DB_HOST": "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
    }
    
    # 1. Create kg-triples-ready SNS topic
    kg_triples_ready_topic_arn = create_sns_topic(
        "kg-triples-ready",
        "Knowledge Graph Triples Ready for Neptune Loading"
    )
    
    if not kg_triples_ready_topic_arn:
        print("❌ Failed to create kg-triples-ready topic")
        sys.exit(1)
    
    # 2. Deploy Document Structure KG Processor
    doc_kg_zip = create_lambda_zip(
        "lambda/document-structure-kg-processor",
        "document-structure-kg-processor.zip"
    )
    
    doc_kg_env = {
        **standard_env,
        "CHUNKS_BUCKET": "solve-global-kr-dl-chunks-861276078413-us-east-1",
        "TEXT_BUCKET": "solve-global-kr-dl-text-861276078413-us-east-1",
        "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1",
        "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
        "NEPTUNE_PORT": "8182",
        "KG_TRIPLES_READY_TOPIC_ARN": kg_triples_ready_topic_arn
    }
    
    deploy_lambda_function(
        "document-structure-kg-processor",
        doc_kg_zip,
        "handler.lambda_handler",
        "Document Structure KG Processor",
        timeout=300,
        memory=1024,
        env_vars=doc_kg_env
    )
    
    # 3. Deploy KG Integration Worker
    kg_worker_zip = create_lambda_zip(
        "lambda/kg-integration-worker",
        "kg-integration-worker.zip"
    )
    
    kg_worker_env = {
        **standard_env,
        "NEPTUNE_ENDPOINT": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
        "NEPTUNE_PORT": "8182",
        "TTL_BUCKET": "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
    }
    
    deploy_lambda_function(
        "kg-integration-worker",
        kg_worker_zip,
        "handler.lambda_handler",
        "KG Integration Worker for Neptune Loading",
        timeout=600,
        memory=512,
        env_vars=kg_worker_env
    )
    
    # 4. Subscribe Document Structure KG Processor to chunks-ready topic
    chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
    subscribe_lambda_to_sns(chunks_ready_topic_arn, "document-structure-kg-processor")
    
    # 5. Subscribe KG Integration Worker to kg-triples-ready topic
    subscribe_lambda_to_sns(kg_triples_ready_topic_arn, "kg-integration-worker")
    
    print("\n🎉 KG Integration Components Deployment Complete!")
    print("=" * 60)
    print("\n📋 Deployed Components:")
    print(f"• SNS Topic: kg-triples-ready ({kg_triples_ready_topic_arn})")
    print("• Lambda Function: document-structure-kg-processor")
    print("• Lambda Function: kg-integration-worker")
    print("• SNS Subscriptions: chunks-ready → document-structure-kg-processor")
    print("• SNS Subscriptions: kg-triples-ready → kg-integration-worker")
    
    print("\n🔧 Next Steps:")
    print("1. Test the pipeline with a sample document")
    print("2. Monitor CloudWatch logs for proper operation")
    print("3. Verify TTL generation and Neptune loading")

if __name__ == "__main__":
    main()
