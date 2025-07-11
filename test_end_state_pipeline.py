#!/usr/bin/env python3
"""
End-State Pipeline Test
Tests the complete pipeline using the source documents bucket approach
Simulates the end-state where DocumentIDManager creates doc_id before S3 upload
"""

import boto3
import json
import time
import threading
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import os
import sys

# Add layers to path for shared utilities
sys.path.append('layers/app-source')
sys.path.append('layers/app-source/utils')

try:
    from utils.DocumentIDManager import DocumentIDManager
    from lambda.nlp_worker.standardized_messaging import StandardizedMessagePublisher
except ImportError as e:
    print(f"Warning: Could not import shared utilities: {e}")
    DocumentIDManager = None
    StandardizedMessagePublisher = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EndStatePipelineTest:
    """Tests the end-state pipeline using source documents bucket"""
    
    def __init__(self):
        # AWS clients
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.sns_client = boto3.client('sns', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Bucket configuration
        self.source_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
        self.text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        self.chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        
        # Initialize DocumentIDManager
        if DocumentIDManager:
            try:
                self.doc_id_manager = DocumentIDManager()
                logger.info("DocumentIDManager initialized successfully")
            except Exception as e:
                logger.warning(f"DocumentIDManager not available: {e}")
                self.doc_id_manager = None
        else:
            self.doc_id_manager = None
        
        # Thread-safe results storage
        self.results_lock = threading.Lock()
        self.test_results = []
    
    def get_prepared_documents(self, limit: int = 10) -> List[Dict]:
        """Get prepared documents from source bucket"""
        try:
            logger.info(f"Fetching prepared documents from source bucket: {self.source_bucket}")
            
            # List documents in source bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.source_bucket,
                MaxKeys=limit * 2
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in source bucket")
                return []
            
            documents = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    # Extract doc_id from filename (key should be <doc_id>.pdf)
                    doc_id = os.path.splitext(key)[0]
                    
                    # Get object metadata
                    try:
                        head_response = self.s3_client.head_object(
                            Bucket=self.source_bucket,
                            Key=key
                        )
                        metadata = head_response.get('Metadata', {})
                        
                        documents.append({
                            'doc_id': doc_id,
                            'key': key,
                            'size': obj['Size'],
                            'size_mb': round(obj['Size'] / (1024 * 1024), 2),
                            'last_modified': obj['LastModified'],
                            'source_url': metadata.get('source-url'),
                            'original_filename': metadata.get('original-filename'),
                            'prepared_at': metadata.get('prepared-at')
                        })
                        
                    except Exception as e:
                        logger.warning(f"Could not get metadata for {key}: {e}")
                        # Add without metadata
                        documents.append({
                            'doc_id': doc_id,
                            'key': key,
                            'size': obj['Size'],
                            'size_mb': round(obj['Size'] / (1024 * 1024), 2),
                            'last_modified': obj['LastModified'],
                            'source_url': None,
                            'original_filename': None,
                            'prepared_at': None
                        })
            
            # Sort by size for consistent testing
            documents.sort(key=lambda x: x['size'])
            
            logger.info(f"Found {len(documents)} prepared documents")
            return documents[:limit]
            
        except Exception as e:
            logger.error(f"Error getting prepared documents: {e}")
            return []
    
    def verify_document_in_database(self, doc_id: str) -> bool:
        """Verify document exists in PostgreSQL database"""
        if not self.doc_id_manager:
            logger.warning("DocumentIDManager not available for verification")
            return False
        
        try:
            metadata = self.doc_id_manager.get_document_metadata(doc_id)
            if metadata:
                logger.info(f"Document {doc_id} verified in database")
                logger.info(f"  - URL: {metadata.get('url', 'N/A')}")
                logger.info(f"  - Status: {metadata.get('status', 'N/A')}")
                return True
            else:
                logger.warning(f"Document {doc_id} not found in database")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying document {doc_id} in database: {e}")
            return False
    
    def trigger_text_extraction(self, doc_info: Dict) -> Dict:
        """Trigger text extraction for a document (end-state simulation)"""
        thread_name = threading.current_thread().name
        doc_id = doc_info['doc_id']
        
        logger.info(f"[{thread_name}] Starting text extraction for document: {doc_id}")
        
        try:
            # Verify document is in database first
            if not self.verify_document_in_database(doc_id):
                return {
                    'doc_id': doc_id,
                    'status': 'failed',
                    'error': 'Document not found in database',
                    'stage': 'verification'
                }
            
            # Create S3 event payload for text extractor
            s3_event_payload = {
                "Records": [{
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "eventTime": datetime.utcnow().isoformat() + "Z",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "bucket": {
                            "name": self.source_bucket,
                            "arn": f"arn:aws:s3:::{self.source_bucket}"
                        },
                        "object": {
                            "key": doc_info['key'],
                            "size": doc_info['size']
                        }
                    },
                    # Add metadata for end-state simulation
                    "customMetadata": {
                        "docId": doc_id,
                        "sourceUrl": doc_info.get('source_url'),
                        "endStateTest": True
                    }
                }]
            }
            
            # Trigger text extractor initiator
            logger.info(f"[{thread_name}] Triggering text extraction for {doc_id}")
            
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',
                Payload=json.dumps(s3_event_payload)
            )
            
            if response['StatusCode'] != 202:
                error_msg = f"Failed to trigger text extraction: {response['StatusCode']}"
                logger.error(f"[{thread_name}] {error_msg}")
                return {
                    'doc_id': doc_id,
                    'status': 'failed',
                    'error': error_msg,
                    'stage': 'trigger'
                }
            
            logger.info(f"[{thread_name}] Successfully triggered text extraction for {doc_id}")
            
            return {
                'doc_id': doc_id,
                'source_url': doc_info.get('source_url'),
                'original_filename': doc_info.get('original_filename'),
                'status': 'triggered',
                'stage': 'trigger',
                'lambda_response_status': response['StatusCode'],
                'processing_started': datetime.utcnow().isoformat() + "Z",
                'size_mb': doc_info['size_mb']
            }
            
        except Exception as e:
            error_msg = f"Error triggering text extraction: {str(e)}"
            logger.error(f"[{thread_name}] {error_msg}")
            return {
                'doc_id': doc_id,
                'status': 'failed',
                'error': error_msg,
                'stage': 'trigger'
            }
    
    def monitor_processing_progress(self, doc_info: Dict, initial_result: Dict) -> Dict:
        """Monitor processing progress for a document"""
        thread_name = threading.current_thread().name
        doc_id = doc_info['doc_id']
        
        logger.info(f"[{thread_name}] Monitoring processing for document: {doc_id}")
        
        result = initial_result.copy()
        
        # Wait for text extraction (5 minutes)
        logger.info(f"[{thread_name}] Waiting 5 minutes for text extraction...")
        time.sleep(300)
        
        # Check text extraction
        try:
            text_key = f"text/{doc_id}.txt"
            response = self.s3_client.get_object(Bucket=self.text_bucket, Key=text_key)
            text_content = response['Body'].read().decode('utf-8')
            
            result.update({
                'text_extraction': 'success',
                'text_length': len(text_content),
                'text_location': f"s3://{self.text_bucket}/{text_key}"
            })
            logger.info(f"[{thread_name}] Text extraction successful: {len(text_content):,} characters")
            
        except Exception as e:
            result.update({
                'text_extraction': 'failed',
                'text_error': str(e)
            })
            logger.error(f"[{thread_name}] Text extraction failed: {e}")
        
        # Wait for text chunking (2 minutes)
        logger.info(f"[{thread_name}] Waiting 2 minutes for text chunking...")
        time.sleep(120)
        
        # Check chunks
        try:
            chunks_prefix = f"chunks/{doc_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.chunks_bucket,
                Prefix=chunks_prefix
            )
            chunk_count = response.get('KeyCount', 0)
            
            if chunk_count > 0:
                result.update({
                    'text_chunking': 'success',
                    'chunk_count': chunk_count,
                    'chunks_location': f"s3://{self.chunks_bucket}/{chunks_prefix}"
                })
                logger.info(f"[{thread_name}] Text chunking successful: {chunk_count} chunks")
            else:
                result.update({
                    'text_chunking': 'failed',
                    'chunk_error': 'No chunks found'
                })
                logger.error(f"[{thread_name}] Text chunking failed: No chunks found")
                
        except Exception as e:
            result.update({
                'text_chunking': 'failed',
                'chunk_error': str(e)
            })
            logger.error(f"[{thread_name}] Text chunking failed: {e}")
        
        # Check database status
        try:
            if self.doc_id_manager:
                db_metadata = self.doc_id_manager.get_document_metadata(doc_id)
                if db_metadata:
                    result.update({
                        'database_status': db_metadata.get('status', 'unknown'),
                        'database_updated': True
                    })
                else:
                    result.update({
                        'database_status': 'not_found',
                        'database_updated': False
                    })
        except Exception as e:
            result.update({
                'database_error': str(e),
                'database_updated': False
            })
        
        # Determine overall status
        if result.get('text_extraction') == 'success' and result.get('text_chunking') == 'success':
            result['status'] = 'success'
            result['stage'] = 'complete'
        else:
            result['status'] = 'partial' if result.get('text_extraction') == 'success' else 'failed'
            result['stage'] = 'incomplete'
        
        result['processing_completed'] = datetime.utcnow().isoformat() + "Z"
        
        logger.info(f"[{thread_name}] Processing monitoring complete for {doc_id}: {result['status']}")
        return result
    
    def process_document_thread(self, doc_info: Dict) -> Dict:
        """Process a single document in a thread (trigger + monitor)"""
        # Trigger processing
        initial_result = self.trigger_text_extraction(doc_info)
        
        if initial_result['status'] == 'failed':
            return initial_result
        
        # Monitor processing
        final_result = self.monitor_processing_progress(doc_info, initial_result)
        
        # Store result thread-safely
        with self.results_lock:
            self.test_results.append(final_result)
        
        return final_result
    
    def run_end_state_test(self, num_documents: int = 5) -> Dict:
        """Run end-state pipeline test"""
        logger.info(f"🧪 STARTING END-STATE PIPELINE TEST")
        logger.info(f"📊 Target: {num_documents} documents")
        logger.info("=" * 60)
        
        # Get prepared documents
        prepared_docs = self.get_prepared_documents(limit=num_documents * 2)
        
        if len(prepared_docs) < num_documents:
            logger.warning(f"Only {len(prepared_docs)} documents available, adjusting target")
            num_documents = len(prepared_docs)
        
        if num_documents == 0:
            logger.error("No prepared documents available for testing")
            return {'status': 'failed', 'error': 'No prepared documents available'}
        
        # Select documents for testing
        test_documents = prepared_docs[:num_documents]
        
        logger.info(f"📄 Selected {len(test_documents)} documents for testing:")
        for i, doc in enumerate(test_documents, 1):
            logger.info(f"  {i}. {doc['doc_id']} ({doc['size_mb']} MB)")
            if doc.get('source_url'):
                logger.info(f"     Source: {doc['source_url']}")
        
        # Start processing
        start_time = datetime.utcnow()
        logger.info(f"\n🚀 Starting end-state pipeline test at {start_time.isoformat()}Z")
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=num_documents, thread_name_prefix="EndStateProcessor") as executor:
            # Submit all tasks
            future_to_doc = {
                executor.submit(self.process_document_thread, doc): doc 
                for doc in test_documents
            }
            
            # Collect results as they complete
            completed_results = []
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    completed_results.append(result)
                    logger.info(f"✅ Completed processing: {result['doc_id']} - {result['status']}")
                except Exception as e:
                    error_result = {
                        'doc_id': doc['doc_id'],
                        'status': 'failed',
                        'error': str(e),
                        'stage': 'thread_execution'
                    }
                    completed_results.append(error_result)
                    logger.error(f"❌ Thread execution failed: {doc['doc_id']} - {e}")
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()
        
        # Compile summary results
        successful = sum(1 for r in completed_results if r['status'] == 'success')
        partial = sum(1 for r in completed_results if r['status'] == 'partial')
        failed = sum(1 for r in completed_results if r['status'] == 'failed')
        
        summary = {
            'test_type': 'end_state_pipeline_test',
            'source_bucket': self.source_bucket,
            'documents_processed': len(completed_results),
            'target_documents': num_documents,
            'successful': successful,
            'partial': partial,
            'failed': failed,
            'success_rate': (successful / len(completed_results)) * 100 if completed_results else 0,
            'total_duration_seconds': total_duration,
            'average_duration_per_doc': total_duration / len(completed_results) if completed_results else 0,
            'start_time': start_time.isoformat() + "Z",
            'end_time': end_time.isoformat() + "Z",
            'results': completed_results
        }
        
        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 END-STATE PIPELINE TEST COMPLETE")
        logger.info("=" * 60)
        logger.info(f"📊 Documents Processed: {summary['documents_processed']}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"⚠️  Partial: {partial}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"⏱️  Total Duration: {total_duration:.1f} seconds")
        logger.info(f"⏱️  Average per Document: {summary['average_duration_per_doc']:.1f} seconds")
        
        return summary

def main():
    """Main test execution"""
    try:
        # Initialize test manager
        test_manager = EndStatePipelineTest()
        
        # Run end-state test with 5 documents
        results = test_manager.run_end_state_test(num_documents=5)
        
        # Save results to file
        results_filename = f"end_state_pipeline_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📄 Results saved to: {results_filename}")
        
        # Print final status
        if results['success_rate'] >= 80:
            logger.info("🎉 TEST PASSED: End-state pipeline is working well!")
        elif results['success_rate'] >= 50:
            logger.info("⚠️  TEST PARTIAL: End-state pipeline has some issues")
        else:
            logger.info("❌ TEST FAILED: End-state pipeline needs attention")
        
        return results
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'failed', 'error': str(e)}

if __name__ == "__main__":
    main()
