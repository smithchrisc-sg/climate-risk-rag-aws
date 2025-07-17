#!/usr/bin/env python3
"""
Simple Database Connectivity Test
Focus only on database connectivity with Secrets Manager
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Deploy simple database connectivity test"""
    print("🔧 Simple Database Connectivity Test")
    print("===================================")
    
    # Create simple function code that only tests database connectivity
    function_code = '''#!/usr/bin/env python3
"""
Simple Database Connectivity Test - Secrets Manager Integration
"""

import json
import logging
import os
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url_from_secrets():
    """Construct DATABASE_URL from standard environment variables and Secrets Manager"""
    try:
        # Get standard environment variables
        secret_name = os.environ.get('DATABASE_SECRET_NAME')
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_port = os.environ.get('DB_PORT', '5432')
        
        logger.info(f"Using secret: {secret_name}")
        logger.info(f"Database: {db_host}:{db_port}/{db_name}")
        
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
    """Lambda handler function"""
    logger.info(f"Simple database test invoked")
    
    try:
        # Construct DATABASE_URL from Secrets Manager
        database_url = get_database_url_from_secrets()
        
        # Set DATABASE_URL environment variable
        os.environ['DATABASE_URL'] = database_url
        logger.info("DATABASE_URL set from Secrets Manager")
        
        # Import and test DatabaseManager
        from utils.DatabaseManager import DatabaseManager
        db_manager = DatabaseManager()
        logger.info("DatabaseManager initialized successfully")
        
        # Test connection
        if db_manager.test_connection():
            logger.info("✅ Database connection successful")
            
            # Try a simple query
            try:
                result = db_manager.execute_query("SELECT 1 as test")
                logger.info(f"✅ Simple query successful: {result}")
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'SUCCESS: Database connectivity working with Secrets Manager!',
                        'query_result': result,
                        'database_url_constructed': True,
                        'connection_test': True
                    }
                }
            except Exception as e:
                logger.warning(f"Query test failed: {e}")
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'SUCCESS: Database connection working, query test failed',
                        'connection_test': True,
                        'query_error': str(e)
                    }
                }
        else:
            logger.error("❌ Database connection test failed")
            return {
                'statusCode': 500,
                'body': 'Database connection test failed'
            }
            
    except Exception as e:
        logger.error(f"Database test error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': f'Database test error: {str(e)}'
        }
'''
    
    # Deploy the function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write function code
        handler_path = os.path.join(temp_dir, 'pipeline_test_handler.py')
        with open(handler_path, 'w') as f:
            f.write(function_code)
        
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
        
        print(f"✅ Deployed function: {response['CodeSha256']}")
    
    # Test database connectivity
    print("\n📋 Testing database connectivity...")
    test_database_connectivity(lambda_client)

def test_database_connectivity(lambda_client):
    """Test database connectivity"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps({'test': 'database'})
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Database test result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: Database connectivity working with Secrets Manager!")
            print("✅ Standard environment variables working")
            print("✅ Secrets Manager integration working")
            print("✅ DATABASE_URL construction working")
            return True
        else:
            print(f"⚠️ Database test issues: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    main()
