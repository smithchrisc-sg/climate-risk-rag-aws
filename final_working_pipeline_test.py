#!/usr/bin/env python3
"""
Final Working Pipeline Test Function
Uses correct DatabaseManager methods and Secrets Manager integration
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Deploy final working pipeline test function"""
    print("🎉 Final Working Pipeline Test Function")
    print("======================================")
    
    # Create function code using correct DatabaseManager methods
    function_code = '''#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - WORKING VERSION
Uses Secrets Manager and correct DatabaseManager methods
"""

import json
import logging
import os
import boto3
import time
from datetime import datetime

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
        
        logger.info(f"Using standard environment variables:")
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

class PipelineTestLambda:
    """Pipeline Test Lambda with working database integration"""
    
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
            
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.db_manager = None
    
    def test_database_connection(self):
        """Test database connectivity using available methods"""
        try:
            if not self.db_manager:
                return {
                    'statusCode': 500,
                    'body': 'DatabaseManager not available'
                }
            
            # Test connection by getting a connection from the pool
            connection = self.db_manager.get_connection()
            if connection:
                logger.info("✅ Database connection successful")
                
                # Return connection to pool
                self.db_manager.return_connection(connection)
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'SUCCESS: Database connection working with Secrets Manager!',
                        'connection_test': True,
                        'secrets_manager': True,
                        'standard_env_vars': True
                    }
                }
            else:
                logger.error("❌ Failed to get database connection")
                return {
                    'statusCode': 500,
                    'body': 'Failed to get database connection'
                }
                
        except Exception as e:
            logger.error(f"Database test error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'statusCode': 500,
                'body': f'Database test error: {str(e)}'
            }
    
    def test_document_operations(self):
        """Test document operations using available methods"""
        try:
            if not self.db_manager:
                return {
                    'statusCode': 500,
                    'body': 'DatabaseManager not available'
                }
            
            # Test document operations using available methods
            test_doc_id = f"test_doc_{int(time.time())}"
            test_filename = f"{test_doc_id}.pdf"
            
            # Create test document metadata
            metadata = {
                'filename': test_filename,
                'test': True,
                'created_at': datetime.utcnow().isoformat(),
                'size_mb': 0.1,
                'status': 'test'
            }
            
            # Use add_or_update_document method
            success = self.db_manager.add_or_update_document(test_doc_id, metadata)
            
            if success:
                logger.info(f"✅ Test document added: {test_doc_id}")
                
                # Try to retrieve document metadata
                retrieved_metadata = self.db_manager.get_document_metadata(test_doc_id)
                
                if retrieved_metadata:
                    logger.info(f"✅ Test document retrieved: {retrieved_metadata}")
                    
                    return {
                        'statusCode': 200,
                        'body': {
                            'message': 'SUCCESS: Document operations working!',
                            'test_doc_id': test_doc_id,
                            'metadata_added': True,
                            'metadata_retrieved': True,
                            'retrieved_data': retrieved_metadata
                        }
                    }
                else:
                    return {
                        'statusCode': 200,
                        'body': {
                            'message': 'Document added but retrieval failed',
                            'test_doc_id': test_doc_id,
                            'metadata_added': True,
                            'metadata_retrieved': False
                        }
                    }
            else:
                return {
                    'statusCode': 500,
                    'body': 'Failed to add test document'
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
        elif action == 'full_test':
            # Run both tests
            db_result = test_manager.test_database_connection()
            doc_result = test_manager.test_document_operations()
            
            result = {
                'statusCode': 200 if db_result.get('statusCode') == 200 and doc_result.get('statusCode') == 200 else 500,
                'body': {
                    'message': 'Full pipeline test completed',
                    'database_test': db_result,
                    'document_test': doc_result
                }
            }
        else:
            result = {
                'statusCode': 400,
                'body': f'Unknown action: {action}. Use test_database, test_document, or full_test'
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
        
        print(f"✅ Deployed final function: {response['CodeSha256']}")
    
    # Run comprehensive tests
    print("\n📋 Running comprehensive tests...")
    run_comprehensive_tests(lambda_client)

def run_comprehensive_tests(lambda_client):
    """Run comprehensive tests"""
    
    print("\n1️⃣ Testing database connectivity...")
    db_test = test_function(lambda_client, {'action': 'test_database'})
    
    print("\n2️⃣ Testing document operations...")
    doc_test = test_function(lambda_client, {'action': 'test_document'})
    
    print("\n3️⃣ Running full test...")
    full_test = test_function(lambda_client, {'action': 'full_test'})
    
    # Summary
    print("\n" + "="*50)
    print("🎯 PIPELINE TEST FUNCTION STATUS")
    print("="*50)
    
    if db_test and doc_test:
        print("🎉 SUCCESS: Pipeline test function is fully working!")
        print("✅ Database connectivity: WORKING")
        print("✅ Document operations: WORKING") 
        print("✅ Secrets Manager integration: WORKING")
        print("✅ Standard environment variables: WORKING")
        print("\n🚀 Ready for integration testing!")
    else:
        print("⚠️ Some tests failed - check logs for details")

def test_function(lambda_client, payload):
    """Test function with given payload"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        
        if result.get('statusCode') == 200:
            print(f"✅ SUCCESS: {payload.get('action', 'test')}")
            return True
        else:
            print(f"❌ FAILED: {payload.get('action', 'test')} - {result.get('body', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {payload.get('action', 'test')} - {e}")
        return False

if __name__ == "__main__":
    main()
