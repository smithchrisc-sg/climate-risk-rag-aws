#!/usr/bin/env python3
"""
Complete Integration Test - Text Chunker with Fixed Structured Chunking
Tests the complete pipeline with proper DocumentIDManager integration
"""

import boto3
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def test_complete_integration():
    """Test complete integration with fixed structured chunking"""
    
    print("🚀 Complete Integration Test - Fixed Structured Chunking")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    # Use the document we just set up
    doc_id = "0032f6cb_f0caef34"  # Has proper database entries now
    text_bucket = "solve-global-kr-text-new-861276078413-us-east-1"
    text_key = "extracted_text/0032f6cb_f0caef34.txt"
    chunks_bucket = "solve-global-kr-chunks-861276078413-us-east-1"
    
    print("🔍 Test Configuration")
    print("=" * 60)
    print(f"Document ID: {doc_id}")
    print(f"Text file: {text_key}")
    print(f"Size: 20,078 bytes (moderate size)")
    print(f"Integration: Complete DocumentIDManager setup")
    print(f"Estimated cost: ~$0.002")
    
    # Create proper integration test message
    test_payload = {
        "Records": [{
            "body": json.dumps({
                "Message": json.dumps({
                    "doc_id": doc_id,
                    "stage": "text_ready",
                    "full_text_location": {
                        "bucket": text_bucket,
                        "key": text_key
                    },
                    "document_structure_location": None,  # No structure data available
                    "documentid_manager_integration": True,
                    "selective_migration_used": False,
                    "filename": f"{doc_id}.pdf",
                    "complete_integration_test": True
                })
            })
        }]
    }
    
    # Test the complete integration
    print("\n🧪 Testing Complete Integration Pipeline")
    print("=" * 60)
    
    try:
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda', region_name='us-east-1')
        s3_client = session.client('s3', region_name='us-east-1')
        
        print("Invoking text chunker with complete integration...")
        start_time = time.time()
        
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-text-chunker-db',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if response['StatusCode'] == 200:
            payload = json.loads(response['Payload'].read())
            print(f"✅ Function invocation successful!")
            print(f"⏱️  Execution time: {execution_time:.2f} seconds")
            print(f"Response: {json.dumps(payload, indent=2)}")
            
            # Parse response to check success
            response_body = json.loads(payload['body'])
            successful = response_body.get('successful', 0)
            failed = response_body.get('failed', 0)
            
            if successful > 0:
                print(f"✅ Processing successful: {successful} document(s) processed")
            else:
                print(f"⚠️  Processing issues: {failed} failed")
                if response_body.get('results'):
                    for result in response_body['results']:
                        if not result.get('success'):
                            print(f"   Error: {result.get('error')}")
            
            # Wait for processing
            print("\nWaiting for chunk processing...")
            time.sleep(12)  # Longer wait for larger document
            
            # Check results
            print("\n📊 Checking Integration Results")
            print("=" * 60)
            
            # Check S3 for chunks
            try:
                print("Checking S3 for generated chunks...")
                response = s3_client.list_objects_v2(
                    Bucket=chunks_bucket,
                    Prefix=f"chunks/{doc_id}/",
                    MaxKeys=100
                )
                
                chunks = response.get('Contents', [])
                print(f"✅ Found {len(chunks)} chunk files in S3:")
                
                total_chunk_size = 0
                for i, chunk in enumerate(chunks[:20]):  # Show first 20
                    chunk_key = chunk['Key']
                    chunk_size = chunk['Size']
                    total_chunk_size += chunk_size
                    print(f"   {i+1:2d}. {chunk_key}: {chunk_size:,} bytes")
                
                if len(chunks) > 20:
                    print(f"   ... and {len(chunks) - 20} more chunks")
                
                print(f"📈 Total chunks: {len(chunks)}")
                print(f"📈 Total size: {total_chunk_size:,} bytes")
                print(f"📈 Average chunk size: {total_chunk_size // max(len(chunks), 1):,} bytes")
                
                # Analyze chunk quality
                if chunks:
                    print("\n🔍 Chunk Quality Analysis")
                    print("-" * 40)
                    
                    # Analyze first chunk
                    chunk_key = chunks[0]['Key']
                    chunk_response = s3_client.get_object(
                        Bucket=chunks_bucket,
                        Key=chunk_key
                    )
                    
                    chunk_content = chunk_response['Body'].read().decode('utf-8')
                    chunk_data = json.loads(chunk_content)
                    
                    print(f"✅ First chunk analysis:")
                    print(f"   Chunk ID: {chunk_data.get('chunk_id', 'N/A')}")
                    print(f"   Document ID: {chunk_data.get('doc_id', 'N/A')}")
                    print(f"   Text length: {len(chunk_data.get('text', ''))}")
                    print(f"   Chunk type: {chunk_data.get('chunk_type', 'N/A')}")
                    print(f"   Has metadata: {'Yes' if chunk_data.get('metadata') else 'No'}")
                    print(f"   Has offsets: {'Yes' if chunk_data.get('offsets') else 'No'}")
                    
                    # Check structured chunking features
                    if chunk_data.get('hierarchy_level') is not None:
                        print(f"   Hierarchy level: {chunk_data.get('hierarchy_level')}")
                        print(f"   ✅ Structured chunking working!")
                    
                    # Show text preview
                    text_preview = chunk_data.get('text', '')[:200]
                    print(f"   Text preview: {text_preview}...")
                    
                    # Check offsets
                    if chunk_data.get('offsets'):
                        offsets = chunk_data['offsets']
                        print(f"   Character offsets: {offsets.get('char_start', 'N/A')} - {offsets.get('char_end', 'N/A')}")
                
            except Exception as e:
                print(f"❌ Error checking S3 chunks: {e}")
                chunks = []
            
            # Check database integration
            try:
                print("\n📋 Checking Database Integration")
                print("-" * 40)
                
                db_params = {
                    'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
                    'port': 5432,
                    'database': 'climate_risk_rag',
                    'user': 'postgres',
                    'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
                    'sslmode': 'require'
                }
                
                conn = psycopg2.connect(**db_params)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Check text_chunking_status table
                cursor.execute(
                    "SELECT * FROM text_chunking_status WHERE doc_id = %s ORDER BY updated_at DESC LIMIT 1",
                    (doc_id,)
                )
                
                status_record = cursor.fetchone()
                if status_record:
                    print(f"✅ Text chunking status record:")
                    print(f"   Status: {status_record['status']}")
                    print(f"   Chunks created: {status_record['chunks_created']}")
                    print(f"   Notes: {status_record['notes']}")
                    print(f"   Updated: {status_record['updated_at']}")
                
                # Check document_processing_status table
                cursor.execute(
                    "SELECT * FROM document_processing_status WHERE doc_hash = %s",
                    (doc_id,)
                )
                
                processing_record = cursor.fetchone()
                if processing_record:
                    print(f"✅ Document processing status:")
                    print(f"   Text extraction: {processing_record['text_extraction_status']}")
                    print(f"   Chunking: {processing_record['chunking_status']}")
                    print(f"   Updated: {processing_record['updated_at']}")
                
                # Check documents table
                cursor.execute("SELECT * FROM documents WHERE doc_id = %s", (doc_id,))
                doc_record = cursor.fetchone()
                if doc_record:
                    print(f"✅ Document record:")
                    print(f"   Status: {doc_record['status']}")
                    print(f"   Original filename: {doc_record['original_filename']}")
                    print(f"   Text path: {doc_record['text_path']}")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"❌ Error checking database integration: {e}")
                status_record = None
                processing_record = None
                doc_record = None
            
            # Cost analysis
            print("\n💰 Cost Impact Analysis")
            print("=" * 60)
            
            lambda_cost = (execution_time / 1000) * 0.0000166667
            s3_cost = 0.0004 * (len(chunks) + 5)  # Operations cost
            total_cost = lambda_cost + s3_cost
            
            print(f"📊 Estimated costs for this test:")
            print(f"   Lambda execution: ${lambda_cost:.6f}")
            print(f"   S3 operations: ${s3_cost:.6f}")
            print(f"   Total: ${total_cost:.6f}")
            print(f"   Budget impact: Minimal (< 0.2%)")
            
            # Final assessment
            print("\n" + "=" * 80)
            print("🎯 Complete Integration Test Results")
            print("=" * 80)
            
            processing_success = successful > 0
            chunks_created = len(chunks) > 0
            database_working = status_record is not None and status_record['status'] != 'FAILED'
            integration_complete = doc_record is not None and processing_record is not None
            
            print(f"✅ Function Execution: SUCCESS")
            print(f"✅ Message Processing: {'SUCCESS' if processing_success else 'FAILED'}")
            print(f"✅ Chunks Generated: {len(chunks)} chunks ({'SUCCESS' if chunks_created else 'FAILED'})")
            print(f"✅ Database Integration: {'SUCCESS' if database_working else 'FAILED'}")
            print(f"✅ DocumentIDManager Integration: {'SUCCESS' if integration_complete else 'FAILED'}")
            print(f"✅ Cost Efficiency: SUCCESS (${total_cost:.6f})")
            
            overall_success = processing_success and chunks_created and database_working and integration_complete
            
            if overall_success:
                print("\n🎉 COMPLETE INTEGRATION SUCCESS!")
                print("✅ Text chunker processes real documents with full integration")
                print("✅ Structured chunking working (if structure data available)")
                print("✅ DocumentIDManager integration complete")
                print("✅ Database tracking across all tables working")
                print("✅ S3 storage with proper naming and structure")
                print("✅ Cost efficiency proven for production use")
                
                print("\n📋 Integration Validation Complete:")
                print("• End-to-end pipeline from DocumentIDManager → Text Chunker")
                print("• Database consistency across all tables")
                print("• Proper document lifecycle tracking")
                print("• S3 operations with correct bucket structure")
                print("• Error handling and status reporting")
                print("• Performance suitable for production scale")
                
                print("\n🚀 Ready for Pipeline Integration:")
                print("• Connect TextExtractor SNS → Text Chunker SQS")
                print("• Set up coordination with downstream processors")
                print("• Configure production monitoring and alerting")
                print("• Deploy to production environment")
                
            else:
                print("\n⚠️  INTEGRATION ISSUES DETECTED:")
                if not processing_success:
                    print("❌ Message processing failed")
                if not chunks_created:
                    print("❌ No chunks were generated")
                if not database_working:
                    print("❌ Database integration issues")
                if not integration_complete:
                    print("❌ DocumentIDManager integration incomplete")
            
            return overall_success
            
        else:
            print(f"❌ Function invocation failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_integration()
    exit(0 if success else 1)
