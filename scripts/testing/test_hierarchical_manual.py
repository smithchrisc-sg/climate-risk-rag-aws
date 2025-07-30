#!/usr/bin/env python3
"""
Manual Test for Hierarchical Chunker
Tests with a specific document that has LAYOUT blocks
"""

import boto3
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_hierarchical_chunker_manual():
    """Test the hierarchical chunker manually"""
    
    # Use a document that should have LAYOUT blocks
    test_doc_id = "064762102bead7b04a39"
    
    logger.info(f"🧪 Testing hierarchical chunker with document: {test_doc_id}")
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Create test message for the chunker
        test_message = {
            "doc_id": test_doc_id,
            "stage": "text_ready",
            "data_locations": {
                "text_location": f"s3://solve-global-kr-dl-text-861276078413-us-east-1/data-lake/{test_doc_id}/raw_text.txt",
                "structure_location": f"s3://solve-global-kr-dl-text-861276078413-us-east-1/data-lake/{test_doc_id}/textract_response.json"
            },
            "processing_metadata": {
                "text_extraction_complete": True,
                "layout_analysis_enabled": True
            },
            "document_metadata": {
                "filename": f"{test_doc_id}.pdf",
                "upload_timestamp": "2025-07-28T19:47:00Z"
            }
        }
        
        # Invoke the Lambda function
        logger.info("Invoking text-chunker-processor Lambda function...")
        
        response = lambda_client.invoke(
            FunctionName='text-chunker-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'Records': [{
                    'body': json.dumps(test_message)
                }]
            })
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        logger.info(f"Lambda response status: {response.get('StatusCode')}")
        logger.info(f"Response payload: {response_payload}")
        
        if response.get('StatusCode') == 200:
            logger.info("✅ Lambda function executed successfully")
            
            # Check for errors in the response
            if 'errorMessage' in response_payload:
                logger.error(f"❌ Lambda function error: {response_payload['errorMessage']}")
                if 'errorType' in response_payload:
                    logger.error(f"Error type: {response_payload['errorType']}")
                if 'stackTrace' in response_payload:
                    logger.error("Stack trace:")
                    for line in response_payload['stackTrace']:
                        logger.error(f"  {line}")
                return False
            
            logger.info("📊 Processing completed successfully")
            return True
            
        else:
            logger.error(f"❌ Lambda invocation failed with status: {response.get('StatusCode')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return False

def main():
    """Main test execution"""
    
    logger.info("🚀 Starting manual hierarchical chunker test")
    
    try:
        success = test_hierarchical_chunker_manual()
        
        if success:
            logger.info("✅ Manual hierarchical chunker test completed!")
        else:
            logger.error("❌ Manual hierarchical chunker test failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
