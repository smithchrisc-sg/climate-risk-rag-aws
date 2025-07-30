#!/usr/bin/env python3
"""
Manually Trigger Text Chunker for Processed Documents
Bypasses VPC networking issues by directly invoking Lambda
"""

import boto3
import json
from datetime import datetime

def trigger_text_chunker():
    """Manually trigger text chunker for documents with text but no chunks-ready processing"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Documents that have text but may not have triggered chunking
    test_documents = [
        "01eef8c1_a403b295",  # Most recent test
        "01dd077e_86ce1ac2",  # Previous test
        "0249c7aa_ae155247",  # From parallel processing
        "00f79db3_73eecd13",  # From parallel processing
        "01487dbe_a6e69b7a",  # From parallel processing
        "004e17a3_3bb90d8e",  # From parallel processing
        "007f21ed_c25a961d"   # From parallel processing
    ]
    
    print("🔧 MANUALLY TRIGGERING TEXT CHUNKER")
    print("=" * 50)
    
    for doc_id in test_documents:
        print(f"\n📄 Processing: {doc_id}")
        
        # Check if text exists
        try:
            text_key = f"text/{doc_id}.txt"
            s3_client.head_object(Bucket="solve-global-kr-dl-text-861276078413-us-east-1", Key=text_key)
            print(f"   ✅ Text file exists")
        except:
            print(f"   ⚠️  No text file, skipping")
            continue
        
        # Create text-extraction-complete message
        message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "text_ready",
            "doc_id": doc_id,
            "doc_hash": f"manual-trigger-{doc_id}",
            "data_locations": {
                "text": f"s3://solve-global-kr-dl-text-861276078413-us-east-1/text/{doc_id}.txt"
            },
            "processing_metadata": {
                "manual_trigger": True,
                "triggered_at": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Directly invoke text chunker
        try:
            # Create Lambda event format
            lambda_event = {
                "Records": [{
                    "eventSource": "aws:sqs",
                    "body": json.dumps(message)
                }]
            }
            
            response = lambda_client.invoke(
                FunctionName='text-chunker-pipeline',
                InvocationType='Event',
                Payload=json.dumps(lambda_event)
            )
            
            if response['StatusCode'] == 202:
                print(f"   ✅ Text chunker triggered successfully")
            else:
                print(f"   ❌ Failed to trigger text chunker: {response['StatusCode']}")
                
        except Exception as e:
            print(f"   ❌ Error triggering text chunker: {e}")
    
    print(f"\n⏳ Waiting 2 minutes for text chunking to complete...")
    import time
    time.sleep(120)
    
    # Check results
    print(f"\n📊 CHECKING RESULTS:")
    
    for doc_id in test_documents:
        try:
            # Check chunks
            chunks_prefix = f"chunks/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-dl-chunks-861276078413-us-east-1",
                Prefix=chunks_prefix
            )
            chunk_count = response.get('KeyCount', 0)
            
            if chunk_count > 0:
                print(f"   ✅ {doc_id}: {chunk_count} chunks")
            else:
                print(f"   ❌ {doc_id}: No chunks")
                
        except Exception as e:
            print(f"   ❌ {doc_id}: Error checking chunks - {e}")

if __name__ == "__main__":
    trigger_text_chunker()
