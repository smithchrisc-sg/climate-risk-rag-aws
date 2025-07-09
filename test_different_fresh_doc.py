#!/usr/bin/env python3
"""
Test with Different Fresh Document
"""

import boto3
import json
import time
from datetime import datetime

def test_different_fresh_document():
    """Test with a different fresh document"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # Use a different small document
    test_document = {
        "key": "documents/0297eeee_0e55d7a3.pdf",
        "size": 36401
    }
    
    bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
    doc_id = test_document['key'].split('/')[-1].replace('.pdf', '')
    
    print(f"🧪 Testing Different Fresh Document: {doc_id}")
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
            
            print(f"\n📋 Recent Textract Initiator Logs:")
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
        print(f"⚠️  Could not retrieve logs: {e}")
        return False
    
    # Wait for Textract completion and check processor
    print(f"\n⏳ Waiting 3 minutes for Textract completion...")
    time.sleep(180)
    
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
            
            print(f"\n📋 Recent Textract Processor Logs:")
            processor_success = False
            for event in events_response['events'][-8:]:
                message = event['message'].strip()
                if "Successfully processed" in message or "Processing complete" in message:
                    print(f"  ✅ {message}")
                    processor_success = True
                elif "ERROR" in message or "Exception" in message or "Invalid" in message:
                    print(f"  ❌ {message}")
                elif "Processing Textract job completion" in message:
                    print(f"  ✅ {message}")
                    processor_success = True
                elif "Received SNS message format" in message:
                    print(f"  ℹ️  {message}")
                else:
                    print(f"  ℹ️  {message}")
    
    except Exception as e:
        print(f"⚠️  Could not retrieve processor logs: {e}")
    
    # Check if text was created
    try:
        text_key = f"text/{doc_id}.txt"
        s3_client.head_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
        print(f"\n✅ SUCCESS: Text extraction found: {text_key}")
        
        # Also check for chunks
        try:
            chunks_prefix = f"chunks/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-chunks-861276078413-us-east-1",
                Prefix=chunks_prefix,
                MaxKeys=1
            )
            if response.get('KeyCount', 0) > 0:
                print(f"✅ SUCCESS: Chunks also created for {doc_id}")
            else:
                print(f"⏳ Chunks not yet created for {doc_id}")
        except:
            print(f"⏳ Chunks not yet created for {doc_id}")
        
        return True
        
    except:
        print(f"\n❌ FAILED: Text extraction not found: text/{doc_id}.txt")
        return False

if __name__ == "__main__":
    success = test_different_fresh_document()
    print(f"\n🎯 Final Result: {'✅ SUCCESS - Pipeline Working!' if success else '❌ FAILED - Still Issues'}")
    exit(0 if success else 1)
