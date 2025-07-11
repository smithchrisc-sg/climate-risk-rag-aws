#!/usr/bin/env python3
"""
Complete End-to-End Pipeline Test with Source URL Integration
Multi-threaded test of 10 documents in parallel using proper source URLs from POC database
"""

import boto3
import json
import time
import sqlite3
import threading
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
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
    print("Some functionality may be limited")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineTestManager:
    """Manages multi-threaded pipeline testing with source URL integration"""
    
    def __init__(self):
        # AWS clients
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.sns_client = boto3.client('sns', region_name='us-east-1')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Configuration
        self.documents_bucket = "solve-global-kr-documents-861276078413-us-east-1"
        self.text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        self.chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        self.sqlite_db_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        
        # Initialize DocumentIDManager
        try:
            self.doc_id_manager = DocumentIDManager()
            logger.info("DocumentIDManager initialized successfully")
        except Exception as e:
            logger.warning(f"DocumentIDManager not available: {e}")
            self.doc_id_manager = None
        
        # Initialize StandardizedMessagePublisher
        try:
            self.message_publisher = StandardizedMessagePublisher()
            logger.info("StandardizedMessagePublisher initialized successfully")
        except Exception as e:
            logger.warning(f"StandardizedMessagePublisher not available: {e}")
            self.message_publisher = None
        
        # Thread-safe results storage
        self.results_lock = threading.Lock()
        self.test_results = []
    
    def get_available_documents(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get available documents from S3 bucket and match with SQLite database
        
        Args:
            limit: Maximum number of documents to retrieve
            
        Returns:
            List of document info dictionaries
        """
        try:
            logger.info(f"Fetching available documents from S3 bucket: {self.documents_bucket}")
            
            # List documents in S3 bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.documents_bucket,
                Prefix="documents/",
                MaxKeys=100
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in S3 bucket")
                return []
            
            # Extract document info
            s3_documents = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    filename = os.path.basename(key)
                    doc_id_from_filename = filename.replace('.pdf', '')
                    
                    s3_documents.append({
                        'key': key,
                        'filename': filename,
                        'doc_id_from_filename': doc_id_from_filename,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            logger.info(f"Found {len(s3_documents)} PDF documents in S3")
            
            # Match with SQLite database to get source URLs
            matched_documents = self.match_documents_with_database(s3_documents[:limit])
            
            logger.info(f"Successfully matched {len(matched_documents)} documents with database")
            return matched_documents
            
        except Exception as e:
            logger.error(f"Error getting available documents: {e}")
            return []
    
    def match_documents_with_database(self, s3_documents: List[Dict]) -> List[Dict]:
        """
        Match S3 documents with SQLite database to get source URLs
        
        Args:
            s3_documents: List of S3 document info
            
        Returns:
            List of matched documents with source URLs
        """
        matched_documents = []
        
        try:
            # Connect to SQLite database
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            logger.info(f"Connected to SQLite database: {self.sqlite_db_path}")
            
            for doc_info in s3_documents:
                doc_id = doc_info['doc_id_from_filename']
                
                try:
                    # Query database for source URL
                    cursor.execute(
                        "SELECT url, original_filename FROM documents WHERE doc_id = ?",
                        (doc_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        source_url, original_filename = result
                        
                        # Generate proper document ID using DocumentIDManager
                        if self.doc_id_manager:
                            try:
                                proper_doc_id = self.doc_id_manager.get_or_create_id(source_url)
                            except Exception as e:
                                logger.warning(f"DocumentIDManager failed for {source_url}: {e}")
                                proper_doc_id = doc_id  # Fallback to filename-based ID
                        else:
                            proper_doc_id = doc_id
                        
                        matched_doc = {
                            **doc_info,
                            'source_url': source_url,
                            'original_filename': original_filename,
                            'proper_doc_id': proper_doc_id
                        }
                        matched_documents.append(matched_doc)
                        
                        logger.debug(f"Matched document: {doc_id} -> {source_url}")
                    else:
                        logger.warning(f"No database entry found for doc_id: {doc_id}")
                        
                except Exception as e:
                    logger.error(f"Error querying database for {doc_id}: {e}")
                    continue
            
            conn.close()
            logger.info(f"Database connection closed. Matched {len(matched_documents)} documents")
            
        except Exception as e:
            logger.error(f"Error connecting to SQLite database: {e}")
        
        return matched_documents
    
    def create_pipeline_message(self, doc_info: Dict) -> Dict:
        """
        Create standardized pipeline message for document processing
        
        Args:
            doc_info: Document information dictionary
            
        Returns:
            Standardized message dictionary
        """
        return {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-test",
            "stage": "document_processing_request",
            "doc_id": doc_info['proper_doc_id'],
            "document_metadata": {
                "source_url": doc_info['source_url'],
                "original_filename": doc_info['original_filename'],
                "s3_key": doc_info['key'],
                "file_size": doc_info['size'],
                "processing_started": datetime.utcnow().isoformat() + "Z",
                "test_run": True
            },
            "data_locations": {
                "source_bucket": self.documents_bucket,
                "source_key": doc_info['key']
            },
            "processing_metadata": {
                "initiated_by": "test_complete_pipeline_with_source_urls",
                "test_batch": True,
                "parallel_processing": True
            }
        }
    
    def trigger_document_processing(self, doc_info: Dict) -> Dict:
        """
        Trigger processing for a single document
        
        Args:
            doc_info: Document information dictionary
            
        Returns:
            Processing result dictionary
        """
        thread_name = threading.current_thread().name
        doc_id = doc_info['proper_doc_id']
        
        logger.info(f"[{thread_name}] Starting processing for document: {doc_id}")
        
        try:
            # Create S3 event payload (compatible with existing text extractor)
            s3_event_payload = {
                "Records": [{
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "eventTime": datetime.utcnow().isoformat() + "Z",
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "bucket": {
                            "name": self.documents_bucket,
                            "arn": f"arn:aws:s3:::{self.documents_bucket}"
                        },
                        "object": {
                            "key": doc_info['key'],
                            "size": doc_info['size']
                        }
                    },
                    # Add custom metadata for source URL
                    "customMetadata": {
                        "sourceUrl": doc_info['source_url'],
                        "properDocId": doc_info['proper_doc_id'],
                        "testRun": True
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
                error_msg = f"Failed to trigger processing: {response['StatusCode']}"
                logger.error(f"[{thread_name}] {error_msg}")
                return {
                    'doc_id': doc_id,
                    'status': 'failed',
                    'error': error_msg,
                    'stage': 'trigger'
                }
            
            logger.info(f"[{thread_name}] Successfully triggered processing for {doc_id}")
            
            # Return initial success
            return {
                'doc_id': doc_id,
                'proper_doc_id': doc_info['proper_doc_id'],
                'source_url': doc_info['source_url'],
                'status': 'triggered',
                'stage': 'trigger',
                'lambda_response_status': response['StatusCode'],
                'processing_started': datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            error_msg = f"Error triggering processing: {str(e)}"
            logger.error(f"[{thread_name}] {error_msg}")
            return {
                'doc_id': doc_id,
                'status': 'failed',
                'error': error_msg,
                'stage': 'trigger'
            }
    
    def monitor_document_processing(self, doc_info: Dict, initial_result: Dict) -> Dict:
        """
        Monitor processing progress for a document
        
        Args:
            doc_info: Document information dictionary
            initial_result: Initial processing result
            
        Returns:
            Final processing result
        """
        thread_name = threading.current_thread().name
        doc_id = doc_info['proper_doc_id']
        
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
        """
        Process a single document in a thread (trigger + monitor)
        
        Args:
            doc_info: Document information dictionary
            
        Returns:
            Complete processing result
        """
        # Trigger processing
        initial_result = self.trigger_document_processing(doc_info)
        
        if initial_result['status'] == 'failed':
            return initial_result
        
        # Monitor processing
        final_result = self.monitor_document_processing(doc_info, initial_result)
        
        # Store result thread-safely
        with self.results_lock:
            self.test_results.append(final_result)
        
        return final_result
    
    def run_parallel_test(self, num_documents: int = 10) -> Dict:
        """
        Run parallel processing test with multiple documents
        
        Args:
            num_documents: Number of documents to process in parallel
            
        Returns:
            Test summary results
        """
        logger.info(f"🧪 STARTING PARALLEL PIPELINE TEST")
        logger.info(f"📊 Target: {num_documents} documents in parallel")
        logger.info("=" * 60)
        
        # Get available documents
        available_docs = self.get_available_documents(limit=num_documents * 2)  # Get extra in case some fail
        
        if len(available_docs) < num_documents:
            logger.warning(f"Only {len(available_docs)} documents available, adjusting target")
            num_documents = len(available_docs)
        
        if num_documents == 0:
            logger.error("No documents available for testing")
            return {'status': 'failed', 'error': 'No documents available'}
        
        # Select documents for testing
        test_documents = available_docs[:num_documents]
        
        logger.info(f"📄 Selected {len(test_documents)} documents for testing:")
        for i, doc in enumerate(test_documents, 1):
            logger.info(f"  {i}. {doc['proper_doc_id']} ({doc['filename']})")
            logger.info(f"     Source: {doc['source_url']}")
        
        # Start parallel processing
        start_time = datetime.utcnow()
        logger.info(f"\n🚀 Starting parallel processing at {start_time.isoformat()}Z")
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=num_documents, thread_name_prefix="DocProcessor") as executor:
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
                        'doc_id': doc['proper_doc_id'],
                        'status': 'failed',
                        'error': str(e),
                        'stage': 'thread_execution'
                    }
                    completed_results.append(error_result)
                    logger.error(f"❌ Thread execution failed: {doc['proper_doc_id']} - {e}")
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()
        
        # Compile summary results
        successful = sum(1 for r in completed_results if r['status'] == 'success')
        partial = sum(1 for r in completed_results if r['status'] == 'partial')
        failed = sum(1 for r in completed_results if r['status'] == 'failed')
        
        summary = {
            'test_type': 'parallel_pipeline_test',
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
        logger.info("🎉 PARALLEL PIPELINE TEST COMPLETE")
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
        test_manager = PipelineTestManager()
        
        # Run parallel test with 10 documents
        results = test_manager.run_parallel_test(num_documents=10)
        
        # Save results to file
        results_filename = f"parallel_pipeline_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📄 Results saved to: {results_filename}")
        
        # Print final status
        if results['success_rate'] >= 80:
            logger.info("🎉 TEST PASSED: Pipeline is working well!")
        elif results['success_rate'] >= 50:
            logger.info("⚠️  TEST PARTIAL: Pipeline has some issues")
        else:
            logger.info("❌ TEST FAILED: Pipeline needs attention")
        
        return results
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'failed', 'error': str(e)}

if __name__ == "__main__":
    main()
