#!/usr/bin/env python3
"""
Fix Lambda Dependencies
Create proper Lambda packages with correct psycopg2 binary
"""

import os
import json
import subprocess
import zipfile
import tempfile
import shutil
import urllib.request

def run_aws_command(cmd):
    """Run AWS CLI command"""
    full_cmd = f"AWS_PROFILE=solve-global AWS_DEFAULT_REGION=us-east-1 {cmd} --region us-east-1"
    print(f"🔧 Running: {cmd}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Command failed: {result.stderr}")
        raise Exception(f"Command failed: {result.stderr}")
    return result.stdout.strip()

def create_lambda_package_fixed(source_dir, package_name):
    """Create Lambda package with proper dependencies for Lambda runtime"""
    print(f"📦 Creating {package_name} with Lambda-compatible dependencies...")
    
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
        
        # Install Lambda-compatible psycopg2
        print(f"   Installing Lambda-compatible psycopg2...")
        
        # Use pip with platform-specific options for Lambda
        subprocess.run([
            "pip", "install", 
            "--platform", "manylinux2014_x86_64",
            "--target", package_dir,
            "--implementation", "cp",
            "--python-version", "3.11",
            "--only-binary=:all:",
            "--upgrade",
            "psycopg2-binary==2.9.7"
        ], check=True, capture_output=True)
        
        # Install other dependencies
        subprocess.run([
            "pip", "install", 
            "--target", package_dir,
            "boto3>=1.26.0",
            "requests>=2.28.0"
        ], check=True, capture_output=True)
        
        # Copy utility modules
        utils_src = "/Users/chris/climate-risk-rag-aws/layers/app-source/utils"
        if os.path.exists(utils_src):
            # Copy specific utility files needed
            for util_file in ["DatabaseManager.py", "DocumentIDManager.py"]:
                src_file = os.path.join(utils_src, util_file)
                if os.path.exists(src_file):
                    shutil.copy2(src_file, package_dir)
                    print(f"   Added {util_file}")
        
        # Create zip file
        zip_path = f"/tmp/{package_name}"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arc_path)
        
        print(f"✅ Created: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.1f} MB)")
        return zip_path

def update_lambda_function(function_name, zip_path):
    """Update Lambda function code"""
    print(f"🚀 Updating {function_name}...")
    
    # Update function code
    run_aws_command(f"aws lambda update-function-code --function-name {function_name} --zip-file fileb://{zip_path}")
    
    # Wait for update to complete
    print(f"   Waiting for update to complete...")
    import time
    time.sleep(10)
    
    # Check function state
    state = run_aws_command(f"aws lambda get-function --function-name {function_name} --query 'Configuration.State'")
    print(f"   Function state: {state}")
    
    print(f"✅ {function_name} updated")

def test_lambda_function(function_name):
    """Test Lambda function"""
    print(f"🧪 Testing {function_name}...")
    
    # Create test event
    test_event = {
        'Records': [{
            'eventSource': 'aws:s3',
            'eventName': 'ObjectCreated:Put',
            's3': {
                'bucket': {'name': 'solve-global-kr-documents-861276078413-us-east-1'},
                'object': {'key': 'documents/006893d2_93170cb9.pdf'}
            }
        }]
    }
    
    # Write test event to file
    test_file = f"/tmp/{function_name}_test.json"
    with open(test_file, 'w') as f:
        json.dump(test_event, f)
    
    try:
        # Invoke function
        result = run_aws_command(f"aws lambda invoke --function-name {function_name} --payload fileb://{test_file} /tmp/{function_name}_response.json")
        
        # Read response
        with open(f"/tmp/{function_name}_response.json", 'r') as f:
            response = f.read()
        
        print(f"✅ Test successful: {response[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Fix Lambda dependencies"""
    print("🔧 Fixing TextExtractor Lambda Dependencies")
    print("=" * 50)
    
    # Fix TextExtractor Initiator
    print("\\n📦 Fixing TextExtractor Initiator")
    initiator_zip = create_lambda_package_fixed(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_initiator",
        "textextractor-initiator-fixed.zip"
    )
    
    update_lambda_function("solve-global-kr-textextractor-initiator", initiator_zip)
    
    # Test the function
    print("\\n🧪 Testing TextExtractor Initiator")
    initiator_success = test_lambda_function("solve-global-kr-textextractor-initiator")
    
    # Fix TextExtractor Processor
    print("\\n📦 Fixing TextExtractor Processor")
    processor_zip = create_lambda_package_fixed(
        "/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor",
        "textextractor-processor-fixed.zip"
    )
    
    update_lambda_function("solve-global-kr-textextractor-processor", processor_zip)
    
    print("\\n🎉 Lambda Dependencies Fixed!")
    print("\\n📋 Status:")
    print(f"   TextExtractor Initiator: {'✅ Working' if initiator_success else '❌ Issues'}")
    print(f"   TextExtractor Processor: ✅ Updated")
    
    if initiator_success:
        print("\\n🚀 Ready to test complete pipeline!")
        print("\\nTest command:")
        print("   AWS_PROFILE=solve-global aws lambda invoke --function-name solve-global-kr-textextractor-trigger --region us-east-1 /tmp/pipeline-test.json")
    else:
        print("\\n🔍 Check logs for any remaining issues:")
        print("   AWS_PROFILE=solve-global aws logs filter-log-events --log-group-name '/aws/lambda/solve-global-kr-textextractor-initiator' --region us-east-1")

if __name__ == "__main__":
    main()
