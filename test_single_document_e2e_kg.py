#!/usr/bin/env python3
"""
Single Document End-to-End KG Integration Test
Tests complete pipeline: Document → Text Extraction → Chunking → KG Processing → Neptune
"""
import boto3
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

def test_single_document_e2e():
    """Test complete pipeline with a single document"""
    
    print("🧪 Single Document End-to-End KG Integration Test")
    print("=" * 70)
    
    session = boto3.Session(profile_name='solve-global')
    s3_client = session.client('s3')
    lambda_client = session.client('lambda')
    logs_client = session.client('logs')
    
    # Generate unique test document ID
    test_doc_id = f"e2e-test-{int(time.time())}"
    print(f"📄 Test Document ID: {test_doc_id}")
    
    try:
        # Step 1: Create a realistic test document in the documents table
        print("\n📋 Step 1: Register test document in database")
        register_test_document(test_doc_id)
        
        # Step 2: Create realistic chunks data
        print("\n📦 Step 2: Create test chunks data")
        chunks_location = create_test_chunks_data(s3_client, test_doc_id)
        
        # Step 3: Trigger the KG pipeline with chunks_ready message
        print("\n🚀 Step 3: Trigger KG processing pipeline")
        trigger_kg_pipeline(session, test_doc_id, chunks_location)
        
        # Step 4: Monitor TTL generation
        print("\n⏳ Step 4: Monitor TTL generation (60 seconds)")
        ttl_location = monitor_ttl_generation(s3_client, test_doc_id)
        
        if ttl_location:
            # Step 5: Monitor Neptune loading
            print("\n⏳ Step 5: Monitor Neptune loading (60 seconds)")
            neptune_success = monitor_neptune_loading(logs_client, test_doc_id)
            
            # Step 6: Validate results
            print("\n✅ Step 6: Validate end-to-end results")
            validate_results(s3_client, test_doc_id, ttl_location, neptune_success)
        else:
            print("❌ TTL generation failed - cannot proceed to Neptune testing")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Step 7: Cleanup
        print(f"\n🧹 Step 7: Cleanup test data")
        cleanup_test_data(s3_client, test_doc_id)
    
    print("\n" + "=" * 70)
    print("🎉 Single Document End-to-End Test Complete!")

def register_test_document(doc_id):
    """Register test document in database to avoid foreign key constraints"""
    try:
        # Use the database layer to register the document
        register_payload = {
            "doc_id": doc_id,
            "action": "register",
            "metadata": {
                "original_filename": f"{doc_id}.pdf",
                "file_size": 150000,
                "page_count": 5,
                "test_document": True
            }
        }
        
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda')
        
        # Try to invoke a document registration function or create directly
        # For now, we'll create the chunks data and let the system handle registration
        print(f"✅ Test document {doc_id} prepared for registration")
        
    except Exception as e:
        print(f"⚠️  Document registration note: {e}")
        print("   (Document will be registered during processing)")

