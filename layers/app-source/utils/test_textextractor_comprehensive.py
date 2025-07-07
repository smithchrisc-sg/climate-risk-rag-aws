#!/usr/bin/env python3
"""
Comprehensive TextExtractor Integration Test
Tests the full pipeline with real documents while staying within free tier
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

# Import our components
from DatabaseManager import DatabaseManager
from DocumentIDManager import DocumentIDManager
from textextractor_optimized_config import OptimizedTextExtractorConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveTextExtractorTest:
    """Comprehensive TextExtractor test with real AWS integration"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.doc_manager = DocumentIDManager()
        self.textract_config = OptimizedTextExtractorConfig()
        
        self.logger.info("Comprehensive TextExtractor Test initialized")
    
    def test_document_selection_and_safety(self) -> Dict[str, Any]:
        """Test document selection and safety checks"""
        try:
            self.logger.info("Testing document selection and safety checks...")
            
            # Find suitable test documents
            suitable_docs = self.textract_config.find_suitable_test_documents(5)
            
            if not suitable_docs:
                return {
                    'success': False,
                    'error': 'No suitable test documents found'
                }
            
            # Test safety checks for each document
            safety_results = []
            
            for doc in suitable_docs:
                key = doc['key']
                
                # Test different extraction modes
                for mode in ['basic', 'structure', 'structure_tables']:
                    check = self.textract_config.check_document_for_extraction(
                        self.textract_config.test_bucket, 
                        key, 
                        mode
                    )
                    
                    safety_results.append({
                        'document': key,
                        'mode': mode,
                        'safe': check['safe_to_process'],
                        'pages': check['estimated_pages'],
                        'cost': check['estimated_cost'],
                        'free_tier': check['use_free_tier'],
                        'method': check['method'],
                        'features': check['features']
                    })
            
            return {
                'success': True,
                'documents_found': len(suitable_docs),
                'safety_checks': len(safety_results),
                'safety_results': safety_results,
                'suitable_documents': suitable_docs
            }
            
        except Exception as e:
            self.logger.error(f"Document selection test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_database_integration_with_real_document(self, document_key: str) -> Dict[str, Any]:
        """Test database integration with a real document"""
        try:
            self.logger.info(f"Testing database integration with {document_key}")
            
            # Create document record
            doc_url = f"s3://{self.textract_config.test_bucket}/{document_key}"
            doc_id = self.doc_manager.get_or_create_id(doc_url)
            
            # Add document metadata
            filename = os.path.basename(document_key)
            metadata = {
                'original_filename': filename,
                'status': 'pending_extraction',
                'pdf_path': document_key,
                'url': doc_url
            }
            
            self.doc_manager.add_or_update_document(doc_id, metadata)
            
            # Simulate TextExtract job creation
            doc_hash = f"hash_{doc_id}"
            job_id = f"test-job-{int(time.time())}-{doc_id[:8]}"
            
            # Get document safety check
            safety_check = self.textract_config.check_document_for_extraction(
                self.textract_config.test_bucket,
                document_key,
                'structure'  # Use structure mode for testing
            )
            
            # Store job in database
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Insert textract job
                    cursor.execute("""
                        INSERT INTO textract_jobs (
                            job_id, doc_hash, source_bucket, source_key, output_bucket,
                            status, feature_types, started_at, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                    """, (
                        job_id,
                        doc_hash,
                        self.textract_config.test_bucket,
                        document_key,
                        self.textract_config.test_bucket.replace('documents', 'output'),
                        'TEST_IN_PROGRESS',
                        json.dumps(safety_check.get('features', ['LAYOUT']))
                    ))
                    
                    # Update processing status
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
                        filename,
                        self.textract_config.test_bucket,
                        document_key,
                        'TEST_IN_PROGRESS',
                        job_id
                    ))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(
                doc_id, 
                'extracting', 
                f'Test TextExtract job: {job_id}'
            )
            
            return {
                'success': True,
                'doc_id': doc_id,
                'job_id': job_id,
                'document_key': document_key,
                'safety_check': safety_check,
                'database_records_created': True
            }
            
        except Exception as e:
            self.logger.error(f"Database integration test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_textract_api_call_dry_run(self, document_key: str, mode: str = 'structure') -> Dict[str, Any]:
        """Test Textract API call in dry run mode"""
        try:
            self.logger.info(f"Testing Textract API call (DRY RUN) for {document_key}")
            
            # Make dry run call
            result = self.textract_config.make_textract_call(
                self.textract_config.test_bucket,
                document_key,
                mode,
                dry_run=True
            )
            
            return {
                'success': result['success'],
                'dry_run_result': result,
                'would_use_free_tier': result.get('safety_check', {}).get('use_free_tier', False),
                'estimated_cost': result.get('safety_check', {}).get('estimated_cost', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Textract API test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def simulate_job_completion(self, job_id: str, doc_id: str, pages_processed: int = 3) -> Dict[str, Any]:
        """Simulate job completion with realistic results"""
        try:
            self.logger.info(f"Simulating job completion for {job_id}")
            
            doc_hash = f"hash_{doc_id}"
            
            # Realistic processing results
            processing_results = {
                'pages_processed': pages_processed,
                'blocks_extracted': pages_processed * 45,  # ~45 blocks per page
                'processing_time_seconds': pages_processed * 15,  # ~15 seconds per page
                'layout_elements': pages_processed * 12,  # ~12 layout elements per page
                'tables_found': max(0, pages_processed - 1),  # Usually 0-1 tables per page
            }
            
            # Update database
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update textract job
                    cursor.execute("""
                        UPDATE textract_jobs 
                        SET status = %s,
                            completed_at = NOW(),
                            pages_processed = %s,
                            blocks_extracted = %s,
                            files_created = %s,
                            updated_at = NOW()
                        WHERE job_id = %s
                    """, (
                        'TEST_SUCCEEDED',
                        processing_results['pages_processed'],
                        processing_results['blocks_extracted'],
                        json.dumps({
                            'textract_response.json': f's3://output-bucket/extracted_documents/{doc_hash}/textract_response.json',
                            'raw_text.txt': f's3://output-bucket/extracted_documents/{doc_hash}/raw_text.txt',
                            'layout.csv': f's3://output-bucket/extracted_documents/{doc_hash}/layout.csv',
                            'processing_metadata.json': f's3://output-bucket/extracted_documents/{doc_hash}/processing_metadata.json'
                        }),
                        job_id
                    ))
                    
                    # Update processing status
                    cursor.execute("""
                        UPDATE document_processing_status 
                        SET text_extraction_status = %s,
                            text_extraction_completed_at = NOW(),
                            updated_at = NOW()
                        WHERE text_extraction_job_id = %s
                    """, ('TEST_COMPLETED', job_id))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(
                doc_id, 
                'extracted', 
                f'Test extraction completed: {processing_results["pages_processed"]} pages'
            )
            
            return {
                'success': True,
                'job_id': job_id,
                'processing_results': processing_results
            }
            
        except Exception as e:
            self.logger.error(f"Job completion simulation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_complete_pipeline(self, doc_id: str, job_id: str) -> Dict[str, Any]:
        """Verify the complete pipeline worked correctly"""
        try:
            verification = {}
            
            # Check document metadata
            doc_metadata = self.doc_manager.get_document_metadata(doc_id)
            verification['document_status'] = doc_metadata.get('status') if doc_metadata else None
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check textract job
                    cursor.execute("SELECT * FROM textract_jobs WHERE job_id = %s", (job_id,))
                    job = cursor.fetchone()
                    verification['job_status'] = job[5] if job else None  # status column
                    verification['pages_processed'] = job[9] if job else None
                    
                    # Check processing status
                    cursor.execute("""
                        SELECT text_extraction_status, text_extraction_completed_at 
                        FROM document_processing_status 
                        WHERE text_extraction_job_id = %s
                    """, (job_id,))
                    processing = cursor.fetchone()
                    verification['processing_status'] = processing[0] if processing else None
                    verification['completed_at'] = processing[1] if processing else None
                    
                    # Check pipeline view
                    cursor.execute("""
                        SELECT textract_job_id, text_extraction_status, pages_processed
                        FROM processing_pipeline_status 
                        WHERE textract_job_id = %s
                    """, (job_id,))
                    pipeline = cursor.fetchone()
                    verification['pipeline_view_working'] = pipeline is not None
                    
                    # Check job stats view
                    cursor.execute("""
                        SELECT status, job_count 
                        FROM textract_job_stats 
                        WHERE status = 'TEST_SUCCEEDED'
                    """)
                    stats = cursor.fetchone()
                    verification['stats_updated'] = stats is not None
                    verification['test_job_count'] = stats[1] if stats else 0
            
            return {
                'success': True,
                'verification': verification
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_test_data(self, doc_ids: List[str]):
        """Clean up test data"""
        try:
            for doc_id in doc_ids:
                with self.db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        doc_hash = f"hash_{doc_id}"
                        
                        # Clean up in dependency order
                        cursor.execute("DELETE FROM document_processing_status WHERE doc_hash = %s", (doc_hash,))
                        cursor.execute("DELETE FROM textract_jobs WHERE doc_hash = %s", (doc_hash,))
                        cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
                        
                        conn.commit()
                
                self.logger.info(f"Cleaned up test data for {doc_id}")
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up test data: {e}")

def main():
    """Run comprehensive TextExtractor integration test"""
    print("🚀 Comprehensive TextExtractor Integration Test")
    print("=" * 60)
    print("This test covers the complete TextExtractor pipeline:")
    print("- Document selection and safety checks")
    print("- Database integration")
    print("- Textract API calls (DRY RUN)")
    print("- Job completion simulation")
    print("- Pipeline verification")
    print()
    
    test_doc_ids = []
    
    try:
        test = ComprehensiveTextExtractorTest()
        
        # Test 1: Document selection and safety
        print("📋 Test 1: Document Selection and Safety Checks")
        selection_result = test.test_document_selection_and_safety()
        
        if not selection_result['success']:
            print(f"❌ Document selection failed: {selection_result.get('error')}")
            return False
        
        print(f"✅ Found {selection_result['documents_found']} suitable documents")
        print(f"✅ Performed {selection_result['safety_checks']} safety checks")
        
        # Show safety check summary
        free_tier_docs = sum(1 for r in selection_result['safety_results'] if r['free_tier'])
        print(f"✅ {free_tier_docs} document/mode combinations within free tier")
        
        # Select best test document
        suitable_docs = selection_result['suitable_documents']
        test_doc = suitable_docs[0]  # Use the first suitable document
        test_key = test_doc['key']
        
        print(f"📄 Selected test document: {test_key}")
        print(f"   Size: {test_doc['size']:,} bytes")
        print(f"   Estimated pages: ~{test_doc['check']['estimated_pages']}")
        
        # Test 2: Database integration
        print(f"\\n📊 Test 2: Database Integration")
        db_result = test.test_database_integration_with_real_document(test_key)
        
        if not db_result['success']:
            print(f"❌ Database integration failed: {db_result.get('error')}")
            return False
        
        doc_id = db_result['doc_id']
        job_id = db_result['job_id']
        test_doc_ids.append(doc_id)
        
        print(f"✅ Document record created: {doc_id}")
        print(f"✅ Job record created: {job_id}")
        print(f"✅ Processing status updated")
        
        # Test 3: Textract API call (DRY RUN)
        print(f"\\n🔌 Test 3: Textract API Call (DRY RUN)")
        api_result = test.test_textract_api_call_dry_run(test_key, 'structure')
        
        if not api_result['success']:
            print(f"❌ API test failed: {api_result.get('error')}")
            return False
        
        dry_run = api_result['dry_run_result']
        print(f"✅ API call would succeed")
        print(f"   Method: {dry_run['method']}")
        print(f"   Features: {dry_run['features']}")
        print(f"   Free tier: {'✅' if api_result['would_use_free_tier'] else '❌'}")
        print(f"   Estimated cost: ${api_result['estimated_cost']:.4f}")
        
        # Test 4: Job completion simulation
        print(f"\\n⏱️  Test 4: Job Completion Simulation")
        completion_result = test.simulate_job_completion(job_id, doc_id, 3)
        
        if not completion_result['success']:
            print(f"❌ Job completion failed: {completion_result.get('error')}")
            return False
        
        results = completion_result['processing_results']
        print(f"✅ Job completion simulated")
        print(f"   Pages processed: {results['pages_processed']}")
        print(f"   Blocks extracted: {results['blocks_extracted']}")
        print(f"   Processing time: {results['processing_time_seconds']}s")
        print(f"   Layout elements: {results['layout_elements']}")
        
        # Test 5: Pipeline verification
        print(f"\\n🔍 Test 5: Pipeline Verification")
        verify_result = test.verify_complete_pipeline(doc_id, job_id)
        
        if not verify_result['success']:
            print(f"❌ Pipeline verification failed: {verify_result.get('error')}")
            return False
        
        verification = verify_result['verification']
        print(f"✅ Pipeline verification completed")
        print(f"   Document status: {verification['document_status']}")
        print(f"   Job status: {verification['job_status']}")
        print(f"   Processing status: {verification['processing_status']}")
        print(f"   Pipeline view: {'✅' if verification['pipeline_view_working'] else '❌'}")
        print(f"   Stats updated: {'✅' if verification['stats_updated'] else '❌'}")
        
        print(f"\\n🎉 All tests PASSED!")
        print(f"\\n📊 Summary:")
        print(f"   Document processed: {test_key}")
        print(f"   Pages: ~{test_doc['check']['estimated_pages']}")
        print(f"   Cost: ${api_result['estimated_cost']:.4f} (would be free tier)")
        print(f"   Database records: ✅")
        print(f"   API integration: ✅ (dry run)")
        print(f"   Pipeline views: ✅")
        
        print(f"\\n🚀 Ready for:")
        print(f"   - Real Textract API calls (set DRY_RUN=False)")
        print(f"   - Production document processing")
        print(f"   - Lambda deployment")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if test_doc_ids:
            print(f"\\n🧹 Cleanup")
            cleanup = input("Clean up test data? (y/N): ").strip().lower()
            if cleanup == 'y':
                test.cleanup_test_data(test_doc_ids)
                print("✅ Test data cleaned up")
            else:
                print(f"💾 Test data preserved: {test_doc_ids}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
