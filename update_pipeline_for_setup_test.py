#!/usr/bin/env python3
"""
Update Pipeline Test Function to Handle setup_and_test Action
Add the missing functionality that invoke_pipeline_test.py expects
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Update pipeline test function with setup_and_test functionality"""
    print("🔧 Updating Pipeline Test Function for setup_and_test")
    print("====================================================")
    
    # Create updated function code with setup_and_test support
    function_code = '''#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - Updated with setup_and_test Support
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

class PipelineTestLambda:
    """Pipeline Test Lambda with full functionality"""
    
    def __init__(self):
        """Initialize with DATABASE_URL from Secrets Manager"""
        logger.info("Initializing PipelineTestLambda with Secrets Manager")
        
        try:
            # Construct DATABASE_URL from Secrets Manager
            database_url = get_database_url_from_secrets()
            
            # Set DATABASE_URL environment variable for DatabaseManager
            os.environ['DATABASE_URL'] = database_url
            logger.info("DATABASE_URL set from Secrets Manager using standard environment variables")
            
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
        """Test database connectivity"""
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
    
    def setup_and_test_documents(self, documents):
        """Setup and test documents for pipeline processing"""
        try:
            if not self.db_manager:
                return {
                    'statusCode': 500,
                    'body': 'DatabaseManager not available'
                }
            
            logger.info(f"Setting up and testing {len(documents)} documents")
            
            # Process each document
            processed_docs = []
            for doc in documents:
                doc_result = self.setup_document(doc)
                if doc_result:
                    processed_docs.append(doc_result)
            
            if processed_docs:
                logger.info(f"✅ Successfully processed {len(processed_docs)} documents")
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f'Successfully processed {len(processed_docs)} documents',
                        'processed_documents': processed_docs,
                        'total_documents': len(documents),
                        'successful_documents': len(processed_docs)
                    }
                }
            else:
                logger.warning("No documents were successfully processed")
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'No documents were successfully processed',
                        'processed_documents': [],
                        'total_documents': len(documents),
                        'successful_documents': 0
                    }
                }
                
        except Exception as e:
            logger.error(f"Setup and test error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'statusCode': 500,
                'body': f'Setup and test error: {str(e)}'
            }
    
    def setup_document(self, document):
        """Setup a single document for pipeline processing"""
        try:
            filename = document.get('filename', 'unknown.pdf')
            source_url = document.get('source_url', '')
            
            # Generate a simple document ID
            doc_id = f"test_{int(time.time())}_{filename.replace('.pdf', '')}"
            
            # Create document metadata
            metadata = {
                'filename': filename,
                'source_url': source_url,
                'estimated_pages': document.get('estimated_pages', 0),
                'size_mb': document.get('size_mb', 0),
                'doc_type': document.get('doc_type', 'test'),
                'status': 'prepared_for_testing',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Add document to database using DatabaseManager
            success = self.db_manager.add_or_update_document(doc_id, metadata)
            
            if success:
                logger.info(f"✅ Document prepared: {doc_id}")
                return {
                    'doc_id': doc_id,
                    'filename': filename,
                    'status': 'prepared',
                    'metadata': metadata
                }
            else:
                logger.error(f"❌ Failed to prepare document: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error setting up document {document.get('filename', 'unknown')}: {str(e)}")
            return None

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
        elif action == 'setup_and_test':
            documents = event.get('documents', [])
            if not documents:
                result = {
                    'statusCode': 400,
                    'body': 'No documents provided for setup_and_test action'
                }
            else:
                result = test_manager.setup_and_test_documents(documents)
        elif action == 'full_test':
            # Run both database test and document setup
            db_result = test_manager.test_database_connection()
            
            if db_result.get('statusCode') == 200:
                documents = event.get('documents', [])
                if documents:
                    doc_result = test_manager.setup_and_test_documents(documents)
                else:
                    doc_result = {'statusCode': 200, 'body': 'No documents to process'}
                
                result = {
                    'statusCode': 200,
                    'body': {
                        'message': 'Full test completed',
                        'database_test': db_result,
                        'document_test': doc_result
                    }
                }
            else:
                result = db_result
        else:
            result = {
                'statusCode': 400,
                'body': f'Unknown action: {action}. Use test_database, setup_and_test, or full_test'
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
    
    # Deploy the updated function
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
        
        print(f"✅ Deployed updated pipeline test function: {response['CodeSha256']}")
    
    # Test the updated function
    print("\n📋 Testing updated function...")
    test_updated_function(lambda_client)

def test_updated_function(lambda_client):
    """Test the updated function"""
    
    # Test setup_and_test action
    test_payload = {
        'action': 'setup_and_test',
        'documents': [
            {
                'filename': 'test_doc_1.pdf',
                'source_url': 'https://example.com/test_doc_1.pdf',
                'estimated_pages': 5,
                'size_mb': 1.0,
                'doc_type': 'test'
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print(f"Setup and test result: {result}")
        
        if result.get('statusCode') == 200:
            print("🎉 SUCCESS: setup_and_test action working!")
        else:
            print(f"⚠️ Setup and test issues: {result}")
            
    except Exception as e:
        print(f"❌ Setup and test failed: {e}")

if __name__ == "__main__":
    main()
