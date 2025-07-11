#!/usr/bin/env python3
"""
Pipeline Test Lambda Function
Runs parameterized pipeline tests from within the VPC with database access
"""

import json
import boto3
import sqlite3
import os
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import re

# Import from Lambda layers
try:
    from utils.DocumentIDManager import DocumentIDManager
except ImportError:
    # Fallback for testing
    DocumentIDManager = None

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class PipelineTestLambda:
    """Simplified Lambda-based pipeline test manager (no SQLite dependency)"""
    
    def __init__(self):
        # AWS clients
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        
        # Environment configuration
        self.source_bucket = os.environ.get('SOURCE_DOCUMENTS_BUCKET', 'solve-global-kr-dl-source-documents-861276078413-us-east-1')
        
        # Initialize DocumentIDManager with DATABASE_URL from environment
        if DocumentIDManager:
            try:
                self.doc_id_manager = DocumentIDManager()
                logger.info("DocumentIDManager initialized successfully")
            except Exception as e:
                logger.warning(f"DocumentIDManager initialization failed: {e}")
                self.doc_id_manager = None
        else:
            self.doc_id_manager = None
    
    def download_sqlite_db(self):
        """Download SQLite database from S3 to Lambda temp storage"""
        try:
            sqlite_s3_key = os.environ.get('SQLITE_S3_KEY', 'database/corpus_document_ids.db')
            sqlite_s3_bucket = os.environ.get('SQLITE_S3_BUCKET', 'solve-global-kr-cache-861276078413-us-east-1')
            
            logger.info(f"Downloading SQLite database from s3://{sqlite_s3_bucket}/{sqlite_s3_key}")
            
            self.s3_client.download_file(
                sqlite_s3_bucket,
                sqlite_s3_key,
                self.sqlite_db_path
            )
            
            logger.info(f"SQLite database downloaded to {self.sqlite_db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download SQLite database: {e}")
            return False
    
    def estimate_pages_from_size(self, size_mb: float) -> int:
        """Estimate number of pages based on file size"""
        estimated_pages = int((size_mb * 1024) / 75)  # ~75KB per page
        return max(1, estimated_pages)
    
    def check_textract_limits(self, documents: List[Dict], max_parallel: int = 10) -> Tuple[bool, str]:
        """Check if document processing would exceed Textract limits"""
        total_pages = sum(self.estimate_pages_from_size(doc['size_mb']) for doc in documents)
        
        if total_pages > 100:
            return False, f"Total estimated pages ({total_pages}) exceeds recommended limit of 100."
        
        if len(documents) > max_parallel:
            return False, f"Number of documents ({len(documents)}) exceeds Textract parallel limit of {max_parallel}."
        
        large_docs = [doc for doc in documents if doc['size_mb'] > 400]
        if large_docs:
            return False, f"Found {len(large_docs)} documents larger than 400MB."
        
        return True, f"Processing {len(documents)} documents (~{total_pages} pages) is within safe limits."
    
    def get_available_documents(self, limit: int = 100) -> List[Dict]:
        """Get available documents from existing bucket"""
        try:
            logger.info(f"Fetching documents from existing bucket: {self.existing_bucket}")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.existing_bucket,
                Prefix="documents/",
                MaxKeys=limit * 2
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
                    
                    size_mb = round(obj['Size'] / (1024 * 1024), 2)
                    estimated_pages = self.estimate_pages_from_size(size_mb)
                    
                    documents.append({
                        'key': key,
                        'filename': filename,
                        'doc_id_from_filename': doc_id_from_filename,
                        'size': obj['Size'],
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
            logger.info(f"Filtering documents: {num_documents} docs, {min_size_mb}-{max_size_mb} MB, types: {document_types}")
            
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
            
            if filtered:
                total_pages = sum(doc['estimated_pages'] for doc in filtered)
                avg_pages = total_pages / len(filtered)
                
                logger.info(f"Selected {len(filtered)} documents:")
                logger.info(f"  - Total estimated pages: {total_pages}")
                logger.info(f"  - Average pages per doc: {avg_pages:.1f}")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return documents[:num_documents]
    
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
        """Prepare a single document for the source bucket (with fallback for testing)"""
        try:
            # Source URL is already provided by the client
            source_url = doc_info.get('source_url')
            if not source_url:
                logger.error(f"No source URL provided for document: {doc_info.get('filename', 'unknown')}")
                return None
            
            # Try to get proper doc_id from DocumentIDManager, fallback to hash-based ID
            if self.doc_id_manager:
                try:
                    proper_doc_id = self.doc_id_manager.get_or_create_id(source_url)
                    logger.info(f"Generated proper doc_id: {proper_doc_id} for URL: {source_url}")
                except Exception as e:
                    logger.error(f"DocumentIDManager failed for {source_url}: {e}")
                    # Fallback to simple hash-based ID
                    import hashlib
                    proper_doc_id = hashlib.sha256(source_url.encode()).hexdigest()[:16]
                    logger.info(f"Using fallback doc_id: {proper_doc_id}")
            else:
                # Fallback to simple hash-based ID for testing
                import hashlib
                proper_doc_id = hashlib.sha256(source_url.encode()).hexdigest()[:16]
                logger.info(f"DocumentIDManager not available, using fallback doc_id: {proper_doc_id}")
            
            # Copy document to source bucket with proper doc_id
            source_key = f"{proper_doc_id}.pdf"
            
            try:
                # Copy object from existing bucket to source bucket
                existing_bucket = "solve-global-kr-documents-861276078413-us-east-1"
                copy_source = {
                    'Bucket': existing_bucket,
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
                        'size-mb': str(doc_info['size_mb']),
                        'test-mode': 'true'
                    }
                )
                
                logger.info(f"Copied document to source bucket: {source_key}")
                
                return {
                    'original_doc_id': doc_info['doc_id_from_filename'],
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
    
    def trigger_text_extraction(self, doc_info: Dict) -> Dict:
        """Trigger text extraction for a document"""
        # Handle both prepared documents (with proper_doc_id) and selected documents
        doc_id = doc_info.get('proper_doc_id') or doc_info.get('doc_id_from_filename')
        source_key = doc_info.get('source_key') or f"{doc_id}.pdf"
        
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
                            "key": source_key,
                            "size": int(doc_info['size_mb'] * 1024 * 1024)
                        }
                    },
                    "customMetadata": {
                        "docId": doc_id,
                        "sourceUrl": doc_info.get('source_url'),
                        "estimatedPages": str(doc_info['estimated_pages']),
                        "lambdaTest": True
                    }
                }]
            }
            
            # Trigger text extractor initiator
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='Event',
                Payload=json.dumps(s3_event_payload)
            )
            
            if response['StatusCode'] != 202:
                error_msg = f"Failed to trigger text extraction: {response['StatusCode']}"
                logger.error(error_msg)
                return {
                    'doc_id': doc_id,
                    'status': 'failed',
                    'error': error_msg,
                    'stage': 'trigger'
                }
            
            logger.info(f"Successfully triggered text extraction for {doc_id}")
            
            return {
                'doc_id': doc_id,
                'source_url': doc_info.get('source_url'),
                'original_filename': doc_info.get('original_filename') or doc_info.get('filename'),
                'estimated_pages': doc_info['estimated_pages'],
                'status': 'triggered',
                'stage': 'trigger',
                'lambda_response_status': response['StatusCode'],
                'processing_started': datetime.utcnow().isoformat() + "Z",
                'size_mb': doc_info['size_mb']
            }
            
        except Exception as e:
            error_msg = f"Error triggering text extraction: {str(e)}"
            logger.error(error_msg)
            return {
                'doc_id': doc_id,
                'status': 'failed',
                'error': error_msg,
                'stage': 'trigger'
            }

