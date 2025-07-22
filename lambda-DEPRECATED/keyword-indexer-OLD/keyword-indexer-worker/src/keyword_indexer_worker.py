"""
Keyword Indexer Worker Lambda Function
Processes documents for OpenSearch indexing with Textract structure analysis
Uses audit-first database design with DatabaseManager
PRESERVES ALL OPENSEARCH FUNCTIONALITY
"""

import json
import boto3
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import from locked database core layer - DO NOT CHANGE
from utils.DatabaseManager import DatabaseManager

# Import structure-aware processor - PRESERVED FUNCTIONALITY
from structure_aware_processor import StructureAwareProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class KeywordIndexerWorker:
    """
    Enhanced background worker with Textract structure analysis and audit-first database design
    PRESERVES ALL OPENSEARCH INDEXING FUNCTIONALITY
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # OpenSearch configuration - PRESERVED
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.index_name = os.environ.get('INDEX_NAME', 'solve-global-kr-search-v2')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        # Initialize OpenSearch client - PRESERVED FUNCTIONALITY
        self.opensearch_client = self._initialize_opensearch_client()
        
        # Initialize structure-aware processor - PRESERVED FUNCTIONALITY
        if self.opensearch_client:
            self.structure_processor = StructureAwareProcessor(
                self.opensearch_client, 
                self.index_name
            )
            # Ensure index exists with proper mapping
            self.structure_processor.create_enhanced_index_mapping()
        else:
            self.structure_processor = None
            logger.error("OpenSearch client initialization failed")
        
        logger.info("✅ Keyword Indexer Worker initialized")
        logger.info(f"OpenSearch endpoint: {self.opensearch_endpoint}")
        logger.info(f"Index name: {self.index_name}")
    
    def _initialize_opensearch_client(self) -> Optional[OpenSearch]:
        """Initialize OpenSearch client with AWS authentication - PRESERVED"""
        try:
            if not self.opensearch_endpoint:
                logger.error("OPENSEARCH_ENDPOINT environment variable not set")
                return None
            
            # Extract host from endpoint URL
            host = self.opensearch_endpoint.replace('https://', '').replace('http://', '')
            
            # AWS authentication for OpenSearch Serverless
            credentials = boto3.Session().get_credentials()
            awsauth = AWSRequestsAuth(
                aws_access_key=credentials.access_key,
                aws_secret_access_key=credentials.secret_key,
                aws_token=credentials.token,
                aws_host=host,
                aws_region=self.region,
                aws_service='aoss'  # OpenSearch Serverless
            )
            
            # Create OpenSearch client
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Note: OpenSearch Serverless doesn't support info() endpoint
            logger.info(f"OpenSearch client initialized for endpoint: {self.opensearch_endpoint}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {e}")
            return None
    
    def download_text_files(self, text_location: str, structure_location: str) -> Dict[str, Any]:
        """Download text and structure files from S3"""
        try:
            files_data = {}
            
            # Parse S3 locations
            for location_name, s3_url in [('text', text_location), ('structure', structure_location)]:
                if not s3_url.startswith('s3://'):
                    raise ValueError(f"Invalid S3 URL format: {s3_url}")
                
                # Extract bucket and key
                s3_parts = s3_url[5:].split('/', 1)
                bucket = s3_parts[0]
                key = s3_parts[1]
                
                logger.info(f"Downloading {location_name} from s3://{bucket}/{key}")
                
                # Download file
                response = self.s3.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read()
                
                if location_name == 'text':
                    # Text file - decode as string
                    files_data['raw_text'] = content.decode('utf-8')
                    logger.info(f"Downloaded text file: {len(files_data['raw_text'])} characters")
                    
                elif location_name == 'structure':
                    # JSON file - parse as JSON
                    files_data['textract_response'] = json.loads(content.decode('utf-8'))
                    logger.info(f"Downloaded structure file: {len(files_data['textract_response'].get('blocks', []))} blocks")
            
            return files_data
            
        except Exception as e:
            logger.error(f"Failed to download text files: {e}")
            raise
    
    def index_document_with_structure(self, doc_id: str, raw_text: str, 
                                    textract_response: Dict, metadata: Dict = None) -> Dict[str, Any]:
        """Index document using structure-aware processing - PRESERVED FUNCTIONALITY"""
        try:
            if not self.structure_processor:
                raise Exception("Structure processor not initialized")
            
            # Use structure-aware indexing - PRESERVED FUNCTIONALITY
            success = self.structure_processor.index_enhanced_document(
                doc_id=doc_id,
                raw_text=raw_text,
                textract_response=textract_response,
                metadata=metadata
            )
            
            if success:
                return {
                    'indexing_method': 'structure_aware',
                    'success': True,
                    'character_count': len(raw_text),
                    'blocks_processed': len(textract_response.get('blocks', [])),
                    'index_name': self.index_name
                }
            else:
                raise Exception("Structure-aware indexing failed")
                
        except Exception as e:
            logger.warning(f"Structure-aware indexing failed for {doc_id}: {e}")
            
            # Fallback to basic indexing - PRESERVED FUNCTIONALITY
            try:
                success = self.structure_processor.fallback_index_document(
                    doc_id=doc_id,
                    raw_text=raw_text,
                    metadata=metadata
                )
                
                if success:
                    return {
                        'indexing_method': 'fallback',
                        'success': True,
                        'character_count': len(raw_text),
                        'index_name': self.index_name,
                        'fallback_reason': str(e)
                    }
                else:
                    raise Exception("Fallback indexing also failed")
                    
            except Exception as fallback_error:
                logger.error(f"Both structure-aware and fallback indexing failed for {doc_id}: {fallback_error}")
                raise Exception(f"All indexing methods failed: {fallback_error}")
    
    def publish_completion_message(self, doc_id: str, indexing_result: Dict[str, Any]) -> None:
        """Publish keyword indexing completion message"""
        try:
            # Create standardized completion message
            message = {
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "climate-risk-rag-system",
                "stage": "keyword_index_ready",
                "doc_id": doc_id,
                "processing_metadata": {
                    "indexing_method": indexing_result.get('indexing_method', 'unknown'),
                    "character_count": indexing_result.get('character_count', 0),
                    "blocks_processed": indexing_result.get('blocks_processed', 0),
                    "index_name": indexing_result.get('index_name', self.index_name),
                    "processing_completed": datetime.utcnow().isoformat() + "Z"
                },
                "integration_flags": {
                    "database_tracking_enabled": True,
                    "audit_first_design": True,
                    "structure_aware_indexing": indexing_result.get('indexing_method') == 'structure_aware'
                }
            }
            
            # Add fallback reason if applicable
            if 'fallback_reason' in indexing_result:
                message['processing_metadata']['fallback_reason'] = indexing_result['fallback_reason']
            
            # Publish to SNS (if topic configured)
            completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
            if completion_topic_arn:
                response = self.sns.publish(
                    TopicArn=completion_topic_arn,
                    Message=json.dumps(message, default=str),
                    Subject=f"Keyword indexing complete: {doc_id}",
                    MessageAttributes={
                        'stage': {
                            'DataType': 'String',
                            'StringValue': 'keyword_index_ready'
                        },
                        'doc_id': {
                            'DataType': 'String',
                            'StringValue': doc_id
                        },
                        'version': {
                            'DataType': 'String',
                            'StringValue': '1.0'
                        }
                    }
                )
                
                logger.info(f"Published keyword indexing complete message for {doc_id}: {response['MessageId']}")
            else:
                logger.info(f"No completion topic configured, skipping message publication for {doc_id}")
                
        except Exception as e:
            logger.error(f"Failed to publish completion message for {doc_id}: {e}")
            # Don't raise - this is not critical for the indexing process
    
    def process_keyword_indexing_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process keyword indexing job for a document"""
        
        doc_id = job_data.get('doc_id')
        if not doc_id:
            raise ValueError("Missing doc_id in job data")
        
        try:
            logger.info(f"Processing keyword indexing job for doc_id: {doc_id}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_index_complete',
                status='in_progress'
            )
            
            # Download text and structure files
            files_data = self.download_text_files(
                text_location=job_data.get('text_location'),
                structure_location=job_data.get('structure_location')
            )
            
            # Prepare metadata
            metadata = {
                'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
                'document_metadata': job_data.get('document_metadata', {}),
                'processing_metadata': job_data.get('processing_metadata', {})
            }
            
            # Index document with structure analysis - PRESERVED FUNCTIONALITY
            indexing_result = self.index_document_with_structure(
                doc_id=doc_id,
                raw_text=files_data['raw_text'],
                textract_response=files_data['textract_response'],
                metadata=metadata
            )
            
            # Publish completion message
            self.publish_completion_message(doc_id, indexing_result)
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_index_complete',
                status='completed'
            )
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'indexing_result': indexing_result
            }
            
        except Exception as e:
            logger.error(f"Error processing keyword indexing job for {doc_id}: {str(e)}")
            
            # Update status to failed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_index_complete',
                status='failed',
                error_message=str(e)
            )
            
            return {
                'status': 'failed',
                'doc_id': doc_id,
                'error': str(e)
            }

def lambda_handler(event, context):
    """Lambda handler for Keyword Indexer Worker"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        worker = KeywordIndexerWorker()
        
        # Process the job data
        result = worker.process_keyword_indexing_job(event)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Keyword indexing job processed',
                'result': result
            }, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
