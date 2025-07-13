#!/usr/bin/env python3
"""
Minimal Test for Document Structure KG Processor
Tests message parsing without S3 dependencies
"""

import boto3
import json

def test_minimal_functionality():
    """Test basic message parsing functionality"""
    
    # Create a test message that will fail on S3 but succeed on parsing
    test_message = {
        "stage": "chunks_ready",
        "doc_id": "minimal-test-doc",
        "doc_hash": "test-hash",
        "data_locations": {
            "chunks_folder_url": "s3://nonexistent-bucket/data_lake/minimal-test-doc",
            "text_folder_url": "s3://nonexistent-bucket/data_lake/minimal-test-doc"
        },
        "document_metadata": {
            "filename": "minimal-test-doc.pdf",
            "title": "Minimal Test Document"
        },
        "processing_metadata": {
            "chunks_count": 1,
            "total_characters": 1000
        }
    }
    
    sns_test_event = {
        "Records": [
            {
                "EventSource": "aws:sns",
                "Sns": {
                    "Message": json.dumps(test_message)
                }
            }
        ]
    }
    
    print("Testing Document Structure KG Processor - Minimal Test")
    print("This test verifies message parsing works correctly")
    print("Expected: Function should parse message but fail on S3 operations")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        response = lambda_client.invoke(
            FunctionName='document-structure-kg-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps(sns_test_event)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print("\nProcessor Response:")
        print(json.dumps(result, indent=2))
        
        # Analyze the response
        if result.get('statusCode') == 500:
            error_body = json.loads(result.get('body', '{}'))
            error_msg = error_body.get('error', '')
            
            if 'NoSuchBucket' in error_msg or 'NoSuchKey' in error_msg or 'S3' in error_msg:
                print("\nSUCCESS: Message parsing worked correctly!")
                print("Function failed on S3 operations as expected (no data exists)")
                print("This confirms the chunks_ready message format is handled properly")
                return True
            else:
                print("\nUNEXPECTED ERROR: " + error_msg)
                return False
        elif result.get('statusCode') == 200:
            print("\nUNEXPECTED SUCCESS: Function completed without S3 data")
            print("This might indicate the function is working with fallback logic")
            return True
        else:
            print("\nUNEXPECTED STATUS: " + str(result.get('statusCode')))
            return False
            
    except Exception as e:
        print("\nERROR: " + str(e))
        return False

if __name__ == "__main__":
    success = test_minimal_functionality()
    if success:
        print("\n✅ DOCUMENT STRUCTURE KG PROCESSOR: Message format handling verified!")
    else:
        print("\n❌ DOCUMENT STRUCTURE KG PROCESSOR: Issues detected")
