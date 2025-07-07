#!/usr/bin/env python3
"""
Real Textract API Test
Tests actual Textract calls with manual job monitoring (no SQS/SNS yet)
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
from textextractor_optimized_config import OptimizedTextExtractorConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTextractTest:
    """Test real Textract API calls with manual monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.doc_manager = DocumentIDManager()
        self.textract_config = OptimizedTextExtractorConfig()
        
        # Override to enable real API calls
        self.textract_config.DRY_RUN = False
        
        self.logger.info("Real Textract Test initialized")
        self.logger.warning("🚨 REAL API CALLS ENABLED - This will incur charges!")
    
    def start_real_textract_job(self, document_key: str, mode: str = 'structure') -> Dict[str, Any]:
        """Start a real Textract job and track it in database"""
        try:
            self.logger.info(f"Starting REAL Textract job for {document_key}")
            
            # Safety check first
            safety_check = self.textract_config.check_document_for_extraction(
                self.textract_config.test_bucket,
                document_key,
                mode
            )
            
            if not safety_check['safe_to_process']:
                return {
                    'success': False,
                    'error': 'Document failed safety check',
                    'safety_check': safety_check
                }
            
            # Confirm with user before making real API call
            print(f"\\n⚠️  REAL TEXTRACT API CALL")
            print(f"Document: {document_key}")
            print(f"Mode: {mode}")
            print(f"Method: {safety_check['method']}")
            print(f"Features: {safety_check['features']}")
            print(f"Estimated pages: {safety_check['estimated_pages']}")
            print(f"Estimated cost: ${safety_check['estimated_cost']:.4f}")
            print(f"Free tier: {'✅' if safety_check['use_free_tier'] else '❌'}")
            
            confirm = input("\\nProceed with REAL API call? (yes/no): ").strip().lower()
            if confirm != 'yes':
                return {
                    'success': False,
                    'error': 'User cancelled API call'
                }
            
            # Create document record
            doc_url = f"s3://{self.textract_config.test_bucket}/{document_key}"
            doc_id = self.doc_manager.get_or_create_id(doc_url)
            
            metadata = {
                'original_filename': os.path.basename(document_key),
                'status': 'starting_extraction',
                'pdf_path': document_key,
                'url': doc_url
            }
            self.doc_manager.add_or_update_document(doc_id, metadata)
            
            # Make real Textract API call
            api_result = self.textract_config.make_textract_call(
                self.textract_config.test_bucket,
                document_key,
                mode,
                dry_run=False  # REAL API CALL
            )
            
            if not api_result['success']:
                return {
                    'success': False,
                    'error': f"Textract API failed: {api_result.get('error')}",
                    'doc_id': doc_id
                }
            
            job_id = api_result['job_id']
            
            # Store job in database
            doc_hash = f"hash_{doc_id}"
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
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
                        'IN_PROGRESS',
                        json.dumps(api_result['features'])
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
                        os.path.basename(document_key),
                        self.textract_config.test_bucket,
                        document_key,
                        'IN_PROGRESS',
                        job_id
                    ))
                    
                    conn.commit()
            
            # Update document status
            self.doc_manager.update_document_status(
                doc_id,
                'extracting',
                f'Textract job started: {job_id}'
            )
            
            self.logger.info(f"✅ Real Textract job started: {job_id}")
            
            return {
                'success': True,
                'job_id': job_id,
                'doc_id': doc_id,
                'document_key': document_key,
                'safety_check': safety_check,
                'api_result': api_result
            }
            
        except Exception as e:
            self.logger.error(f"Real Textract job failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def monitor_job_status(self, job_id: str, max_wait_minutes: int = 10) -> Dict[str, Any]:
        """Monitor Textract job status manually (since we don't have SQS/SNS yet)"""
        try:
            self.logger.info(f"Monitoring job {job_id} (max {max_wait_minutes} minutes)")
            
            start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            
            while time.time() - start_time < max_wait_seconds:
                # Check job status
                try:
                    if self.textract_config.get_extraction_config()['method'] == 'DetectDocumentText':
                        response = self.textract_config.textract.get_document_text_detection(JobId=job_id)
                    else:
                        response = self.textract_config.textract.get_document_analysis(JobId=job_id)
                    
                    status = response['JobStatus']
                    
                    print(f"\\r⏱️  Job Status: {status} (elapsed: {int(time.time() - start_time)}s)", end='', flush=True)
                    
                    if status == 'SUCCEEDED':
                        print("\\n✅ Job completed successfully!")
                        return {
                            'success': True,
                            'status': status,
                            'response': response,
                            'elapsed_seconds': int(time.time() - start_time)
                        }
                    elif status == 'FAILED':
                        print(f"\\n❌ Job failed: {response.get('StatusMessage', 'Unknown error')}")
                        return {
                            'success': False,
                            'status': status,
                            'error': response.get('StatusMessage', 'Job failed'),
                            'elapsed_seconds': int(time.time() - start_time)
                        }
                    elif status in ['IN_PROGRESS']:
                        # Continue monitoring
                        time.sleep(10)  # Check every 10 seconds
                    else:
                        print(f"\\n⚠️  Unexpected status: {status}")
                        time.sleep(10)
                
                except Exception as e:
                    print(f"\\n❌ Error checking job status: {e}")
                    time.sleep(10)
            
            print(f"\\n⏰ Timeout after {max_wait_minutes} minutes")
            return {
                'success': False,
                'error': f'Timeout after {max_wait_minutes} minutes',
                'status': 'TIMEOUT'
            }
            
        except Exception as e:
            self.logger.error(f"Job monitoring failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_completed_job(self, job_id: str, doc_id: str, textract_response: Dict) -> Dict[str, Any]:
        """Process completed Textract job results"""
        try:
            self.logger.info(f"Processing completed job {job_id}")
            
            # Extract key information from response
            blocks = textract_response.get('Blocks', [])
            pages = len([b for b in blocks if b['BlockType'] == 'PAGE'])
            lines = len([b for b in blocks if b['BlockType'] == 'LINE'])
            words = len([b for b in blocks if b['BlockType'] == 'WORD'])
            tables = len([b for b in blocks if b['BlockType'] == 'TABLE'])
            
            # Extract text content
            text_blocks = [b for b in blocks if b['BlockType'] == 'LINE']
            extracted_text = '\\n'.join([b.get('Text', '') for b in text_blocks])
            
            processing_results = {
                'pages_processed': pages,
                'blocks_extracted': len(blocks),
                'lines_found': lines,
                'words_found': words,
                'tables_found': tables,
                'text_length': len(extracted_text),
                'processing_time_seconds': textract_response.get('elapsed_seconds', 0)
            }
            
            # Update database
            doc_hash = f"hash_{doc_id}"
            
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
                        'SUCCEEDED',
                        processing_results['pages_processed'],
                        processing_results['blocks_extracted'],
                        json.dumps({
                            'extracted_text_length': processing_results['text_length'],
                            'lines_found': processing_results['lines_found'],
                            'words_found': processing_results['words_found'],
                            'tables_found': processing_results['tables_found']
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
            self.doc_manager.update_document_status(
                doc_id,
                'extracted',
                f'Text extraction completed: {processing_results["pages_processed"]} pages, {processing_results["text_length"]} chars'
            )
            
            # Save extracted text (optional - for verification)
            text_preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
            
            return {
                'success': True,
                'processing_results': processing_results,
                'text_preview': text_preview,
                'full_text': extracted_text
            }
            
        except Exception as e:
            self.logger.error(f"Job processing failed: {e}")
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
                    
                    cursor.execute("DELETE FROM document_processing_status WHERE doc_hash = %s", (doc_hash,))
                    cursor.execute("DELETE FROM textract_jobs WHERE doc_hash = %s", (doc_hash,))
                    cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
                    
                    conn.commit()
            
            self.logger.info(f"Cleaned up test data for {doc_id}")
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up: {e}")

def main():
    """Run real Textract API test"""
    print("🚨 REAL TEXTRACT API TEST")
    print("=" * 50)
    print("⚠️  WARNING: This will make actual AWS API calls and incur charges!")
    print("💰 Estimated cost: $0.00 - $0.20 per document (depending on size)")
    print("🆓 Free tier: 100 pages/month for AnalyzeDocument")
    print()
    
    # Final confirmation
    proceed = input("Do you want to proceed with REAL API calls? (yes/no): ").strip().lower()
    if proceed != 'yes':
        print("❌ Test cancelled by user")
        return False
    
    try:
        test = RealTextractTest()
        
        # Find a suitable test document
        suitable_docs = test.textract_config.find_suitable_test_documents(3)
        
        if not suitable_docs:
            print("❌ No suitable test documents found")
            return False
        
        print(f"\\n📄 Available test documents:")
        for i, doc in enumerate(suitable_docs):
            check = doc['check']
            print(f"  {i+1}. {doc['key']}")
            print(f"     Size: {doc['size']:,} bytes")
            print(f"     Pages: ~{check['estimated_pages']}")
            print(f"     Cost: ${check['estimated_cost']:.4f}")
        
        # Select document
        while True:
            try:
                choice = int(input(f"\\nSelect document (1-{len(suitable_docs)}): ")) - 1
                if 0 <= choice < len(suitable_docs):
                    selected_doc = suitable_docs[choice]
                    break
                else:
                    print("Invalid choice")
            except ValueError:
                print("Please enter a number")
        
        document_key = selected_doc['key']
        
        # Start real Textract job
        print(f"\\n🚀 Starting real Textract job...")
        job_result = test.start_real_textract_job(document_key, 'structure')
        
        if not job_result['success']:
            print(f"❌ Job start failed: {job_result.get('error')}")
            return False
        
        job_id = job_result['job_id']
        doc_id = job_result['doc_id']
        
        print(f"✅ Job started: {job_id}")
        print(f"📋 Document ID: {doc_id}")
        
        # Monitor job
        print(f"\\n⏱️  Monitoring job progress...")
        monitor_result = test.monitor_job_status(job_id, max_wait_minutes=10)
        
        if not monitor_result['success']:
            print(f"❌ Job monitoring failed: {monitor_result.get('error')}")
            return False
        
        # Process results
        print(f"\\n📊 Processing job results...")
        process_result = test.process_completed_job(
            job_id, 
            doc_id, 
            monitor_result['response']
        )
        
        if not process_result['success']:
            print(f"❌ Result processing failed: {process_result.get('error')}")
            return False
        
        # Show results
        results = process_result['processing_results']
        print(f"\\n🎉 REAL TEXTRACT TEST COMPLETED!")
        print(f"📊 Results:")
        print(f"   Pages processed: {results['pages_processed']}")
        print(f"   Total blocks: {results['blocks_extracted']}")
        print(f"   Lines found: {results['lines_found']}")
        print(f"   Words found: {results['words_found']}")
        print(f"   Tables found: {results['tables_found']}")
        print(f"   Text length: {results['text_length']:,} characters")
        print(f"   Processing time: {results['processing_time_seconds']}s")
        
        print(f"\\n📝 Text Preview:")
        print(f"   {process_result['text_preview']}")
        
        # Cleanup option
        cleanup = input(f"\\nClean up test data? (y/N): ").strip().lower()
        if cleanup == 'y':
            test.cleanup_test_data(doc_id)
            print("✅ Test data cleaned up")
        else:
            print(f"💾 Test data preserved (doc_id: {doc_id})")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
