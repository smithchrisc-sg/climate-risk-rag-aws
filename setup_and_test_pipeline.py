#!/usr/bin/env python3
"""
Parameterized Pipeline Setup and Test
Comprehensive script for setting up and testing the end-state pipeline with configurable parameters
"""

import boto3
import json
import sqlite3
import os
import sys
import argparse
import time
import threading
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import re

# Add layers to path for shared utilities
sys.path.append('layers/app-source')
sys.path.append('layers/app-source/utils')

try:
    from utils.DocumentIDManager import DocumentIDManager
except ImportError as e:
    print(f"Warning: Could not import DocumentIDManager: {e}")
    DocumentIDManager = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ParameterizedPipelineManager:
    """Manages parameterized pipeline setup and testing"""
    
    def __init__(self):
        # AWS clients
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.textract_client = boto3.client('textract', region_name='us-east-1')
        
        # Bucket configuration
        self.existing_bucket = "solve-global-kr-documents-861276078413-us-east-1"
        self.source_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
        self.text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        self.chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        self.sqlite_db_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        
        # Initialize DocumentIDManager
        if DocumentIDManager:
            try:
                self.doc_id_manager = DocumentIDManager()
                logger.info("DocumentIDManager initialized successfully")
            except Exception as e:
                logger.warning(f"DocumentIDManager initialization failed: {e}")
                self.doc_id_manager = None
        else:
            self.doc_id_manager = None
        
        # Thread-safe results storage
        self.results_lock = threading.Lock()
        self.test_results = []
        
        # Document type patterns for filtering
        self.document_type_patterns = {
            "report": ["report", "assessment", "evaluation", "study"],
            "policy": ["policy", "strategy", "framework", "guideline"],
            "research": ["research", "analysis", "working", "paper"],
            "project": ["project", "implementation", "completion", "icr"],
            "financial": ["financial", "economic", "budget", "cost"],
            "technical": ["technical", "manual", "specification", "guide"]
        }
    
    def estimate_pages_from_size(self, size_mb: float) -> int:
        """Estimate number of pages based on file size (rough approximation)"""
        # Rough estimate: 1 page ≈ 50-100KB for text-heavy PDFs
        # Using 75KB average per page
        estimated_pages = int((size_mb * 1024) / 75)
        return max(1, estimated_pages)  # At least 1 page
    
    def check_textract_limits(self, documents: List[Dict], max_parallel: int = 10) -> Tuple[bool, str]:
        """Check if document processing would exceed Textract limits"""
        total_pages = sum(self.estimate_pages_from_size(doc['size_mb']) for doc in documents)
        
        # Check total pages limit
        if total_pages > 100:
            return False, f"Total estimated pages ({total_pages}) exceeds recommended limit of 100. This could be expensive and slow."
        
        # Check parallel processing limit
        if len(documents) > max_parallel:
            return False, f"Number of documents ({len(documents)}) exceeds Textract parallel limit of {max_parallel}."
        
        # Check individual document size (Textract has 500MB limit per document)
        large_docs = [doc for doc in documents if doc['size_mb'] > 400]
        if large_docs:
            return False, f"Found {len(large_docs)} documents larger than 400MB, which may exceed Textract limits."
        
        return True, f"Processing {len(documents)} documents (~{total_pages} pages) is within safe limits."
    
    def get_available_documents(self, limit: int = 100) -> List[Dict]:
        """Get available documents from existing bucket with enhanced metadata"""
        try:
            logger.info(f"Fetching documents from existing bucket: {self.existing_bucket}")
            
            # List documents in existing bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.existing_bucket,
                Prefix="documents/",
                MaxKeys=limit * 2  # Get extra to allow for filtering
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in existing bucket")
                return []
            
            documents = []
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    filename = os.path.basename(key)
                    doc_id_from_filename = filename.replace('.pdf', '')
                    
                    # Get object metadata for size filtering
                    try:
                        head_response = self.s3_client.head_object(
                            Bucket=self.existing_bucket,
                            Key=key
                        )
                        content_length = head_response.get('ContentLength', 0)
                    except:
                        content_length = obj.get('Size', 0)
                    
                    size_mb = round(content_length / (1024 * 1024), 2)
                    estimated_pages = self.estimate_pages_from_size(size_mb)
                    
                    documents.append({
                        'key': key,
                        'filename': filename,
                        'doc_id_from_filename': doc_id_from_filename,
                        'size': content_length,
                        'size_mb': size_mb,
                        'estimated_pages': estimated_pages,
                        'last_modified': obj['LastModified']
                    })
            
            logger.info(f"Found {len(documents)} PDF documents in existing bucket")
            return documents
            
        except Exception as e:
            logger.error(f"Error getting available documents: {e}")
            return []
    
    def filter_documents_by_criteria(self, documents: List[Dict], 
                                   num_documents: int = 10,
                                   min_size_mb: float = 0.5, 
                                   max_size_mb: float = 50.0,
                                   language: str = "english",
                                   document_types: List[str] = None,
                                   target_avg_pages: int = 20) -> List[Dict]:
        """Filter documents by comprehensive criteria"""
        try:
            logger.info(f"Filtering documents with criteria:")
            logger.info(f"  - Count: {num_documents}")
            logger.info(f"  - Size: {min_size_mb}-{max_size_mb} MB")
            logger.info(f"  - Language: {language}")
            logger.info(f"  - Document types: {document_types or 'any'}")
            logger.info(f"  - Target avg pages: {target_avg_pages}")
            
            # Filter by size
            filtered = [
                doc for doc in documents 
                if min_size_mb <= doc['size_mb'] <= max_size_mb
            ]
            logger.info(f"After size filtering: {len(filtered)} documents")
            
            # Filter by document type if specified
            if document_types:
                type_filtered = []
                for doc in filtered:
                    filename_lower = doc['filename'].lower()
                    for doc_type in document_types:
                        if doc_type in self.document_type_patterns:
                            patterns = self.document_type_patterns[doc_type]
                            if any(pattern in filename_lower for pattern in patterns):
                                type_filtered.append(doc)
                                break
                filtered = type_filtered
                logger.info(f"After document type filtering: {len(filtered)} documents")
            
            # Sort by how close they are to target page count
            filtered.sort(key=lambda x: abs(x['estimated_pages'] - target_avg_pages))
            
            # Limit results
            filtered = filtered[:num_documents]
            
            # Calculate statistics
            if filtered:
                total_pages = sum(doc['estimated_pages'] for doc in filtered)
                avg_pages = total_pages / len(filtered)
                avg_size = sum(doc['size_mb'] for doc in filtered) / len(filtered)
                
                logger.info(f"Selected {len(filtered)} documents:")
                logger.info(f"  - Total estimated pages: {total_pages}")
                logger.info(f"  - Average pages per doc: {avg_pages:.1f}")
                logger.info(f"  - Average size: {avg_size:.1f} MB")
                
                for i, doc in enumerate(filtered, 1):
                    logger.info(f"  {i}. {doc['filename']}: {doc['size_mb']} MB (~{doc['estimated_pages']} pages)")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return documents[:num_documents]  # Fallback to first N documents
    
    def get_source_url_from_sqlite(self, doc_id_from_filename: str) -> Optional[str]:
        """Get source URL from SQLite database"""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT url FROM documents WHERE doc_id = ?",
                (doc_id_from_filename,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                logger.warning(f"No source URL found for doc_id: {doc_id_from_filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying SQLite for {doc_id_from_filename}: {e}")
            return None
    
    def prepare_source_document(self, doc_info: Dict) -> Optional[Dict]:
        """Prepare a single document for the source bucket"""
        try:
            doc_id_from_filename = doc_info['doc_id_from_filename']
            
            # Get source URL from SQLite
            source_url = self.get_source_url_from_sqlite(doc_id_from_filename)
            if not source_url:
                logger.error(f"Cannot prepare document without source URL: {doc_id_from_filename}")
                return None
            
            # Get proper doc_id from DocumentIDManager
            if self.doc_id_manager:
                try:
                    proper_doc_id = self.doc_id_manager.get_or_create_id(source_url)
                    logger.info(f"Generated proper doc_id: {proper_doc_id} for URL: {source_url}")
                except Exception as e:
                    logger.error(f"DocumentIDManager failed for {source_url}: {e}")
                    return None
            else:
                logger.error("DocumentIDManager not available")
                return None
            
            # Copy document to source bucket with proper doc_id
            source_key = f"{proper_doc_id}.pdf"
            
            try:
                # Copy object
                copy_source = {
                    'Bucket': self.existing_bucket,
                    'Key': doc_info['key']
                }
                
                self.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.source_bucket,
                    Key=source_key,
                    MetadataDirective='REPLACE',
                    Metadata={
                        'source-url': source_url,
                        'original-filename': doc_info['filename'],
                        'prepared-at': datetime.utcnow().isoformat(),
                        'doc-id': proper_doc_id,
                        'estimated-pages': str(doc_info['estimated_pages']),
                        'size-mb': str(doc_info['size_mb'])
                    }
                )
                
                logger.info(f"Copied document to source bucket: {source_key}")
                
                return {
                    'original_doc_id': doc_id_from_filename,
                    'proper_doc_id': proper_doc_id,
                    'source_url': source_url,
                    'original_filename': doc_info['filename'],
                    'source_key': source_key,
                    'size_mb': doc_info['size_mb'],
                    'estimated_pages': doc_info['estimated_pages'],
                    'prepared_at': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error copying document to source bucket: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error preparing document {doc_info.get('filename', 'unknown')}: {e}")
            return None
    
    def setup_documents(self, num_documents: int = 10, 
                       min_size_mb: float = 0.5, 
                       max_size_mb: float = 20.0,
                       language: str = "english",
                       document_types: List[str] = None,
                       target_avg_pages: int = 20,
                       force: bool = False) -> List[Dict]:
        """Set up test documents in source bucket with comprehensive parameters"""
        try:
            logger.info(f"🔧 SETTING UP TEST DOCUMENTS")
            logger.info("=" * 50)
            
            # Get available documents
            available_docs = self.get_available_documents(limit=100)
            if not available_docs:
                logger.error("No documents available")
                return []
            
            # Filter by criteria
            filtered_docs = self.filter_documents_by_criteria(
                available_docs, 
                num_documents=num_documents,
                min_size_mb=min_size_mb, 
                max_size_mb=max_size_mb,
                language=language,
                document_types=document_types,
                target_avg_pages=target_avg_pages
            )
            
            if not filtered_docs:
                logger.error("No documents match criteria")
                return []
            
            # Check Textract limits and get user confirmation if needed
            limits_ok, limits_msg = self.check_textract_limits(filtered_docs)
            logger.info(f"Textract limits check: {limits_msg}")
            
            if not limits_ok and not force:
                total_pages = sum(doc['estimated_pages'] for doc in filtered_docs)
                if total_pages > 100:
                    response = input(f"\n⚠️  WARNING: {limits_msg}\nThis could be expensive and slow. Continue anyway? (y/N): ")
                    if response.lower() != 'y':
                        logger.info("Operation cancelled by user")
                        return []
                else:
                    logger.error(f"Cannot proceed: {limits_msg}")
                    return []
            
            # Prepare each document
            logger.info(f"📄 Preparing {len(filtered_docs)} documents...")
            prepared_docs = []
            for i, doc_info in enumerate(filtered_docs, 1):
                logger.info(f"Preparing document {i}/{len(filtered_docs)}: {doc_info['filename']}")
                prepared = self.prepare_source_document(doc_info)
                if prepared:
                    prepared_docs.append(prepared)
                else:
                    logger.warning(f"Failed to prepare document: {doc_info['filename']}")
            
            logger.info(f"✅ Successfully prepared {len(prepared_docs)} documents")
            
            # Save preparation summary
            summary = {
                'prepared_at': datetime.utcnow().isoformat(),
                'source_bucket': self.source_bucket,
                'parameters': {
                    'num_documents': num_documents,
                    'min_size_mb': min_size_mb,
                    'max_size_mb': max_size_mb,
                    'language': language,
                    'document_types': document_types,
                    'target_avg_pages': target_avg_pages
                },
                'statistics': {
                    'documents_prepared': len(prepared_docs),
                    'total_estimated_pages': sum(doc['estimated_pages'] for doc in prepared_docs),
                    'average_pages': sum(doc['estimated_pages'] for doc in prepared_docs) / len(prepared_docs) if prepared_docs else 0,
                    'total_size_mb': sum(doc['size_mb'] for doc in prepared_docs),
                    'average_size_mb': sum(doc['size_mb'] for doc in prepared_docs) / len(prepared_docs) if prepared_docs else 0
                },
                'documents': prepared_docs
            }
            
            summary_file = f"pipeline_setup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"📄 Setup summary saved to: {summary_file}")
            
            return prepared_docs
            
        except Exception as e:
            logger.error(f"Error setting up test documents: {e}")
            return []
    
    def trigger_text_extraction(self, doc_info: Dict) -> Dict:
        """Trigger text extraction for a document"""
        thread_name = threading.current_thread().name
        doc_id = doc_info['proper_doc_id']
        
        logger.info(f"[{thread_name}] Starting text extraction for document: {doc_id}")
        
        try:
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
                            "key": doc_info['source_key'],
                            "size": int(doc_info['size_mb'] * 1024 * 1024)
                        }
                    },
                    "customMetadata": {
                        "docId": doc_id,
                        "sourceUrl": doc_info.get('source_url'),
                        "estimatedPages": str(doc_info['estimated_pages']),
                        "parameterizedTest": True
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
                'estimated_pages': doc_info['estimated_pages'],
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
    
    def run_pipeline_test(self, prepared_docs: List[Dict], 
                         monitor_duration_minutes: int = 10) -> Dict:
        """Run the complete pipeline test with prepared documents"""
        if not prepared_docs:
            logger.error("No prepared documents to test")
            return {'status': 'failed', 'error': 'No prepared documents'}
        
        logger.info(f"🧪 STARTING PARAMETERIZED PIPELINE TEST")
        logger.info(f"📊 Documents: {len(prepared_docs)}")
        logger.info(f"📄 Total estimated pages: {sum(doc['estimated_pages'] for doc in prepared_docs)}")
        logger.info(f"⏱️  Monitor duration: {monitor_duration_minutes} minutes")
        logger.info("=" * 60)
        
        # Start processing
        start_time = datetime.utcnow()
        logger.info(f"🚀 Starting pipeline test at {start_time.isoformat()}Z")
        
        # Trigger all documents in parallel (respecting Textract limits)
        with ThreadPoolExecutor(max_workers=min(len(prepared_docs), 10), thread_name_prefix="PipelineTest") as executor:
            # Submit all tasks
            future_to_doc = {
                executor.submit(self.trigger_text_extraction, doc): doc 
                for doc in prepared_docs
            }
            
            # Collect trigger results
            trigger_results = []
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    trigger_results.append(result)
                    logger.info(f"✅ Triggered: {result['doc_id']} - {result['status']}")
                except Exception as e:
                    error_result = {
                        'doc_id': doc['proper_doc_id'],
                        'status': 'failed',
                        'error': str(e),
                        'stage': 'trigger'
                    }
                    trigger_results.append(error_result)
                    logger.error(f"❌ Trigger failed: {doc['proper_doc_id']} - {e}")
        
        # Monitor processing for specified duration
        logger.info(f"⏱️  Monitoring processing for {monitor_duration_minutes} minutes...")
        time.sleep(monitor_duration_minutes * 60)
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()
        
        # Compile results
        successful_triggers = sum(1 for r in trigger_results if r['status'] == 'triggered')
        failed_triggers = sum(1 for r in trigger_results if r['status'] == 'failed')
        
        summary = {
            'test_type': 'parameterized_pipeline_test',
            'source_bucket': self.source_bucket,
            'documents_tested': len(prepared_docs),
            'successful_triggers': successful_triggers,
            'failed_triggers': failed_triggers,
            'trigger_success_rate': (successful_triggers / len(trigger_results)) * 100 if trigger_results else 0,
            'total_estimated_pages': sum(doc['estimated_pages'] for doc in prepared_docs),
            'monitor_duration_minutes': monitor_duration_minutes,
            'total_duration_seconds': total_duration,
            'start_time': start_time.isoformat() + "Z",
            'end_time': end_time.isoformat() + "Z",
            'trigger_results': trigger_results,
            'prepared_documents': prepared_docs
        }
        
        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 PARAMETERIZED PIPELINE TEST COMPLETE")
        logger.info("=" * 60)
        logger.info(f"📊 Documents Tested: {summary['documents_tested']}")
        logger.info(f"✅ Successful Triggers: {successful_triggers}")
        logger.info(f"❌ Failed Triggers: {failed_triggers}")
        logger.info(f"📈 Trigger Success Rate: {summary['trigger_success_rate']:.1f}%")
        logger.info(f"📄 Total Estimated Pages: {summary['total_estimated_pages']}")
        logger.info(f"⏱️  Total Duration: {total_duration:.1f} seconds")
        
        return summary

def main():
    """Main execution with argument parsing"""
    parser = argparse.ArgumentParser(description='Parameterized Pipeline Setup and Test')
    
    # Document selection parameters
    parser.add_argument('--num-documents', type=int, default=5,
                       help='Number of documents to process (default: 5)')
    parser.add_argument('--min-size-mb', type=float, default=1.0,
                       help='Minimum document size in MB (default: 1.0)')
    parser.add_argument('--max-size-mb', type=float, default=15.0,
                       help='Maximum document size in MB (default: 15.0)')
    parser.add_argument('--language', type=str, default='english',
                       help='Document language (default: english)')
    parser.add_argument('--document-types', nargs='+', 
                       choices=['report', 'policy', 'research', 'project', 'financial', 'technical'],
                       help='Document types to include')
    parser.add_argument('--target-avg-pages', type=int, default=20,
                       help='Target average pages per document (default: 20)')
    
    # Test parameters
    parser.add_argument('--monitor-duration', type=int, default=10,
                       help='How long to monitor processing in minutes (default: 10)')
    parser.add_argument('--force', action='store_true',
                       help='Skip safety confirmations')
    parser.add_argument('--setup-only', action='store_true',
                       help='Only setup documents, do not run test')
    parser.add_argument('--test-only', action='store_true',
                       help='Only run test on existing prepared documents')
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline manager
        pipeline_manager = ParameterizedPipelineManager()
        
        # Setup phase
        if not args.test_only:
            logger.info(f"🔧 Setting up {args.num_documents} documents...")
            prepared_docs = pipeline_manager.setup_documents(
                num_documents=args.num_documents,
                min_size_mb=args.min_size_mb,
                max_size_mb=args.max_size_mb,
                language=args.language,
                document_types=args.document_types,
                target_avg_pages=args.target_avg_pages,
                force=args.force
            )
            
            if not prepared_docs:
                logger.error("No documents were prepared")
                return False
        else:
            # Get existing prepared documents from source bucket
            logger.info("📄 Using existing prepared documents...")
            # Implementation would list documents from source bucket
            prepared_docs = []  # Placeholder
        
        # Test phase
        if not args.setup_only and prepared_docs:
            logger.info(f"🧪 Running pipeline test...")
            results = pipeline_manager.run_pipeline_test(
                prepared_docs,
                monitor_duration_minutes=args.monitor_duration
            )
            
            # Save results
            results_filename = f"parameterized_pipeline_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"📄 Results saved to: {results_filename}")
            
            # Final status
            if results['trigger_success_rate'] >= 90:
                logger.info("🎉 TEST PASSED: Pipeline triggers working well!")
            elif results['trigger_success_rate'] >= 70:
                logger.info("⚠️  TEST PARTIAL: Some pipeline issues detected")
            else:
                logger.info("❌ TEST FAILED: Pipeline needs attention")
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
