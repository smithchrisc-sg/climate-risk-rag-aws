#!/usr/bin/env python3
"""
Manually Trigger NLP Processor for Documents with Chunks
"""

import boto3
import json
from datetime import datetime

def trigger_nlp_processor():
    """Manually trigger NLP processor for documents that have chunks"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    test_documents = [
        "01eef8c1_a403b295",
        "01dd077e_86ce1ac2", 
        "0249c7aa_ae155247",
        "00f79db3_73eecd13",
        "01487dbe_a6e69b7a",
        "004e17a3_3bb90d8e",
        "007f21ed_c25a961d"
    ]
    
    print("🧠 MANUALLY TRIGGERING NLP PROCESSOR")
    print("=" * 50)
    
    for doc_id in test_documents:
        print(f"\n📄 Processing: {doc_id}")
        
        # Check if chunks exist
        try:
            chunks_prefix = f"chunks/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-dl-chunks-861276078413-us-east-1",
                Prefix=chunks_prefix,
                MaxKeys=1
            )
            
            if response.get('KeyCount', 0) == 0:
                print(f"   ⚠️  No chunks found, skipping")
                continue
                
            print(f"   ✅ Chunks found")
            
        except Exception as e:
            print(f"   ❌ Error checking chunks: {e}")
            continue
        
        # Create chunks-ready message
        message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "chunks_ready",
            "doc_id": doc_id,
            "doc_hash": f"manual-trigger-{doc_id}",
            "document_metadata": {
                "original_filename": f"{doc_id}.pdf",
                "file_size": 100000,
                "page_count": 10
            },
            "data_locations": {
                "chunks": f"s3://solve-global-kr-dl-chunks-861276078413-us-east-1/chunks/{doc_id}/",
                "text": f"s3://solve-global-kr-dl-text-861276078413-us-east-1/text/{doc_id}.txt"
            },
            "processing_metadata": {
                "chunks_count": 50,
                "processing_duration_ms": 1000,
                "manual_trigger": True
            }
        }
        
        # Directly invoke NLP processor
        try:
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
                print(f"   ✅ NLP processor triggered successfully")
            else:
                print(f"   ❌ Failed to trigger NLP processor: {response['StatusCode']}")
                
        except Exception as e:
            print(f"   ❌ Error triggering NLP processor: {e}")
    
    print(f"\n⏳ Waiting 5 minutes for NLP processing to complete...")
    import time
    time.sleep(300)
    
    # Check results
    print(f"\n📊 CHECKING NLP RESULTS:")
    
    nlp_success_count = 0
    
    for doc_id in test_documents:
        try:
            nlp_prefix = f"nlp/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-dl-ner-results-861276078413-us-east-1",
                Prefix=nlp_prefix,
                MaxKeys=1
            )
            
            if response.get('KeyCount', 0) > 0:
                print(f"   ✅ {doc_id}: NLP results found")
                nlp_success_count += 1
            else:
                print(f"   ❌ {doc_id}: No NLP results")
                
        except Exception as e:
            print(f"   ❌ {doc_id}: Error checking NLP results - {e}")
    
    total_docs = len(test_documents)
    success_rate = (nlp_success_count / total_docs) * 100
    
    print(f"\n📊 FINAL NLP PROCESSING SUMMARY:")
    print(f"   Success: {nlp_success_count}/{total_docs} ({success_rate:.1f}%)")
    
    if nlp_success_count >= total_docs * 0.7:
        print(f"   🎉 NLP PROCESSING SUCCESS!")
        return True
    else:
        print(f"   ⚠️  NLP processing needs attention")
        return False

if __name__ == "__main__":
    success = trigger_nlp_processor()
    exit(0 if success else 1)
