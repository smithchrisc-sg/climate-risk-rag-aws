#!/usr/bin/env python3
"""
Deploy TextExtractor Lambda Functions
Simplified deployment using AWS CLI to avoid CDK circular dependencies
"""

import os
import json
import subprocess
import zipfile
import tempfile
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        raise

def create_lambda_package(source_dir, package_name):
    """Create Lambda deployment package"""
    print(f"📦 Creating Lambda package for {package_name}...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = os.path.join(temp_dir, package_name)
        os.makedirs(package_dir)
        
        # Copy source code
        if os.path.exists(source_dir):
            for item in os.listdir(source_dir):
                src_path = os.path.join(source_dir, item)
                dst_path = os.path.join(package_dir, item)
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
        
        # Create zip file
        zip_path = f"/tmp/{package_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arc_path)
        
        print(f"✅ Package created: {zip_path}")
        return zip_path

def deploy_lambda_function(function_name, zip_path, handler, role_arn, environment_vars, description):
    """Deploy or update Lambda function"""
    print(f"🚀 Deploying Lambda function: {function_name}...")
    
    # Check if function exists
    try:
        run_command(
            f"aws lambda get-function --function-name {function_name} --profile solve-global",
            f"Checking if {function_name} exists"
        )
        function_exists = True
    except:
        function_exists = False
    
    if function_exists:
        # Update existing function
        run_command(
            f"aws lambda update-function-code --function-name {function_name} --zip-file fileb://{zip_path} --profile solve-global",
            f"Updating {function_name} code"
        )
        
        # Update configuration
        env_vars_json = json.dumps({"Variables": environment_vars})
        run_command(
            f"aws lambda update-function-configuration --function-name {function_name} --environment '{env_vars_json}' --profile solve-global",
            f"Updating {function_name} configuration"
        )
    else:
        # Create new function
        env_vars_json = json.dumps({"Variables": environment_vars})
        run_command(
            f"""aws lambda create-function \\
                --function-name {function_name} \\
                --runtime python3.11 \\
                --role {role_arn} \\
                --handler {handler} \\
                --zip-file fileb://{zip_path} \\
                --timeout 900 \\
                --memory-size 1024 \\
                --environment '{env_vars_json}' \\
                --description "{description}" \\
                --profile solve-global""",
            f"Creating {function_name}"
        )
    
    print(f"✅ {function_name} deployed successfully")

def setup_sqs_trigger(function_name, queue_arn):
    """Set up SQS trigger for Lambda function"""
    print(f"🔗 Setting up SQS trigger for {function_name}...")
    
    try:
        # Create event source mapping
        run_command(
            f"""aws lambda create-event-source-mapping \\
                --function-name {function_name} \\
                --event-source-arn {queue_arn} \\
                --batch-size 1 \\
                --maximum-batching-window-in-seconds 5 \\
                --profile solve-global""",
            f"Creating SQS trigger for {function_name}"
        )
    except:
        print(f"⚠️  SQS trigger may already exist for {function_name}")

def main():
    """Deploy TextExtractor Lambda functions"""
    print("🚀 TextExtractor Lambda Deployment")
    print("=" * 50)
    
    # Get stack outputs
    print("📋 Getting infrastructure details...")
    
    try:
        stack_outputs = run_command(
            "aws cloudformation describe-stacks --stack-name solve-global-kr-rag-textextractor-messaging --query 'Stacks[0].Outputs' --profile solve-global",
            "Getting CloudFormation outputs"
        )
        
        outputs = json.loads(stack_outputs)
        output_dict = {output['OutputKey']: output['OutputValue'] for output in outputs}
        
        print("✅ Infrastructure details retrieved:")
        for key, value in output_dict.items():
            print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"❌ Failed to get infrastructure details: {e}")
        return False
    
    # Get database URL from our working environment
    database_url = "postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
    
    # Deploy TextExtractor Initiator
    print("\\n📦 Deploying TextExtractor Initiator...")
    
    initiator_zip = create_lambda_package(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_initiator",
        "textextractor-initiator"
    )
    
    deploy_lambda_function(
        function_name="solve-global-kr-textextractor-initiator",
        zip_path=initiator_zip,
        handler="text_extractor_initiator.lambda_handler",
        role_arn=output_dict['TextExtractorLambdaRoleArn'],
        environment_vars={
            "DATABASE_URL": database_url,
            "TEXTRACT_SNS_TOPIC_ARN": output_dict['TextractCompletionTopicArn'],
            "TEXTRACT_SERVICE_ROLE_ARN": output_dict['TextractServiceRoleArn'],
            "OUTPUT_BUCKET": "solve-global-kr-chunks-861276078413-us-east-1"
        },
        description="Initiates async Textract jobs for document processing"
    )
    
    # Deploy TextExtractor Processor
    print("\\n📦 Deploying TextExtractor Processor...")
    
    processor_zip = create_lambda_package(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor",
        "textextractor-processor"
    )
    
    deploy_lambda_function(
        function_name="solve-global-kr-textextractor-processor",
        zip_path=processor_zip,
        handler="text_extractor_processor.lambda_handler",
        role_arn=output_dict['TextExtractorLambdaRoleArn'],
        environment_vars={
            "DATABASE_URL": database_url,
            "OUTPUT_BUCKET": "solve-global-kr-chunks-861276078413-us-east-1",
            "NEXT_STAGE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/placeholder/text-chunker-queue"
        },
        description="Processes completed Textract jobs and extracts structured data"
    )
    
    # Set up SQS trigger for processor
    setup_sqs_trigger(
        "solve-global-kr-textextractor-processor",
        output_dict['TextExtractorQueueArn']
    )
    
    # Create trigger function
    print("\\n📦 Creating TextExtractor Trigger...")
    
    trigger_code = '''
import json
import boto3
import os

def lambda_handler(event, context):
    """Manual trigger for TextExtractor Initiator"""
    
    # Default test document
    default_document = {
        'bucket': 'solve-global-kr-documents-861276078413-us-east-1',
        'key': 'documents/006893d2_93170cb9.pdf'
    }
    
    document = event.get('document', default_document)
    
    # Create S3 event format
    s3_event = {
        'Records': [{
            'eventSource': 'aws:s3',
            'eventName': 'ObjectCreated:Put',
            's3': {
                'bucket': {'name': document['bucket']},
                'object': {'key': document['key']}
            }
        }]
    }
    
    # Invoke TextExtractor Initiator
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='Event',
            Payload=json.dumps(s3_event)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'TextExtractor triggered successfully',
                'document': document,
                'response_status': response['StatusCode']
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'document': document
            })
        }
    '''
    
    # Write trigger code to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(trigger_code)
        trigger_file = f.name
    
    # Create trigger package
    trigger_zip = create_lambda_package(os.path.dirname(trigger_file), "textextractor-trigger")
    
    deploy_lambda_function(
        function_name="solve-global-kr-textextractor-trigger",
        zip_path=trigger_zip,
        handler="index.lambda_handler",
        role_arn=output_dict['TextExtractorLambdaRoleArn'],
        environment_vars={},
        description="Manual trigger for TextExtractor testing"
    )
    
    # Grant invoke permission
    try:
        run_command(
            """aws lambda add-permission \\
                --function-name solve-global-kr-textextractor-initiator \\
                --statement-id textextractor-trigger-invoke \\
                --action lambda:InvokeFunction \\
                --principal arn:aws:iam::861276078413:role/solve-global-kr-textextractor-lambda-role \\
                --profile solve-global""",
            "Granting trigger permission"
        )
    except:
        print("⚠️  Permission may already exist")
    
    print("\\n🎉 TextExtractor Lambda deployment completed!")
    print("\\n📋 Deployed functions:")
    print("   - solve-global-kr-textextractor-initiator")
    print("   - solve-global-kr-textextractor-processor")
    print("   - solve-global-kr-textextractor-trigger")
    print("\\n🧪 To test the pipeline:")
    print("   aws lambda invoke --function-name solve-global-kr-textextractor-trigger --profile solve-global /tmp/trigger-response.json")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        exit(1)
