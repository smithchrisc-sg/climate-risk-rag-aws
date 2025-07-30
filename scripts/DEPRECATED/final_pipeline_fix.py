#!/usr/bin/env python3
"""
Final Pipeline Test Function Fix
Uses the exact same import pattern as the working text-chunker function
"""

import boto3
import json
import tempfile
import zipfile
import os

def main():
    """Fix pipeline test function with working import pattern"""
    print("🔧 Final Pipeline Test Function Fix")
    print("===================================")
    
    # Create function code using exact same pattern as text-chunker
    function_code = '''#!/usr/bin/env python3
"""
Pipeline Test Lambda Function - Fixed with working import pattern
"""

import json
import logging
import os
import boto3
import sqlite3
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PipelineTestLambda:
    """Pipeline Test Lambda using standardized database layer"""
    
    def __init__(self):
        """Initialize with database manager using working pattern"""
        logger.info("Initializing PipelineTestLambda")
        
        # Import shared utilities from lambda layer (same pattern as text-chunker)
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
            self.db_manager = None
        
        # Import DocumentIDManager
        try:
            from utils.DocumentIDManager import DocumentIDManager
            if self.db_manager:
                self.doc_id_manager = DocumentIDManager(self.db_manager)
                logger.info("DocumentIDManager initialized successfully")
            else:
                self.doc_id_manager = None
        except Exception as e:
            logger.error(f"Failed to import DocumentIDManager: {e}")
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
                    'body': 'SUCCESS: Database connection working with standardized layer!'
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
    
    def prepare_test_document(self):
        """Prepare a test document to verify full functionality"""
        try:
            if not self.doc_id_manager:
                return {
                    'statusCode': 500,
                    'body': 'DocumentIDManager not available'
                }
            
            # Generate test document
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
                    'body': f'SUCCESS: Full database functionality working! Test doc_id: {doc_id}'
                }
            else:
                return {
                    'statusCode': 500,
                    'body': 'Failed to register test document'
                }
                
        except Exception as e:
            logger.error(f"Document test error: {str(e)}")
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
            result = test_manager.prepare_test_document()
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
            print("🎉 SUCCESS: Database connectivity working!")
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
            print("🎉 SUCCESS: Document functionality working!")
            return True
        else:
            print(f"⚠️ Document test issues: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Document test failed: {e}")
        return False

if __name__ == "__main__":
    main()
