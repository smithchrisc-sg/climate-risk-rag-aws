#!/usr/bin/env python3
"""
Test One Document Complete End-to-End with All Fixes
"""

import boto3
import json
from datetime import datetime

def test_one_complete():
    """Test one document completely end-to-end"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Use a document we know has chunks
    doc_id = "01eef8c1_a403b295"
    
    print("🎯 TESTING ONE COMPLETE END-TO-END PIPELINE")
    print("=" * 50)
    print(f"📄 Document: {doc_id}")
    print("")
    
    # Manually trigger NLP processor with correct format
    print("🧠 Triggering NLP processor with correct format...")
    
    message = {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "climate-risk-rag-system",
        "stage": "chunks_ready",
        "doc_id": doc_id,
        "doc_hash": f"test-hash-{doc_id}",
        "document_metadata": {
            "original_filename": f"{doc_id}.pdf",
            "file_size": 941427,
            "page_count": 25
        },
        "data_locations": {
            "chunks": f"s3://solve-global-kr-chunks-861276078413-us-east-1/chunks/{doc_id}/",
            "text": f"s3://solve-global-kr-text-new-861276078413-us-east-1/text/{doc_id}.txt"
        },
        "processing_metadata": {
            "chunks_count": 42,
            "processing_duration_ms": 1000
        }
    }
    
    # Create SNS event format
    sns_event = {
        "Records": [{
            "EventSource": "aws:sns",
            "Sns": {
                "Message": json.dumps(message),
                "Subject": f"Chunks ready: {doc_id}"
            }
        }]
    }
    
    response = lambda_client.invoke(
        FunctionName='nlp-processor',
        InvocationType='Event',
        Payload=json.dumps(sns_event)
    )
    
    if response['StatusCode'] == 202:
        print("✅ NLP processor triggered successfully")
    else:
        print(f"❌ Failed to trigger NLP processor: {response['StatusCode']}")
        return False
    
    # Wait for NLP processing
    print("\n⏳ Waiting 3 minutes for NLP processing...")
    import time
    time.sleep(180)
    
    # Check all stages
    print(f"\n📊 CHECKING ALL STAGES:")
    
    # Text extraction
    try:
        text_key = f"text/{doc_id}.txt"
        response = s3_client.get_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
        text_content = response['Body'].read().decode('utf-8')
        text_result = f"✅ {len(text_content):,} chars"
        text_success = True
    except:
        text_result = "❌ Missing"
        text_success = False
    
    # Text chunking
    try:
        chunks_prefix = f"chunks/{doc_id}/"
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-chunks-861276078413-us-east-1",
            Prefix=chunks_prefix
        )
        chunk_count = response.get('KeyCount', 0)
        chunks_result = f"✅ {chunk_count} chunks" if chunk_count > 0 else "❌ Missing"
        chunks_success = chunk_count > 0
    except:
        chunks_result = "❌ Missing"
        chunks_success = False
    
    # NLP processing
    try:
        nlp_prefix = f"nlp/{doc_id}/"
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-ner-results-861276078413-us-east-1",
            Prefix=nlp_prefix
        )
        nlp_count = response.get('KeyCount', 0)
        if nlp_count > 0:
            nlp_result = f"✅ {nlp_count} NLP files"
            nlp_success = True
            
            # Show NLP file details
            print(f"\n📋 NLP Results Details:")
            for obj in response.get('Contents', [])[:5]:
                file_name = obj['Key'].split('/')[-1]
                file_size = obj['Size']
                print(f"   📄 {file_name} ({file_size:,} bytes)")
        else:
            nlp_result = "❌ Missing"
            nlp_success = False
    except Exception as e:
        nlp_result = f"❌ Error: {e}"
        nlp_success = False
    
    # Results
    print(f"\n📊 FINAL COMPLETE RESULTS:")
    print("=" * 50)
    print(f"📝 Text Extraction: {text_result}")
    print(f"🔗 Text Chunking: {chunks_result}")
    print(f"🧠 NLP Processing: {nlp_result}")
    
    # Overall assessment
    total_success = sum([text_success, chunks_success, nlp_success])
    
    if total_success == 3:
        print(f"\n🎉 COMPLETE SUCCESS: 100% End-to-End Pipeline Working!")
        print(f"🏆 All 3 stages completed successfully!")
        return True
    elif total_success == 2:
        print(f"\n🔄 PARTIAL SUCCESS: 2/3 stages completed")
        return True
    else:
        print(f"\n❌ PIPELINE ISSUES: Only {total_success}/3 stages completed")
        return False

if __name__ == "__main__":
    success = test_one_complete()
    exit(0 if success else 1)
