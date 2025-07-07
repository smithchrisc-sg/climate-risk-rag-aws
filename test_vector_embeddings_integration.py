#!/usr/bin/env python3
"""
Integration test for vector embeddings system
"""
import boto3
import json
import time
from datetime import datetime

def test_vector_embeddings_integration():
    """Test the complete vector embeddings pipeline"""
    
    print("VECTOR EMBEDDINGS INTEGRATION TEST")
    print("=" * 60)
    
    # Test document that already has chunks
    doc_id = "0032f6cb_f0caef34"
    
    print("Test Document: {}".format(doc_id))
    print("Expected Chunks: 19")
    print("Model: SentenceTransformers (free)")
    print("=" * 60)
    
    # Create AWS clients
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns', region_name='us-east-1')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Step 1: Trigger vector embeddings processor directly
    print("\n1. TRIGGERING VECTOR EMBEDDINGS PROCESSOR")
    print("-" * 40)
    
    # Create chunks-ready message (simulating text chunker completion)
    chunks_ready_message = {
        "doc_id": doc_id,
        "stage": "chunks_ready",
        "chunks_location": {
            "bucket": "solve-global-kr-chunks-861276078413-us-east-1",
            "prefix": "{}/".format(doc_id),
            "pattern": "{}_chunk_*.json".format(doc_id)
        },
        "chunks_count": 19,
        "timestamp": datetime.now().isoformat()
    }
    
    # Create SNS event format
    processor_event = {
        "Records": [{
            "Sns": {
                "Message": json.dumps(chunks_ready_message)
            }
        }]
    }
    
    try:
        # Invoke vector embeddings processor
        processor_function = "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA"
        
        print("Invoking processor: {}".format(processor_function))
        
        response = lambda_client.invoke(
            FunctionName=processor_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(processor_event)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response.get('StatusCode') == 200:
            print("SUCCESS: Processor invoked successfully")
            print("Response: {}".format(response_payload))
            
            # Check if it delegated to worker
            if 'body' in response_payload:
                body = json.loads(response_payload['body'])
                if body.get('status') == 'delegated_to_worker':
                    print("SUCCESS: Work delegated to background worker")
                    return True
                else:
                    print("WARNING: Unexpected processor response")
                    return False
        else:
            print("ERROR: Processor invocation failed")
            print("Response: {}".format(response_payload))
            return False
            
    except Exception as e:
        print("ERROR: Failed to invoke processor - {}".format(str(e)))
        return False

def monitor_worker_execution():
    """Monitor the worker function execution"""
    print("\n2. MONITORING WORKER EXECUTION")
    print("-" * 40)
    
    session = boto3.Session(profile_name='solve-global')
    logs_client = session.client('logs', region_name='us-east-1')
    
    # Worker function log group
    log_group = "/aws/lambda/vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi"
    
    try:
        # Get recent log events
        end_time = int(time.time() * 1000)
        start_time = end_time - (5 * 60 * 1000)  # Last 5 minutes
        
        print("Checking logs from: {}".format(log_group))
        
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            limit=10
        )
        
        events = response.get('events', [])
        
        if events:
            print("Recent worker log events:")
            for event in events[-5:]:  # Show last 5 events
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                print("  [{}] {}".format(timestamp.strftime('%H:%M:%S'), event['message'].strip()))
        else:
            print("No recent log events found (worker may not have executed yet)")
            
        return len(events) > 0
        
    except Exception as e:
        print("ERROR: Failed to check worker logs - {}".format(str(e)))
        return False

def check_opensearch_index():
    """Check if vector index was created in OpenSearch"""
    print("\n3. CHECKING OPENSEARCH VECTOR INDEX")
    print("-" * 40)
    
    # This would require OpenSearch client setup
    # For now, we'll just indicate what to check
    print("Manual verification needed:")
    print("1. Check OpenSearch console for 'climate-risk-vector-index'")
    print("2. Verify vector documents were indexed")
    print("3. Test vector similarity search")
    
    return True

def main():
    """Run complete integration test"""
    
    print("Starting Vector Embeddings Integration Test...")
    print("This will test the complete pipeline from chunks-ready to vector indexing")
    
    # Step 1: Trigger processor
    processor_success = test_vector_embeddings_integration()
    
    if processor_success:
        print("\nWaiting 30 seconds for worker to process...")
        time.sleep(30)
        
        # Step 2: Monitor worker
        worker_activity = monitor_worker_execution()
        
        # Step 3: Check OpenSearch
        opensearch_check = check_opensearch_index()
        
        # Summary
        print("\n" + "=" * 60)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print("Processor Trigger: {}".format("PASS" if processor_success else "FAIL"))
        print("Worker Activity: {}".format("DETECTED" if worker_activity else "NOT DETECTED"))
        print("OpenSearch Check: {}".format("MANUAL VERIFICATION NEEDED"))
        
        if processor_success:
            print("\nSUCCESS: Vector embeddings pipeline triggered successfully!")
            print("Monitor CloudWatch logs for detailed execution status.")
        else:
            print("\nFAILED: Integration test encountered issues.")
            
    else:
        print("\nFAILED: Could not trigger vector embeddings processor.")

if __name__ == "__main__":
    main()
