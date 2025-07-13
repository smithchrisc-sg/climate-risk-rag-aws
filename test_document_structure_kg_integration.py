#!/usr/bin/env python3
"""
Test Document Structure KG Processor Integration with chunks_ready Message
Tests the updated processor with standardized pipeline messaging
"""

import boto3
import json
import time
from datetime import datetime

def test_document_structure_kg_integration():
    """Test document structure KG processor with chunks_ready message format"""
    
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
            "upload_timestamp": datetime.utcnow().isoformat() + 'Z',
            "content_type": "application/pdf",
            "title": "Climate Risk Assessment Document"
        },
        "processing_metadata": {
            "chunks_count": 10,
            "total_characters": 50000,
            "processing_time": 45.2
        }
    }
    
    # Test SNS message format (what the processor receives)
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
    
    print("Testing Document Structure KG Processor Integration")
    print("Document ID: " + test_doc_id)
    print("Chunks Folder URL: " + test_message['data_locations']['chunks_folder_url'])
    print("Text Folder URL: " + test_message['data_locations']['text_folder_url'])
    
    # Test processor function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        print("\nInvoking document structure KG processor...")
        
        response = lambda_client.invoke(
            FunctionName='document-structure-kg-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps(sns_test_event)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        print("Processor Response: " + json.dumps(result, indent=2))
        
        if result.get('statusCode') == 200:
            print("SUCCESS: Document structure KG processor handled chunks_ready message!")
            print("TTL generation and KG integration should be triggered...")
            
            # Check if TTL was generated
            print("\nChecking for generated TTL file...")
            s3_client = boto3.client('s3', region_name='us-east-1')
            
            try:
                ttl_key = "documents/" + test_doc_id + "/document_structure.ttl"
                ttl_bucket = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
                
                ttl_response = s3_client.head_object(Bucket=ttl_bucket, Key=ttl_key)
                print("SUCCESS: TTL file generated at s3://" + ttl_bucket + "/" + ttl_key)
                print("TTL file size: " + str(ttl_response.get('ContentLength', 0)) + " bytes")
                print("Generated at: " + str(ttl_response.get('LastModified', 'unknown')))
                
            except Exception as ttl_error:
                print("TTL file not found or error: " + str(ttl_error))
            
            print("Integration test completed!")
            
        else:
            print("FAILED: Processor failed: " + str(result))
            
    except Exception as e:
        print("ERROR: " + str(e))

if __name__ == "__main__":
    test_document_structure_kg_integration()
