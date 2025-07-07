#!/usr/bin/env python3
"""
Deploy Updated TextExtractor Processor Lambda
Deploys the new directory structure implementation
"""

import boto3
import json
import zipfile
import os
import tempfile
import shutil
from datetime import datetime

def create_lambda_package():
    """Create deployment package for updated TextExtractor Processor"""
    
    print("📦 Creating Lambda deployment package...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        package_dir = os.path.join(temp_dir, 'package')
        os.makedirs(package_dir)
        
        # Copy updated Lambda function code
        lambda_file = '/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor/text_extractor_processor.py'
        shutil.copy2(lambda_file, os.path.join(package_dir, 'lambda_function.py'))
        
        # Copy requirements if they exist
        requirements_file = '/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor/requirements.txt'
        if os.path.exists(requirements_file):
            shutil.copy2(requirements_file, package_dir)
        
        # Create zip file
        zip_path = '/Users/chris/climate-risk-rag-aws/text_extractor_processor_updated.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Created Lambda package: {zip_path}")
        return zip_path

def update_lambda_function(zip_path):
    """Update the Lambda function with new code"""
    
    print("🚀 Updating Lambda function...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Lambda function name (adjust if different)
    function_name = 'text-extractor-processor'
    
    try:
        # Read the zip file
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Last Modified: {response['LastModified']}")
        print(f"   Code Size: {response['CodeSize']} bytes")
        
        return response
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"❌ Lambda function '{function_name}' not found")
        print("   Available functions:")
        
        # List available functions
        functions = lambda_client.list_functions()
        for func in functions['Functions']:
            if 'text' in func['FunctionName'].lower() or 'extractor' in func['FunctionName'].lower():
                print(f"     - {func['FunctionName']}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return None

def update_environment_variables():
    """Update Lambda environment variables for new bucket"""
    
    print("🔧 Updating environment variables...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'text-extractor-processor'
    
    try:
        # Get current configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Update OUTPUT_BUCKET to use new bucket
        updated_env = current_env.copy()
        updated_env['OUTPUT_BUCKET'] = 'solve-global-kr-text-new-861276078413-us-east-1'
        
        # Update environment variables
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': updated_env}
        )
        
        print("✅ Environment variables updated:")
        print(f"   OUTPUT_BUCKET: {updated_env['OUTPUT_BUCKET']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating environment variables: {str(e)}")
        return False

def verify_deployment():
    """Verify the deployment was successful"""
    
    print("🔍 Verifying deployment...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'text-extractor-processor'
    
    try:
        # Get function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        print("✅ Deployment verification:")
        print(f"   Function Name: {response['FunctionName']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Last Modified: {response['LastModified']}")
        print(f"   Timeout: {response['Timeout']} seconds")
        print(f"   Memory: {response['MemorySize']} MB")
        
        # Check environment variables
        env_vars = response.get('Environment', {}).get('Variables', {})
        print(f"   Output Bucket: {env_vars.get('OUTPUT_BUCKET', 'NOT SET')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying deployment: {str(e)}")
        return False

def main():
    """Main deployment process"""
    
    print("🚀 Deploying Updated TextExtractor Processor")
    print("=" * 50)
    print(f"Deployment Time: {datetime.utcnow().isoformat()}")
    print()
    
    # Step 1: Create deployment package
    zip_path = create_lambda_package()
    if not zip_path:
        print("❌ Failed to create deployment package")
        return False
    
    # Step 2: Update Lambda function
    update_result = update_lambda_function(zip_path)
    if not update_result:
        print("❌ Failed to update Lambda function")
        return False
    
    # Step 3: Update environment variables
    env_result = update_environment_variables()
    if not env_result:
        print("⚠️  Warning: Failed to update environment variables")
    
    # Step 4: Verify deployment
    verify_result = verify_deployment()
    if not verify_result:
        print("⚠️  Warning: Could not verify deployment")
    
    # Cleanup
    try:
        os.remove(zip_path)
        print(f"🧹 Cleaned up deployment package: {zip_path}")
    except:
        pass
    
    print()
    print("✅ Deployment completed successfully!")
    print()
    print("📋 Next Steps:")
    print("  1. Test with a small document (2-3 pages)")
    print("  2. Verify new directory structure in S3")
    print("  3. Check text chunker integration")
    print("  4. Monitor processing logs")
    print()
    print("💰 Cost-Conscious Testing:")
    print("  • Use small documents to minimize Textract costs")
    print("  • Reuse existing extractions for downstream testing")
    print("  • Monitor usage to stay within budget")
    
    return True

if __name__ == "__main__":
    main()
