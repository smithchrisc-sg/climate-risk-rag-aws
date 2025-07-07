#!/usr/bin/env python3
"""
Simple TextExtractor Lambda Deployment
Deploy Lambda functions with known infrastructure values
"""

import os
import json
import subprocess
import zipfile
import tempfile
import shutil

def run_aws_command(cmd):
    """Run AWS CLI command"""
    full_cmd = f"AWS_PROFILE=solve-global AWS_DEFAULT_REGION=us-east-1 {cmd} --region us-east-1"
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        raise Exception(f"Command failed: {result.stderr}")
    return result.stdout.strip()

def create_lambda_zip(source_dir, zip_name):
    """Create Lambda deployment zip"""
    print(f"📦 Creating {zip_name}...")
    
    zip_path = f"/tmp/{zip_name}"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists(source_dir):
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arc_path)
    
    print(f"✅ Created: {zip_path}")
    return zip_path

def deploy_lambda(function_name, zip_path, handler, role_arn, env_vars, description, timeout=900):
    """Deploy Lambda function"""
    print(f"🚀 Deploying {function_name}...")
    
    # Check if function exists
    try:
        run_aws_command(f"aws lambda get-function --function-name {function_name}")
        exists = True
    except:
        exists = False
    
    env_json = json.dumps({"Variables": env_vars})
    
    if exists:
        # Update function
        run_aws_command(f"aws lambda update-function-code --function-name {function_name} --zip-file fileb://{zip_path}")
        run_aws_command(f"aws lambda update-function-configuration --function-name {function_name} --environment '{env_json}' --timeout {timeout}")
    else:
        # Create function
        run_aws_command(f"""aws lambda create-function \\
            --function-name {function_name} \\
            --runtime python3.11 \\
            --role {role_arn} \\
            --handler {handler} \\
            --zip-file fileb://{zip_path} \\
            --timeout {timeout} \\
            --memory-size 1024 \\
            --environment '{env_json}' \\
            --description "{description}" """)
    
    print(f"✅ {function_name} deployed")

def main():
    """Deploy TextExtractor Lambdas"""
    print("🚀 TextExtractor Lambda Deployment")
    print("=" * 50)
    
    # Infrastructure values from CloudFormation
    role_arn = "arn:aws:iam::861276078413:role/solve-global-kr-textextractor-lambda-role"
    sns_topic_arn = "arn:aws:sns:us-east-1:861276078413:solve-global-kr-textract-completion"
    textract_role_arn = "arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role"
    queue_arn = "arn:aws:sqs:us-east-1:861276078413:solve-global-kr-textextractor-processor"
    database_url = "postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
    
    # Deploy TextExtractor Initiator
    print("\\n📦 TextExtractor Initiator")
    initiator_zip = create_lambda_zip(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_initiator",
        "textextractor-initiator.zip"
    )
    
    deploy_lambda(
        function_name="solve-global-kr-textextractor-initiator",
        zip_path=initiator_zip,
        handler="text_extractor_initiator.lambda_handler",
        role_arn=role_arn,
        env_vars={
            "DATABASE_URL": database_url,
            "TEXTRACT_SNS_TOPIC_ARN": sns_topic_arn,
            "TEXTRACT_SERVICE_ROLE_ARN": textract_role_arn,
            "OUTPUT_BUCKET": "solve-global-kr-chunks-861276078413-us-east-1"
        },
        description="Initiates async Textract jobs",
        timeout=300
    )
    
    # Deploy TextExtractor Processor
    print("\\n📦 TextExtractor Processor")
    processor_zip = create_lambda_zip(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor",
        "textextractor-processor.zip"
    )
    
    deploy_lambda(
        function_name="solve-global-kr-textextractor-processor",
        zip_path=processor_zip,
        handler="text_extractor_processor.lambda_handler",
        role_arn=role_arn,
        env_vars={
            "DATABASE_URL": database_url,
            "OUTPUT_BUCKET": "solve-global-kr-chunks-861276078413-us-east-1",
            "NEXT_STAGE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/placeholder/text-chunker-queue"
        },
        description="Processes completed Textract jobs",
        timeout=900
    )
    
    # Set up SQS trigger for processor
    print("\\n🔗 Setting up SQS trigger...")
    try:
        run_aws_command(f"""aws lambda create-event-source-mapping \\
            --function-name solve-global-kr-textextractor-processor \\
            --event-source-arn {queue_arn} \\
            --batch-size 1 \\
            --maximum-batching-window-in-seconds 5""")
        print("✅ SQS trigger created")
    except:
        print("⚠️  SQS trigger may already exist")
    
    # Create simple trigger function
    print("\\n📦 TextExtractor Trigger")
    
    trigger_code = '''import json
import boto3

def lambda_handler(event, context):
    """Trigger TextExtractor for testing"""
    
    document = event.get('document', {
        'bucket': 'solve-global-kr-documents-861276078413-us-east-1',
        'key': 'documents/006893d2_93170cb9.pdf'
    })
    
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
                'message': 'TextExtractor triggered',
                'document': document,
                'status': response['StatusCode']
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
'''
    
    # Create trigger zip
    with tempfile.TemporaryDirectory() as temp_dir:
        trigger_file = os.path.join(temp_dir, "index.py")
        with open(trigger_file, 'w') as f:
            f.write(trigger_code)
        
        trigger_zip = create_lambda_zip(temp_dir, "textextractor-trigger.zip")
        
        deploy_lambda(
            function_name="solve-global-kr-textextractor-trigger",
            zip_path=trigger_zip,
            handler="index.lambda_handler",
            role_arn=role_arn,
            env_vars={},
            description="Manual trigger for TextExtractor testing",
            timeout=60
        )
    
    print("\\n🎉 Deployment Complete!")
    print("\\n📋 Deployed Functions:")
    print("   - solve-global-kr-textextractor-initiator")
    print("   - solve-global-kr-textextractor-processor")
    print("   - solve-global-kr-textextractor-trigger")
    
    print("\\n🧪 Test the pipeline:")
    print("   aws lambda invoke --function-name solve-global-kr-textextractor-trigger --profile solve-global /tmp/test-response.json")
    print("   cat /tmp/test-response.json")

if __name__ == "__main__":
    main()
