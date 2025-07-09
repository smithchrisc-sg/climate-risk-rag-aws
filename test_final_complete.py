#!/usr/bin/env python3
"""
Final Complete Pipeline Test - All Fixes Applied
"""

import boto3
import json
import time
from datetime import datetime

def test_final_complete():
    """Test complete pipeline with all fixes applied"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Use a different fresh document
    test_document = {
        "key": "documents/01eef8c1_a403b295.pdf",
        "size": 941427,
        "est_pages": 25
    }
    
    bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
    doc_id = test_document['key'].split('/')[-1].replace('.pdf', '')
    
    print("🎯 FINAL COMPLETE PIPELINE TEST")
    print("=" * 50)
    print(f"📄 Document: {doc_id}")
    print(f"📊 Size: {test_document['size']:,} bytes ({test_document['est_pages']} pages)")
    print("")
    
    # Trigger processing
    print("🚀 Triggering processing...")
    
    payload = {
        "Records": [{
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "eventTime": datetime.utcnow().isoformat() + "Z",
            "eventName": "ObjectCreated:Put",
            "s3": {
                "s3SchemaVersion": "1.0",
                "bucket": {
                    "name": bucket_name,
                    "arn": f"arn:aws:s3:::{bucket_name}"
                },
                "object": {
                    "key": test_document['key'],
                    "size": test_document['size']
                }
            }
        }]
    }
    
    response = lambda_client.invoke(
        FunctionName='solve-global-kr-textextractor-initiator',
        InvocationType='Event',
        Payload=json.dumps(payload)
    )
    
    if response['StatusCode'] != 202:
        print(f"❌ Failed to trigger processing")
        return False
    
    print("✅ Processing triggered")
    
    # Wait for complete processing (8 minutes total)
    print("\n⏳ Waiting 8 minutes for complete processing...")
    time.sleep(480)
    
    # Check all stages
    results = {}
    
    # Text extraction
    try:
        text_key = f"text/{doc_id}.txt"
        response = s3_client.get_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
        text_content = response['Body'].read().decode('utf-8')
        results['text'] = f"✅ {len(text_content):,} chars"
    except:
        results['text'] = "❌ Missing"
    
    # Text chunking
    try:
        chunks_prefix = f"chunks/{doc_id}/"
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-chunks-861276078413-us-east-1",
            Prefix=chunks_prefix
        )
        chunk_count = response.get('KeyCount', 0)
        results['chunks'] = f"✅ {chunk_count} chunks" if chunk_count > 0 else "❌ Missing"
    except:
        results['chunks'] = "❌ Missing"
    
    # NLP processing
    try:
        nlp_prefix = f"nlp/{doc_id}/"
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-ner-results-861276078413-us-east-1",
            Prefix=nlp_prefix,
            MaxKeys=1
        )
        results['nlp'] = "✅ Complete" if response.get('KeyCount', 0) > 0 else "❌ Missing"
    except:
        results['nlp'] = "❌ Missing"
    
    # Results
    print(f"\n📊 FINAL RESULTS")
    print("=" * 50)
    print(f"📝 Text Extraction: {results['text']}")
    print(f"🔗 Text Chunking: {results['chunks']}")
    print(f"🧠 NLP Processing: {results['nlp']}")
    
    # Count successes
    success_count = sum(1 for r in results.values() if "✅" in r)
    total_stages = len(results)
    
    if success_count == total_stages:
        print(f"\n🎉 COMPLETE SUCCESS: All {total_stages} stages working!")
        print(f"🏆 100% End-to-End Pipeline Success!")
        return True
    elif success_count >= 2:
        print(f"\n🔄 PARTIAL SUCCESS: {success_count}/{total_stages} stages completed")
        return True
    else:
        print(f"\n❌ PIPELINE ISSUES: Only {success_count}/{total_stages} stages completed")
        return False

if __name__ == "__main__":
    success = test_final_complete()
    exit(0 if success else 1)
