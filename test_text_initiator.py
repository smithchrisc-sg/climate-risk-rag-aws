#!/usr/bin/env python3
"""
Test text extractor initiator directly
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_text_initiator():
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create a simple S3 event
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "solve-global-kr-dl-source-documents-861276078413-us-east-1"
                    },
                    "object": {
                        "key": "test-document.pdf"
                    }
                }
            }
        ]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== TEXT INITIATOR RESULT ===")
        logger.info(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_text_initiator()
