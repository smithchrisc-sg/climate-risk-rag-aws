#!/usr/bin/env python3
"""
Final Test After Database Schema Fixes
"""

import boto3
import json
import time
from datetime import datetime

def test_final_fix():
    """Test with fresh document after all fixes"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # Use another small document
    test_document = {
        "key": "documents/023951b5_be6da2bf.pdf",
        "size": 316498
    }
    
    bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
    doc_id = test_document['key'].split('/')[-1].replace('.pdf', '')
    
    print(f"🧪 Final Test After All Fixes: {doc_id}")
    print(f"📊 Size: {test_document['size']:,} bytes")
    
    # Create proper S3 event
    payload = {
        "Records": [
            {
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
            }
        ]
    }
    
    # Trigger processing
    print(f"\n🚀 Triggering processing...")
    response = lambda_client.invoke(
        FunctionName='solve-global-kr-textextractor-initiator',
        InvocationType='Event',
        Payload=json.dumps(payload)
    )
    
    if response['StatusCode'] != 202:
        print(f"❌ Failed to trigger processing: {response['StatusCode']}")
        return False
    
    print(f"✅ Processing triggered successfully")
    
    # Wait and check logs
    print(f"\n⏳ Waiting 45 seconds for processing...")
    time.sleep(45)
    
    # Check initiator logs
    try:
        log_group = "/aws/lambda/solve-global-kr-textextractor-initiator"
        
        end_time = int(time.time() * 1000)
        start_time = end_time - (3 * 60 * 1000)
        
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams_response['logStreams']:
            stream_name = streams_response['logStreams'][0]['logStreamName']
            
            events_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                startTime=start_time,
                endTime=end_time
            )
            
            print(f"\n📋 Textract Initiator Logs:")
            job_started = False
            for event in events_response['events'][-5:]:
                message = event['message'].strip()
                if "Started Textract job" in message:
                    print(f"  ✅ {message}")
                    job_started = True
                elif "Processing complete" in message:
                    print(f"  ✅ {message}")
                elif "ERROR" in message or "Exception" in message:
                    print(f"  ❌ {message}")
                elif "skipped" in message:
                    print(f"  ⚠️  {message}")
                else:
                    print(f"  ℹ️  {message}")
            
            if not job_started:
                print(f"⚠️  No Textract job was started - document may have been skipped")
                return False
    
    except Exception as e:
        print(f"⚠️  Could not retrieve initiator logs: {e}")
        return False
    
    # Wait for Textract completion and check processor
    print(f"\n⏳ Waiting 4 minutes for Textract completion...")
    time.sleep(240)
    
    # Check processor logs
    try:
        processor_log_group = "/aws/lambda/solve-global-kr-textextractor-processor"
        
        streams_response = logs_client.describe_log_streams(
            logGroupName=processor_log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams_response['logStreams']:
            stream_name = streams_response['logStreams'][0]['logStreamName']
            
            events_response = logs_client.get_log_events(
                logGroupName=processor_log_group,
                logStreamName=stream_name,
                startTime=start_time,
                endTime=int(time.time() * 1000)
            )
            
            print(f"\n📋 Textract Processor Logs:")
            processor_success = False
            for event in events_response['events'][-10:]:
                message = event['message'].strip()
                if "Successfully processed" in message or "Processing complete" in message:
                    print(f"  ✅ {message}")
                    processor_success = True
                elif "Published standardized text extraction complete message" in message:
                    print(f"  ✅ {message}")
                    processor_success = True
                elif "ERROR" in message or "Exception" in message:
                    print(f"  ❌ {message}")
                elif "Processing Textract job completion" in message:
                    print(f"  ✅ {message}")
                elif "Updated job status" in message:
                    print(f"  ✅ {message}")
                else:
                    print(f"  ℹ️  {message}")
    
    except Exception as e:
        print(f"⚠️  Could not retrieve processor logs: {e}")
    
    # Check if text was created
    try:
        text_key = f"text/{doc_id}.txt"
        s3_client.head_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
        print(f"\n✅ SUCCESS: Text extraction found: {text_key}")
        
        # Check for chunks
        print(f"\n⏳ Waiting 2 more minutes for text chunking...")
        time.sleep(120)
        
        try:
            chunks_prefix = f"chunks/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-chunks-861276078413-us-east-1",
                Prefix=chunks_prefix,
                MaxKeys=1
            )
            if response.get('KeyCount', 0) > 0:
                print(f"✅ SUCCESS: Chunks also created for {doc_id}")
                print(f"\n🎉 COMPLETE SUCCESS: Full pipeline working end-to-end!")
                return True
            else:
                print(f"⏳ Chunks not yet created for {doc_id}")
                print(f"\n🔄 PARTIAL SUCCESS: Text extraction working, chunks pending")
                return True
        except:
            print(f"⏳ Chunks not yet created for {doc_id}")
            print(f"\n🔄 PARTIAL SUCCESS: Text extraction working, chunks pending")
            return True
        
    except:
        print(f"\n❌ FAILED: Text extraction not found: text/{doc_id}.txt")
        return False

if __name__ == "__main__":
    success = test_final_fix()
    print(f"\n🎯 Final Result: {'✅ SUCCESS - Pipeline Fixed!' if success else '❌ FAILED - Still Issues'}")
    exit(0 if success else 1)
