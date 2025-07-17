#!/usr/bin/env python3
"""
Test Pipeline Test Function Directly
Check what's happening with the pipeline test function
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test pipeline test function directly"""
    logger.info("🔍 Testing Pipeline Test Function Directly")
    logger.info("==========================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test 1: Simple database test
    logger.info("Test 1: Simple database connectivity test")
    test_database_connectivity(lambda_client)
    
    # Test 2: Document test
    logger.info("\nTest 2: Document operations test")
    test_document_operations(lambda_client)
    
    # Test 3: Setup and test with minimal payload
    logger.info("\nTest 3: Setup and test with minimal payload")
    test_setup_and_test(lambda_client)

def test_database_connectivity(lambda_client):
    """Test database connectivity"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps({'action': 'test_database'})
        )
        
        # Get raw response
        raw_response = response['Payload'].read().decode('utf-8')
        logger.info(f"Raw response: {raw_response}")
        
        if raw_response:
            result = json.loads(raw_response)
            logger.info(f"Database test result: {result}")
            
            if result.get('statusCode') == 200:
                logger.info("✅ Database connectivity working")
            else:
                logger.warning(f"⚠️ Database connectivity issues: {result}")
        else:
            logger.error("❌ Empty response from function")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        logger.error(f"Raw response was: {raw_response}")
    except Exception as e:
        logger.error(f"❌ Database connectivity test failed: {e}")

def test_document_operations(lambda_client):
    """Test document operations"""
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            Payload=json.dumps({'action': 'test_document'})
        )
        
        # Get raw response
        raw_response = response['Payload'].read().decode('utf-8')
        logger.info(f"Raw response: {raw_response}")
        
        if raw_response:
            result = json.loads(raw_response)
            logger.info(f"Document test result: {result}")
            
            if result.get('statusCode') == 200:
                logger.info("✅ Document operations working")
            else:
                logger.warning(f"⚠️ Document operations issues: {result}")
        else:
            logger.error("❌ Empty response from function")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        logger.error(f"Raw response was: {raw_response}")
    except Exception as e:
        logger.error(f"❌ Document operations test failed: {e}")

def test_setup_and_test(lambda_client):
    """Test setup and test with minimal payload"""
    
    # Minimal test payload
    test_payload = {
        'action': 'setup_and_test',
        'documents': [
            {
                'filename': 'test_doc.pdf',
                'source_url': 'https://example.com/test_doc.pdf',
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
        
        # Get raw response
        raw_response = response['Payload'].read().decode('utf-8')
        logger.info(f"Raw response: {raw_response}")
        
        if raw_response:
            result = json.loads(raw_response)
            logger.info(f"Setup and test result: {result}")
            
            if result.get('statusCode') == 200:
                logger.info("✅ Setup and test working")
            else:
                logger.warning(f"⚠️ Setup and test issues: {result}")
        else:
            logger.error("❌ Empty response from function")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        logger.error(f"Raw response was: {raw_response}")
    except Exception as e:
        logger.error(f"❌ Setup and test failed: {e}")

if __name__ == "__main__":
    main()
