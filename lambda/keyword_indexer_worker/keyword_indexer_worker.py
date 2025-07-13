#!/usr/bin/env python3
"""
Enhanced Keyword Indexer Worker with Textract Structure Support
Background processing with structure-aware indexing and fallback
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Import our structure-aware components
from structure_aware_processor import StructureAwareProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedKeywordIndexerWorker:
    """
    Enhanced background worker with Textract structure analysis and fallback
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
        
        # Initialize structure-aware processor
        self.structure_processor = StructureAwareProcessor(
            self.opensearch_client, 
            self.index_name
        )
        
        # Ensure enhanced index exists
        self._ensure_enhanced_index_exists()

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

    def _ensure_enhanced_index_exists(self):
        """Ensure the enhanced index with structure support exists"""
        try:
            if self.opensearch_client.indices.exists(index=self.index_name):
                logger.info(f"Enhanced index {self.index_name} already exists")
                return
            
            # Create enhanced index mapping
            mapping = self.structure_processor.create_enhanced_index_mapping()
            
            self.opensearch_client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Created enhanced index {self.index_name} with structure support")
            
        except Exception as e:
            logger.error(f"Error ensuring enhanced index exists: {e}")
            # Continue anyway - might be a permissions issue but index might exist

    def lambda_handler(self, event, context):
        """Enhanced worker handler with structure processing"""
        
        try:
            action = event.get('action')
            if action == 'index_document':
                return self.process_enhanced_indexing_job(event)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Enhanced worker error: {e}")
            # Send error callback
            self.send_error_callback(event, str(e))
            raise

    def process_enhanced_indexing_job(self, job_data: Dict) -> Dict:
        """Process indexing job with structure enhancement"""
        
        doc_id = job_data['doc_id']
        text_folder_url = job_data.get('text_folder_url') or job_data.get('full_text_location')  # Support both
        filename = job_data.get('filename', 'unknown')
        completion_topic_arn = job_data.get('completion_topic_arn')
        
        try:
            logger.info(f"Starting enhanced indexing for {doc_id}")
            
            # Read full text from S3 folder
            full_text = self.read_full_text(text_folder_url)
            
            # Get document metadata
            metadata = self.get_document_metadata(doc_id)
            
            # Try to get Textract structure data from same folder
            textract_structure = self.get_textract_structure(text_folder_url)
            
            # Prepare document with structure enhancement or fallback
            doc_data = self.structure_processor.prepare_structure_enhanced_document(
                doc_id, full_text, textract_structure, metadata, filename
            )
            
            # Index document in OpenSearch
            success = self.index_document(doc_id, doc_data)
            
            if success:
                # Determine processing type for status
                processing_type = "structure-enhanced" if textract_structure else "standard"
                notes = f"Enhanced keyword indexing completed ({processing_type})"
                
                # Update success status
                self.update_processing_status(doc_id, 'COMPLETED', notes)
                
                # Send success callback with enhancement info
                self.send_success_callback(doc_id, completion_topic_arn, {
                    'indexed_at': datetime.utcnow().isoformat(),
                    'word_count': doc_data.get('processing', {}).get('word_count', 0),
                    'structure_enhanced': textract_structure is not None,
                    'document_type': doc_data.get('structure_metadata', {}).get('document_type'),
                    'section_count': doc_data.get('structure_metadata', {}).get('section_count', 0),
                    'table_count': doc_data.get('structure_metadata', {}).get('table_count', 0)
                })
                
                logger.info(f"Successfully completed enhanced indexing for {doc_id}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'doc_id': doc_id,
                        'structure_enhanced': textract_structure is not None,
                        'indexed_at': datetime.utcnow().isoformat()
                    })
                }
            else:
                raise Exception("Enhanced document indexing failed")
                
        except Exception as e:
            logger.error(f"Enhanced indexing job failed for {doc_id}: {e}")
            
            # Update error status
            self.update_processing_status(doc_id, 'FAILED', str(e))
            
            # Send error callback
            self.send_error_callback(job_data, str(e))
            
            raise

    def get_textract_structure(self, folder_url: str) -> Optional[Dict]:
        """Try to get Textract structure data from folder URL"""
        
        try:
            # Handle both dict format (backward compatibility) and string URL
            if isinstance(folder_url, dict):
                bucket = folder_url['bucket']
                text_key = folder_url['key']
                # Old hardcoded transformation for backward compatibility
                structure_key = text_key.replace('extracted_text/', 'textract_structure/').replace('.txt', '.json')
            else:
                # Construct path to textract_response.json from folder URL
                if folder_url.endswith('/'):
                    textract_url = f"{folder_url}textract_response.json"
                else:
                    textract_url = f"{folder_url}/textract_response.json"
                
                # Parse S3 location
                if textract_url.startswith('s3://'):
                    s3_path = textract_url[5:]
                    bucket, structure_key = s3_path.split('/', 1)
                else:
                    raise ValueError(f"Invalid S3 location format: {textract_url}")
            
            logger.info(f"Looking for Textract structure at s3://{bucket}/{structure_key}")
            
            try:
                response = self.s3.get_object(Bucket=bucket, Key=structure_key)
                structure_data = json.loads(response['Body'].read().decode('utf-8'))
                
                logger.info(f"Found Textract structure data")
                return structure_data
                
            except self.s3.exceptions.NoSuchKey:
                logger.info(f"No Textract structure data found - using fallback")
                return None
            except Exception as e:
                logger.warning(f"Error reading Textract structure: {e} - using fallback")
                return None
                
        except Exception as e:
            logger.warning(f"Error getting Textract structure: {e} - using fallback")
            return None

    def read_full_text(self, folder_url: str) -> str:
        """Read full text from S3 folder URL (constructs path to raw_text.txt)"""
        try:
            # Handle both dict format (backward compatibility) and string URL
            if isinstance(folder_url, dict):
                bucket = folder_url['bucket']
                key = folder_url['key']
                raw_text_url = f"s3://{bucket}/{key}"
            else:
                # Construct path to raw_text.txt file from folder URL
                if folder_url.endswith('/'):
                    raw_text_url = f"{folder_url}raw_text.txt"
                else:
                    raw_text_url = f"{folder_url}/raw_text.txt"
            
            # Parse S3 location
            if raw_text_url.startswith('s3://'):
                s3_path = raw_text_url[5:]
                bucket, key = s3_path.split('/', 1)
            else:
                raise ValueError(f"Invalid S3 location format: {raw_text_url}")
            
            logger.info(f"Reading full text from s3://{bucket}/{key}")
            
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

    def index_document(self, doc_id: str, doc_data: Dict) -> bool:
        """Index enhanced document in OpenSearch"""
        try:
            response = self.opensearch_client.index(
                index=self.index_name,
                id=doc_id,
                body=doc_data
            )
            
            if response['result'] in ['created', 'updated']:
                structure_status = "with structure" if doc_data.get('structure_metadata', {}).get('structure_available') else "standard"
                logger.info(f"Successfully indexed document {doc_id} ({structure_status})")
                return True
            else:
                logger.error(f"Unexpected indexing result: {response['result']}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing enhanced document {doc_id}: {e}")
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
        """Send enhanced success callback via SNS"""
        if not topic_arn:
            logger.info("No completion topic configured, skipping callback")
            return
        
        try:
            message = {
                'doc_id': doc_id,
                'stage': 'enhanced_keyword_indexing_complete',
                'status': 'SUCCESS',
                'processor': 'enhanced_keyword_indexer',
                'details': details,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f'Enhanced Keyword Indexing Complete: {doc_id}',
                MessageAttributes={
                    'processor': {'DataType': 'String', 'StringValue': 'enhanced_keyword_indexer'},
                    'status': {'DataType': 'String', 'StringValue': 'SUCCESS'},
                    'doc_id': {'DataType': 'String', 'StringValue': doc_id},
                    'structure_enhanced': {
                        'DataType': 'String', 
                        'StringValue': str(details.get('structure_enhanced', False))
                    }
                }
            )
            
            logger.info(f"Sent enhanced success callback for {doc_id}")
            
        except Exception as e:
            logger.error(f"Error sending enhanced success callback: {e}")

    def send_error_callback(self, job_data: Dict, error_message: str):
        """Send error callback via SNS"""
        topic_arn = job_data.get('completion_topic_arn')
        if not topic_arn:
            return
        
        try:
            doc_id = job_data.get('doc_id', 'unknown')
            
            message = {
                'doc_id': doc_id,
                'stage': 'enhanced_keyword_indexing_failed',
                'status': 'ERROR',
                'processor': 'enhanced_keyword_indexer',
                'error': error_message,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f'Enhanced Keyword Indexing Failed: {doc_id}',
                MessageAttributes={
                    'processor': {'DataType': 'String', 'StringValue': 'enhanced_keyword_indexer'},
                    'status': {'DataType': 'String', 'StringValue': 'ERROR'},
                    'doc_id': {'DataType': 'String', 'StringValue': doc_id}
                }
            )
            
            logger.info(f"Sent enhanced error callback for {doc_id}")
            
        except Exception as e:
            logger.error(f"Error sending enhanced error callback: {e}")

def lambda_handler(event, context):
    """Lambda entry point"""
    worker = EnhancedKeywordIndexerWorker()
    return worker.lambda_handler(event, context)
