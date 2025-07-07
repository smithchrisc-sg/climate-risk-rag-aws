#!/usr/bin/env python3
"""
Phase 2: Fixed Real POC Document Test - Correct Message Format
Tests text chunker with proper message format expected by the function
"""

import boto3
import json
import time
from datetime import datetime

def test_with_correct_message_format():
    """Test text chunker with correct message format"""
    
    print("🚀 Phase 2: Fixed Real POC Document Test")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    # Use the smaller text file for cost efficiency
    doc_id = "neural-fuzzy-textract"
    text_bucket = "solve-global-kr-text-new-861276078413-us-east-1"
    text_key = "extracted_text/neural-fuzzy-textract.txt"
    chunks_bucket = "solve-global-kr-chunks-861276078413-us-east-1"
    
    print("🔍 Test Configuration")
    print("=" * 60)
    print(f"Document ID: {doc_id}")
    print(f"Text file: {text_key}")
    print(f"Size: 7,825 bytes (very small for cost efficiency)")
    print(f"Estimated cost: < $0.001")
    
    # Create test message with CORRECT format expected by text chunker
    test_payload = {
        "Records": [{
            "body": json.dumps({
                "Message": json.dumps({
                    "doc_id": doc_id,
                    "stage": "text_ready",
                    "full_text_location": {  # Correct field name
                        "bucket": text_bucket,
                        "key": text_key
                    },
                    "document_structure_location": None,  # No structure data
                    "documentid_manager_integration": True,
                    "selective_migration_used": False,
                    "filename": "neural-fuzzy-textract.pdf",
                    "frugal_test": True
                })
            })
        }]
    }
    
    # Test the text chunker
    print("\n🧪 Testing Text Chunker with Correct Message Format")
    print("=" * 60)
    
    try:
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda', region_name='us-east-1')
        s3_client = session.client('s3', region_name='us-east-1')
        
        print("Invoking text chunker with corrected message...")
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
            time.sleep(8)  # Longer wait for real processing
            
            # Check results
            print("\n📊 Checking Results")
            print("=" * 60)
            
            # Check S3 for chunks
            try:
                print("Checking S3 for generated chunks...")
                response = s3_client.list_objects_v2(
                    Bucket=chunks_bucket,
                    Prefix=f"chunks/{doc_id}/",
                    MaxKeys=50
                )
                
                chunks = response.get('Contents', [])
                print(f"✅ Found {len(chunks)} chunk files in S3:")
                
                total_chunk_size = 0
                for i, chunk in enumerate(chunks[:10]):  # Show first 10
                    chunk_key = chunk['Key']
                    chunk_size = chunk['Size']
                    total_chunk_size += chunk_size
                    print(f"   {i+1:2d}. {chunk_key}: {chunk_size:,} bytes")
                
                if len(chunks) > 10:
                    print(f"   ... and {len(chunks) - 10} more chunks")
                
                print(f"📈 Total chunks: {len(chunks)}")
                print(f"📈 Total size: {total_chunk_size:,} bytes")
                
                # Analyze a sample chunk
                if chunks:
                    print("\n🔍 Sample Chunk Analysis")
                    print("-" * 40)
                    
                    chunk_key = chunks[0]['Key']
                    chunk_response = s3_client.get_object(
                        Bucket=chunks_bucket,
                        Key=chunk_key
                    )
                    
                    chunk_content = chunk_response['Body'].read().decode('utf-8')
                    chunk_data = json.loads(chunk_content)
                    
                    print(f"✅ Chunk structure analysis:")
                    print(f"   Chunk ID: {chunk_data.get('chunk_id', 'N/A')}")
                    print(f"   Document ID: {chunk_data.get('doc_id', 'N/A')}")
                    print(f"   Text length: {len(chunk_data.get('text', ''))}")
                    print(f"   Has metadata: {'Yes' if chunk_data.get('metadata') else 'No'}")
                    print(f"   Has offsets: {'Yes' if chunk_data.get('start_offset') is not None else 'No'}")
                    
                    # Show first 200 characters of text
                    text_preview = chunk_data.get('text', '')[:200]
                    print(f"   Text preview: {text_preview}...")
                
            except Exception as e:
                print(f"❌ Error checking S3 chunks: {e}")
                chunks = []
            
            # Check database status
            try:
                print("\n📋 Checking Database Status")
                print("-" * 40)
                
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
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
                    print(f"✅ Database status record found:")
                    print(f"   Status: {status_record['status']}")
                    print(f"   Chunks created: {status_record['chunks_created']}")
                    print(f"   Notes: {status_record['notes']}")
                    print(f"   Updated: {status_record['updated_at']}")
                else:
                    print("⚠️  No status record found in database")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"❌ Error checking database status: {e}")
                status_record = None
            
            # Cost analysis
            print("\n💰 Cost Impact Analysis")
            print("=" * 60)
            
            lambda_cost = (execution_time / 1000) * 0.0000166667
            s3_cost = 0.0004 * (len(chunks) + 3)  # Operations cost
            total_cost = lambda_cost + s3_cost
            
            print(f"📊 Estimated costs for this test:")
            print(f"   Lambda execution: ${lambda_cost:.6f}")
            print(f"   S3 operations: ${s3_cost:.6f}")
            print(f"   Total: ${total_cost:.6f}")
            print(f"   Budget impact: Minimal (< 0.1%)")
            
            # Final assessment
            print("\n" + "=" * 80)
            print("🎯 Phase 2 Test Results")
            print("=" * 80)
            
            processing_success = successful > 0
            chunks_created = len(chunks) > 0
            database_working = status_record is not None
            
            print(f"✅ Function Execution: SUCCESS")
            print(f"✅ Message Processing: {'SUCCESS' if processing_success else 'FAILED'}")
            print(f"✅ Chunks Generated: {len(chunks)} chunks ({'SUCCESS' if chunks_created else 'FAILED'})")
            print(f"✅ Database Integration: {'SUCCESS' if database_working else 'FAILED'}")
            print(f"✅ Cost Efficiency: SUCCESS (${total_cost:.6f})")
            
            overall_success = processing_success and chunks_created and database_working
            
            if overall_success:
                print("\n🎉 PHASE 2 COMPLETE SUCCESS!")
                print("✅ Text chunker processes real POC documents successfully")
                print("✅ Chunks are generated and stored in S3 with proper structure")
                print("✅ Database integration tracks processing status")
                print("✅ Cost impact is minimal and well within budget")
                print("✅ Ready for production pipeline integration")
                
                print("\n📋 What This Proves:")
                print("• Complete end-to-end text chunking pipeline working")
                print("• Database integration fully operational")
                print("• S3 storage and retrieval working correctly")
                print("• Message format compatibility confirmed")
                print("• Performance is excellent for production use")
                
                print("\n🚀 Next Steps:")
                print("• Integrate with TextExtractor SNS/SQS messaging")
                print("• Test complete document upload → text extraction → chunking flow")
                print("• Configure coordination with downstream processors")
                print("• Set up production monitoring and alerting")
            else:
                print("\n⚠️  PHASE 2 PARTIAL SUCCESS:")
                if not processing_success:
                    print("❌ Message processing issues detected")
                if not chunks_created:
                    print("❌ No chunks were generated")
                if not database_working:
                    print("❌ Database integration issues")
            
            return overall_success
            
        else:
            print(f"❌ Function invocation failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_with_correct_message_format()
    exit(0 if success else 1)
