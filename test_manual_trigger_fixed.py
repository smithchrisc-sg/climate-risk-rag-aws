#!/usr/bin/env python3
"""
Manual test of text extraction trigger with correct payload format
"""

import boto3
import json
from datetime import datetime

def test_manual_trigger():
    """Test manual trigger of text extraction"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test payload in the correct format for direct invocation
    test_payload = {
        'bucket': 'solve-global-kr-dl-source-documents-861276078413-us-east-1',
        'key': '064762102bead7b0.pdf'
    }
    
    print("Testing manual trigger of text extraction...")
    print(f"Document: s3://{test_payload['bucket']}/{test_payload['key']}")
    
    try:
        # Invoke the textextractor-initiator function
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='RequestResponse',  # Synchronous for testing
            Payload=json.dumps(test_payload)
        )
        
        print(f"\nLambda invocation status: {response['StatusCode']}")
        
        if 'Payload' in response:
            payload = json.loads(response['Payload'].read())
            print(f"Response payload: {json.dumps(payload, indent=2)}")
        
        if response['StatusCode'] == 200:
            print("✅ Text extraction trigger successful!")
            
            # Check if the response indicates success
            if 'body' in payload:
                body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
                if 'summary' in body:
                    summary = body['summary']
                    print(f"Summary: {summary}")
        else:
            print(f"❌ Text extraction trigger failed with status: {response['StatusCode']}")
            
    except Exception as e:
        print(f"❌ Error invoking textextractor-initiator: {e}")

if __name__ == "__main__":
    test_manual_trigger()
