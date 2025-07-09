#!/usr/bin/env python3
"""
Simple Parallel Test - Immediate Feedback
"""

import boto3
import json
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

def trigger_single_document(doc_info):
    """Trigger processing for a single document"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    doc_key, doc_size, thread_id = doc_info
    doc_id = doc_key.split('/')[-1].replace('.pdf', '')
    
    print(f"🔄 [Thread {thread_id}] Starting: {doc_id}", flush=True)
    
    try:
        payload = {
            "Records": [{
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventTime": datetime.utcnow().isoformat() + "Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "bucket": {
                        "name": "solve-global-kr-documents-861276078413-us-east-1",
                        "arn": "arn:aws:s3:::solve-global-kr-documents-861276078413-us-east-1"
                    },
                    "object": {
                        "key": doc_key,
                        "size": doc_size
                    }
                }
            }]
        }
        
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        
        if response['StatusCode'] == 202:
            print(f"✅ [Thread {thread_id}] Success: {doc_id}", flush=True)
            return {'doc_id': doc_id, 'thread_id': thread_id, 'status': 'success'}
        else:
            print(f"❌ [Thread {thread_id}] Failed: {doc_id} - HTTP {response['StatusCode']}", flush=True)
            return {'doc_id': doc_id, 'thread_id': thread_id, 'status': 'failed'}
            
    except Exception as e:
        print(f"❌ [Thread {thread_id}] Error: {doc_id} - {e}", flush=True)
        return {'doc_id': doc_id, 'thread_id': thread_id, 'status': 'error', 'error': str(e)}

def main():
    """Test parallel processing with 5 medium documents"""
    
    print("🚀 TESTING PARALLEL PROCESSING", flush=True)
    print("=" * 50, flush=True)
    
    # 5 medium-sized documents for quick test
    documents = [
        ("documents/006893d2_93170cb9.pdf", 34580, 1),
        ("documents/0068a512_1780336e.pdf", 81776, 2),
        ("documents/004e17a3_3bb90d8e.pdf", 135830, 3),
        ("documents/0032f6cb_f0caef34.pdf", 142850, 4),
        ("documents/007f21ed_c25a961d.pdf", 166430, 5)
    ]
    
    print(f"📄 Processing {len(documents)} documents in parallel", flush=True)
    print(f"⚡ Max concurrent: 5 threads", flush=True)
    print("", flush=True)
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(trigger_single_document, documents))
    
    # Summary
    successful = sum(1 for r in results if r['status'] == 'success')
    total = len(results)
    
    print("", flush=True)
    print("📊 PARALLEL PROCESSING RESULTS:", flush=True)
    print(f"✅ Successful: {successful}/{total}", flush=True)
    print(f"❌ Failed: {total - successful}/{total}", flush=True)
    
    for result in results:
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"   {status_icon} Thread {result['thread_id']}: {result['doc_id']} - {result['status']}", flush=True)
    
    if successful >= total * 0.8:
        print("\n🎉 PARALLEL PROCESSING WORKING!", flush=True)
        return True
    else:
        print("\n⚠️  PARALLEL PROCESSING ISSUES", flush=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
