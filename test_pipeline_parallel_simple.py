#!/usr/bin/env python3
"""
Simplified Parallel Pipeline Test with Source URL Integration
Multi-threaded test of 10 documents using proper source URLs from POC database
"""

import boto3
import json
import sqlite3
import threading
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import os
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplePipelineTest:
    """Simplified pipeline test with source URL integration"""
    
    def __init__(self):
        # AWS clients
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Configuration
        self.documents_bucket = "solve-global-kr-documents-861276078413-us-east-1"
        self.sqlite_db_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        
        # Thread-safe results storage
        self.results_lock = threading.Lock()
        self.test_results = []
    
    def generate_document_id_from_url(self, url: str) -> str:
        """
        Generate document ID from URL (simplified DocumentIDManager logic)
        
        Args:
            url: Source URL
            
        Returns:
            Generated document ID
        """
        # Create hash from URL
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        
        # Take first 8 and last 8 characters for readability
        doc_id = f"{url_hash[:8]}_{url_hash[-8:]}"
        
        return doc_id
    
    def get_test_documents(self, limit: int = 15) -> List[Dict]:
        """
        Get documents for testing from S3 and SQLite database
        
        Args:
            limit: Maximum number of documents to retrieve
            
        Returns:
            List of document info dictionaries
        """
        try:
            logger.info(f"Fetching documents from S3 bucket: {self.documents_bucket}")
            
            # List documents in S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.documents_bucket,
                Prefix="documents/",
                MaxKeys=50
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in S3 bucket")
                return []
            
            # Connect to SQLite database
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            logger.info(f"Connected to SQLite database")
            
            matched_documents = []
            
            for obj in response['Contents']:
                if len(matched_documents) >= limit:
                    break
                    
                key = obj['Key']
                if not key.endswith('.pdf'):
                    continue
                
                filename = os.path.basename(key)
                doc_id_from_filename = filename.replace('.pdf', '')
                
                try:
                    # Query database for source URL
                    cursor.execute(
                        "SELECT url, original_filename FROM documents WHERE doc_id = ?",
                        (doc_id_from_filename,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        source_url, original_filename = result
                        
                        # Generate proper document ID from URL
                        proper_doc_id = self.generate_document_id_from_url(source_url)
                        
                        doc_info = {
                            'key': key,
                            'filename': filename,
                            'doc_id_from_filename': doc_id_from_filename,
                            'source_url': source_url,
                            'original_filename': original_filename,
                            'proper_doc_id': proper_doc_id,
                            'size': obj['Size']
                        }
                        matched_documents.append(doc_info)
                        
                        logger.debug(f"Matched: {doc_id_from_filename} -> {source_url}")
                    else:
                        logger.debug(f"No database entry for: {doc_id_from_filename}")
                        
                except Exception as e:
                    logger.error(f"Error querying database for {doc_id_from_filename}: {e}")
                    continue
            
            conn.close()
            logger.info(f"Found {len(matched_documents)} documents with source URLs")
            
            return matched_documents
            
        except Exception as e:
            logger.error(f"Error getting test documents: {e}")
            return []
    
    def trigger_document_processing(self, doc_info: Dict) -> Dict:
        """
        Trigger processing for a single document
        
        Args:
            doc_info: Document information
            
        Returns:
            Processing result
        """
        thread_name = threading.current_thread().name
        doc_id = doc_info['proper_doc_id']
        
        logger.info(f"[{thread_name}] Processing document: {doc_id}")
        logger.info(f"[{thread_name}] Source URL: {doc_info['source_url']}")
        
        try:
            # Create S3 event payload for text extractor
            payload = {
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
                    # Include metadata for downstream processing
                    "userMetadata": {
                        "sourceUrl": doc_info['source_url'],
                        "properDocId": doc_info['proper_doc_id'],
                        "originalFilename": doc_info['original_filename'],
                        "testRun": "true"
                    }
                }]
            }
            
            # Invoke text extractor initiator
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',
                Payload=json.dumps(payload)
            )
            
            result = {
                'doc_id': doc_id,
                'filename': doc_info['filename'],
                'source_url': doc_info['source_url'],
                'proper_doc_id': doc_info['proper_doc_id'],
                'lambda_status': response['StatusCode'],
                'triggered_at': datetime.utcnow().isoformat() + "Z"
            }
            
            if response['StatusCode'] == 202:
                result['status'] = 'triggered_successfully'
                logger.info(f"[{thread_name}] ✅ Successfully triggered: {doc_id}")
            else:
                result['status'] = 'trigger_failed'
                result['error'] = f"Lambda returned status {response['StatusCode']}"
                logger.error(f"[{thread_name}] ❌ Trigger failed: {doc_id}")
            
            return result
            
        except Exception as e:
            error_result = {
                'doc_id': doc_id,
                'filename': doc_info['filename'],
                'source_url': doc_info['source_url'],
                'status': 'error',
                'error': str(e),
                'triggered_at': datetime.utcnow().isoformat() + "Z"
            }
            logger.error(f"[{thread_name}] ❌ Error processing {doc_id}: {e}")
            return error_result
    
    def process_document_thread(self, doc_info: Dict) -> Dict:
        """
        Process document in thread and store result
        
        Args:
            doc_info: Document information
            
        Returns:
            Processing result
        """
        result = self.trigger_document_processing(doc_info)
        
        # Store result thread-safely
        with self.results_lock:
            self.test_results.append(result)
        
        return result
    
    def run_parallel_test(self, num_documents: int = 10) -> Dict:
        """
        Run parallel processing test
        
        Args:
            num_documents: Number of documents to process
            
        Returns:
            Test summary
        """
        logger.info("🧪 PARALLEL PIPELINE TEST WITH SOURCE URLS")
        logger.info("=" * 60)
        logger.info(f"📊 Target: {num_documents} documents in parallel")
        
        # Get test documents
        available_docs = self.get_test_documents(limit=num_documents + 5)
        
        if len(available_docs) < num_documents:
            logger.warning(f"Only {len(available_docs)} documents available")
            num_documents = len(available_docs)
        
        if num_documents == 0:
            return {'status': 'failed', 'error': 'No documents available'}
        
        test_documents = available_docs[:num_documents]
        
        logger.info(f"\n📄 Selected {len(test_documents)} documents:")
        for i, doc in enumerate(test_documents, 1):
            logger.info(f"  {i}. {doc['filename']}")
            logger.info(f"     Doc ID: {doc['proper_doc_id']}")
            logger.info(f"     Source: {doc['source_url'][:80]}...")
        
        # Start parallel processing
        start_time = datetime.utcnow()
        logger.info(f"\n🚀 Starting parallel processing...")
        
        # Use ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_documents, thread_name_prefix="Doc") as executor:
            # Submit all tasks
            futures = [
                executor.submit(self.process_document_thread, doc) 
                for doc in test_documents
            ]
            
            # Wait for completion
            completed_results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    completed_results.append(result)
                except Exception as e:
                    logger.error(f"Thread execution error: {e}")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Compile results
        successful = sum(1 for r in completed_results if r['status'] == 'triggered_successfully')
        failed = len(completed_results) - successful
        
        summary = {
            'test_type': 'parallel_pipeline_with_source_urls',
            'documents_processed': len(completed_results),
            'successful_triggers': successful,
            'failed_triggers': failed,
            'success_rate': (successful / len(completed_results)) * 100 if completed_results else 0,
            'duration_seconds': duration,
            'start_time': start_time.isoformat() + "Z",
            'end_time': end_time.isoformat() + "Z",
            'results': completed_results
        }
        
        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 PARALLEL TEST COMPLETE")
        logger.info("=" * 60)
        logger.info(f"📊 Documents: {summary['documents_processed']}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        
        return summary

def main():
    """Main execution"""
    try:
        test = SimplePipelineTest()
        results = test.run_parallel_test(num_documents=10)
        
        # Save results
        filename = f"parallel_test_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"📄 Results saved to: {filename}")
        
        # Final status
        if results['success_rate'] >= 90:
            logger.info("🎉 TEST PASSED: Excellent pipeline performance!")
        elif results['success_rate'] >= 70:
            logger.info("✅ TEST GOOD: Pipeline working well")
        elif results['success_rate'] >= 50:
            logger.info("⚠️  TEST PARTIAL: Some issues detected")
        else:
            logger.info("❌ TEST FAILED: Pipeline needs attention")
        
        return results
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

if __name__ == "__main__":
    main()
