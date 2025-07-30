#!/usr/bin/env python3
"""
Restore Original Pipeline Test Function with Database Layer Updates
Keep the original functionality, only add Secrets Manager integration
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Restore original pipeline test function with database layer updates"""
    print("🔧 Restoring Original Pipeline Test Function")
    print("===========================================")
    
    # Read the original pipeline test function
    original_path = "/Users/chris/climate-risk-rag-aws/lambda/pipeline_test_function/pipeline_test_handler.py"
    
    with open(original_path, 'r') as f:
        original_code = f.read()
    
    # Create updated version with only database layer changes
    updated_code = add_secrets_manager_to_original(original_code)
    
    # Deploy the updated function
    deploy_updated_function(updated_code)
    
    # Test the function
    test_restored_function()

def add_secrets_manager_to_original(original_code):
    """Add Secrets Manager integration to original code without changing functionality"""
    
    # Add Secrets Manager function at the top
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
    
    # Find the __init__ method and update it to use Secrets Manager
    init_start = updated_code.find('def __init__(self):')
    if init_start == -1:
        raise ValueError("Could not find __init__ method")
    
    # Find the database initialization part and replace it
    old_db_init = '''        # Get DATABASE_URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Initialize DocumentIDManager with DATABASE_URL
        if DocumentIDManager is None:
            raise ImportError("DocumentIDManager module not available")
        
        try:
            self.doc_id_manager = DocumentIDManager(database_url)
            logger.info("DocumentIDManager initialized successfully")
        except Exception as e:
            # Treat database connectivity as a hard requirement
            logger.error(f"FATAL ERROR: DocumentIDManager initialization failed: {str(e)}")
            logger.error("Database connectivity is required for pipeline operation")
            raise RuntimeError(f"Database connectivity failure: {str(e)}")'''
    
    new_db_init = '''        # Construct DATABASE_URL from Secrets Manager using standard environment variables
        try:
            database_url = get_database_url_from_secrets()
            os.environ['DATABASE_URL'] = database_url
            logger.info("DATABASE_URL set from Secrets Manager using standard environment variables")
        except Exception as e:
            logger.error(f"Failed to construct DATABASE_URL: {str(e)}")
            raise RuntimeError(f"Database configuration failure: {str(e)}")
        
        # Initialize DocumentIDManager with DATABASE_URL
        if DocumentIDManager is None:
            raise ImportError("DocumentIDManager module not available")
        
        try:
            self.doc_id_manager = DocumentIDManager(database_url)
            logger.info("DocumentIDManager initialized successfully")
        except Exception as e:
            # Treat database connectivity as a hard requirement
            logger.error(f"FATAL ERROR: DocumentIDManager initialization failed: {str(e)}")
            logger.error("Database connectivity is required for pipeline operation")
            raise RuntimeError(f"Database connectivity failure: {str(e)}")'''
    
    # Replace the database initialization
    updated_code = updated_code.replace(old_db_init, new_db_init)
    
    return updated_code

def deploy_updated_function(updated_code):
    """Deploy the updated function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write function code
        handler_path = os.path.join(temp_dir, 'pipeline_test_handler.py')
        with open(handler_path, 'w') as f:
            f.write(updated_code)
        
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
        
        print(f"✅ Deployed restored pipeline test function: {response['CodeSha256']}")

def test_restored_function():
    """Test the restored function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Wait for deployment
    import time
    time.sleep(30)
    
    print("\n📋 Testing restored pipeline test function...")
    
    # Test with a simple setup_and_test payload
    test_payload = {
        'action': 'setup_and_test',
        'documents': [
            {
                'filename': '01dd077e_86ce1ac2.pdf',
                'source_url': 'https://example.com/test_doc.pdf',
                'estimated_pages': 6,
                'size_mb': 0.51,
                'doc_type': 'test'
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps(test_payload)
        )
        
        raw_response = response['Payload'].read().decode('utf-8')
        print(f"Raw response: {raw_response}")
        
        if raw_response:
            result = json.loads(raw_response)
            print(f"Test result: {result}")
            
            if result.get('statusCode') == 200:
                print("🎉 SUCCESS: Original pipeline test function restored and working!")
            else:
                print(f"⚠️ Function issues: {result}")
        else:
            print("❌ Empty response from function")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
