#!/usr/bin/env python3
"""
Test Document Structure KG Processor Message Format Handling
Simple test to verify the processor can parse chunks_ready messages correctly
"""

import boto3
import json
from datetime import datetime

def test_message_format_handling():
    """Test that the processor can handle chunks_ready message format"""
    
    # Create a minimal test message
    test_message = {
        "stage": "chunks_ready",
        "doc_id": "test-doc-123",
        "doc_hash": "test-hash",
        "data_locations": {
            "chunks_folder_url": "s3://test-bucket/data_lake/test-doc-123",
            "text_folder_url": "s3://test-bucket/data_lake/test-doc-123"
        },
        "document_metadata": {
            "filename": "test-doc-123.pdf",
            "file_size": 12345,
            "title": "Test Document"
        },
        "processing_metadata": {
            "chunks_count": 5,
            "total_characters": 25000
        }
    }
    
    # Test SNS message format
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
    
    print("Testing Document Structure KG Processor Message Format")
    print("Test Document ID: test-doc-123")
    print("Message Stage: " + test_message['stage'])
    
    # Test processor function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        print("\nInvoking document structure KG processor with test message...")
        
        response = lambda_client.invoke(
            FunctionName='document-structure-kg-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps(sns_test_event)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print("Processor Response: " + json.dumps(result, indent=2))
        
        # Check if the processor handled the message format correctly
        if result.get('statusCode') == 200:
            print("SUCCESS: Processor handled chunks_ready message format!")
        elif result.get('statusCode') == 500:
            error_body = json.loads(result.get('body', '{}'))
            if 'S3' in error_body.get('error', '') or 'NoSuchKey' in error_body.get('error', ''):
                print("EXPECTED: Processor parsed message correctly but failed on missing S3 data")
                print("This confirms the message format handling is working!")
            else:
                print("FAILED: Unexpected error: " + str(error_body.get('error', 'unknown')))
        else:
            print("FAILED: Unexpected status code: " + str(result.get('statusCode')))
            
    except Exception as e:
        print("ERROR: " + str(e))

if __name__ == "__main__":
    test_message_format_handling()
