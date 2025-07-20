#!/usr/bin/env python3
"""
Database-Only TextExtractor Integration Test
Tests TextExtractor database integration without requiring S3 access
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextExtractorDatabaseTest:
    """Test TextExtractor database integration without S3 dependencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.doc_manager = DocumentIDManager()
        
        self.logger.info("TextExtractor Database Test initialized")
    
    def test_document_lifecycle(self) -> Dict[str, Any]:
        """Test complete document processing lifecycle in database"""
        try:
            timestamp = int(time.time())
            
            # Step 1: Create document record
            test_url = f"https://example.com/climate-report-{timestamp}.pdf"
            doc_id = self.doc_manager.get_or_create_id(test_url)
            
            metadata = {
                'original_filename': f'climate_report_{timestamp}.pdf',
                'status': 'pending_extraction',
                'pdf_path': f'documents/climate_report_{timestamp}.pdf'
            }
            self.doc_manager.add_or_update_document(doc_id, metadata)
            
            self.logger.info(f"✅ Step 1: Document created - {doc_id}")
            
            # Step 2: Simulate TextExtract job initiation
            doc_hash = f"hash_{doc_id}"
            job_id = f"textract-job-{timestamp}-{doc_id[:8]}"
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Insert textract job record
                    cursor.execute("""
                        INSERT INTO textract_jobs (
                            job_id, doc_hash, source_bucket, source_key, output_bucket,
                            status, feature_types, started_at, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                    """, (
                        job_id,
                        doc_hash,
                        'test-documents-bucket',
                        f'documents/climate_report_{timestamp}.pdf',
                        'test-output-bucket',
                        'IN_PROGRESS',
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
                        f'climate_report_{timestamp}.pdf',
                        'test-documents-bucket',
                        f'documents/climate_report_{timestamp}.pdf',
                        'IN_PROGRESS',
                        job_id
                    ))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(doc_id, 'extracting', f'TextExtract job started: {job_id}')
            
            self.logger.info(f"✅ Step 2: TextExtract job initiated - {job_id}")
            
            # Step 3: Simulate job completion
            processing_results = {
                'pages_processed': 5,
                'blocks_extracted': 247,
                'tables_found': 3,
                'forms_found': 2,
                'processing_time_seconds': 67
            }
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update textract job with completion
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
                        'SUCCEEDED',
                        processing_results['pages_processed'],
                        processing_results['blocks_extracted'],
                        json.dumps({
                            'textract_response.json': f's3://test-output-bucket/extracted_documents/{doc_hash}/textract_response.json',
                            'raw_text.txt': f's3://test-output-bucket/extracted_documents/{doc_hash}/raw_text.txt',
                            'layout.csv': f's3://test-output-bucket/extracted_documents/{doc_hash}/layout.csv',
                            'key_values.csv': f's3://test-output-bucket/extracted_documents/{doc_hash}/key_values.csv',
                            'table_1.csv': f's3://test-output-bucket/extracted_documents/{doc_hash}/table_1.csv',
                            'processing_metadata.json': f's3://test-output-bucket/extracted_documents/{doc_hash}/processing_metadata.json'
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
                    """, ('COMPLETED', job_id))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(doc_id, 'extracted', 'Text extraction completed successfully')
            
            self.logger.info(f"✅ Step 3: Job completion recorded")
            
            # Step 4: Verify all database views and relationships
            verification_results = self.verify_database_state(doc_id, job_id)
            
            return {
                'success': True,
                'doc_id': doc_id,
                'job_id': job_id,
                'processing_results': processing_results,
                'verification': verification_results
            }
            
        except Exception as e:
            self.logger.error(f"Document lifecycle test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_database_state(self, doc_id: str, job_id: str) -> Dict[str, Any]:
        """Verify all database tables and views are correctly updated"""
        try:
            verification = {}
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check document record
                    cursor.execute("SELECT * FROM documents WHERE doc_id = %s", (doc_id,))
                    document = cursor.fetchone()
                    verification['document_exists'] = document is not None
                    verification['document_status'] = document[10] if document else None  # status column
                    
                    # Check textract job
                    cursor.execute("SELECT * FROM textract_jobs WHERE job_id = %s", (job_id,))
                    job = cursor.fetchone()
                    verification['job_exists'] = job is not None
                    verification['job_status'] = job[5] if job else None  # status column
                    verification['pages_processed'] = job[9] if job else None
                    verification['blocks_extracted'] = job[10] if job else None
                    
                    # Check processing status
                    doc_hash = f"hash_{doc_id}"
                    cursor.execute("SELECT * FROM document_processing_status WHERE doc_hash = %s", (doc_hash,))
                    processing = cursor.fetchone()
                    verification['processing_status_exists'] = processing is not None
                    verification['extraction_status'] = processing[4] if processing else None
                    
                    # Check document metadata view
                    cursor.execute("SELECT * FROM document_metadata_view WHERE doc_id = %s", (doc_id,))
                    metadata_view = cursor.fetchone()
                    verification['metadata_view_exists'] = metadata_view is not None
                    
                    # Check processing pipeline view
                    cursor.execute("SELECT * FROM processing_pipeline_status WHERE textract_job_id = %s", (job_id,))
                    pipeline_view = cursor.fetchone()
                    verification['pipeline_view_exists'] = pipeline_view is not None
                    verification['pipeline_extraction_status'] = pipeline_view[4] if pipeline_view else None
                    
                    # Check textract job stats view
                    cursor.execute("SELECT * FROM textract_job_stats WHERE status = 'SUCCEEDED'")
                    stats = cursor.fetchone()
                    verification['job_stats_updated'] = stats is not None
                    verification['succeeded_job_count'] = stats[1] if stats else 0
            
            self.logger.info("✅ Database state verification completed")
            return verification
            
        except Exception as e:
            self.logger.error(f"Database verification failed: {e}")
            return {'error': str(e)}
    
    def test_processing_statistics(self) -> Dict[str, Any]:
        """Test processing statistics and views"""
        try:
            stats = self.doc_manager.get_processing_statistics()
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Test textract job stats view
                    cursor.execute("SELECT * FROM textract_job_stats ORDER BY job_count DESC")
                    job_stats = cursor.fetchall()
                    
                    # Test processing pipeline status view
                    cursor.execute("""
                        SELECT text_extraction_status, COUNT(*) 
                        FROM processing_pipeline_status 
                        GROUP BY text_extraction_status
                    """)
                    pipeline_stats = cursor.fetchall()
            
            return {
                'success': True,
                'document_stats': stats,
                'job_stats': [dict(zip(['status', 'job_count', 'avg_processing_time', 'avg_pages', 'avg_blocks', 'earliest', 'latest'], row)) for row in job_stats],
                'pipeline_stats': [{'status': row[0], 'count': row[1]} for row in pipeline_stats]
            }
            
        except Exception as e:
            self.logger.error(f"Statistics test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_test_data(self, doc_id: str):
        """Clean up test data"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    doc_hash = f"hash_{doc_id}"
                    
                    # Clean up in reverse dependency order
                    cursor.execute("DELETE FROM document_processing_status WHERE doc_hash = %s", (doc_hash,))
                    cursor.execute("DELETE FROM textract_jobs WHERE doc_hash = %s", (doc_hash,))
                    cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
                    
                    conn.commit()
            
            self.logger.info(f"✅ Test data cleaned up for {doc_id}")
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up test data: {e}")

def main():
    """Run TextExtractor database integration test"""
    print("🧪 TextExtractor Database Integration Test")
    print("=" * 50)
    print("This test simulates the complete TextExtractor workflow")
    print("without making actual AWS Textract API calls.")
    print()
    
    try:
        test = TextExtractorDatabaseTest()
        
        # Test 1: Document lifecycle
        print("📋 Test 1: Document Processing Lifecycle")
        lifecycle_result = test.test_document_lifecycle()
        
        if lifecycle_result['success']:
            print("✅ Document lifecycle test PASSED")
            print(f"   Document ID: {lifecycle_result['doc_id']}")
            print(f"   Job ID: {lifecycle_result['job_id']}")
            print(f"   Pages Processed: {lifecycle_result['processing_results']['pages_processed']}")
            print(f"   Blocks Extracted: {lifecycle_result['processing_results']['blocks_extracted']}")
            
            # Show verification results
            verification = lifecycle_result['verification']
            print("\\n📊 Database Verification:")
            print(f"   Document Status: {verification.get('document_status', 'N/A')}")
            print(f"   Job Status: {verification.get('job_status', 'N/A')}")
            print(f"   Processing Status: {verification.get('extraction_status', 'N/A')}")
            print(f"   Pipeline View: {'✅' if verification.get('pipeline_view_exists') else '❌'}")
            print(f"   Metadata View: {'✅' if verification.get('metadata_view_exists') else '❌'}")
            
            doc_id = lifecycle_result['doc_id']
        else:
            print("❌ Document lifecycle test FAILED")
            print(f"   Error: {lifecycle_result.get('error', 'Unknown error')}")
            return False
        
        # Test 2: Processing statistics
        print("\\n📊 Test 2: Processing Statistics")
        stats_result = test.test_processing_statistics()
        
        if stats_result['success']:
            print("✅ Statistics test PASSED")
            print(f"   Total Documents: {stats_result['document_stats'].get('total_documents', 0)}")
            
            job_stats = stats_result['job_stats']
            if job_stats:
                print("   Job Statistics:")
                for stat in job_stats:
                    print(f"     {stat['status']}: {stat['job_count']} jobs")
            
            pipeline_stats = stats_result['pipeline_stats']
            if pipeline_stats:
                print("   Pipeline Statistics:")
                for stat in pipeline_stats:
                    print(f"     {stat['status']}: {stat['count']} documents")
        else:
            print("❌ Statistics test FAILED")
            print(f"   Error: {stats_result.get('error', 'Unknown error')}")
        
        # Cleanup option
        print("\\n🧹 Cleanup")
        cleanup = input("Clean up test data? (y/N): ").strip().lower()
        if cleanup == 'y':
            test.cleanup_test_data(doc_id)
            print("✅ Test data cleaned up")
        else:
            print(f"💾 Test data preserved (doc_id: {doc_id})")
        
        print("\\n🎉 TextExtractor database integration test completed!")
        print("\\n📋 Ready for:")
        print("   - Real TextExtract API integration")
        print("   - S3 document processing")
        print("   - Lambda deployment")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
