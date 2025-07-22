#!/usr/bin/env python3
"""
End-to-end test for KG integration pipeline
"""
import boto3
import json
import time
from datetime import datetime

def test_kg_pipeline():
    """Test complete KG processing pipeline"""
    
    print("🧪 Testing KG Integration Pipeline End-to-End")
    print("=" * 60)
    
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns')
    lambda_client = session.client('lambda')
    s3_client = session.client('s3')
    
    # Test document ID
    test_doc_id = f"kg-test-{int(time.time())}"
    
    print(f"📄 Test Document ID: {test_doc_id}")
    
    # 1. Create a sample chunks_ready message
    chunks_ready_message = {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "climate-risk-rag-system",
        "stage": "chunks_ready",
        "doc_id": test_doc_id,
        "data_locations": {
            "chunks_location": f"s3://solve-global-kr-dl-chunks-861276078413-us-east-1/test-data/{test_doc_id}/",
            "chunk_metadata_location": f"s3://solve-global-kr-dl-chunks-861276078413-us-east-1/test-data/{test_doc_id}/metadata.json"
        },
        "processing_metadata": {
            "chunks_created": 3,
            "chunking_method": "smart_structured",
            "total_characters": 500,
            "processing_completed": datetime.utcnow().isoformat() + "Z"
        },
        "integration_flags": {
            "database_tracking_enabled": True,
            "audit_first_design": True,
            "smart_structured_chunking": True
        }
    }
    
    # 2. Create test chunks data in S3
    print("\n📦 Creating test chunks data in S3...")
    
    # Sample chunks
    test_chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "Climate change poses significant risks to financial institutions and their portfolios.",
            "section_title": "Executive Summary",
            "chunk_type": "text",
            "start_char": 0,
            "end_char": 80
        },
        {
            "chunk_id": "chunk_002",
            "content": "Physical risks include extreme weather events that can damage assets and disrupt operations.",
            "section_title": "Physical Risks",
            "chunk_type": "text", 
            "start_char": 81,
            "end_char": 170
        },
        {
            "chunk_id": "chunk_003",
            "content": "Transition risks arise from policy changes and technological shifts toward a low-carbon economy.",
            "section_title": "Transition Risks",
            "chunk_type": "text",
            "start_char": 171,
            "end_char": 265
        }
    ]
    
    # Upload test chunks
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    chunks_prefix = f"test-data/{test_doc_id}/"
    
    for i, chunk in enumerate(test_chunks):
        chunk_key = f"{chunks_prefix}chunk_{i:03d}.json"
        s3_client.put_object(
            Bucket=chunks_bucket,
            Key=chunk_key,
            Body=json.dumps(chunk, indent=2),
            ContentType='application/json'
        )
    
    # Upload metadata
    metadata = {
        "document_info": {
            "title": "Climate Risk Assessment Test Document",
            "source_url": "https://example.com/test-climate-report.pdf"
        },
        "chunking_config": {
            "method": "smart_structured",
            "max_chunk_size": 1000
        },
        "chunks_created": len(test_chunks),
        "total_characters": sum(len(chunk["content"]) for chunk in test_chunks)
    }
    
    metadata_key = f"{chunks_prefix}metadata.json"
    s3_client.put_object(
        Bucket=chunks_bucket,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2),
        ContentType='application/json'
    )
    
    print(f"✅ Created {len(test_chunks)} test chunks and metadata in S3")
    
    # 3. Trigger the document structure KG processor by publishing to chunks-ready
    print("\n🚀 Triggering document structure KG processor...")
    
    chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
    
    response = sns_client.publish(
        TopicArn=chunks_ready_topic_arn,
        Message=json.dumps(chunks_ready_message, default=str),
        Subject=f"Test: Text chunking complete: {test_doc_id}",
        MessageAttributes={
            'stage': {
                'DataType': 'String',
                'StringValue': 'chunks_ready'
            },
            'doc_id': {
                'DataType': 'String',
                'StringValue': test_doc_id
            },
            'version': {
                'DataType': 'String',
                'StringValue': '1.0'
            }
        }
    )
    
    print(f"✅ Published chunks_ready message: {response['MessageId']}")
    
    # 4. Wait and check for TTL generation
    print("\n⏳ Waiting for TTL generation (30 seconds)...")
    time.sleep(30)
    
    # Check if TTL was generated
    ttl_bucket = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
    ttl_key = f"documents/{test_doc_id}/document_structure.ttl"
    
    try:
        ttl_response = s3_client.get_object(Bucket=ttl_bucket, Key=ttl_key)
        ttl_content = ttl_response['Body'].read().decode('utf-8')
        print(f"✅ TTL file generated successfully ({len(ttl_content)} characters)")
        print(f"   Location: s3://{ttl_bucket}/{ttl_key}")
        
        # Show sample of TTL content
        print("\n📄 Sample TTL content:")
        print("-" * 40)
        print(ttl_content[:500] + "..." if len(ttl_content) > 500 else ttl_content)
        print("-" * 40)
        
    except s3_client.exceptions.NoSuchKey:
        print("❌ TTL file not found - document structure processor may have failed")
        return False
    except Exception as e:
        print(f"❌ Error checking TTL file: {e}")
        return False
    
    # 5. Wait and check for Neptune loading
    print("\n⏳ Waiting for Neptune loading (30 seconds)...")
    time.sleep(30)
    
    # 6. Check CloudWatch logs for both functions
    print("\n📊 Checking CloudWatch logs...")
    
    logs_client = session.client('logs')
    
    # Check document structure processor logs
    try:
        doc_processor_logs = logs_client.filter_log_events(
            logGroupName='/aws/lambda/document-structure-kg-processor',
            startTime=int((time.time() - 300) * 1000),  # Last 5 minutes
            filterPattern=test_doc_id
        )
        
        if doc_processor_logs['events']:
            print(f"✅ Found {len(doc_processor_logs['events'])} log events for document processor")
            for event in doc_processor_logs['events'][-3:]:  # Show last 3 events
                print(f"   {event['message'].strip()}")
        else:
            print("⚠️  No log events found for document processor")
            
    except Exception as e:
        print(f"⚠️  Could not check document processor logs: {e}")
    
    # Check KG integration worker logs
    try:
        kg_worker_logs = logs_client.filter_log_events(
            logGroupName='/aws/lambda/kg-integration-worker',
            startTime=int((time.time() - 300) * 1000),  # Last 5 minutes
            filterPattern=test_doc_id
        )
        
        if kg_worker_logs['events']:
            print(f"✅ Found {len(kg_worker_logs['events'])} log events for KG worker")
            for event in kg_worker_logs['events'][-3:]:  # Show last 3 events
                print(f"   {event['message'].strip()}")
        else:
            print("⚠️  No log events found for KG worker")
            
    except Exception as e:
        print(f"⚠️  Could not check KG worker logs: {e}")
    
    # 7. Cleanup test data
    print(f"\n🧹 Cleaning up test data for {test_doc_id}...")
    
    try:
        # Delete test chunks
        objects_to_delete = []
        for i in range(len(test_chunks)):
            objects_to_delete.append({'Key': f"{chunks_prefix}chunk_{i:03d}.json"})
        objects_to_delete.append({'Key': metadata_key})
        
        if objects_to_delete:
            s3_client.delete_objects(
                Bucket=chunks_bucket,
                Delete={'Objects': objects_to_delete}
            )
        
        # Delete TTL file
        try:
            s3_client.delete_object(Bucket=ttl_bucket, Key=ttl_key)
        except:
            pass  # TTL file might not exist if processing failed
        
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"⚠️  Error cleaning up test data: {e}")
    
    print("\n🎉 KG Integration Pipeline Test Complete!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_kg_pipeline()
    exit(0 if success else 1)
