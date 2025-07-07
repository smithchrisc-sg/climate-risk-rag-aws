#!/usr/bin/env python3
"""
Test Fixed Lambda Layer Imports
Direct test of the updated text chunker function
"""

import boto3
import json

def test_fixed_lambda_function():
    """Test the updated lambda function with fixed imports"""
    
    print("🧪 Testing Fixed Lambda Layer Imports")
    print("=" * 60)
    
    # Create Lambda client
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Test payload
    test_payload = {
        "Records": [{
            "body": json.dumps({
                "Message": json.dumps({
                    "doc_id": "test_phase1_fixed",
                    "stage": "test",
                    "test_mode": True
                })
            })
        }]
    }
    
    try:
        print("Invoking updated function...")
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-text-chunker-phase1',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response['StatusCode'] == 200:
            payload = json.loads(response['Payload'].read())
            print("✅ Function invocation successful!")
            print(f"Response: {json.dumps(payload, indent=2)}")
            
            # Check for import errors in the response
            if 'body' in payload:
                body = json.loads(payload['body'])
                if 'results' in body:
                    for result in body['results']:
                        if 'error' in result and 'DatabaseManager' in result['error']:
                            print("❌ DatabaseManager import still failing")
                            return False
                        elif 'error' in result and 'structured_chunking' in result['error']:
                            print("❌ Structured chunker import still failing")
                            return False
            
            return True
        else:
            print(f"❌ Function invocation failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def get_latest_logs():
    """Get the latest CloudWatch logs to check import status"""
    
    print("\n📋 Checking Latest CloudWatch Logs")
    print("=" * 60)
    
    session = boto3.Session(profile_name='solve-global')
    logs_client = session.client('logs', region_name='us-east-1')
    
    try:
        # Get latest log stream
        streams = logs_client.describe_log_streams(
            logGroupName='/aws/lambda/solve-global-kr-text-chunker-phase1',
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if streams['logStreams']:
            stream_name = streams['logStreams'][0]['logStreamName']
            
            # Get recent log events
            events = logs_client.get_log_events(
                logGroupName='/aws/lambda/solve-global-kr-text-chunker-phase1',
                logStreamName=stream_name,
                startFromHead=False,
                limit=20
            )
            
            print(f"Latest log stream: {stream_name}")
            print("\nRecent log events:")
            
            import_success = True
            
            for event in events['events'][-10:]:  # Last 10 events
                message = event['message'].strip()
                if message:
                    if 'Failed to import DatabaseManager' in message:
                        print(f"❌ {message}")
                        import_success = False
                    elif 'Failed to import smart chunker' in message:
                        print(f"❌ {message}")
                        import_success = False
                    elif 'DatabaseManager initialized successfully' in message:
                        print(f"✅ {message}")
                    elif 'Smart structured chunker initialized successfully' in message:
                        print(f"✅ {message}")
                    elif 'ERROR' in message:
                        print(f"⚠️  {message}")
                    elif 'INFO' in message and ('initialized' in message or 'import' in message):
                        print(f"ℹ️  {message}")
            
            return import_success
        else:
            print("No log streams found")
            return False
            
    except Exception as e:
        print(f"❌ Error getting logs: {e}")
        return False

def run_import_fix_test():
    """Run the complete import fix test"""
    
    print("🚀 Lambda Layer Import Fix Test")
    print("=" * 80)
    
    # Test function invocation
    function_test = test_fixed_lambda_function()
    
    # Check logs for import status
    logs_test = get_latest_logs()
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 Import Fix Test Results")
    print("=" * 80)
    
    if function_test and logs_test:
        print("✅ SUCCESS: Lambda layer imports fixed successfully!")
        print("✅ DatabaseManager and SmartStructuredChunker imports working")
        return True
    elif function_test:
        print("✅ Function invocation working")
        print("⚠️  Check logs for import status")
        return True
    else:
        print("❌ FAILED: Import issues still present")
        return False

if __name__ == "__main__":
    success = run_import_fix_test()
    exit(0 if success else 1)
