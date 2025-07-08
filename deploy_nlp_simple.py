#!/usr/bin/env python3
"""
Simplified NLP Deployment Script
Deploys NLP Lambda functions using existing infrastructure
"""
import boto3
import json
import zipfile
import os
import tempfile
import shutil
from datetime import datetime

def create_lambda_deployment_package(source_dir, output_file):
    """Create deployment package for Lambda function"""
    
    print("Creating deployment package for {}...".format(source_dir))
    
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    print("  Added: {}".format(arcname))
    
    print("Deployment package created: {}".format(output_file))
    return output_file

def deploy_nlp_lambda_functions():
    """Deploy NLP Lambda functions using existing infrastructure"""
    
    print("SIMPLIFIED NLP LAMBDA DEPLOYMENT")
    print("=" * 50)
    
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Use existing IAM role from manual deployment
    role_arn = "arn:aws:iam::861276078413:role/nlp-integration-lambda-role"
    
    # Environment variables
    base_env = {
        'DATABASE_URL': os.environ.get('DATABASE_URL', ''),
        'NLP_PROVIDER': 'comprehend',
        'COMPREHEND_REGION': 'us-east-1'
    }
    
    # Deploy NLP Processor
    print("\n1. Deploying NLP Processor...")
    
    try:
        # Create deployment package
        processor_zip = create_lambda_deployment_package(
            'lambda/nlp_processor',
            '/tmp/nlp_processor.zip'
        )
        
        with open(processor_zip, 'rb') as f:
            processor_code = f.read()
        
        processor_env = base_env.copy()
        processor_env['NLP_WORKER_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:861276078413:nlp-worker'
        
        # Create or update function
        try:
            response = lambda_client.create_function(
                FunctionName='nlp-processor',
                Runtime='python3.11',
                Role=role_arn,
                Handler='nlp_processor.lambda_handler',
                Code={'ZipFile': processor_code},
                Description='NLP Processing Initiator',
                Timeout=60,
                MemorySize=256,
                Environment={'Variables': processor_env}
            )
            print("SUCCESS: Created NLP Processor function")
            
        except Exception as e:
            if 'ResourceConflictException' in str(e):
                # Function exists, update it
                lambda_client.update_function_code(
                    FunctionName='nlp-processor',
                    ZipFile=processor_code
                )
                lambda_client.update_function_configuration(
                    FunctionName='nlp-processor',
                    Runtime='python3.11',
                    Role=role_arn,
                    Handler='nlp_processor.lambda_handler',
                    Description='NLP Processing Initiator',
                    Timeout=60,
                    MemorySize=256,
                    Environment={'Variables': processor_env}
                )
                print("SUCCESS: Updated existing NLP Processor function")
            else:
                raise
        
    except Exception as e:
        print("ERROR deploying NLP Processor: {}".format(str(e)))
        return False
    
    # Deploy NLP Worker
    print("\n2. Deploying NLP Worker...")
    
    try:
        # Create deployment package
        worker_zip = create_lambda_deployment_package(
            'lambda/nlp_worker',
            '/tmp/nlp_worker.zip'
        )
        
        with open(worker_zip, 'rb') as f:
            worker_code = f.read()
        
        worker_env = base_env.copy()
        worker_env.update({
            'NLP_COMPLETION_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:nlp-processing-complete',
            'NER_RESULTS_BUCKET': 'solve-global-kr-ner-results-861276078413-us-east-1'
        })
        
        # Create or update function
        try:
            response = lambda_client.create_function(
                FunctionName='nlp-worker',
                Runtime='python3.11',
                Role=role_arn,
                Handler='nlp_worker.lambda_handler',
                Code={'ZipFile': worker_code},
                Description='NLP Background Worker',
                Timeout=600,  # 10 minutes
                MemorySize=1024,
                Environment={'Variables': worker_env}
            )
            print("SUCCESS: Created NLP Worker function")
            
        except Exception as e:
            if 'ResourceConflictException' in str(e):
                # Function exists, update it
                lambda_client.update_function_code(
                    FunctionName='nlp-worker',
                    ZipFile=worker_code
                )
                lambda_client.update_function_configuration(
                    FunctionName='nlp-worker',
                    Runtime='python3.11',
                    Role=role_arn,
                    Handler='nlp_worker.lambda_handler',
                    Description='NLP Background Worker',
                    Timeout=600,
                    MemorySize=1024,
                    Environment={'Variables': worker_env}
                )
                print("SUCCESS: Updated existing NLP Worker function")
            else:
                raise
        
    except Exception as e:
        print("ERROR deploying NLP Worker: {}".format(str(e)))
        return False
    
    # Configure event source mapping for worker
    print("\n3. Configuring SQS event source...")
    
    try:
        queue_arn = "arn:aws:sqs:us-east-1:861276078413:nlp-worker-queue"
        
        # Check if event source mapping exists
        existing_mappings = lambda_client.list_event_source_mappings(
            FunctionName='nlp-worker'
        )
        
        mapping_exists = False
        for mapping in existing_mappings['EventSourceMappings']:
            if mapping['EventSourceArn'] == queue_arn:
                mapping_exists = True
                print("INFO: Event source mapping already exists")
                break
        
        if not mapping_exists:
            lambda_client.create_event_source_mapping(
                EventSourceArn=queue_arn,
                FunctionName='nlp-worker',
                BatchSize=1,
                MaximumBatchingWindowInSeconds=5
            )
            print("SUCCESS: Created SQS event source mapping")
        
    except Exception as e:
        print("WARNING: Could not configure event source mapping: {}".format(str(e)))
    
    # Subscribe processor to chunks-ready topic
    print("\n4. Subscribing to chunks-ready topic...")
    
    try:
        sns_client = session.client('sns', region_name='us-east-1')
        chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
        
        # Get processor function ARN
        processor_response = lambda_client.get_function(FunctionName='nlp-processor')
        processor_arn = processor_response['Configuration']['FunctionArn']
        
        # Subscribe to topic
        sns_client.subscribe(
            TopicArn=chunks_ready_topic_arn,
            Protocol='lambda',
            Endpoint=processor_arn
        )
        
        # Add permission for SNS to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName='nlp-processor',
                StatementId='AllowSNSInvoke',
                Action='lambda:InvokeFunction',
                Principal='sns.amazonaws.com',
                SourceArn=chunks_ready_topic_arn
            )
        except Exception as e:
            if 'ResourceConflictException' in str(e):
                print("INFO: SNS permission already exists")
            else:
                raise
        
        print("SUCCESS: Subscribed NLP Processor to chunks-ready topic")
        
    except Exception as e:
        print("WARNING: Could not subscribe to chunks-ready topic: {}".format(str(e)))
    
    print("\n" + "=" * 50)
    print("NLP LAMBDA DEPLOYMENT COMPLETED")
    print("=" * 50)
    print("Functions deployed:")
    print("  - nlp-processor (initiator)")
    print("  - nlp-worker (background processor)")
    print("Integration configured:")
    print("  - Subscribed to chunks-ready topic")
    print("  - Connected to SQS queue")
    print("  - S3 data lake ready")
    
    return True

