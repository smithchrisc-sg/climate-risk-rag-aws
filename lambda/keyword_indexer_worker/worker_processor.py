#!/usr/bin/env python3
"""
Keyword Indexer Worker - Background Processing with Callbacks
Handles the actual OpenSearch indexing and sends completion notifications
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeywordIndexerWorker:
    """
    Background worker that does the actual indexing and sends callbacks
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # OpenSearch configuration
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.index_name = os.environ.get('INDEX_NAME', 'climate-risk-keyword-index')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Database manager
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
        except ImportError:
            self.db_manager = None
        
        # Initialize OpenSearch client
        self.opensearch_client = self._create_opensearch_client()

    def _create_opensearch_client(self):
        """Create OpenSearch client"""
        try:
            host = self.opensearch_endpoint.replace('https://', '').replace('http://', '')
            
            auth = AWSRequestsAuth(
                aws_access_key=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                aws_token=os.environ.get('AWS_SESSION_TOKEN'),
                aws_host=host,
                aws_region=self.region,
                aws_service='aoss'
            )
            
            return OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client: {e}")
            raise

    def lambda_handler(self, event, context):
        """Worker handler - does the actual indexing work"""
        
        try:
            action = event.get('action')
            if action == 'index_document':
                return self.process_indexing_job(event)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            # Send error callback
            self.send_error_callback(event, str(e))
            raise

    def process_indexing_job(self, job_data: Dict) -> Dict:
        """Process the actual indexing job"""
        
        doc_id = job_data['doc_id']
        full_text_location = job_data['full_text_location']
        filename = job_data.get('filename', 'unknown')
        completion_topic_arn = job_data.get('completion_topic_arn')
        
        try:
            logger.info(f"Starting background indexing for {doc_id}")
            
            # Read full text from S3
            full_text = self.read_full_text(full_text_location)
            
            # Get document metadata
            metadata = self.get_document_metadata(doc_id)
            
            # Prepare document for indexing
            doc_data = self.prepare_document_for_indexing(doc_id, full_text, metadata, filename)
            
            # Index document in OpenSearch (this is the slow part)
            success = self.index_document(doc_id, doc_data)
            
            if success:
                # Update success status
                self.update_processing_status(doc_id, 'COMPLETED', 'Keyword indexing completed successfully')
                
                # Send success callback
                self.send_success_callback(doc_id, completion_topic_arn, {
                    'indexed_at': datetime.utcnow().isoformat(),
                    'word_count': doc_data.get('processing', {}).get('word_count', 0)
                })
                
                logger.info(f"Successfully completed indexing for {doc_id}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'doc_id': doc_id,
                        'indexed_at': datetime.utcnow().isoformat()
                    })
                }
            else:
                raise Exception("Document indexing failed")
                
        except Exception as e:
            logger.error(f"Indexing job failed for {doc_id}: {e}")
            
            # Update error status
            self.update_processing_status(doc_id, 'FAILED', str(e))
            
            # Send error callback
            self.send_error_callback(job_data, str(e))
            
            raise

    def read_full_text(self, location: Dict) -> str:
        """Read full text from S3"""
        try:
            bucket = location['bucket']
            key = location['key']
            
            response = self.s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            if isinstance(content, bytes):
                return content.decode('utf-8')
            return str(content)
            
        except Exception as e:
            logger.error(f"Error reading text from S3: {e}")
            raise

    def get_document_metadata(self, doc_id: str) -> Dict:
        """Get document metadata"""
        try:
            if self.db_manager:
                metadata = self.db_manager.get_document_metadata(doc_id)
                if metadata:
                    return metadata
            
            return {
                'title': {'value': 'Untitled'},
                'author': {'value': None},
                'language': {'value': 'en'},
                'processing': {'overall_confidence': 0.8}
            }
        except Exception as e:
            logger.warning(f"Error getting metadata for {doc_id}: {e}")
            return {}

    def prepare_document_for_indexing(self, doc_id: str, full_text: str, 
                                    metadata: Dict, filename: str) -> Dict:
        """Prepare document for indexing"""
        try:
            # Extract metadata values
            title = metadata.get('title', {})
            if isinstance(title, dict) and 'value' in title:
                title_value = title['value']
            else:
                title_value = filename or 'Untitled'

            author = metadata.get('author', {})
            author_value = author.get('value') if isinstance(author, dict) else None

            language = metadata.get('language', {})
            language_value = language.get('value', 'en') if isinstance(language, dict) else 'en'

            word_count = len(full_text.split()) if full_text else 0

            return {
                "doc_id": doc_id,
                "content": full_text,
                "title": title_value,
                "title_metadata": {
                    "confidence": title.get('confidence', 0.8) if isinstance(title, dict) else 0.8,
                    "source": "textract"
                },
                "author": author_value,
                "language": language_value,
                "processing": {
                    "overall_confidence": metadata.get('processing', {}).get('overall_confidence', 0.8),
                    "status": "indexed",
                    "word_count": word_count
                },
                "indexed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error preparing document {doc_id}: {e}")
            raise

    def index_document(self, doc_id: str, doc_data: Dict) -> bool:
        """Index document in OpenSearch"""
        try:
            response = self.opensearch_client.index(
                index=self.index_name,
                id=doc_id,
                body=doc_data
            )
            
            if response['result'] in ['created', 'updated']:
                logger.info(f"Successfully indexed document {doc_id}")
                return True
            else:
                logger.error(f"Unexpected indexing result: {response['result']}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing document {doc_id}: {e}")
            return False

    def update_processing_status(self, doc_id: str, status: str, notes: str = None):
        """Update processing status"""
        if not self.db_manager:
            return
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO keyword_indexing_status (doc_id, status, notes, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (doc_id) 
                        DO UPDATE SET 
                            status = EXCLUDED.status,
                            notes = EXCLUDED.notes,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (doc_id, status, notes, datetime.utcnow())
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Status update error: {e}")

    def send_success_callback(self, doc_id: str, topic_arn: Optional[str], details: Dict):
        """Send success callback via SNS"""
        if not topic_arn:
            logger.info("No completion topic configured, skipping callback")
            return
        
        try:
            message = {
                'doc_id': doc_id,
                'stage': 'keyword_indexing_complete',
                'status': 'SUCCESS',
                'processor': 'keyword_indexer',
                'details': details,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f'Keyword Indexing Complete: {doc_id}',
                MessageAttributes={
                    'processor': {'DataType': 'String', 'StringValue': 'keyword_indexer'},
                    'status': {'DataType': 'String', 'StringValue': 'SUCCESS'},
                    'doc_id': {'DataType': 'String', 'StringValue': doc_id}
                }
            )
            
            logger.info(f"Sent success callback for {doc_id}")
            
        except Exception as e:
            logger.error(f"Error sending success callback: {e}")

    def send_error_callback(self, job_data: Dict, error_message: str):
        """Send error callback via SNS"""
        topic_arn = job_data.get('completion_topic_arn')
        if not topic_arn:
            return
        
        try:
            doc_id = job_data.get('doc_id', 'unknown')
            
            message = {
                'doc_id': doc_id,
                'stage': 'keyword_indexing_failed',
                'status': 'ERROR',
                'processor': 'keyword_indexer',
                'error': error_message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f'Keyword Indexing Failed: {doc_id}',
                MessageAttributes={
                    'processor': {'DataType': 'String', 'StringValue': 'keyword_indexer'},
                    'status': {'DataType': 'String', 'StringValue': 'ERROR'},
                    'doc_id': {'DataType': 'String', 'StringValue': doc_id}
                }
            )
            
            logger.info(f"Sent error callback for {doc_id}")
            
        except Exception as e:
            logger.error(f"Error sending error callback: {e}")

def lambda_handler(event, context):
    """Lambda entry point"""
    worker = KeywordIndexerWorker()
    return worker.lambda_handler(event, context)
