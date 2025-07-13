#!/usr/bin/env python3
"""
Test Keyword Indexer Integration with Folder URL Structure
Tests the updated keyword indexer with /data_lake/{doc_id}/ structure
"""

import boto3
import json
import time
from datetime import datetime

def test_keyword_indexer_integration():
    """Test keyword indexer with folder URL structure"""
    
    # Use a document we know exists from previous testing
    test_doc_id = "024c99ee7a0fce7b"  # From our previous Textract test
    
    # Construct test message matching text_ready format
    test_message = {
        "stage": "text_ready",
        "doc_id": test_doc_id,
        "doc_hash": "test-hash-value",
        "text_folder_url": "s3://solve-global-kr-dl-text-861276078413-us-east-1/data_lake/" + test_doc_id,
        "filename": test_doc_id + ".pdf",
        "document_metadata": {
            "filename": test_doc_id + ".pdf",
            "file_size": 1234567,
            "upload_timestamp": datetime.utcnow().isoformat() + 'Z'
        },
        "processing_metadata": {
            "textract_job_id": "test-job-id",
            "processing_time": 45.2,
            "page_count": 26,
            "confidence_score": 0.95
        }
    }
    
    # Test SNS message format (what the initiator receives)
    sns_test_event = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps(test_message)
                }
            }
        ]
    }
    
    print("Testing Keyword Indexer Integration")
    print("Document ID: " + test_doc_id)
    print("Text Folder URL: " + test_message['text_folder_url'])
    
    # Test initiator function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        print("\nInvoking keyword indexer initiator...")
        
        response = lambda_client.invoke(
            FunctionName='async-keyword-indexer-initiator',
            InvocationType='RequestResponse',
            Payload=json.dumps(sns_test_event)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print("Initiator Response: " + json.dumps(result, indent=2))
        
        if result.get('success'):
            print("SUCCESS: Keyword indexer initiator processed folder URL structure!")
            print("Worker function has been invoked asynchronously...")
            print("Check CloudWatch logs for worker processing details")
            
            # Give some time for async processing
            print("\nWaiting 30 seconds for async processing...")
            time.sleep(30)
            
            print("Integration test completed!")
            print("Check OpenSearch index for indexed document")
            
        else:
            print("FAILED: Initiator failed: " + str(result))
            
    except Exception as e:
        print("ERROR: " + str(e))

if __name__ == "__main__":
    test_keyword_indexer_integration()
