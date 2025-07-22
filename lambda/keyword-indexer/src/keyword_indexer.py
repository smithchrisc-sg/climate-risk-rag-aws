"""
Consolidated Keyword Indexer Lambda Function
Combines initiator + worker functionality for OpenSearch document indexing
Uses audit-first database design with DatabaseManager
PRESERVES ALL OPENSEARCH FUNCTIONALITY AND CONFIGURATIONS
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

class KeywordIndexer:
    """
    Consolidated keyword indexer combining message parsing and document processing
    PRESERVES ALL OPENSEARCH INDEXING FUNCTIONALITY AND NETWORK CONFIGURATIONS
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment configuration - PRESERVED FROM BOTH FUNCTIONS
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.collection_name = os.environ.get('COLLECTION_NAME', 'solve-global-kr-search-v2')
        self.completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        # Initialize OpenSearch client - PRESERVED FUNCTIONALITY
        self.opensearch_client = self._initialize_opensearch_client()
        
        # Initialize structure-aware processor - PRESERVED FUNCTIONALITY
        if self.opensearch_client:
            self.structure_processor = StructureAwareProcessor(
                self.opensearch_client, 
                self.collection_name
            )
            # Ensure index exists with proper mapping
            self.structure_processor.create_enhanced_index_mapping()
        else:
            self.structure_processor = None
            logger.error("OpenSearch client initialization failed")
        
        logger.info("✅ Consolidated Keyword Indexer initialized")
        logger.info(f"Text bucket: {self.text_bucket}")
        logger.info(f"OpenSearch endpoint: {self.opensearch_endpoint}")
        logger.info(f"Collection name: {self.collection_name}")
    
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
                aws_service='aoss'  # OpenSearch Serverless service
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
            
            logger.info(f"OpenSearch client initialized for endpoint: {self.opensearch_endpoint}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            return None
    
    def parse_sqs_records(self, records: List[Dict]) -> List[Dict[str, Any]]:
        """Parse SQS records containing SNS messages - FROM INITIATOR"""
        parsed_messages = []
        
        for record in records:
            try:
                # Parse SQS record body (contains SNS message)
                sqs_body = json.loads(record['body'])
                
                # Extract SNS message
                if sqs_body.get('Type') == 'Notification':
                    sns_message = json.loads(sqs_body['Message'])
                    
                    # Extract key fields from standardized message
                    doc_id = sns_message.get('doc_id')
                    stage = sns_message.get('stage')
                    data_locations = sns_message.get('data_locations', {})
                    
                    if not doc_id:
                        raise ValueError("Missing doc_id in SNS message")
                    
                    if stage != 'text_ready':
                        raise ValueError(f"Expected stage 'text_ready', got '{stage}'")
                    
                    # Extract S3 locations
                    text_location = data_locations.get('text_location')
                    structure_location = data_locations.get('structure_location')
                    
                    if not text_location or not structure_location:
                        raise ValueError("Missing required S3 locations in message")
                    
                    parsed_messages.append({
                        'doc_id': doc_id,
                        'text_location': text_location,
                        'structure_location': structure_location,
                        'processing_metadata': sns_message.get('processing_metadata', {}),
                        'document_metadata': sns_message.get('document_metadata', {})
                    })
                    
                else:
                    logger.warning(f"Unexpected SQS message type: {sqs_body.get('Type')}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SQS record JSON: {e}")
                continue
            except Exception as e:
                logger.error(f"Failed to parse SQS record: {e}")
                continue
        
        return parsed_messages
    
    def download_s3_file(self, s3_location: str) -> str:
        """Download file content from S3 - FROM WORKER"""
        try:
            # Parse S3 location
            if not s3_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 location format: {s3_location}")
            
            # Extract bucket and key
            s3_parts = s3_location[5:].split('/', 1)
            if len(s3_parts) != 2:
                raise ValueError(f"Invalid S3 location format: {s3_location}")
            
            bucket, key = s3_parts
            
            # Download file
            response = self.s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Downloaded file from {s3_location}: {len(content)} characters")
            return content
            
        except Exception as e:
            logger.error(f"Failed to download file from {s3_location}: {str(e)}")
            raise
    
    def extract_document_structure(self, structure_content: str) -> Dict[str, Any]:
        """Extract document structure from Textract response - FROM WORKER"""
        try:
            structure_data = json.loads(structure_content)
            
            # Count different block types
            blocks = structure_data.get('Blocks', [])
            page_count = len([b for b in blocks if b.get('BlockType') == 'PAGE'])
            table_count = len([b for b in blocks if b.get('BlockType') == 'TABLE'])
            form_count = len([b for b in blocks if b.get('BlockType') == 'KEY_VALUE_SET'])
            line_count = len([b for b in blocks if b.get('BlockType') == 'LINE'])
            
            structure_info = {
                'page_count': page_count,
                'table_count': table_count,
                'form_count': form_count,
                'line_count': line_count,
                'has_tables': table_count > 0,
                'has_forms': form_count > 0
            }
            
            logger.info(f"Extracted structure: {structure_info}")
            return structure_info
            
        except Exception as e:
            logger.error(f"Failed to extract document structure: {str(e)}")
            return {
                'page_count': 0,
                'table_count': 0,
                'form_count': 0,
                'line_count': 0,
                'has_tables': False,
                'has_forms': False
            }
    
    def index_document_in_opensearch(self, doc_id: str, text_content: str, 
                                   structure_info: Dict, metadata: Dict) -> Dict[str, Any]:
        """Index document in OpenSearch using structure-aware processing - FROM WORKER"""
        try:
            if not self.structure_processor:
                raise Exception("Structure processor not initialized")
            
            # Try structure-aware indexing first
            try:
                result = self.structure_processor.index_enhanced_document(
                    doc_id=doc_id,
                    text_content=text_content,
                    structure_info=structure_info,
                    metadata=metadata
                )
                
                if result.get('result') in ['created', 'updated']:
                    logger.info(f"Indexed enhanced document {doc_id}: {result.get('result')}")
                    return {
                        'status': 'success',
                        'method': 'structure_aware',
                        'result': result
                    }
                else:
                    raise Exception("Structure-aware indexing failed")
                    
            except Exception as e:
                logger.warning(f"Structure-aware indexing failed for {doc_id}: {str(e)}")
                
                # Fallback to basic indexing
                basic_document = {
                    'doc_id': doc_id,
                    'content': text_content,
                    'timestamp': datetime.utcnow().isoformat(),
                    'structure_info': structure_info,
                    'metadata': metadata
                }
                
                result = self.opensearch_client.index(
                    index=self.collection_name,
                    id=doc_id,
                    body=basic_document
                )
                
                if result.get('result') in ['created', 'updated']:
                    logger.info(f"Indexed basic document {doc_id}: {result.get('result')}")
                    return {
                        'status': 'success',
                        'method': 'basic',
                        'result': result
                    }
                else:
                    raise Exception("Fallback indexing also failed")
                    
        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {str(e)}")
            raise
    
    def publish_completion_message(self, doc_id: str, indexing_result: Dict) -> None:
        """Publish keyword indexing completion message - NEW FUNCTIONALITY"""
        try:
            if self.completion_topic_arn:
                completion_message = {
                    'version': '1.0',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'source': 'climate-risk-rag-system',
                    'stage': 'keyword_indexing_complete',
                    'doc_id': doc_id,
                    'indexing_result': {
                        'status': indexing_result.get('status'),
                        'method': indexing_result.get('method'),
                        'opensearch_result': indexing_result.get('result', {}).get('result')
                    },
                    'integration_flags': {
                        'database_tracking_enabled': True,
                        'audit_first_design': True
                    }
                }
                
                response = self.sns.publish(
                    TopicArn=self.completion_topic_arn,
                    Message=json.dumps(completion_message),
                    Subject=f'Keyword indexing complete: {doc_id}',
                    MessageAttributes={
                        'stage': {
                            'DataType': 'String',
                            'StringValue': 'keyword_indexing_complete'
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
    
    def process_document(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document for keyword indexing - COMBINED LOGIC"""
        doc_id = message_data['doc_id']
        
        try:
            logger.info(f"Processing keyword indexing for doc_id: {doc_id}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_indexing',
                status='in_progress'
            )
            
            # Download text file
            logger.info(f"Downloading text from {message_data['text_location']}")
            text_content = self.download_s3_file(message_data['text_location'])
            logger.info(f"Downloaded text file: {len(text_content)} characters")
            
            # Download structure file
            logger.info(f"Downloading structure from {message_data['structure_location']}")
            structure_content = self.download_s3_file(message_data['structure_location'])
            structure_data = json.loads(structure_content)
            logger.info(f"Downloaded structure file: {len(structure_data.get('Blocks', []))} blocks")
            
            # Extract document structure
            structure_info = self.extract_document_structure(structure_content)
            
            # Index document in OpenSearch
            indexing_result = self.index_document_in_opensearch(
                doc_id=doc_id,
                text_content=text_content,
                structure_info=structure_info,
                metadata={
                    'processing_metadata': message_data.get('processing_metadata', {}),
                    'document_metadata': message_data.get('document_metadata', {})
                }
            )
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_indexing',
                status='completed'
            )
            
            # Publish completion message
            self.publish_completion_message(doc_id, indexing_result)
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'indexing_result': indexing_result
            }
            
        except Exception as e:
            logger.error(f"Error processing keyword indexing for {doc_id}: {str(e)}")
            
            # Update status to failed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_indexing',
                status='failed',
                error_message=str(e)
            )
            
            return {
                'status': 'failed',
                'doc_id': doc_id,
                'error': str(e)
            }

def lambda_handler(event, context):
    """Lambda handler for Consolidated Keyword Indexer"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        indexer = KeywordIndexer()
        
        # Parse SQS records
        sqs_records = event.get('Records', [])
        if not sqs_records:
            logger.warning("No SQS records found in event")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No records to process'})
            }
        
        # Parse messages from SQS records
        messages = indexer.parse_sqs_records(sqs_records)
        if not messages:
            logger.warning("No valid messages found in SQS records")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No valid messages to process'})
            }
        
        # Process each document
        results = []
        for message_data in messages:
            result = indexer.process_document(message_data)
            results.append(result)
        
        # Summary
        successful = len([r for r in results if r['status'] == 'success'])
        failed = len([r for r in results if r['status'] == 'failed'])
        
        logger.info(f"Processed {len(results)} documents: {successful} successful, {failed} failed")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Keyword indexing batch processed',
                'total_processed': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            }, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
