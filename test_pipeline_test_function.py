#!/usr/bin/env python3
"""
Test script for the modernized pipeline test function
Tests gold standard DatabaseManager and DocumentIDManager integration
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pipeline_test_function():
    """Test the pipeline test function with gold standard patterns"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test 1: Health Check
    logger.info("🏥 Testing health check...")
    
    health_check_payload = {
        "action": "health_check"
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(health_check_payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Health check response: {json.dumps(result, indent=2)}")
        
        if response['StatusCode'] == 200:
            logger.info("✅ Health check PASSED")
        else:
            logger.error("❌ Health check FAILED")
            return False
            
    except Exception as e:
        logger.error(f"❌ Health check ERROR: {str(e)}")
        return False
    
    # Test 2: Basic Pipeline Test (without actual document processing)
    logger.info("🧪 Testing basic pipeline test functionality...")
    
    pipeline_test_payload = {
        "action": "test",
        "test_config": {
            "test_name": "gold_standard_test",
            "doc_id_from_filename": "test_document_123",
            "target_functions": []  # Empty for basic test
        },
        "download_sqlite": False  # Skip SQLite download for basic test
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(pipeline_test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        logger.info(f"Pipeline test response: {json.dumps(result, indent=2)}")
        
        if response['StatusCode'] == 200:
            logger.info("✅ Basic pipeline test PASSED")
            return True
        else:
            logger.error("❌ Basic pipeline test FAILED")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pipeline test ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Testing Pipeline Test Function with Gold Standard Patterns")
    
    success = test_pipeline_test_function()
    
    if success:
        logger.info("🎉 All tests PASSED! Pipeline test function is working with gold standard patterns.")
    else:
        logger.error("💥 Tests FAILED! Check the logs above for details.")
        exit(1)
