#!/usr/bin/env python3
"""
Minimal Pipeline Test Function Fix
Creates a working version with new database layer
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Create and deploy minimal working version"""
    
    # Create minimal working function code
    function_code = '''#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - Updated for database-core-layer
"""

import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from database-core-layer
try:
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    from utils.database_config import validate_database_environment
    logger.info("Successfully imported database utilities from database-core-layer")
except ImportError as e:
    logger.error(f"Failed to import database utilities: {e}")
    DatabaseManager = None
    DocumentIDManager = None

def lambda_handler(event, context):
    """Lambda handler function"""
    logger.info(f"Pipeline test invoked with event: {json.dumps(event, default=str)}")
    
    try:
        # Test database connection
        if DatabaseManager is None:
            return {
                'statusCode': 500,
                'body': 'Database utilities not available'
            }
        
        # Validate environment
        validate_database_environment()
        
        # Initialize database manager
        db_manager = DatabaseManager()
        logger.info("DatabaseManager initialized")
        
        # Test connection
        if db_manager.test_connection():
            logger.info("Database connection successful")
            return {
                'statusCode': 200,
                'body': 'Database connection successful - new database layer working!'
            }
        else:
            logger.error("Database connection failed")
            return {
                'statusCode': 500,
                'body': 'Database connection failed'
            }
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
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
        
        print(f"✅ Deployed minimal function: {response['CodeSha256']}")
    
    # Test the function
    test_payload = {"test": "database"}
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Test result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: Pipeline test function is working with new database layer!")
        else:
            print(f"⚠️ Function returned: {result}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
