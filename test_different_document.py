#!/usr/bin/env python3
"""
Test text extraction with a different document
"""

import boto3
import json

def test_different_document():
    """Test with a different document from the source bucket"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Try with a different document
    test_payload = {
        'bucket': 'solve-global-kr-dl-source-documents-861276078413-us-east-1',
        'key': '024c99ee7a0fce7b.pdf'  # Different document
    }
    
    print("Testing text extraction with different document...")
    print(f"Document: s3://{test_payload['bucket']}/{test_payload['key']}")
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        print(f"\nLambda invocation status: {response['StatusCode']}")
        
        if 'Payload' in response:
            payload = json.loads(response['Payload'].read())
            print(f"Response payload: {json.dumps(payload, indent=2)}")
            
            if 'body' in payload:
                body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
                if 'summary' in body:
                    summary = body['summary']
                    print(f"Summary: {summary}")
                    
                    if summary.get('success', 0) > 0:
                        print("✅ New Textract job started successfully!")
                        return True
                    elif summary.get('skipped', 0) > 0:
                        print("ℹ️  Document already processed")
                        return True
                        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return False

if __name__ == "__main__":
    test_different_document()
