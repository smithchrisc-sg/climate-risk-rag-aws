#!/usr/bin/env python3
"""
Safe TextExtractor Integration Test
Tests TextExtractor with database integration while preventing cost overruns
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Import our components
from DatabaseManager import DatabaseManager
from DocumentIDManager import DocumentIDManager
from textextractor_test_config import TextExtractorTestSafety

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SafeTextExtractorTest:
    """Safe integration test for TextExtractor with database"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.doc_manager = DocumentIDManager()
        self.safety = TextExtractorTestSafety()
        
        # Test configuration
        self.test_bucket = os.environ.get('TEST_BUCKET', 'solve-global-kr-documents-614290363854-us-east-1')
        
        self.logger.info("Safe TextExtractor Test initialized")
    
    def create_test_document_record(self) -> str:
        """Create a test document record in the database"""
        try:
            # Create unique test document
            timestamp = int(time.time())
            test_url = f"s3://{self.test_bucket}/test-textextractor-{timestamp}.pdf"
            
            # Generate document ID
            doc_id = self.doc_manager.generate_id(test_url)
            
            # Add to database
            metadata = {
                'url': test_url,
                'original_filename': f'textextractor_test_{timestamp}.pdf',
                'status': 'pending_extraction',
                'pdf_path': f'test-documents/textextractor_test_{timestamp}.pdf'
            }
            
            self.doc_manager.add_or_update_document(doc_id, metadata)
            
            self.logger.info(f"Created test document record: {doc_id}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Error creating test document: {e}")
            raise
    
    def simulate_textract_job_creation(self, doc_id: str, bucket: str, key: str) -> Dict[str, Any]:
        """Simulate TextExtractor job creation with safety checks"""
        try:
            self.logger.info(f"Simulating TextExtract job for {doc_id}")
            
            # Safety check the document
            safety_result = self.safety.safe_textract_call(bucket, key, dry_run=True)
            
            if not safety_result.get('job_started', False) and 'error' in safety_result:
                self.logger.warning(f"Safety check failed: {safety_result['error']}")
                return safety_result
            
            # Generate mock job ID for testing
            mock_job_id = f"mock-job-{int(time.time())}-{doc_id[:8]}"
            
            # Create textract job record in database
            doc_hash = f"hash_{doc_id}"
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Insert mock textract job
                    cursor.execute("""
                        INSERT INTO textract_jobs (
                            job_id, doc_hash, source_bucket, source_key, output_bucket,
                            status, feature_types, started_at, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                    """, (
                        mock_job_id,
                        doc_hash,
                        bucket,
                        key,
                        self.test_bucket,
                        'MOCK_IN_PROGRESS',
                        json.dumps(['TABLES', 'FORMS', 'LAYOUT'])
                    ))
                    
                    # Update document processing status
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
                        os.path.basename(key),
                        bucket,
                        key,
                        'MOCK_IN_PROGRESS',
                        mock_job_id
                    ))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(doc_id, 'extracting', f'Mock Textract job started: {mock_job_id}')
            
            result = {
                'job_started': True,
                'job_id': mock_job_id,
                'doc_id': doc_id,
                'safety_check': safety_result['safety_check'],
                'estimated_cost': safety_result.get('estimated_cost', 0),
                'mock_job': True
            }
            
            self.logger.info(f"Mock TextExtract job created: {mock_job_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error simulating TextExtract job: {e}")
            raise
    
    def simulate_job_completion(self, job_id: str, doc_id: str) -> Dict[str, Any]:
        """Simulate TextExtract job completion"""
        try:
            self.logger.info(f"Simulating job completion for {job_id}")
            
            doc_hash = f"hash_{doc_id}"
            
            # Mock processing results
            mock_results = {
                'pages_processed': 3,
                'blocks_extracted': 150,
                'tables_found': 2,
                'forms_found': 1,
                'processing_time_seconds': 45
            }
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update textract job status
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
                        'MOCK_SUCCEEDED',
                        mock_results['pages_processed'],
                        mock_results['blocks_extracted'],
                        json.dumps({
                            'raw_text.txt': f's3://{self.test_bucket}/extracted_documents/{doc_hash}/raw_text.txt',
                            'layout.csv': f's3://{self.test_bucket}/extracted_documents/{doc_hash}/layout.csv',
                            'tables.csv': f's3://{self.test_bucket}/extracted_documents/{doc_hash}/tables.csv'
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
                    """, ('MOCK_COMPLETED', job_id))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(doc_id, 'extracted', 'Mock text extraction completed')
            
            result = {
                'job_completed': True,
                'job_id': job_id,
                'doc_id': doc_id,
                'results': mock_results,
                'mock_completion': True
            }
            
            self.logger.info(f"Mock job completion recorded: {job_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error simulating job completion: {e}")
            raise
    
    def test_full_pipeline(self) -> Dict[str, Any]:
        """Test the full TextExtractor pipeline safely"""
        try:
            self.logger.info("Starting safe TextExtractor pipeline test")
            
            # Step 1: Create test document record
            doc_id = self.create_test_document_record()
            
            # Step 2: Simulate TextExtract job initiation
            test_bucket = self.test_bucket
            test_key = f"test-documents/textextractor_test_{int(time.time())}.pdf"
            
            job_result = self.simulate_textract_job_creation(doc_id, test_bucket, test_key)
            
            if not job_result.get('job_started'):
                return {
                    'success': False,
                    'error': 'Job creation failed',
                    'details': job_result
                }
            
            job_id = job_result['job_id']
            
            # Step 3: Simulate job completion
            completion_result = self.simulate_job_completion(job_id, doc_id)
            
            # Step 4: Verify database state
            final_metadata = self.doc_manager.get_document_metadata(doc_id)
            
            # Step 5: Check processing pipeline view
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM processing_pipeline_status 
                        WHERE textract_job_id = %s
                    """, (job_id,))
                    pipeline_status = cursor.fetchone()
            
            result = {
                'success': True,
                'doc_id': doc_id,
                'job_id': job_id,
                'job_creation': job_result,
                'job_completion': completion_result,
                'final_document_status': final_metadata.get('status') if final_metadata else None,
                'pipeline_status': dict(pipeline_status) if pipeline_status else None,
                'estimated_cost': job_result.get('estimated_cost', 0),
                'safety_warnings': job_result.get('safety_check', {}).get('warnings', [])
            }
            
            self.logger.info("Safe TextExtractor pipeline test completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_test_data(self, doc_id: str = None):
        """Clean up test data"""
        try:
            if doc_id:
                # Remove test document and related records
                with self.db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        doc_hash = f"hash_{doc_id}"
                        
                        # Clean up in reverse dependency order
                        cursor.execute("DELETE FROM document_processing_status WHERE doc_hash = %s", (doc_hash,))
                        cursor.execute("DELETE FROM textract_jobs WHERE doc_hash = %s", (doc_hash,))
                        cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
                        
                        conn.commit()
                
                self.logger.info(f"Cleaned up test data for {doc_id}")
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up test data: {e}")

def main():
    """Run safe TextExtractor integration test"""
    print("🛡️  Safe TextExtractor Integration Test")
    print("=" * 50)
    
    # Show safety configuration
    safety = TextExtractorTestSafety()
    print(f"DRY RUN Mode: {safety.DRY_RUN}")
    print(f"Use Basic Textract: {safety.USE_BASIC_TEXTRACT}")
    print(f"Max Pages Per Test: {safety.MAX_PAGES_PER_TEST}")
    print()
    
    try:
        # Initialize test
        test = SafeTextExtractorTest()
        
        # Run pipeline test
        result = test.test_full_pipeline()
        
        if result['success']:
            print("✅ TextExtractor Pipeline Test PASSED")
            print(f"📋 Document ID: {result['doc_id']}")
            print(f"📋 Job ID: {result['job_id']}")
            print(f"📋 Final Status: {result['final_document_status']}")
            print(f"💰 Estimated Cost: ${result['estimated_cost']:.4f}")
            
            if result['safety_warnings']:
                print("⚠️  Safety Warnings:")
                for warning in result['safety_warnings']:
                    print(f"   - {warning}")
            
            # Ask about cleanup
            cleanup = input("\\nClean up test data? (y/N): ").strip().lower()
            if cleanup == 'y':
                test.cleanup_test_data(result['doc_id'])
                print("🧹 Test data cleaned up")
        else:
            print("❌ TextExtractor Pipeline Test FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
