#!/usr/bin/env python3
"""
Check Processing Status and Investigate Delays
"""

import boto3
import json
import time
from datetime import datetime, timedelta

def check_processing_status():
    """Check the status of processing and investigate delays"""
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    sqs_client = boto3.client('sqs', region_name='us-east-1')
    
    print("🔍 INVESTIGATING PROCESSING STATUS AND DELAYS")
    print("=" * 60)
    
    # Check recent activity in key functions
    functions_to_check = [
        'text-chunker-pipeline',
        'nlp-processor', 
        'nlp-worker',
        'solve-global-kr-textextractor-processor'
    ]
    
    # Time range - last 2 hours
    end_time = int(time.time() * 1000)
    start_time = end_time - (2 * 60 * 60 * 1000)
    
    for function_name in functions_to_check:
        print(f"\n📋 {function_name.upper()} LOGS:")
        try:
            log_group = f"/aws/lambda/{function_name}"
            
            # Get recent log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=2
            )
            
            recent_events = []
            for stream in streams_response['logStreams']:
                if stream.get('lastEventTime', 0) >= start_time:
                    events_response = logs_client.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream['logStreamName'],
                        startTime=start_time,
                        endTime=end_time
                    )
                    
                    for event in events_response['events']:
                        recent_events.append({
                            'timestamp': event['timestamp'],
                            'message': event['message']
                        })
            
            # Sort by timestamp and show recent events
            recent_events.sort(key=lambda x: x['timestamp'])
            
            if recent_events:
                print(f"   📊 Found {len(recent_events)} recent events")
                for event in recent_events[-5:]:  # Last 5 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()
                    
                    if "ERROR" in message or "Exception" in message:
                        print(f"   ❌ [{timestamp.strftime('%H:%M:%S')}] {message}")
                    elif "Successfully" in message or "complete" in message:
                        print(f"   ✅ [{timestamp.strftime('%H:%M:%S')}] {message}")
                    elif "Processing" in message or "Started" in message:
                        print(f"   🔄 [{timestamp.strftime('%H:%M:%S')}] {message}")
                    else:
                        print(f"   ℹ️  [{timestamp.strftime('%H:%M:%S')}] {message}")
            else:
                print("   ⚠️  No recent activity found")
                
        except Exception as e:
            print(f"   ❌ Error checking logs: {e}")
    
    # Check SQS queue status
    print(f"\n📬 SQS QUEUE STATUS:")
    
    queues_to_check = [
        "https://sqs.us-east-1.amazonaws.com/861276078413/text-chunker-queue",
        "https://sqs.us-east-1.amazonaws.com/861276078413/nlp-worker-queue",
        "https://sqs.us-east-1.amazonaws.com/861276078413/solve-global-kr-textextractor-processor"
    ]
    
    for queue_url in queues_to_check:
        queue_name = queue_url.split('/')[-1]
        try:
            response = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            
            visible = response['Attributes']['ApproximateNumberOfMessages']
            in_flight = response['Attributes']['ApproximateNumberOfMessagesNotVisible']
            
            print(f"   📋 {queue_name}:")
            print(f"      Visible: {visible} messages")
            print(f"      In-flight: {in_flight} messages")
            
        except Exception as e:
            print(f"   ❌ Error checking {queue_name}: {e}")
    
    # Check if NLP processing might be happening but taking time
    print(f"\n🧠 NLP PROCESSING INVESTIGATION:")
    
    # Check if there are any recent NLP results
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # List recent NLP results
        response = s3_client.list_objects_v2(
            Bucket="solve-global-kr-dl-ner-results-861276078413-us-east-1",
            Prefix="nlp/",
            MaxKeys=10
        )
        
        if response.get('KeyCount', 0) > 0:
            print(f"   📊 Found {response['KeyCount']} NLP result files")
            
            # Check modification times
            recent_files = []
            cutoff_time = datetime.now() - timedelta(hours=2)
            
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) > cutoff_time:
                    recent_files.append(obj)
            
            if recent_files:
                print(f"   ✅ {len(recent_files)} files modified in last 2 hours")
                for file in recent_files[-3:]:
                    print(f"      📄 {file['Key']} ({file['LastModified']})")
            else:
                print(f"   ⚠️  No recent NLP files (last 2 hours)")
        else:
            print(f"   ❌ No NLP result files found")
            
    except Exception as e:
        print(f"   ❌ Error checking NLP results: {e}")
    
    # Performance analysis
    print(f"\n⏱️  PERFORMANCE ANALYSIS:")
    print(f"   🔍 Possible reasons for delays:")
    print(f"      • Textract jobs take 2-5 minutes per document")
    print(f"      • Large documents (80+ pages) take longer")
    print(f"      • Cold starts in Lambda functions")
    print(f"      • Database connection timeouts")
    print(f"      • SNS/SQS message delays")
    print(f"      • Comprehend API rate limits")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   1. Wait longer - some documents may still be processing")
    print(f"   2. Check for stuck messages in SQS queues")
    print(f"   3. Monitor Comprehend API usage and limits")
    print(f"   4. Consider increasing Lambda timeouts for large documents")

if __name__ == "__main__":
    check_processing_status()
