#!/usr/bin/env python3
"""
Test Vector Embeddings Integration with Folder URL Structure
Tests the updated vector embeddings with /data_lake/{doc_id}/ structure
"""

import boto3
import json
import time
from datetime import datetime

def test_vector_embeddings_integration():
    """Test vector embeddings with folder URL structure"""
    
    # Use a document we know exists from previous testing
    test_doc_id = "024c99ee7a0fce7b"  # From our previous tests
    
    # Construct test message matching chunks_ready format
    test_message = {
        "stage": "chunks_ready",
        "doc_id": test_doc_id,
        "doc_hash": "test-hash-value",
        "data_locations": {
            "chunks_folder_url": "s3://solve-global-kr-dl-chunks-861276078413-us-east-1/data_lake/" + test_doc_id,
            "text_folder_url": "s3://solve-global-kr-dl-text-861276078413-us-east-1/data_lake/" + test_doc_id
        },
        "document_metadata": {
            "filename": test_doc_id + ".pdf",
            "file_size": 1234567,
            "upload_timestamp": datetime.utcnow().isoformat() + 'Z'
        },
        "processing_metadata": {
            "chunks_count": 10,
            "processing_time": 45.2,
            "cost_threshold": 0.50
        }
    }
    
    # Test SNS message format (what the processor receives)
    sns_test_event = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps(test_message)
                }
            }
        ]
    }
    
    print("Testing Vector Embeddings Integration")
    print("Document ID: " + test_doc_id)
    print("Chunks Folder URL: " + test_message['data_locations']['chunks_folder_url'])
    
    # Test processor function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        print("\nInvoking vector embeddings processor...")
        
        response = lambda_client.invoke(
            FunctionName='vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA',
            InvocationType='RequestResponse',
            Payload=json.dumps(sns_test_event)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print("Processor Response: " + json.dumps(result, indent=2))
        
        if result.get('statusCode') == 200:
            print("SUCCESS: Vector embeddings processor processed folder URL structure!")
            print("Worker function has been invoked asynchronously...")
            print("Check CloudWatch logs for worker processing details")
            
            # Give some time for async processing
            print("\nWaiting 60 seconds for async processing...")
            time.sleep(60)
            
            print("Integration test completed!")
            print("Check OpenSearch vector index for embedded chunks")
            
        else:
            print("FAILED: Processor failed: " + str(result))
            
    except Exception as e:
        print("ERROR: " + str(e))

if __name__ == "__main__":
    test_vector_embeddings_integration()
