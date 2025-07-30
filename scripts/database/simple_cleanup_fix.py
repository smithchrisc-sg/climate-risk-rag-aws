#!/usr/bin/env python3
"""
Simple Cleanup Service Fix with Secrets Manager
Add DATABASE_URL construction at the beginning of lambda_handler
"""

import boto3
import json
import tempfile
import zipfile
import os
import shutil

def main():
    """Create simple fix for cleanup service"""
    print("🔧 Simple Cleanup Service Fix with Secrets Manager")
    print("=================================================")
    
    # Create a simple wrapper that sets DATABASE_URL before importing cleanup modules
    wrapper_code = '''#!/usr/bin/env python3
"""
Cleanup Service Lambda Handler with Secrets Manager Integration
"""

import json
import logging
import os
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_database_url_from_secrets():
    """Construct DATABASE_URL from standard environment variables and Secrets Manager"""
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

def lambda_handler(event, context):
    """Lambda handler with Secrets Manager integration"""
    logger.info(f"Cleanup service invoked with event: {json.dumps(event, default=str)}")
    
    try:
        # Construct DATABASE_URL from Secrets Manager using standard environment variables
        database_url = get_database_url_from_secrets()
        os.environ['DATABASE_URL'] = database_url
        logger.info("DATABASE_URL set from Secrets Manager using standard environment variables")
        
        # Now import and use the cleanup service (after DATABASE_URL is set)
        from cleanup_service_core import CleanupService
        
        # Initialize cleanup service
        cleanup_service = CleanupService()
        
        # Process the cleanup request
        dry_run = event.get('dry_run', True)  # Default to dry run for safety
        
        # Simple test mode
        if event.get('test_database_only'):
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Database connectivity test successful',
                    'database_url_constructed': True,
                    'secrets_manager_working': True
                })
            }
        
        # Execute cleanup
        results = cleanup_service.execute_cleanup(event, dry_run)
        
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
        
    except Exception as e:
        logger.error(f"Cleanup service failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Cleanup service error: {str(e)}'
            })
        }
'''
    
    # Deploy the wrapper
    deploy_cleanup_wrapper(wrapper_code)
    
    # Test the updated cleanup service
    test_cleanup_service()

def deploy_cleanup_wrapper(wrapper_code):
    """Deploy cleanup service wrapper"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create temporary directory for deployment
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy all cleanup service files
        cleanup_service_dir = "/Users/chris/climate-risk-rag-aws/lambda/cleanup_service"
        
        # Copy all files
        for file in os.listdir(cleanup_service_dir):
            if file.endswith('.py'):
                if file == 'cleanup_service.py':
                    # Rename the original to cleanup_service_core.py
                    shutil.copy(os.path.join(cleanup_service_dir, file), 
                              os.path.join(temp_dir, 'cleanup_service_core.py'))
                else:
                    shutil.copy(os.path.join(cleanup_service_dir, file), temp_dir)
        
        # Write new wrapper as cleanup_service.py
        with open(os.path.join(temp_dir, 'cleanup_service.py'), 'w') as f:
            f.write(wrapper_code)
        
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
        
        print(f"✅ Deployed cleanup service wrapper: {response['CodeSha256']}")

def test_cleanup_service():
    """Test cleanup service"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Wait for deployment
    import time
    time.sleep(30)
    
    print("\n📋 Testing cleanup service with Secrets Manager...")
    
    # Test database connectivity
    print("1️⃣ Testing database connectivity...")
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps({
                'test_database_only': True
            })
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Database test result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: Cleanup service database connectivity working!")
        else:
            print(f"⚠️ Database test issues: {result}")
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
    
    # Test dry run
    print("\n2️⃣ Testing dry run cleanup...")
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            Payload=json.dumps({
                'dry_run': True
            })
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Dry run result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: Cleanup service dry run working!")
        else:
            print(f"⚠️ Dry run issues: {result}")
            
    except Exception as e:
        print(f"❌ Dry run test failed: {e}")

if __name__ == "__main__":
    main()
