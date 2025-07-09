#!/usr/bin/env python3
"""
Test chunks-ready message flow to diagnose NLP processing issue
"""

import boto3
import json
import time
from datetime import datetime, timedelta

def test_chunks_ready_flow():
    """Test the chunks-ready message flow"""
    
    sns_client = boto3.client('sns', region_name='us-east-1')
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    print("🔍 TESTING CHUNKS-READY MESSAGE FLOW")
    print("=" * 50)
    
    # Check recent text chunker activity
    print("\n📋 Checking Text Chunker Logs (last 30 minutes):")
    
    try:
        log_group = "/aws/lambda/text-chunker-pipeline"
        
        end_time = int(time.time() * 1000)
        start_time = end_time - (30 * 60 * 1000)  # 30 minutes ago
        
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=3
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
        
        # Sort by timestamp
        recent_events.sort(key=lambda x: x['timestamp'])
        
        if recent_events:
            print(f"   📊 Found {len(recent_events)} recent events")
            
            chunks_ready_published = 0
            processing_events = 0
            
            for event in recent_events[-10:]:  # Last 10 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                
                if "Published standardized chunks ready message" in message:
                    print(f"   ✅ [{timestamp.strftime('%H:%M:%S')}] {message}")
                    chunks_ready_published += 1
                elif "Successfully processed" in message and "chunks" in message:
                    print(f"   🔄 [{timestamp.strftime('%H:%M:%S')}] {message}")
                    processing_events += 1
                elif "ERROR" in message or "Failed" in message:
                    print(f"   ❌ [{timestamp.strftime('%H:%M:%S')}] {message}")
                else:
                    print(f"   ℹ️  [{timestamp.strftime('%H:%M:%S')}] {message}")
            
            print(f"\n   📊 Summary:")
            print(f"      Processing Events: {processing_events}")
            print(f"      Chunks-Ready Published: {chunks_ready_published}")
            
        else:
            print("   ⚠️  No recent text chunker activity found")
            
    except Exception as e:
        print(f"   ❌ Error checking text chunker logs: {e}")
    
    # Check NLP processor activity
    print("\n📋 Checking NLP Processor Logs (last 30 minutes):")
    
    try:
        log_group = "/aws/lambda/nlp-processor"
        
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=3
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
        
        if recent_events:
            print(f"   📊 Found {len(recent_events)} recent NLP processor events")
            
            for event in recent_events[-5:]:  # Last 5 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                
                if "ERROR" in message or "Failed" in message:
                    print(f"   ❌ [{timestamp.strftime('%H:%M:%S')}] {message}")
                elif "Processing" in message or "Started" in message:
                    print(f"   🔄 [{timestamp.strftime('%H:%M:%S')}] {message}")
                else:
                    print(f"   ℹ️  [{timestamp.strftime('%H:%M:%S')}] {message}")
        else:
            print("   ⚠️  No recent NLP processor activity - THIS IS THE ISSUE!")
            
    except Exception as e:
        print(f"   ❌ Error checking NLP processor logs: {e}")
    
    # Test direct SNS message to NLP processor
    print("\n🧪 Testing Direct SNS Message to NLP Processor:")
    
    try:
        # Create a test chunks-ready message
        test_message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "chunks_ready",
            "doc_id": "test-doc-001",
            "doc_hash": "test-hash-001",
            "document_metadata": {
                "original_filename": "test.pdf",
                "file_size": 100000,
                "page_count": 5
            },
            "data_locations": {
                "chunks": "s3://solve-global-kr-chunks-861276078413-us-east-1/chunks/test-doc-001/",
                "text": "s3://solve-global-kr-text-new-861276078413-us-east-1/text/test-doc-001.txt"
            },
            "processing_metadata": {
                "chunks_count": 10,
                "processing_duration_ms": 1000
            }
        }
        
        # Publish test message
        response = sns_client.publish(
            TopicArn="arn:aws:sns:us-east-1:861276078413:chunks-ready",
            Message=json.dumps(test_message),
            Subject="Test chunks-ready message"
        )
        
        print(f"   ✅ Test message published: {response['MessageId']}")
        print(f"   ⏳ Waiting 30 seconds to check if NLP processor receives it...")
        
        time.sleep(30)
        
        # Check if NLP processor received the message
        end_time_after = int(time.time() * 1000)
        start_time_after = end_time_after - (2 * 60 * 1000)  # 2 minutes ago
        
        streams_response = logs_client.describe_log_streams(
            logGroupName="/aws/lambda/nlp-processor",
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams_response['logStreams']:
            events_response = logs_client.get_log_events(
                logGroupName="/aws/lambda/nlp-processor",
                logStreamName=streams_response['logStreams'][0]['logStreamName'],
                startTime=start_time_after,
                endTime=end_time_after
            )
            
            if events_response['events']:
                print(f"   ✅ NLP processor received the test message!")
                for event in events_response['events'][-3:]:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    print(f"      [{timestamp.strftime('%H:%M:%S')}] {event['message'].strip()}")
            else:
                print(f"   ❌ NLP processor did not receive the test message")
        else:
            print(f"   ❌ No NLP processor log streams found")
            
    except Exception as e:
        print(f"   ❌ Error testing direct SNS message: {e}")
    
    print(f"\n🎯 DIAGNOSIS COMPLETE")
    print(f"   If NLP processor received the test message, the issue is with")
    print(f"   the text chunker not publishing chunks-ready messages.")
    print(f"   If not, there's an SNS subscription issue.")

if __name__ == "__main__":
    test_chunks_ready_flow()
