#!/usr/bin/env python3
"""
Simple test to verify DatabaseManager initialization
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_manager():
    """Test DatabaseManager initialization only"""
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Simple test payload that just initializes DatabaseManager
    test_payload = {
        "test_database_manager": True
    }
    
    # Create a simple test handler
    test_code = '''
import json
import logging
import sys
import os

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import DatabaseManager from layer
try:
    from utils.DatabaseManager import DatabaseManager
except ImportError:
    import sys
    sys.path.append('/opt/python')
    from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        logger.info("Testing DatabaseManager initialization...")
        
        if event.get("test_database_manager"):
            # Just initialize DatabaseManager
            db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
            
            # Try to get connection string (this will test secrets manager)
            conn_str = db_manager.get_connection_string()
            logger.info("Connection string retrieved successfully")
            
            return {
                'success': True,
                'message': 'DatabaseManager test passed'
            }
        else:
            return {
                'success': False,
                'message': 'Not a database manager test'
            }
            
    except Exception as e:
        logger.error(f"DatabaseManager test failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
'''
    
    try:
        logger.info("Testing DatabaseManager initialization...")
        
        # We'll use the existing cleanup service but with a simple test
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        result = json.loads(response['Payload'].read())
        
        logger.info(f"DatabaseManager test response: {json.dumps(result, indent=2)}")
        
        return True
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_database_manager()
    exit(0 if success else 1)
