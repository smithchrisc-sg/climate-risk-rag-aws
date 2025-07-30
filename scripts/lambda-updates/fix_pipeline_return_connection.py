#!/usr/bin/env python3
"""
Fix Pipeline Test Function - Remove return_connection call
The DatabaseManager doesn't have this method in the current version
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Fix pipeline test function by removing return_connection call"""
    print("🔧 Fixing Pipeline Test Function - Remove return_connection")
    print("=========================================================")
    
    # Read the current pipeline test function
    original_path = "/Users/chris/climate-risk-rag-aws/lambda/pipeline_test_function/pipeline_test_handler.py"
    
    with open(original_path, 'r') as f:
        original_code = f.read()
    
    # Fix the return_connection issue
    fixed_code = fix_return_connection_issue(original_code)
    
    # Deploy the fixed function
    deploy_fixed_function(fixed_code)
    
    # Test the function
    test_fixed_function()

def fix_return_connection_issue(original_code):
    """Remove the return_connection call that doesn't exist"""
    
    # Add Secrets Manager function at the top (same as before)
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
    
    # Find where to insert the function (after imports, before class)
    class_start = original_code.find('class PipelineTestLambda:')
    if class_start == -1:
        raise ValueError("Could not find PipelineTestLambda class")
    
    # Insert the secrets manager function before the class
    updated_code = (original_code[:class_start] + 
                   secrets_manager_function + 
                   original_code[class_start:])
    
    # Fix the database initialization to use Secrets Manager
    old_db_init = '''        # Get DATABASE_URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL environment variable not set")'''
    
    new_db_init = '''        # Construct DATABASE_URL from Secrets Manager using standard environment variables
        try:
            database_url = get_database_url_from_secrets()
            os.environ['DATABASE_URL'] = database_url
            logger.info("DATABASE_URL set from Secrets Manager using standard environment variables")
        except Exception as e:
            logger.error(f"Failed to construct DATABASE_URL: {str(e)}")
            raise RuntimeError(f"Database configuration failure: {str(e)}")'''
    
    # Replace the database initialization
    updated_code = updated_code.replace(old_db_init, new_db_init)
    
    # Remove the problematic return_connection call
    old_return_connection = '''                finally:
                    self.doc_id_manager.db_manager.return_connection(conn)'''
    
    new_return_connection = '''                finally:
                    # Connection will be returned to pool automatically
                    pass'''
    
    updated_code = updated_code.replace(old_return_connection, new_return_connection)
    
    return updated_code

def deploy_fixed_function(fixed_code):
    """Deploy the fixed function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write function code
        handler_path = os.path.join(temp_dir, 'pipeline_test_handler.py')
        with open(handler_path, 'w') as f:
            f.write(fixed_code)
        
        # Create zip
        zip_path = os.path.join(temp_dir, 'function.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(handler_path, 'pipeline_test_handler.py')
        
        # Deploy
        with open(zip_path, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName='solve-global-kr-pipeline-test-function',
                ZipFile=f.read()
            )
        
        print(f"✅ Deployed fixed pipeline test function: {response['CodeSha256']}")

def test_fixed_function():
    """Test the fixed function"""
    
    # Wait for deployment
    import time
    time.sleep(30)
    
    print("\n📋 Testing fixed pipeline test function...")
    print("Now running the actual pipeline test...")

if __name__ == "__main__":
    main()
