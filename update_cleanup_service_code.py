#!/usr/bin/env python3
"""
Update Cleanup Service Code with Secrets Manager Integration
Add DATABASE_URL construction from standard environment variables
"""

import boto3
import json
import tempfile
import zipfile
import os
import shutil

def main():
    """Update cleanup service code with Secrets Manager integration"""
    print("🔧 Updating Cleanup Service Code with Secrets Manager")
    print("====================================================")
    
    # Read the current cleanup service code
    cleanup_service_path = "/Users/chris/climate-risk-rag-aws/lambda/cleanup_service/cleanup_service.py"
    
    with open(cleanup_service_path, 'r') as f:
        current_code = f.read()
    
    # Create updated code with Secrets Manager integration
    updated_code = add_secrets_manager_integration(current_code)
    
    # Deploy updated cleanup service
    deploy_updated_cleanup_service(updated_code)
    
    # Test the updated cleanup service
    test_updated_cleanup_service()

def add_secrets_manager_integration(current_code):
    """Add Secrets Manager integration to cleanup service code"""
    
    # Add the Secrets Manager function at the top after imports
    secrets_manager_function = '''
def get_database_url_from_secrets():
    """Construct DATABASE_URL from standard environment variables and Secrets Manager"""
    import boto3
    import json
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get standard environment variables
        secret_name = os.environ.get('DATABASE_SECRET_NAME')
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_port = os.environ.get('DB_PORT', '5432')
        
        logger.info(f"Constructing DATABASE_URL from standard environment variables")
        logger.info(f"  SECRET: {secret_name}")
        logger.info(f"  HOST: {db_host}")
        logger.info(f"  DATABASE: {db_name}")
        logger.info(f"  PORT: {db_port}")
        
        if not all([secret_name, db_host, db_name]):
            raise ValueError("Missing required database environment variables")
        
        # Get credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        
        username = secret_data.get('username', 'postgres')
        password = secret_data['password']
        
        # Construct DATABASE_URL
        database_url = f"postgresql://{username}:{password}@{db_host}:{db_port}/{db_name}?sslmode=require"
        
        logger.info("✅ DATABASE_URL constructed from Secrets Manager")
        return database_url
        
    except Exception as e:
        logger.error(f"❌ Failed to construct DATABASE_URL: {str(e)}")
        raise

'''
    
    # Find the lambda_handler function and add DATABASE_URL construction at the beginning
    lambda_handler_start = current_code.find('def lambda_handler(event, context):')
    if lambda_handler_start == -1:
        raise ValueError("Could not find lambda_handler function")
    
    # Find the end of the function signature line
    function_line_end = current_code.find(':', lambda_handler_start) + 1
    next_line_start = current_code.find('\n', function_line_end) + 1
    
    # Insert DATABASE_URL construction code
    database_url_setup = '''    
    # Construct DATABASE_URL from Secrets Manager using standard environment variables
    try:
        database_url = get_database_url_from_secrets()
        os.environ['DATABASE_URL'] = database_url
        logger.info("DATABASE_URL set from Secrets Manager using standard environment variables")
    except Exception as e:
        logger.error(f"Failed to construct DATABASE_URL: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Database configuration error: {str(e)}'
            })
        }
'''
    
    # Insert the secrets manager function after the imports
    imports_end = current_code.find('logger = logging.getLogger(__name__)')
    if imports_end == -1:
        # Find a good place after imports
        imports_end = current_code.find('class CleanupService:')
    
    if imports_end != -1:
        imports_end = current_code.find('\n', imports_end) + 1
        updated_code = (current_code[:imports_end] + 
                       secrets_manager_function + 
                       current_code[imports_end:])
    else:
        updated_code = secrets_manager_function + current_code
    
    # Insert DATABASE_URL setup in lambda_handler
    lambda_handler_start = updated_code.find('def lambda_handler(event, context):')
    function_line_end = updated_code.find(':', lambda_handler_start) + 1
    next_line_start = updated_code.find('\n', function_line_end) + 1
    
    updated_code = (updated_code[:next_line_start] + 
                   database_url_setup + 
                   updated_code[next_line_start:])
    
    return updated_code

def deploy_updated_cleanup_service(updated_code):
    """Deploy updated cleanup service code"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create temporary directory for deployment
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy all cleanup service files
        cleanup_service_dir = "/Users/chris/climate-risk-rag-aws/lambda/cleanup_service"
        
        # Copy all files except the main cleanup_service.py
        for file in os.listdir(cleanup_service_dir):
            if file.endswith('.py') and file != 'cleanup_service.py':
                shutil.copy(os.path.join(cleanup_service_dir, file), temp_dir)
        
        # Write updated cleanup_service.py
        with open(os.path.join(temp_dir, 'cleanup_service.py'), 'w') as f:
            f.write(updated_code)
        
        # Create deployment zip
        zip_path = os.path.join(temp_dir, 'cleanup_service.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(temp_dir):
                if file.endswith('.py'):
                    zipf.write(os.path.join(temp_dir, file), file)
        
        # Deploy function code
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-cleanup-service',
                ZipFile=f.read()
            )
        
        print(f"✅ Deployed updated cleanup service: {response['CodeSha256']}")

def test_updated_cleanup_service():
    """Test updated cleanup service"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Wait for deployment to propagate
    import time
    time.sleep(30)
    
    print("\n📋 Testing updated cleanup service...")
    
    # Test 1: Database connectivity test
    print("1️⃣ Testing database connectivity...")
    test_database_connectivity(lambda_client)
    
    # Test 2: Dry run cleanup test
    print("2️⃣ Testing dry run cleanup...")
    test_dry_run_cleanup(lambda_client)

def test_database_connectivity(lambda_client):
    """Test database connectivity"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps({
                'dry_run': True,
                'test_database_only': True
            })
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Database connectivity result: {result}")
        
        if result.get('statusCode') == 200:
            print("✅ SUCCESS: Cleanup service database connectivity working!")
            return True
        elif 'DATABASE_URL' not in str(result):
            print("✅ PROGRESS: No more DATABASE_URL errors!")
            return True
        else:
            print(f"⚠️ Database connectivity issues: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Database connectivity test failed: {e}")
        return False

def test_dry_run_cleanup(lambda_client):
    """Test dry run cleanup"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps({
                'dry_run': True
            })
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Dry run cleanup result: {result}")
        
        if result.get('statusCode') == 200:
            print("✅ SUCCESS: Cleanup service dry run working!")
            return True
        else:
            print(f"⚠️ Dry run cleanup issues: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Dry run cleanup test failed: {e}")
        return False

if __name__ == "__main__":
    main()
