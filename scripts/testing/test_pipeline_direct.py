#!/usr/bin/env python3
"""
Test pipeline Lambda directly with correct action
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pipeline_lambda():
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test with correct action
    payload = {
        "action": "test",
        "test_config": {
            "test_name": "integration_test",
            "doc_id_from_filename": "test-doc-123"
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-pipeline-test-function',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== PIPELINE TEST LAMBDA RESULT ===")
        logger.info(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_pipeline_lambda()