def lambda_handler(event, context):
    """Lambda handler for parameterized pipeline testing with pre-selected documents"""
    try:
        logger.info(f"Pipeline test Lambda invoked with event keys: {list(event.keys())}")
        
        # Parse parameters from event
        action = event.get('action', 'setup_and_test')
        selected_documents = event.get('selected_documents', [])
        
        if not selected_documents:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'failed',
                    'error': 'No documents provided in request'
                })
            }
        
        logger.info(f"Processing {len(selected_documents)} pre-selected documents")
        
        # Initialize test manager
        test_manager = PipelineTestLambda()
        
        if action == 'setup_only' or action == 'setup_and_test':
            # Setup phase - prepare documents
            logger.info(f"Preparing {len(selected_documents)} documents...")
            
            prepared_docs = []
            for doc_info in selected_documents:
                prepared = test_manager.prepare_source_document(doc_info)
                if prepared:
                    prepared_docs.append(prepared)
            
            logger.info(f"Successfully prepared {len(prepared_docs)} documents")
            
            if action == 'setup_only':
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'action': 'setup_only',
                        'documents_prepared': len(prepared_docs),
                        'prepared_documents': prepared_docs,
                        'statistics': {
                            'total_estimated_pages': sum(doc['estimated_pages'] for doc in prepared_docs),
                            'average_pages': sum(doc['estimated_pages'] for doc in prepared_docs) / len(prepared_docs) if prepared_docs else 0,
                            'total_size_mb': sum(doc['size_mb'] for doc in prepared_docs),
                            'average_size_mb': sum(doc['size_mb'] for doc in prepared_docs) / len(prepared_docs) if prepared_docs else 0
                        }
                    }, default=str)
                }
        
        if action == 'test_only' or action == 'setup_and_test':
            # Test phase - trigger processing
            if action == 'setup_and_test':
                test_docs = prepared_docs
            else:
                # For test_only, use the selected documents directly
                test_docs = selected_documents
            
            if not test_docs:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'status': 'failed',
                        'error': 'No documents to test'
                    })
                }
            
            logger.info(f"Triggering processing for {len(test_docs)} documents...")
            
            # Trigger all documents
            trigger_results = []
            for doc_info in test_docs:
                result = test_manager.trigger_text_extraction(doc_info)
                trigger_results.append(result)
            
            # Compile results
            successful_triggers = sum(1 for r in trigger_results if r['status'] == 'triggered')
            failed_triggers = sum(1 for r in trigger_results if r['status'] == 'failed')
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'action': action,
                    'documents_tested': len(test_docs),
                    'successful_triggers': successful_triggers,
                    'failed_triggers': failed_triggers,
                    'trigger_success_rate': (successful_triggers / len(trigger_results)) * 100 if trigger_results else 0,
                    'total_estimated_pages': sum(doc['estimated_pages'] for doc in test_docs),
                    'trigger_results': trigger_results,
                    'test_documents': test_docs
                }, default=str)
            }
        
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'failed',
                'error': f'Unknown action: {action}'
            })
        }
        
    except Exception as e:
        logger.error(f"Pipeline test Lambda failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }
