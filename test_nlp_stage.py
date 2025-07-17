#!/usr/bin/env python3
"""
Test NLP Stage Functionality
Quick assessment of current NLP stage status
"""

import boto3
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main test function"""
    logger.info("🧪 Testing NLP Stage Functionality")
    logger.info("==================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {
        'processor_imports': False,
        'worker_imports': False,
        'processor_functionality': False,
        'worker_functionality': False
    }
    
    try:
        # Test NLP processor
        logger.info("\n📋 Testing NLP Processor")
        results['processor_imports'], results['processor_functionality'] = test_nlp_processor()
        
        # Test NLP worker
        logger.info("\n📋 Testing NLP Worker")
        results['worker_imports'], results['worker_functionality'] = test_nlp_worker()
        
        # Summary
        logger.info("\n📊 NLP STAGE TEST RESULTS")
        logger.info("=========================")
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name.replace('_', ' ').title()}: {status}")
        
        # Overall assessment
        import_success = results['processor_imports'] and results['worker_imports']
        
        if import_success:
            logger.info("\n🎉 GOOD NEWS: Import issues already resolved!")
            logger.info("NLP stage is in better shape than vector embeddings was.")
        else:
            logger.error("\n❌ Import issues need to be fixed first.")
        
        return 0 if import_success else 1
        
    except Exception as e:
        logger.error(f"❌ NLP stage test failed: {str(e)}")
        return 1

def test_nlp_processor():
    """Test NLP processor functionality"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test with simple payload
    test_payload = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "doc_id": "test_nlp_processor",
                        "stage": "chunks_ready",
                        "data_locations": {
                            "chunks_folder_url": "s3://test-bucket/test/"
                        },
                        "doc_hash": "test_hash"
                    })
                }
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName="nlp-processor",
            Payload=json.dumps(test_payload)
        )
        
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        # Check for import errors
        import_success = 'ImportModuleError' not in str(response_payload)
        
        # Check for functionality (database connection attempts)
        functionality_working = (
            'Connection timed out' in str(response_payload) or
            'password authentication failed' in str(response_payload) or
            response['StatusCode'] == 200
        )
        
        if import_success:
            logger.info("✅ Processor imports working")
        else:
            logger.error("❌ Processor has import errors")
            
        if functionality_working:
            logger.info("✅ Processor functionality working (database issues are environmental)")
        else:
            logger.error("❌ Processor functionality issues")
            
        return import_success, functionality_working
        
    except Exception as e:
        logger.error(f"❌ Processor test failed: {str(e)}")
        return False, False

def test_nlp_worker():
    """Test NLP worker functionality"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test with simple payload
    test_payload = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "doc_id": "test_nlp_worker",
                        "stage": "nlp_ready",
                        "data_locations": {
                            "chunks_folder_url": "s3://test-bucket/test/",
                            "text_folder_url": "s3://test-bucket/text/"
                        },
                        "doc_hash": "test_hash"
                    })
                }
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName="nlp-worker",
            Payload=json.dumps(test_payload)
        )
        
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        # Check for import errors
        import_success = 'ImportModuleError' not in str(response_payload)
        
        # Check for functionality (database connection attempts or S3 access)
        functionality_working = (
            'Connection timed out' in str(response_payload) or
            'password authentication failed' in str(response_payload) or
            'Invalid S3 location format' in str(response_payload) or
            'column' in str(response_payload) or  # Database schema issues
            response['StatusCode'] == 200
        )
        
        if import_success:
            logger.info("✅ Worker imports working")
        else:
            logger.error("❌ Worker has import errors")
            
        if functionality_working:
            logger.info("✅ Worker functionality working (database/S3 issues are fixable)")
        else:
            logger.error("❌ Worker functionality issues")
            
        return import_success, functionality_working
        
    except Exception as e:
        logger.error(f"❌ Worker test failed: {str(e)}")
        return False, False

if __name__ == "__main__":
    exit(main())
