#!/usr/bin/env python3
"""
Deploy TextExtractor Lambdas with Dependencies
Include all required dependencies in the deployment packages
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

def create_lambda_package_with_deps(source_dir, package_name, include_utils=True):
    """Create Lambda package with all dependencies"""
    print(f"📦 Creating {package_name} with dependencies...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = os.path.join(temp_dir, "package")
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
        
        # Install dependencies
        print(f"   Installing Python dependencies...")
        subprocess.run([
            "pip", "install", 
            "psycopg2-binary==2.9.7",
            "boto3==1.34.0",
            "requests==2.31.0",
            "-t", package_dir
        ], check=True, capture_output=True)
        
        # Copy utility modules if needed
        if include_utils:
            utils_src = "/Users/chris/climate-risk-rag-aws/layers/app-source/utils"
            if os.path.exists(utils_src):
                utils_dst = os.path.join(package_dir, "utils")
                shutil.copytree(utils_src, utils_dst)
                print(f"   Added utility modules")
        
        # Create zip file
        zip_path = f"/tmp/{package_name}"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, package_dir)
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
    """Deploy TextExtractor Lambdas with dependencies"""
    print("🚀 TextExtractor Lambda Deployment (with dependencies)")
    print("=" * 60)
    
    # Infrastructure values
    role_arn = "arn:aws:iam::861276078413:role/solve-global-kr-textextractor-lambda-role"
    sns_topic_arn = "arn:aws:sns:us-east-1:861276078413:solve-global-kr-textract-completion"
    textract_role_arn = "arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role"
    queue_arn = "arn:aws:sqs:us-east-1:861276078413:solve-global-kr-textextractor-processor"
    database_url = "postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
    
    # Deploy TextExtractor Initiator
    print("\\n📦 TextExtractor Initiator (with dependencies)")
    initiator_zip = create_lambda_package_with_deps(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_initiator",
        "textextractor-initiator-full.zip",
        include_utils=True
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
    print("\\n📦 TextExtractor Processor (with dependencies)")
    processor_zip = create_lambda_package_with_deps(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor",
        "textextractor-processor-full.zip",
        include_utils=True
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
    
    print("\\n🎉 Deployment Complete!")
    print("\\n📋 Updated Functions:")
    print("   - solve-global-kr-textextractor-initiator (with dependencies)")
    print("   - solve-global-kr-textextractor-processor (with dependencies)")
    
    print("\\n🧪 Test the pipeline:")
    print("   aws lambda invoke --function-name solve-global-kr-textextractor-trigger --profile solve-global --region us-east-1 /tmp/test-response.json")

if __name__ == "__main__":
    main()
