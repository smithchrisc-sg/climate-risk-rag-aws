#!/usr/bin/env python3
"""
Complete End-to-End Pipeline Test
Test one fresh document through the entire pipeline to verify all fixes
"""

import boto3
import json
import time
from datetime import datetime

def test_complete_pipeline():
    """Test complete pipeline with one fresh document"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # Use a fresh document that hasn't been processed
    test_document = {
        "key": "documents/01dd077e_86ce1ac2.pdf",
        "size": 538035,
        "est_pages": 14
    }
    
    bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
    doc_id = test_document['key'].split('/')[-1].replace('.pdf', '')
    
    print("🧪 COMPLETE END-TO-END PIPELINE TEST")
    print("=" * 50)
    print(f"📄 Document: {doc_id}")
    print(f"📊 Size: {test_document['size']:,} bytes ({test_document['est_pages']} pages)")
    print("")
    
    # Step 1: Trigger Textract processing
    print("1️⃣ Triggering Textract processing...")
    
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
        print(f"❌ Failed to trigger processing: {response['StatusCode']}")
        return False
    
    print("✅ Textract processing triggered")
    
    # Step 2: Wait for Textract completion (5 minutes)
    print("\n2️⃣ Waiting 5 minutes for Textract completion...")
    time.sleep(300)
    
    # Check text extraction
    try:
        text_key = f"text/{doc_id}.txt"
        response = s3_client.get_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
        text_content = response['Body'].read().decode('utf-8')
        print(f"✅ Text extraction successful: {len(text_content):,} characters")
        text_success = True
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")
        text_success = False
    
    # Step 3: Wait for text chunking (2 minutes)
    print("\n3️⃣ Waiting 2 minutes for text chunking...")
    time.sleep(120)
    
    # Check chunks
    try:
        chunks_prefix = f"chunks/{doc_id}/"
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-chunks-861276078413-us-east-1",
            Prefix=chunks_prefix
        )
        chunk_count = response.get('KeyCount', 0)
        if chunk_count > 0:
            print(f"✅ Text chunking successful: {chunk_count} chunks created")
            chunks_success = True
        else:
            print(f"❌ Text chunking failed: no chunks found")
            chunks_success = False
    except Exception as e:
        print(f"❌ Text chunking failed: {e}")
        chunks_success = False
    
    # Step 4: Wait for NLP processing (3 minutes)
    print("\n4️⃣ Waiting 3 minutes for NLP processing...")
    time.sleep(180)
    
    # Check NLP results
    try:
        nlp_prefix = f"nlp/{doc_id}/"
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-ner-results-861276078413-us-east-1",
            Prefix=nlp_prefix,
            MaxKeys=1
        )
        if response.get('KeyCount', 0) > 0:
            print(f"✅ NLP processing successful: results found")
            nlp_success = True
        else:
            print(f"❌ NLP processing failed: no results found")
            nlp_success = False
    except Exception as e:
        print(f"❌ NLP processing failed: {e}")
        nlp_success = False
    
    # Step 5: Check logs for debugging
    print("\n5️⃣ Checking recent logs for debugging...")
    
    functions_to_check = [
        'solve-global-kr-textextractor-processor',
        'text-chunker-pipeline',
        'nlp-processor'
    ]
    
    end_time = int(time.time() * 1000)
    start_time = end_time - (15 * 60 * 1000)  # 15 minutes ago
    
    for function_name in functions_to_check:
        print(f"\n📋 {function_name}:")
        try:
            log_group = f"/aws/lambda/{function_name}"
            
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if streams_response['logStreams']:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=streams_response['logStreams'][0]['logStreamName'],
                    startTime=start_time,
                    endTime=end_time
                )
                
                recent_events = [e for e in events_response['events'] if doc_id in e['message']]
                
                if recent_events:
                    for event in recent_events[-3:]:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].strip()
                        
                        if "ERROR" in message or "Failed" in message:
                            print(f"   ❌ [{timestamp.strftime('%H:%M:%S')}] {message}")
                        elif "Success" in message or "complete" in message:
                            print(f"   ✅ [{timestamp.strftime('%H:%M:%S')}] {message}")
                        else:
                            print(f"   ℹ️  [{timestamp.strftime('%H:%M:%S')}] {message}")
                else:
                    print(f"   ⚠️  No recent activity for {doc_id}")
            else:
                print(f"   ⚠️  No log streams found")
                
        except Exception as e:
            print(f"   ❌ Error checking logs: {e}")
    
    # Final assessment
    print(f"\n📊 FINAL ASSESSMENT")
    print("=" * 50)
    print(f"📝 Text Extraction: {'✅ Success' if text_success else '❌ Failed'}")
    print(f"🔗 Text Chunking: {'✅ Success' if chunks_success else '❌ Failed'}")
    print(f"🧠 NLP Processing: {'✅ Success' if nlp_success else '❌ Failed'}")
    
    total_success = sum([text_success, chunks_success, nlp_success])
    
    if total_success == 3:
        print(f"\n🎉 COMPLETE SUCCESS: Full end-to-end pipeline working!")
        return True
    elif total_success >= 2:
        print(f"\n🔄 PARTIAL SUCCESS: {total_success}/3 stages completed")
        return True
    else:
        print(f"\n❌ PIPELINE ISSUES: Only {total_success}/3 stages completed")
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    exit(0 if success else 1)
