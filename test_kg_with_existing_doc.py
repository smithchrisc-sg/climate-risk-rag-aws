#!/usr/bin/env python3
"""
KG Integration Test with Existing Document
Tests KG processing using a document that already exists in the system
"""
import boto3
import json
import time
from datetime import datetime

def test_kg_with_existing_document():
    """Test KG processing with an existing document ID"""
    
    print("🧪 KG Integration Test with Existing Document")
    print("=" * 60)
    
    session = boto3.Session(profile_name='solve-global')
    s3_client = session.client('s3')
    sns_client = session.client('sns')
    
    # Use an existing document ID from the system
    existing_doc_id = "064762102bead7b04a39"
    print(f"📄 Using existing document ID: {existing_doc_id}")
    
    try:
        # Step 1: Create test chunks for the existing document
        print("\n📦 Step 1: Create test chunks for existing document")
        chunks_location = create_chunks_for_existing_doc(s3_client, existing_doc_id)
        
        # Step 2: Trigger KG processing
        print("\n🚀 Step 2: Trigger KG processing")
        trigger_kg_processing(sns_client, existing_doc_id, chunks_location)
        
        # Step 3: Monitor TTL generation
        print("\n⏳ Step 3: Monitor TTL generation (90 seconds)")
        ttl_location = monitor_ttl_generation(s3_client, existing_doc_id, max_wait=90)
        
        if ttl_location:
            print("\n✅ Step 4: Analyze TTL content")
            analyze_ttl_content(s3_client, ttl_location)
            
            # Step 5: Monitor Neptune loading
            print("\n⏳ Step 5: Monitor Neptune loading (60 seconds)")
            monitor_neptune_logs(session, existing_doc_id)
        else:
            print("\n❌ TTL generation failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\n🧹 Cleanup test chunks")
        cleanup_test_chunks(s3_client, existing_doc_id)
    
    print("\n" + "=" * 60)
    print("🎉 KG Integration Test Complete!")

def create_chunks_for_existing_doc(s3_client, doc_id):
    """Create test chunks for existing document"""
    
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    chunks_prefix = f"kg-test/{doc_id}/"
    
    # Create focused climate risk chunks
    test_chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "Climate-related financial risks are increasingly recognized as a source of financial instability. Central banks and financial supervisors worldwide are developing frameworks to assess and manage these risks.",
            "section_title": "Climate Financial Risk Overview",
            "chunk_type": "text",
            "start_char": 0,
            "end_char": 180,
            "page_number": 1
        },
        {
            "chunk_id": "chunk_002",
            "content": "Physical risks include acute events like hurricanes and floods, as well as chronic changes such as rising temperatures and sea levels. These can directly impact asset values and operational capacity.",
            "section_title": "Physical Climate Risks",
            "chunk_type": "text",
            "start_char": 181,
            "end_char": 380,
            "page_number": 2
        },
        {
            "chunk_id": "chunk_003",
            "content": "Transition risks arise from the shift toward a low-carbon economy, including policy changes, technological developments, and evolving market preferences that can affect asset valuations.",
            "section_title": "Transition Risks",
            "chunk_type": "text",
            "start_char": 381,
            "end_char": 560,
            "page_number": 3
        }
    ]
    
    # Upload chunks
    for i, chunk in enumerate(test_chunks):
        chunk_key = f"{chunks_prefix}chunk_{i:03d}.json"
        s3_client.put_object(
            Bucket=chunks_bucket,
            Key=chunk_key,
            Body=json.dumps(chunk, indent=2),
            ContentType='application/json'
        )
    
    # Create metadata
    metadata = {
        "document_info": {
            "title": "Climate Risk Management Guidelines",
            "source_url": f"https://example.com/docs/{doc_id}.pdf",
            "document_type": "regulatory_guidance"
        },
        "chunking_config": {
            "method": "smart_structured",
            "max_chunk_size": 1000
        },
        "processing_stats": {
            "chunks_created": len(test_chunks),
            "total_characters": sum(len(chunk["content"]) for chunk in test_chunks)
        },
        "created_at": datetime.utcnow().isoformat() + 'Z'
    }
    
    metadata_key = f"{chunks_prefix}metadata.json"
    s3_client.put_object(
        Bucket=chunks_bucket,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2),
        ContentType='application/json'
    )
    
    chunks_location = f"s3://{chunks_bucket}/{chunks_prefix}"
    print(f"✅ Created {len(test_chunks)} chunks at: {chunks_location}")
    
    return chunks_location

