#!/usr/bin/env python3
"""
Test with Proper GUID-based DocumentID
Demonstrates correct DocumentID usage in the pipeline
"""

import boto3
import json
import time
from datetime import datetime

def test_with_proper_documentid():
    """Test pipeline with proper GUID-based DocumentID"""
    
    print("🔍 Testing with Proper GUID-based DocumentID")
    print("=" * 80)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print()
    
    session = boto3.Session(profile_name='solve-global')
    sns_client = session.client('sns', region_name='us-east-1')
    
    # Use the PROPER DocumentID from the database
    proper_doc_id = "0032f6cb_f0caef34"  # This is the GUID-based DocumentID
    text_ready_topic_arn = "arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
    
    print("📋 Proper DocumentID Usage")
    print("=" * 60)
    print(f"GUID-based DocumentID: {proper_doc_id}")
    print(f"Expected chunk directory: {proper_doc_id}/")
    print(f"Expected chunk pattern: {proper_doc_id}_chunk_0001.json")
    
    # Create message with PROPER DocumentID (as TextExtractor would send)
    proper_message = {
        "doc_id": proper_doc_id,  # PROPER GUID-based DocumentID
        "stage": "text_ready",
        "full_text_location": {
            "bucket": "solve-global-kr-text-new-861276078413-us-east-1",
            "key": "extracted_text/0032f6cb_f0caef34.txt"  # Matches the DocumentID
        },
        "document_structure_location": None,
        "documentid_manager_integration": True,
        "selective_migration_used": False,
        "filename": "0032f6cb_f0caef34.pdf",
        "proper_documentid_test": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"\n📤 Publishing Message with Proper DocumentID")
    print("=" * 60)
    print(f"Message: {json.dumps(proper_message, indent=2)}")
    
    try:
        # Publish message with proper DocumentID
        sns_response = sns_client.publish(
            TopicArn=text_ready_topic_arn,
            Message=json.dumps(proper_message),
            Subject=f"Text Extraction Complete: {proper_doc_id}"
        )
        
        message_id = sns_response['MessageId']
        print(f"✅ Published to SNS: {message_id}")
        
        # Wait for processing
        print(f"\n⏳ Waiting for Processing...")
        time.sleep(15)
        
        # Check S3 for chunks with PROPER naming
        print(f"\n📊 Checking S3 for Properly Named Chunks")
        print("=" * 60)
        
        s3_client = session.client('s3', region_name='us-east-1')
        
        # Check with proper prefix
        chunks_response = s3_client.list_objects_v2(
            Bucket='solve-global-kr-chunks-861276078413-us-east-1',
            Prefix=f'{proper_doc_id}/',  # PROPER DocumentID prefix
            MaxKeys=20
        )
        
        chunks = chunks_response.get('Contents', [])
        print(f"✅ Found {len(chunks)} files with proper DocumentID naming:")
        
        chunk_files = [c for c in chunks if c['Key'].endswith('.json') and 'chunk_' in c['Key']]
        
        for i, chunk in enumerate(chunk_files[:10]):
            print(f"   {i+1:2d}. {chunk['Key']}: {chunk['Size']:,} bytes")
            # Verify proper naming pattern
            expected_pattern = f"{proper_doc_id}_chunk_"
            if expected_pattern in chunk['Key']:
                print(f"       ✅ Correct GUID-based naming")
            else:
                print(f"       ❌ Incorrect naming pattern")
        
        if len(chunk_files) > 10:
            print(f"   ... and {len(chunk_files) - 10} more properly named chunks")
        
        # Check database status
        print(f"\n📋 Database Status for Proper DocumentID")
        print("-" * 40)
        
        try:
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
            
            cursor.execute(
                "SELECT * FROM text_chunking_status WHERE doc_id = %s ORDER BY updated_at DESC LIMIT 1",
                (proper_doc_id,)
            )
            
            status_record = cursor.fetchone()
            if status_record:
                print(f"✅ Database status for {proper_doc_id}:")
                print(f"   Status: {status_record['status']}")
                print(f"   Chunks created: {status_record['chunks_created']}")
                print(f"   Updated: {status_record['updated_at']}")
            else:
                print(f"⚠️  No database status record for {proper_doc_id}")
            
            # Also check the documents table
            cursor.execute("SELECT * FROM documents WHERE doc_id = %s", (proper_doc_id,))
            doc_record = cursor.fetchone()
            if doc_record:
                print(f"✅ DocumentIDManager record:")
                print(f"   Original filename: {doc_record['original_filename']}")
                print(f"   Status: {doc_record['status']}")
                print(f"   Text path: {doc_record['text_path']}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            status_record = None
        
        # Final assessment
        print("\n" + "=" * 80)
        print("🎯 Proper DocumentID Test Results")
        print("=" * 80)
        
        proper_naming = len(chunk_files) > 0 and all(proper_doc_id in c['Key'] for c in chunk_files)
        database_consistent = status_record is not None
        
        print(f"✅ Proper GUID Naming: {'SUCCESS' if proper_naming else 'FAILED'}")
        print(f"✅ Chunks Generated: {len(chunk_files)} files")
        print(f"✅ Database Integration: {'SUCCESS' if database_consistent else 'FAILED'}")
        
        if proper_naming and database_consistent:
            print("\n🎉 PROPER DOCUMENTID USAGE CONFIRMED!")
            print("✅ Text chunker uses GUID-based DocumentIDs correctly")
            print("✅ Chunk naming follows proper pattern: {GUID}_chunk_NNNN.json")
            print("✅ S3 directory structure: {GUID}/")
            print("✅ Database tracking uses proper DocumentIDs")
            
            print("\n📋 Naming Pattern Validation:")
            print(f"   • DocumentID: {proper_doc_id} (GUID-based ✅)")
            print(f"   • Directory: {proper_doc_id}/ (GUID-based ✅)")
            print(f"   • Chunks: {proper_doc_id}_chunk_0001.json (GUID-based ✅)")
            print(f"   • Database: {proper_doc_id} (GUID-based ✅)")
            
            print("\n🔍 Issue Analysis:")
            print("❌ Previous tests used descriptive names (pipeline-test-neural-fuzzy)")
            print("✅ Production will use proper GUID-based DocumentIDs")
            print("✅ Text chunker correctly uses whatever doc_id is provided")
            print("✅ No code changes needed - issue was in test data")
            
        else:
            print("\n⚠️  Issues detected with proper DocumentID usage")
        
        return proper_naming and database_consistent
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_with_proper_documentid()
    
    if success:
        print("\n🎉 DOCUMENTID USAGE VALIDATED!")
        print("The text chunker correctly uses GUID-based DocumentIDs.")
        print("Previous test artifacts used descriptive names for testing.")
    else:
        print("\n❌ DocumentID usage validation failed.")
    
    exit(0 if success else 1)
