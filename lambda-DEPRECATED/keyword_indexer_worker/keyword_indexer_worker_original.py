#!/usr/bin/env python3
"""
Enhanced Keyword Indexer Worker with Textract Structure Support
Updated to use DatabaseManager methods instead of direct SQL
"""

import os
import json
import logging
import sys
import boto3
from datetime import datetime
from typing import Dict, Optional, List, Any
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Import our structure-aware components
from structure_aware_processor import StructureAwareProcessor

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class EnhancedKeywordIndexerWorker:
    """
    Enhanced background worker with Textract structure analysis and DatabaseManager integration
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # OpenSearch configuration
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.index_name = os.environ.get('INDEX_NAME', 'climate-risk-keyword-index')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Database manager - updated to use proper DatabaseManager methods
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
        except ImportError:
            self.db_manager = None
            logger.warning("DatabaseManager not available - status updates disabled")
        
        # Initialize OpenSearch client
        self.opensearch_client = self._create_opensearch_client()
        
        # Initialize structure-aware processor
        self.structure_processor = StructureAwareProcessor()
        
        logger.info("Enhanced Keyword Indexer Worker initialized with DatabaseManager integration")
    
    def _create_opensearch_client(self):
        """Create OpenSearch client with AWS authentication"""
        try:
            if not self.opensearch_endpoint:
                logger.warning("OpenSearch endpoint not configured")
                return None
            
            # Create AWS authentication
            credentials = boto3.Session().get_credentials()
            awsauth = AWSRequestsAuth(credentials, self.region, 'es')
            
            # Create OpenSearch client
            client = OpenSearch(
                hosts=[{'host': self.opensearch_endpoint.replace('https://', ''), 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
            
            logger.info(f"OpenSearch client created for endpoint: {self.opensearch_endpoint}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client: {e}")
            return None
    
    def lambda_handler(self, event, context):
        """Main Lambda handler for background processing"""
        logger.info("Enhanced keyword indexer worker started")
        
        try:
            # Extract document information from event
            doc_id = event.get('doc_id')
            if not doc_id:
                raise ValueError("doc_id is required in event payload")
            
            text_bucket = event.get('text_bucket')
            text_key = event.get('text_key')
            completion_topic_arn = event.get('completion_topic_arn')
            
            logger.info(f"Processing keyword indexing for document: {doc_id}")
            
            # Update status to processing using DatabaseManager
            self.update_status_via_db_manager(doc_id, 'PROCESSING', 'Background processing started')
            
            # Get document metadata using existing DatabaseManager method
            metadata = self.get_document_metadata(doc_id)
            
            # Try to get Textract structure data from same folder
            structure_data = self.get_textract_structure_data(doc_id, text_bucket)
            
            # Process with structure awareness
            if structure_data:
                logger.info(f"Processing with Textract structure data for {doc_id}")
                indexing_result = self.process_with_structure(doc_id, structure_data, metadata)
            else:
                logger.info(f"Processing with fallback text extraction for {doc_id}")
                indexing_result = self.process_with_fallback(doc_id, text_bucket, text_key, metadata)
            
            # Update final status using DatabaseManager
            if indexing_result['success']:
                self.update_status_via_db_manager(
                    doc_id, 
                    'COMPLETED', 
                    f"Indexed {indexing_result['keywords_count']} keywords",
                    keywords_count=indexing_result['keywords_count'],
                    opensearch_index_name=self.index_name
                )
                
                # Send success callback
                self.send_success_callback(doc_id, completion_topic_arn, indexing_result)
                
                logger.info(f"Successfully completed keyword indexing for {doc_id}")
            else:
                self.update_status_via_db_manager(
                    doc_id, 
                    'FAILED', 
                    indexing_result.get('error', 'Unknown error'),
                    error_message=indexing_result.get('error')
                )
                
                logger.error(f"Failed keyword indexing for {doc_id}: {indexing_result.get('error')}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'doc_id': doc_id,
                    'success': indexing_result['success'],
                    'keywords_count': indexing_result.get('keywords_count', 0)
                })
            }
            
        except Exception as e:
            logger.error(f"Worker processing error: {str(e)}")
            
            # Update status to failed using DatabaseManager
            if 'doc_id' in locals():
                self.update_status_via_db_manager(
                    doc_id, 
                    'FAILED', 
                    f'Worker error: {str(e)}',
                    error_message=str(e)
                )
            
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    def get_document_metadata(self, doc_id: str) -> Dict:
        """Get document metadata using DatabaseManager"""
        try:
            if self.db_manager:
                metadata = self.db_manager.get_document_metadata(doc_id)
                if metadata:
                    return metadata
            
            # Fallback metadata if DatabaseManager unavailable
            logger.warning(f"Using fallback metadata for {doc_id}")
            return {
                'doc_id': doc_id,
                'status': 'unknown',
                'created_at': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error getting document metadata: {e}")
            return {
                'doc_id': doc_id,
                'status': 'error',
                'error_message': str(e)
            }
    
    def get_textract_structure_data(self, doc_id: str, text_bucket: str) -> Optional[Dict]:
        """Get Textract structure data from S3"""
        try:
            if not text_bucket:
                return None
            
            # Look for structured extraction files
            structure_files = []
            
            # List files in the document's extraction folder
            prefix = f"extracted_text/{doc_id}/"
            response = self.s3.list_objects_v2(Bucket=text_bucket, Prefix=prefix)
            
            if 'Contents' not in response:
                logger.info(f"No extracted text files found for {doc_id}")
                return None
            
            # Collect structure files
            for obj in response['Contents']:
                key = obj['Key']
                if any(pattern in key for pattern in ['table_', 'key_values', 'layout', 'textract_response']):
                    structure_files.append(key)
            
            if not structure_files:
                logger.info(f"No structure files found for {doc_id}")
                return None
            
            # Download and parse structure files
            structure_data = {
                'doc_id': doc_id,
                'files': structure_files,
                'tables': [],
                'key_values': [],
                'layout_info': [],
                'full_text': None
            }
            
            for file_key in structure_files:
                try:
                    obj = self.s3.get_object(Bucket=text_bucket, Key=file_key)
                    content = obj['Body'].read().decode('utf-8')
                    
                    if 'table_' in file_key and file_key.endswith('.csv'):
                        structure_data['tables'].append({
                            'file': file_key,
                            'content': content
                        })
                    elif 'key_values' in file_key:
                        structure_data['key_values'].append({
                            'file': file_key,
                            'content': content
                        })
                    elif 'layout' in file_key:
                        structure_data['layout_info'].append({
                            'file': file_key,
                            'content': content
                        })
                    elif 'full_text.txt' in file_key:
                        structure_data['full_text'] = content
                        
                except Exception as e:
                    logger.warning(f"Could not process structure file {file_key}: {e}")
            
            logger.info(f"Retrieved structure data for {doc_id}: {len(structure_data['tables'])} tables, {len(structure_data['key_values'])} key-value files")
            return structure_data
            
        except Exception as e:
            logger.error(f"Error getting Textract structure data: {e}")
            return None
    
    def process_with_structure(self, doc_id: str, structure_data: Dict, metadata: Dict) -> Dict:
        """Process document with Textract structure awareness"""
        try:
            # Use structure-aware processor
            processing_result = self.structure_processor.process_structured_document(
                doc_id, structure_data, metadata
            )
            
            # Index in OpenSearch
            if self.opensearch_client and processing_result.get('keywords'):
                opensearch_result = self.index_in_opensearch(doc_id, processing_result, metadata)
                processing_result.update(opensearch_result)
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Error in structure-aware processing: {e}")
            return {
                'success': False,
                'error': f'Structure processing failed: {str(e)}',
                'keywords_count': 0
            }
    
    def process_with_fallback(self, doc_id: str, text_bucket: str, text_key: str, metadata: Dict) -> Dict:
        """Fallback processing for documents without structure data"""
        try:
            # Get text content
            if text_bucket and text_key:
                obj = self.s3.get_object(Bucket=text_bucket, Key=text_key)
                text_content = obj['Body'].read().decode('utf-8')
            else:
                # Try to find full text file
                prefix = f"extracted_text/{doc_id}/"
                response = self.s3.list_objects_v2(Bucket=text_bucket, Prefix=prefix)
                
                text_file = None
                if 'Contents' in response:
                    for obj in response['Contents']:
                        if 'full_text.txt' in obj['Key']:
                            text_file = obj['Key']
                            break
                
                if not text_file:
                    raise Exception("No text content found for processing")
                
                obj = self.s3.get_object(Bucket=text_bucket, Key=text_file)
                text_content = obj['Body'].read().decode('utf-8')
            
            # Basic keyword extraction
            keywords = self.extract_basic_keywords(text_content)
            
            # Index in OpenSearch
            processing_result = {
                'success': True,
                'keywords': keywords,
                'keywords_count': len(keywords),
                'processing_method': 'fallback'
            }
            
            if self.opensearch_client:
                opensearch_result = self.index_in_opensearch(doc_id, processing_result, metadata)
                processing_result.update(opensearch_result)
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Error in fallback processing: {e}")
            return {
                'success': False,
                'error': f'Fallback processing failed: {str(e)}',
                'keywords_count': 0
            }
    
    def extract_basic_keywords(self, text_content: str) -> List[str]:
        """Basic keyword extraction for fallback processing"""
        try:
            # Simple keyword extraction (can be enhanced)
            import re
            
            # Remove common stop words and extract meaningful terms
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text_content.lower())
            
            # Basic frequency analysis
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
            return [word for word, freq in keywords if freq > 2]
            
        except Exception as e:
            logger.error(f"Error in basic keyword extraction: {e}")
            return []
    
    def index_in_opensearch(self, doc_id: str, processing_result: Dict, metadata: Dict) -> Dict:
        """Index document in OpenSearch"""
        try:
            if not self.opensearch_client:
                return {'opensearch_indexed': False, 'opensearch_error': 'Client not available'}
            
            # Prepare document for indexing
            doc_data = {
                'doc_id': doc_id,
                'keywords': processing_result.get('keywords', []),
                'keywords_count': processing_result.get('keywords_count', 0),
                'processing_method': processing_result.get('processing_method', 'unknown'),
                'metadata': metadata,
                'indexed_at': datetime.utcnow().isoformat(),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
            # Remove any conflicting fields
            safe_doc_data = self.sanitize_for_opensearch(doc_data)
            
            # Index document
            response = self.opensearch_client.index(
                index=self.index_name,
                id=doc_id,
                body=safe_doc_data
            )
            
            logger.info(f"Successfully indexed document {doc_id} in OpenSearch")
            return {
                'opensearch_indexed': True,
                'opensearch_response': response
            }
            
        except Exception as e:
            logger.error(f"Error indexing in OpenSearch: {e}")
            return {
                'opensearch_indexed': False,
                'opensearch_error': str(e)
            }
    
    def sanitize_for_opensearch(self, doc_data: Dict) -> Dict:
        """Sanitize document data for OpenSearch indexing"""
        try:
            safe_doc_data = {}
            
            for key, value in doc_data.items():
                # Handle datetime objects
                if hasattr(value, 'isoformat'):
                    safe_doc_data[key] = value.isoformat()
                # Handle None values
                elif value is None:
                    continue
                # Handle complex objects
                elif isinstance(value, (dict, list)):
                    try:
                        json.dumps(value)  # Test if serializable
                        safe_doc_data[key] = value
                    except (TypeError, ValueError):
                        logger.warning(f"Skipping non-serializable field: {key}")
                else:
                    safe_doc_data[key] = value
            
            return safe_doc_data
            
        except Exception as e:
            logger.error(f"Error sanitizing document data: {e}")
            return doc_data
    
    def update_status_via_db_manager(self, doc_id: str, status: str, notes: str = None, 
                                   keywords_count: int = None, opensearch_index_name: str = None,
                                   error_message: str = None):
        """Update processing status using DatabaseManager methods"""
        try:
            if not self.db_manager:
                logger.warning("DatabaseManager not available - skipping status update")
                return
            
            # Use the new DatabaseManager method instead of direct SQL
            self.db_manager.update_keyword_indexing_status(
                doc_id=doc_id,
                status=status,
                notes=notes,
                keywords_count=keywords_count,
                opensearch_index_name=opensearch_index_name or self.index_name,
                error_message=error_message
            )
            
            logger.info(f"Updated keyword indexing status via DatabaseManager: {doc_id} -> {status}")
            
        except Exception as e:
            logger.error(f"DatabaseManager status update error: {e}")
            # Don't raise - this shouldn't block the main processing
    
    def send_success_callback(self, doc_id: str, topic_arn: Optional[str], details: Dict):
        """Send enhanced success callback via SNS"""
        if not topic_arn:
            logger.info("No completion topic ARN provided - skipping callback")
            return
        
        try:
            message = {
                'event_type': 'keyword_indexing_complete',
                'doc_id': doc_id,
                'success': True,
                'keywords_count': details.get('keywords_count', 0),
                'processing_method': details.get('processing_method', 'unknown'),
                'opensearch_indexed': details.get('opensearch_indexed', False),
                'opensearch_index_name': self.index_name,
                'completion_timestamp': datetime.utcnow().isoformat()
            }
            
            self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f'Keyword Indexing Complete: {doc_id}'
            )
            
            logger.info(f"Sent success callback for {doc_id}")
            
        except Exception as e:
            logger.error(f"Error sending success callback: {e}")


def lambda_handler(event, context):
    """Lambda entry point"""
    try:
        worker = EnhancedKeywordIndexerWorker()
        return worker.lambda_handler(event, context)
    except Exception as e:
        logger.error(f"Keyword indexer worker error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