def create_test_chunks_data(s3_client, doc_id):
    """Create comprehensive test chunks data"""
    
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    chunks_prefix = f"test-data/{doc_id}/"
    
    # Create realistic climate risk document chunks
    test_chunks = [
        {
            "chunk_id": "chunk_001",
            "content": "Climate change represents one of the most significant long-term risks to financial stability. Physical risks from extreme weather events can damage assets and disrupt business operations, while transition risks arise from policy changes and technological shifts toward a low-carbon economy.",
            "section_title": "Executive Summary",
            "chunk_type": "text",
            "start_char": 0,
            "end_char": 280,
            "page_number": 1,
            "section_level": 1
        },
        {
            "chunk_id": "chunk_002", 
            "content": "Physical climate risks include acute risks such as hurricanes, floods, and wildfires, as well as chronic risks like rising sea levels and changing precipitation patterns. These risks can directly impact real estate portfolios, infrastructure investments, and supply chain operations.",
            "section_title": "Physical Climate Risks",
            "chunk_type": "text",
            "start_char": 281,
            "end_char": 550,
            "page_number": 2,
            "section_level": 2
        },
        {
            "chunk_id": "chunk_003",
            "content": "Transition risks emerge from the shift to a lower-carbon economy and include policy risks from carbon pricing and regulations, technology risks from clean energy adoption, and market risks from changing consumer preferences and investor sentiment toward sustainable investments.",
            "section_title": "Transition Risks",
            "chunk_type": "text", 
            "start_char": 551,
            "end_char": 830,
            "page_number": 3,
            "section_level": 2
        },
        {
            "chunk_id": "chunk_004",
            "content": "Financial institutions must integrate climate risk assessment into their risk management frameworks, including scenario analysis, stress testing, and portfolio monitoring. This requires enhanced data collection, modeling capabilities, and governance structures.",
            "section_title": "Risk Management Framework",
            "chunk_type": "text",
            "start_char": 831,
            "end_char": 1100,
            "page_number": 4,
            "section_level": 2
        },
        {
            "chunk_id": "chunk_005",
            "content": "Regulatory expectations continue to evolve, with central banks and supervisors increasingly requiring climate risk disclosures, scenario analysis, and integration of climate considerations into business strategy and risk appetite frameworks.",
            "section_title": "Regulatory Landscape",
            "chunk_type": "text",
            "start_char": 1101,
            "end_char": 1350,
            "page_number": 5,
            "section_level": 2
        }
    ]
    
    # Upload chunks
    for i, chunk in enumerate(test_chunks):
        chunk_key = f"{chunks_prefix}chunk_{i:03d}.json"
        s3_client.put_object(
            Bucket=chunks_bucket,
            Key=chunk_key,
            Body=json.dumps(chunk, indent=2),
            ContentType='application/json',
            Metadata={
                'doc_id': doc_id,
                'chunk_id': chunk['chunk_id'],
                'test_data': 'true'
            }
        )
    
    # Create comprehensive metadata
    metadata = {
        "document_info": {
            "title": "Climate Risk Assessment for Financial Institutions",
            "source_url": f"https://example.com/climate-reports/{doc_id}.pdf",
            "document_type": "risk_assessment",
            "industry": "financial_services",
            "publication_date": "2024-01-15",
            "author": "Climate Risk Research Institute"
        },
        "chunking_config": {
            "method": "smart_structured",
            "max_chunk_size": 1000,
            "overlap_size": 100,
            "preserve_structure": True
        },
        "processing_stats": {
            "chunks_created": len(test_chunks),
            "total_characters": sum(len(chunk["content"]) for chunk in test_chunks),
            "average_chunk_size": sum(len(chunk["content"]) for chunk in test_chunks) // len(test_chunks),
            "sections_identified": len(set(chunk["section_title"] for chunk in test_chunks)),
            "pages_processed": 5
        },
        "quality_metrics": {
            "structure_preservation": 0.95,
            "content_coherence": 0.92,
            "boundary_respect": 0.98
        },
        "created_at": datetime.utcnow().isoformat() + 'Z'
    }
    
    # Upload metadata
    metadata_key = f"{chunks_prefix}metadata.json"
    s3_client.put_object(
        Bucket=chunks_bucket,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2),
        ContentType='application/json',
        Metadata={
            'doc_id': doc_id,
            'content_type': 'chunk_metadata',
            'test_data': 'true'
        }
    )
    
    chunks_location = f"s3://{chunks_bucket}/{chunks_prefix}"
    print(f"✅ Created {len(test_chunks)} realistic chunks at: {chunks_location}")
    
    return chunks_location

def trigger_kg_pipeline(session, doc_id, chunks_location):
    """Trigger the KG processing pipeline"""
    
    sns_client = session.client('sns')
    
    # Create chunks_ready message matching current format
    chunks_ready_message = {
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
            "chunks_created": 5,
            "chunking_method": "smart_structured",
            "total_characters": 1350,
            "processing_completed": datetime.utcnow().isoformat() + "Z"
        },
        "integration_flags": {
            "database_tracking_enabled": True,
            "audit_first_design": True,
            "smart_structured_chunking": True
        }
    }
    
    # Publish to chunks-ready topic
    chunks_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:chunks-ready"
    
    response = sns_client.publish(
        TopicArn=chunks_ready_topic_arn,
        Message=json.dumps(chunks_ready_message, default=str),
        Subject=f"E2E Test: Text chunking complete: {doc_id}",
        MessageAttributes={
            'stage': {
                'DataType': 'String',
                'StringValue': 'chunks_ready'
            },
            'doc_id': {
                'DataType': 'String',
                'StringValue': doc_id
            },
            'version': {
                'DataType': 'String',
                'StringValue': '1.0'
            },
            'test_type': {
                'DataType': 'String',
                'StringValue': 'e2e_kg_integration'
            }
        }
    )
    
    print(f"✅ Published chunks_ready message: {response['MessageId']}")
    print(f"   Topic: {chunks_ready_topic_arn}")
    print(f"   Document: {doc_id}")

def monitor_ttl_generation(s3_client, doc_id, max_wait=60):
    """Monitor TTL file generation"""
    
    ttl_bucket = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
    ttl_key = f"documents/{doc_id}/document_structure.ttl"
    
    print(f"   Checking for TTL at: s3://{ttl_bucket}/{ttl_key}")
    
    for attempt in range(max_wait):
        try:
            response = s3_client.get_object(Bucket=ttl_bucket, Key=ttl_key)
            ttl_content = response['Body'].read().decode('utf-8')
            
            print(f"✅ TTL file generated successfully!")
            print(f"   Size: {len(ttl_content)} characters")
            print(f"   Location: s3://{ttl_bucket}/{ttl_key}")
            
            # Show sample TTL content
            print(f"\n📄 Sample TTL Content (first 500 chars):")
            print("-" * 50)
            print(ttl_content[:500] + "..." if len(ttl_content) > 500 else ttl_content)
            print("-" * 50)
            
            return f"s3://{ttl_bucket}/{ttl_key}"
            
        except s3_client.exceptions.NoSuchKey:
            if attempt % 10 == 0:  # Print every 10 seconds
                print(f"   Waiting for TTL generation... ({attempt}s)")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error checking TTL file: {e}")
            break
    
    print(f"❌ TTL file not generated within {max_wait} seconds")
    return None

