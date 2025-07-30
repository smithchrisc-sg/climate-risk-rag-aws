#!/usr/bin/env python3
"""
Fix DocumentIDManager Constructor Issue
The DocumentIDManager expects a database URL string, not a DatabaseManager object
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Deploy fixed pipeline test function"""
    print("🔧 Fixing DocumentIDManager Constructor Issue")
    print("============================================")
    
    # Create function code with correct DocumentIDManager usage
    function_code = '''#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - Fixed DocumentIDManager Constructor
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

class PipelineTestLambda:
    """Pipeline Test Lambda with proper Secrets Manager integration"""
    
    def __init__(self):
        """Initialize with DATABASE_URL from Secrets Manager"""
        logger.info("Initializing PipelineTestLambda with Secrets Manager")
        
        try:
            # Construct DATABASE_URL from Secrets Manager
            database_url = get_database_url_from_secrets()
            
            # Set DATABASE_URL environment variable for DatabaseManager
            os.environ['DATABASE_URL'] = database_url
            logger.info("DATABASE_URL set from Secrets Manager")
            
            # Import and initialize DatabaseManager
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
            
            # Import and initialize DocumentIDManager with DATABASE_URL (not DatabaseManager object)
            from utils.DocumentIDManager import DocumentIDManager
            self.doc_id_manager = DocumentIDManager(database_url)  # Pass URL string, not manager object
            logger.info("DocumentIDManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database managers: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.db_manager = None
            self.doc_id_manager = None
    
    def test_database_connection(self):
        """Test database connectivity"""
        try:
            if not self.db_manager:
                return {
                    'statusCode': 500,
                    'body': 'DatabaseManager not available'
                }
            
            # Test connection
            if self.db_manager.test_connection():
                logger.info("✅ Database connection successful")
                return {
                    'statusCode': 200,
                    'body': 'SUCCESS: Database connection working with Secrets Manager!'
                }
            else:
                logger.error("❌ Database connection test failed")
                return {
                    'statusCode': 500,
                    'body': 'Database connection test failed'
                }
        except Exception as e:
            logger.error(f"Database test error: {str(e)}")
            return {
                'statusCode': 500,
                'body': f'Database test error: {str(e)}'
            }
    
    def test_document_operations(self):
        """Test document operations"""
        try:
            if not self.doc_id_manager:
                return {
                    'statusCode': 500,
                    'body': 'DocumentIDManager not available'
                }
            
            # Test document operations
            import time
            from datetime import datetime
            
            test_filename = f"test_doc_{int(time.time())}.pdf"
            doc_id = self.doc_id_manager.generate_doc_id(test_filename)
            
            # Register test document
            metadata = {
                'test': True,
                'created_at': datetime.utcnow().isoformat(),
                'size_mb': 0.1
            }
            
            if self.doc_id_manager.register_document(doc_id, test_filename, metadata):
                logger.info(f"✅ Test document registered: {doc_id}")
                
                # Clean up test document
                self.doc_id_manager.delete_document(doc_id)
                logger.info(f"✅ Test document cleaned up: {doc_id}")
                
                return {
                    'statusCode': 200,
                    'body': f'SUCCESS: Document operations working! Test doc_id: {doc_id}'
                }
            else:
                return {
                    'statusCode': 500,
                    'body': 'Failed to register test document'
                }
                
        except Exception as e:
            logger.error(f"Document test error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'statusCode': 500,
                'body': f'Document test error: {str(e)}'
            }

def lambda_handler(event, context):
    """Lambda handler function"""
    logger.info(f"Pipeline test invoked with event: {json.dumps(event, default=str)}")
    
    try:
        # Initialize test manager
        test_manager = PipelineTestLambda()
        
        # Determine test type
        action = event.get('action', 'test_database')
        
        if action == 'test_database':
            result = test_manager.test_database_connection()
        elif action == 'test_document':
            result = test_manager.test_document_operations()
        else:
            result = {
                'statusCode': 400,
                'body': f'Unknown action: {action}. Use test_database or test_document'
            }
        
        logger.info(f"Test completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': f'Pipeline test failed: {str(e)}'
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
    
    # Test document functionality
    print("\n📋 Testing document functionality...")
    test_document_functionality(lambda_client)

def test_database_connectivity(lambda_client):
    """Test database connectivity"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps({'action': 'test_database'})
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Database test result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: Database connectivity working with Secrets Manager!")
            return True
        else:
            print(f"⚠️ Database test issues: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_document_functionality(lambda_client):
    """Test document functionality"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps({'action': 'test_document'})
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Document test result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: Document functionality working with Secrets Manager!")
            return True
        else:
            print(f"⚠️ Document test issues: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Document test failed: {e}")
        return False

if __name__ == "__main__":
    main()
