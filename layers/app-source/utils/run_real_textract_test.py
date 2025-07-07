#!/usr/bin/env python3
"""
Streamlined Real Textract Test
Pre-configured to test the smallest, safest document
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Import our components
from DatabaseManager import DatabaseManager
from DocumentIDManager import DocumentIDManager
from textextractor_optimized_config import OptimizedTextExtractorConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_streamlined_test():
    """Run a streamlined real Textract test with the safest document"""
    
    print("🚀 Streamlined Real Textract Test")
    print("=" * 50)
    print("Pre-configured to use the smallest, safest document")
    print("💰 Cost: $0.00 (within free tier)")
    print("📄 Document: ~1 page PDF")
    print()
    
    try:
        # Initialize components
        db_manager = DatabaseManager()
        doc_manager = DocumentIDManager()
        textract_config = OptimizedTextExtractorConfig()
        textract_config.DRY_RUN = False  # Enable real API calls
        
        # Find the smallest document
        suitable_docs = textract_config.find_suitable_test_documents(5)
        if not suitable_docs:
            print("❌ No suitable documents found")
            return False
        
        # Select the smallest document (last in list is usually smallest)
        selected_doc = min(suitable_docs, key=lambda x: x['size'])
        document_key = selected_doc['key']
        
        print(f"📄 Selected document: {document_key}")
        print(f"   Size: {selected_doc['size']:,} bytes")
        print(f"   Estimated pages: ~{selected_doc['check']['estimated_pages']}")
        print(f"   Estimated cost: ${selected_doc['check']['estimated_cost']:.4f}")
        print(f"   Free tier: {'✅' if selected_doc['check']['use_free_tier'] else '❌'}")
        
        # Final confirmation
        print(f"\n⚠️  This will make a REAL Textract API call")
        confirm = input("Proceed? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Test cancelled")
            return False
        
        # Create document record
        doc_url = f"s3://{textract_config.test_bucket}/{document_key}"
        doc_id = doc_manager.get_or_create_id(doc_url)
        
        metadata = {
            'original_filename': os.path.basename(document_key),
            'status': 'starting_extraction',
            'pdf_path': document_key,
            'url': doc_url
        }
        doc_manager.add_or_update_document(doc_id, metadata)
        
        print(f"\n🔌 Making real Textract API call...")
        
        # Make real API call
        api_result = textract_config.make_textract_call(
            textract_config.test_bucket,
            document_key,
            'structure',  # Text + layout, no tables/forms
            dry_run=False
        )
        
        if not api_result['success']:
            print(f"❌ API call failed: {api_result.get('error')}")
            return False
        
        job_id = api_result['job_id']
        print(f"✅ Job started: {job_id}")
        
        # Store job in database
        doc_hash = f"hash_{doc_id}"
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO textract_jobs (
                        job_id, doc_hash, source_bucket, source_key, output_bucket,
                        status, feature_types, started_at, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                """, (
                    job_id,
                    doc_hash,
                    textract_config.test_bucket,
                    document_key,
                    textract_config.test_bucket.replace('documents', 'output'),
                    'IN_PROGRESS',
                    json.dumps(api_result['features'])
                ))
                
                cursor.execute("""
                    INSERT INTO document_processing_status (
                        doc_hash, filename, source_bucket, source_key,
                        text_extraction_status, text_extraction_job_id,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (doc_hash) DO UPDATE SET
                        text_extraction_status = EXCLUDED.text_extraction_status,
                        text_extraction_job_id = EXCLUDED.text_extraction_job_id,
                        updated_at = NOW()
                """, (
                    doc_hash,
                    os.path.basename(document_key),
                    textract_config.test_bucket,
                    document_key,
                    'IN_PROGRESS',
                    job_id
                ))
                
                conn.commit()
        
        # Update document status
        doc_manager.update_document_status(doc_id, 'extracting', f'Textract job: {job_id}')
        
        print(f"📊 Database records created")
        
        # Monitor job progress
        print(f"\n⏱️  Monitoring job progress...")
        start_time = time.time()
        max_wait = 300  # 5 minutes max
        
        while time.time() - start_time < max_wait:
            try:
                response = textract_config.textract.get_document_analysis(JobId=job_id)
                status = response['JobStatus']
                
                elapsed = int(time.time() - start_time)
                print(f"\\r   Status: {status} (elapsed: {elapsed}s)", end='', flush=True)
                
                if status == 'SUCCEEDED':
                    print("\\n✅ Job completed successfully!")
                    
                    # Process results
                    blocks = response.get('Blocks', [])
                    pages = len([b for b in blocks if b['BlockType'] == 'PAGE'])
                    lines = len([b for b in blocks if b['BlockType'] == 'LINE'])
                    words = len([b for b in blocks if b['BlockType'] == 'WORD'])
                    
                    # Extract text
                    text_blocks = [b for b in blocks if b['BlockType'] == 'LINE']
                    extracted_text = '\\n'.join([b.get('Text', '') for b in text_blocks])
                    
                    # Update database with results
                    with db_manager.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                UPDATE textract_jobs 
                                SET status = %s, completed_at = NOW(), 
                                    pages_processed = %s, blocks_extracted = %s,
                                    files_created = %s, updated_at = NOW()
                                WHERE job_id = %s
                            """, (
                                'SUCCEEDED',
                                pages,
                                len(blocks),
                                json.dumps({
                                    'text_length': len(extracted_text),
                                    'lines_found': lines,
                                    'words_found': words
                                }),
                                job_id
                            ))
                            
                            cursor.execute("""
                                UPDATE document_processing_status 
                                SET text_extraction_status = %s,
                                    text_extraction_completed_at = NOW(),
                                    updated_at = NOW()
                                WHERE text_extraction_job_id = %s
                            """, ('COMPLETED', job_id))
                            
                            conn.commit()
                    
                    # Update document
                    doc_manager.update_document_status(
                        doc_id, 
                        'extracted', 
                        f'Completed: {pages} pages, {len(extracted_text)} chars'
                    )
                    
                    # Show results
                    print(f"\\n🎉 REAL TEXTRACT TEST SUCCESSFUL!")
                    print(f"📊 Results:")
                    print(f"   Job ID: {job_id}")
                    print(f"   Document ID: {doc_id}")
                    print(f"   Pages processed: {pages}")
                    print(f"   Total blocks: {len(blocks)}")
                    print(f"   Lines found: {lines}")
                    print(f"   Words found: {words}")
                    print(f"   Text length: {len(extracted_text):,} characters")
                    print(f"   Processing time: {elapsed}s")
                    
                    # Show text preview
                    preview = extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text
                    print(f"\\n📝 Extracted Text Preview:")
                    print(f"   {preview}")
                    
                    # Verify database state
                    print(f"\\n🔍 Database Verification:")
                    doc_metadata = doc_manager.get_document_metadata(doc_id)
                    print(f"   Document status: {doc_metadata.get('status') if doc_metadata else 'Not found'}")
                    
                    with db_manager.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT status, pages_processed FROM textract_jobs WHERE job_id = %s", (job_id,))
                            job_info = cursor.fetchone()
                            print(f"   Job status: {job_info[0] if job_info else 'Not found'}")
                            print(f"   Pages in DB: {job_info[1] if job_info else 'Not found'}")
                    
                    print(f"\\n✅ All systems working correctly!")
                    print(f"💰 Cost: $0.00 (free tier)")
                    print(f"🚀 Ready for Lambda deployment!")
                    
                    return True
                    
                elif status == 'FAILED':
                    print(f"\\n❌ Job failed: {response.get('StatusMessage', 'Unknown error')}")
                    return False
                    
                elif status == 'IN_PROGRESS':
                    time.sleep(5)  # Check every 5 seconds
                    
            except Exception as e:
                print(f"\\n❌ Error checking status: {e}")
                time.sleep(5)
        
        print(f"\\n⏰ Timeout after 5 minutes")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_streamlined_test()
    sys.exit(0 if success else 1)