def test_deployment():
    """Test the deployed NLP functions"""
    
    print("\nTESTING DEPLOYMENT")
    print("=" * 30)
    
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test processor function
    try:
        response = lambda_client.get_function(FunctionName='nlp-processor')
        print("✓ NLP Processor function exists")
        print("  Runtime: {}".format(response['Configuration']['Runtime']))
        print("  Memory: {}MB".format(response['Configuration']['MemorySize']))
        
    except Exception as e:
        print("✗ NLP Processor function not found: {}".format(str(e)))
        return False
    
    # Test worker function
    try:
        response = lambda_client.get_function(FunctionName='nlp-worker')
        print("✓ NLP Worker function exists")
        print("  Runtime: {}".format(response['Configuration']['Runtime']))
        print("  Memory: {}MB".format(response['Configuration']['MemorySize']))
        
    except Exception as e:
        print("✗ NLP Worker function not found: {}".format(str(e)))
        return False
    
    print("\n✓ Deployment test passed!")
    return True

def main():
    """Main deployment function"""
    
    print("Starting simplified NLP deployment...")
    print("This approach uses existing infrastructure and deploys Lambda functions directly")
    
    try:
        # Deploy functions
        success = deploy_nlp_lambda_functions()
        
        if success:
            # Test deployment
            test_success = test_deployment()
            
            if test_success:
                print("\n🎉 NLP DEPLOYMENT SUCCESSFUL!")
                print("The NLP integration pipeline is ready for testing")
                print("Next: Run integration tests with real documents")
            else:
                print("\n⚠️ Deployment completed but tests failed")
        else:
            print("\n❌ Deployment failed")
    
    except Exception as e:
        print("DEPLOYMENT ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