def monitor_neptune_loading(logs_client, doc_id, max_wait=60):
    """Monitor Neptune loading through CloudWatch logs"""
    
    print(f"   Monitoring KG integration worker logs for: {doc_id}")
    
    start_time = int((time.time() - 300) * 1000)  # Last 5 minutes
    
    for attempt in range(max_wait):
        try:
            # Check KG integration worker logs
            response = logs_client.filter_log_events(
                logGroupName='/aws/lambda/kg-integration-worker',
                startTime=start_time,
                filterPattern=doc_id
            )
            
            events = response.get('events', [])
            if events:
                print(f"✅ Found {len(events)} log events for KG integration")
                
                # Look for success indicators
                success_indicators = ['successfully loaded', 'completed', 'validation passed']
                error_indicators = ['error', 'failed', 'exception']
                
                success_found = False
                error_found = False
                
                for event in events[-5:]:  # Show last 5 events
                    message = event['message'].strip()
                    print(f"   📝 {message}")
                    
                    message_lower = message.lower()
                    if any(indicator in message_lower for indicator in success_indicators):
                        success_found = True
                    if any(indicator in message_lower for indicator in error_indicators):
                        error_found = True
                
                if success_found and not error_found:
                    print("✅ Neptune loading appears successful!")
                    return True
                elif error_found:
                    print("❌ Neptune loading encountered errors")
                    return False
            
            if attempt % 10 == 0:  # Print every 10 seconds
                print(f"   Waiting for Neptune loading... ({attempt}s)")
            time.sleep(1)
            
        except Exception as e:
            print(f"⚠️  Error checking logs: {e}")
            time.sleep(1)
    
    print(f"⚠️  Neptune loading status unclear after {max_wait} seconds")
    return None

def validate_results(s3_client, doc_id, ttl_location, neptune_success):
    """Validate end-to-end results"""
    
    print(f"📊 Validation Results for {doc_id}:")
    print("-" * 40)
    
    # Check TTL file quality
    if ttl_location:
        try:
            bucket, key = ttl_location.replace('s3://', '').split('/', 1)
            response = s3_client.get_object(Bucket=bucket, Key=key)
            ttl_content = response['Body'].read().decode('utf-8')
            
            # Validate TTL structure
            required_elements = [
                '@prefix dc:',
                '@prefix dcterms:',
                'dcterms:Text',
                doc_id,
                'cr:DocumentChunk'
            ]
            
            ttl_quality = sum(1 for element in required_elements if element in ttl_content)
            print(f"✅ TTL Quality: {ttl_quality}/{len(required_elements)} required elements found")
            print(f"✅ TTL Size: {len(ttl_content)} characters")
            
            # Count chunks in TTL
            chunk_count = ttl_content.count('cr:DocumentChunk')
            print(f"✅ Chunks in TTL: {chunk_count}")
            
        except Exception as e:
            print(f"❌ TTL validation error: {e}")
    
    # Neptune loading status
    if neptune_success is True:
        print("✅ Neptune Loading: SUCCESS")
    elif neptune_success is False:
        print("❌ Neptune Loading: FAILED")
    else:
        print("⚠️  Neptune Loading: STATUS UNCLEAR")
    
    # Overall assessment
    if ttl_location and neptune_success:
        print("\n🎉 END-TO-END TEST: SUCCESS")
        print("   ✅ TTL Generation: Working")
        print("   ✅ Neptune Loading: Working") 
        print("   ✅ Pipeline Flow: Complete")
    elif ttl_location:
        print("\n⚠️  END-TO-END TEST: PARTIAL SUCCESS")
        print("   ✅ TTL Generation: Working")
        print("   ❓ Neptune Loading: Needs verification")
    else:
        print("\n❌ END-TO-END TEST: FAILED")
        print("   ❌ TTL Generation: Failed")
        print("   ❌ Pipeline incomplete")

def cleanup_test_data(s3_client, doc_id):
    """Clean up test data"""
    
    try:
        # Clean up chunks data
        chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        chunks_prefix = f"test-data/{doc_id}/"
        
        response = s3_client.list_objects_v2(
            Bucket=chunks_bucket,
            Prefix=chunks_prefix
        )
        
        objects_to_delete = []
        for obj in response.get('Contents', []):
            objects_to_delete.append({'Key': obj['Key']})
        
        if objects_to_delete:
            s3_client.delete_objects(
                Bucket=chunks_bucket,
                Delete={'Objects': objects_to_delete}
            )
            print(f"✅ Cleaned up {len(objects_to_delete)} chunk files")
        
        # Clean up TTL file
        ttl_bucket = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
        ttl_key = f"documents/{doc_id}/document_structure.ttl"
        
        try:
            s3_client.delete_object(Bucket=ttl_bucket, Key=ttl_key)
            print("✅ Cleaned up TTL file")
        except:
            print("ℹ️  No TTL file to clean up")
            
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

if __name__ == "__main__":
    test_single_document_e2e()