def trigger_kg_processing(sns_client, doc_id, chunks_location):
    """Trigger KG processing with chunks_ready message"""
    
    message = {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "climate-risk-rag-system",
        "stage": "chunks_ready",
        "doc_id": doc_id,
        "data_locations": {
            "chunks_location": chunks_location,
            "chunk_metadata_location": f"{chunks_location}metadata.json"
        },
        "processing_metadata": {
            "chunks_created": 3,
            "chunking_method": "smart_structured",
            "total_characters": 560,
            "processing_completed": datetime.utcnow().isoformat() + "Z"
        },
        "integration_flags": {
            "database_tracking_enabled": True,
            "audit_first_design": True,
            "smart_structured_chunking": True
        }
    }
    
    response = sns_client.publish(
        TopicArn="arn:aws:sns:us-east-1:861276078413:chunks-ready",
        Message=json.dumps(message, default=str),
        Subject=f"KG Test: chunks ready for {doc_id}",
        MessageAttributes={
            'stage': {'DataType': 'String', 'StringValue': 'chunks_ready'},
            'doc_id': {'DataType': 'String', 'StringValue': doc_id},
            'test_type': {'DataType': 'String', 'StringValue': 'kg_integration'}
        }
    )
    
    print(f"✅ Published chunks_ready message: {response['MessageId']}")

def monitor_ttl_generation(s3_client, doc_id, max_wait=90):
    """Monitor TTL file generation with detailed progress"""
    
    ttl_bucket = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
    ttl_key = f"documents/{doc_id}/document_structure.ttl"
    
    print(f"   Monitoring: s3://{ttl_bucket}/{ttl_key}")
    
    for attempt in range(max_wait):
        try:
            response = s3_client.get_object(Bucket=ttl_bucket, Key=ttl_key)
            ttl_content = response['Body'].read().decode('utf-8')
            
            print(f"✅ TTL generated! Size: {len(ttl_content)} characters")
            return f"s3://{ttl_bucket}/{ttl_key}"
            
        except s3_client.exceptions.NoSuchKey:
            if attempt % 15 == 0:  # Print every 15 seconds
                print(f"   ⏳ Waiting... ({attempt}s elapsed)")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print(f"❌ TTL not generated within {max_wait} seconds")
    return None

def analyze_ttl_content(s3_client, ttl_location):
    """Analyze the generated TTL content"""
    
    try:
        bucket, key = ttl_location.replace('s3://', '').split('/', 1)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        ttl_content = response['Body'].read().decode('utf-8')
        
        print(f"📊 TTL Analysis:")
        print(f"   Size: {len(ttl_content)} characters")
        print(f"   Lines: {len(ttl_content.splitlines())}")
        
        # Check for key elements
        elements = {
            'Dublin Core prefixes': '@prefix dc:' in ttl_content,
            'Document resource': 'dcterms:Text' in ttl_content,
            'Document chunks': 'cr:DocumentChunk' in ttl_content,
            'Content abstracts': 'dcterms:abstract' in ttl_content
        }
        
        for element, present in elements.items():
            status = "✅" if present else "❌"
            print(f"   {status} {element}")
        
        # Show sample content
        print(f"\n📄 Sample TTL (first 400 chars):")
        print("-" * 50)
        print(ttl_content[:400] + "..." if len(ttl_content) > 400 else ttl_content)
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ TTL analysis error: {e}")

def monitor_neptune_logs(session, doc_id):
    """Monitor Neptune loading logs"""
    
    logs_client = session.client('logs')
    
    try:
        start_time = int((time.time() - 300) * 1000)  # Last 5 minutes
        
        response = logs_client.filter_log_events(
            logGroupName='/aws/lambda/kg-integration-worker',
            startTime=start_time,
            filterPattern=doc_id
        )
        
        events = response.get('events', [])
        if events:
            print(f"✅ Found {len(events)} Neptune loading events")
            for event in events[-3:]:  # Show last 3
                print(f"   📝 {event['message'].strip()}")
        else:
            print("⚠️  No Neptune loading events found yet")
            
    except Exception as e:
        print(f"⚠️  Log monitoring error: {e}")

def cleanup_test_chunks(s3_client, doc_id):
    """Clean up test chunks"""
    
    try:
        chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        prefix = f"kg-test/{doc_id}/"
        
        response = s3_client.list_objects_v2(Bucket=chunks_bucket, Prefix=prefix)
        objects = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
        
        if objects:
            s3_client.delete_objects(
                Bucket=chunks_bucket,
                Delete={'Objects': objects}
            )
            print(f"✅ Cleaned up {len(objects)} test files")
        
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")

if __name__ == "__main__":
    test_kg_with_existing_document()
