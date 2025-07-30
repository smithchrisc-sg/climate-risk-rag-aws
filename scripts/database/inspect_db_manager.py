#!/usr/bin/env python3
"""
Inspect DatabaseManager Methods
Find out what methods are actually available
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Deploy function to inspect DatabaseManager"""
    print("🔍 Inspecting DatabaseManager Methods")
    print("====================================")
    
    # Create function code that inspects DatabaseManager
    function_code = '''#!/usr/bin/env python3
"""
Inspect DatabaseManager - Find Available Methods
"""

import json
import logging
import os
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url_from_secrets():
    """Construct DATABASE_URL from Secrets Manager"""
    try:
        secret_name = os.environ.get('DATABASE_SECRET_NAME')
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_port = os.environ.get('DB_PORT', '5432')
        
        if not all([secret_name, db_host, db_name]):
            raise ValueError("Missing required database environment variables")
        
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        
        username = secret_data.get('username', 'postgres')
        password = secret_data['password']
        
        database_url = f"postgresql://{username}:{password}@{db_host}:{db_port}/{db_name}?sslmode=require"
        return database_url
        
    except Exception as e:
        logger.error(f"Failed to construct DATABASE_URL: {str(e)}")
        raise

def lambda_handler(event, context):
    """Lambda handler function"""
    logger.info("Inspecting DatabaseManager")
    
    try:
        # Construct DATABASE_URL
        database_url = get_database_url_from_secrets()
        os.environ['DATABASE_URL'] = database_url
        
        # Import DatabaseManager
        from utils.DatabaseManager import DatabaseManager
        db_manager = DatabaseManager()
        
        # Inspect methods and attributes
        methods = [method for method in dir(db_manager) if not method.startswith('_')]
        logger.info(f"DatabaseManager methods: {methods}")
        
        # Try to get connection
        try:
            connection = db_manager.get_connection()
            logger.info("✅ get_connection() method works")
            connection_available = True
        except Exception as e:
            logger.error(f"get_connection() failed: {e}")
            connection_available = False
        
        # Try execute_query if available
        query_result = None
        if hasattr(db_manager, 'execute_query'):
            try:
                query_result = db_manager.execute_query("SELECT 1 as test")
                logger.info(f"✅ execute_query works: {query_result}")
            except Exception as e:
                logger.error(f"execute_query failed: {e}")
                query_result = f"Error: {e}"
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'DatabaseManager inspection complete',
                'methods': methods,
                'connection_available': connection_available,
                'query_result': query_result,
                'database_url_constructed': True
            }
        }
        
    except Exception as e:
        logger.error(f"Inspection error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': f'Inspection error: {str(e)}'
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
        
        print(f"✅ Deployed inspection function: {response['CodeSha256']}")
    
    # Run inspection
    print("\n📋 Running DatabaseManager inspection...")
    inspect_database_manager(lambda_client)

def inspect_database_manager(lambda_client):
    """Inspect DatabaseManager methods"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps({'action': 'inspect'})
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Inspection result: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = result.get('body', {})
            methods = body.get('methods', [])
            print(f"\n📋 Available DatabaseManager methods:")
            for method in methods:
                print(f"  - {method}")
            
            if body.get('connection_available'):
                print("✅ Database connection is working!")
            
            if body.get('query_result'):
                print(f"✅ Query execution working: {body['query_result']}")
            
            return True
        else:
            print(f"⚠️ Inspection failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        return False

if __name__ == "__main__":
    main()
