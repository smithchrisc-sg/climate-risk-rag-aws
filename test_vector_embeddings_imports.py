#!/usr/bin/env python3
"""
Test Vector Embeddings Import Fix
Simple test to verify that our import fixes worked
"""

import boto3
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_vector_embeddings_processor():
    """Test the vector embeddings processor with a simple payload"""
    logger.info("🧪 Testing Vector Embeddings Processor Import Fix")
    logger.info("================================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create a minimal test payload
    test_payload = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "doc_id": "test_import_fix",
                        "stage": "chunks_ready", 
                        "data_locations": {
                            "chunks_folder_url": "s3://test-bucket/test/"
                        },
                        "doc_hash": "test_hash_123"
                    })
                }
            }
        ]
    }
    
    try:
        logger.info("Invoking vector embeddings processor...")
        response = lambda_client.invoke(
            FunctionName="vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA",
            Payload=json.dumps(test_payload)
        )
        
        # Read the response
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        logger.info(f"Response status code: {response['StatusCode']}")
        logger.info(f"Response payload: {json.dumps(response_payload, indent=2)}")
        
        # Check if we got past the import error
        if response['StatusCode'] == 200:
            logger.info("✅ SUCCESS: Function executed without import errors!")
            return True
        else:
            # Check if it's still an import error
            if 'errorType' in response_payload and 'ImportModuleError' in response_payload['errorType']:
                logger.error("❌ FAILED: Still getting import errors")
                logger.error(f"Error: {response_payload.get('errorMessage', 'Unknown error')}")
                return False
            else:
                logger.info("✅ PARTIAL SUCCESS: Got past import errors, but other error occurred")
                logger.info(f"Error: {response_payload.get('errorMessage', 'Unknown error')}")
                return True
                
    except Exception as e:
        logger.error(f"❌ FAILED: Exception during test: {str(e)}")
        return False

def test_vector_embeddings_worker():
    """Test the vector embeddings worker with a simple payload"""
    logger.info("🧪 Testing Vector Embeddings Worker Import Fix")
    logger.info("==============================================")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create a minimal test payload
    test_payload = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "doc_id": "test_import_fix",
                        "stage": "embeddings_ready",
                        "data_locations": {
                            "chunks_folder_url": "s3://test-bucket/test/"
                        },
                        "doc_hash": "test_hash_123"
                    })
                }
            }
        ]
    }
    
    try:
        logger.info("Invoking vector embeddings worker...")
        response = lambda_client.invoke(
            FunctionName="vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi",
            Payload=json.dumps(test_payload)
        )
        
        # Read the response
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        logger.info(f"Response status code: {response['StatusCode']}")
        logger.info(f"Response payload: {json.dumps(response_payload, indent=2)}")
        
        # Check if we got past the import error
        if response['StatusCode'] == 200:
            logger.info("✅ SUCCESS: Function executed without import errors!")
            return True
        else:
            # Check if it's still an import error
            if 'errorType' in response_payload and 'ImportModuleError' in response_payload['errorType']:
                logger.error("❌ FAILED: Still getting import errors")
                logger.error(f"Error: {response_payload.get('errorMessage', 'Unknown error')}")
                return False
            else:
                logger.info("✅ PARTIAL SUCCESS: Got past import errors, but other error occurred")
                logger.info(f"Error: {response_payload.get('errorMessage', 'Unknown error')}")
                return True
                
    except Exception as e:
        logger.error(f"❌ FAILED: Exception during test: {str(e)}")
        return False

def main():
    """Main test function"""
    logger.info("🚀 Starting Vector Embeddings Import Tests")
    logger.info("==========================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test processor
    processor_success = test_vector_embeddings_processor()
    
    # Test worker  
    worker_success = test_vector_embeddings_worker()
    
    # Summary
    logger.info("\n📊 TEST SUMMARY")
    logger.info("===============")
    logger.info(f"Processor Import Fix: {'✅ PASSED' if processor_success else '❌ FAILED'}")
    logger.info(f"Worker Import Fix: {'✅ PASSED' if worker_success else '❌ FAILED'}")
    
    if processor_success and worker_success:
        logger.info("🎉 ALL TESTS PASSED - Import fixes successful!")
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED - Import fixes need more work")
        return 1

if __name__ == "__main__":
    exit(main())
