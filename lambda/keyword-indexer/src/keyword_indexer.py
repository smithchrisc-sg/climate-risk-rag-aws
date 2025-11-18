"""
Consolidated Keyword Indexer Lambda Function
Updated for AWS Managed OpenSearch with basic authentication
Combines initiator + worker functionality for OpenSearch document indexing
Uses audit-first database design with DatabaseManager
"""

import json
import boto3
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection

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
    Consolidated keyword indexer for AWS Managed OpenSearch
    Uses basic authentication instead of AWS auth for managed domains
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment configuration
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.opensearch_username = os.environ.get('OPENSEARCH_USERNAME', 'admin')
        self.opensearch_password = os.environ.get('OPENSEARCH_PASSWORD')
        self.completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Index names for dual indexing strategy
        self.documents_index = 'documents_keyword'  # For TF-IDF document search
        self.chunks_index = 'chunks_vector'         # For vector search (future)
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        # Initialize OpenSearch client for managed domain
        self.opensearch_client = self._initialize_opensearch_client()
        
        # Initialize structure-aware processor
        if self.opensearch_client:
            self.structure_processor = StructureAwareProcessor(
                self.opensearch_client, 
                self.documents_index  # Use documents index for keyword search
            )
            # Ensure index exists with proper mapping
            self._create_document_index_mapping()
        else:
            self.structure_processor = None
            logger.error("OpenSearch client initialization failed")
        
        logger.info("✅ Managed OpenSearch Keyword Indexer initialized")
        logger.info(f"Text bucket: {self.text_bucket}")
        logger.info(f"OpenSearch endpoint: {self.opensearch_endpoint}")
        logger.info(f"Documents index: {self.documents_index}")
    
    def _initialize_opensearch_client(self) -> Optional[OpenSearch]:
        """Initialize OpenSearch client with basic authentication for managed domain"""
        try:
            if not self.opensearch_endpoint:
                logger.error("OPENSEARCH_ENDPOINT environment variable not set")
                return None
                
            if not self.opensearch_password:
                logger.error("OPENSEARCH_PASSWORD environment variable not set")
                return None
            
            # Extract host from endpoint URL
            host = self.opensearch_endpoint.replace('https://', '').replace('http://', '')
            
            # Create OpenSearch client with basic auth for managed domain
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(self.opensearch_username, self.opensearch_password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = client.info()
            logger.info(f"Connected to OpenSearch cluster: {info.get('cluster_name', 'unknown')}")
            logger.info(f"OpenSearch version: {info.get('version', {}).get('number', 'unknown')}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            return None
    
    def _create_document_index_mapping(self):
        """Create the documents index with proper mapping for keyword search"""
        try:
            # Check if index exists
            if self.opensearch_client.indices.exists(index=self.documents_index):
                logger.info(f"Index {self.documents_index} already exists")
                return
            
            # Create index mapping optimized for document-level keyword search
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "analysis": {
                        "analyzer": {
                            "climate_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "stop",
                                    "stemmer"
                                ]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "doc_id": {
                            "type": "keyword"
                        },
                        "title": {
                            "type": "text",
                            "analyzer": "climate_analyzer",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "climate_analyzer"
                        },
                        "document_keywords": {
                            "type": "keyword"
                        },
                        "structure_info": {
                            "properties": {
                                "page_count": {"type": "integer"},
                                "table_count": {"type": "integer"},
                                "form_count": {"type": "integer"},
                                "line_count": {"type": "integer"},
                                "has_tables": {"type": "boolean"},
                                "has_forms": {"type": "boolean"}
                            }
                        },
                        "metadata": {
                            "type": "object",
                            "enabled": False
                        },
                        "timestamp": {
                            "type": "date"
                        }
                    }
                }
            }
            
            # Create the index
            response = self.opensearch_client.indices.create(
                index=self.documents_index,
                body=mapping
            )
            
            logger.info(f"Created documents index {self.documents_index}: {response}")
            
        except Exception as e:
            logger.error(f"Failed to create documents index mapping: {str(e)}")
            raise
    
    def parse_sqs_records(self, records: List[Dict]) -> List[Dict[str, Any]]:
        """Parse SQS records containing SNS messages"""
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
        """Download file content from S3"""
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
        """Extract document structure from Textract response"""
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
    
    def extract_keywords_from_text(self, text_content: str) -> List[str]:
        """Extract keywords from document text for TF-IDF optimization"""
        try:
            # Simple keyword extraction - can be enhanced later
            import re
            
            # Remove common stop words and extract meaningful terms
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
            }
            
            # Extract words (2+ characters, alphanumeric)
            words = re.findall(r'\b[a-zA-Z]{2,}\b', text_content.lower())
            
            # Filter out stop words and get unique terms
            keywords = list(set([word for word in words if word not in stop_words]))
            
            # Sort by frequency in document
            word_freq = {}
            for word in words:
                if word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Return top keywords sorted by frequency
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
            return [word for word, freq in top_keywords]
            
        except Exception as e:
            logger.error(f"Failed to extract keywords: {str(e)}")
            return []
    
    def index_document_in_opensearch(self, doc_id: str, text_content: str, 
                                   structure_info: Dict, metadata: Dict) -> Dict[str, Any]:
        """Index full document in OpenSearch for TF-IDF keyword search"""
        import time
        
        try:
            timing = {}
            
            # Extract keywords from document
            start = time.time()
            document_keywords = self.extract_keywords_from_text(text_content)
            timing['keyword_extraction'] = time.time() - start
            logger.info(f"Extracted {len(document_keywords)} keywords in {timing['keyword_extraction']:.2f}s")
            
            # Get document title from metadata if available
            title = metadata.get('document_metadata', {}).get('title', f"Document {doc_id}")
            
            # Create document for keyword index (full document for proper TF-IDF)
            start = time.time()
            document = {
                'doc_id': doc_id,
                'title': title,
                'content': text_content,  # Full text for TF-IDF calculation
                'document_keywords': document_keywords,
                'structure_info': structure_info,
                'metadata': metadata,
                'timestamp': datetime.utcnow().isoformat()
            }
            timing['document_preparation'] = time.time() - start
            
            # Index in documents index
            start = time.time()
            result = self.opensearch_client.index(
                index=self.documents_index,
                id=doc_id,
                body=document,
                refresh=False  # Don't wait for index refresh - document indexed but searchable in ~1 sec
            )
            timing['opensearch_call'] = time.time() - start
            logger.info(f"OpenSearch index call completed in {timing['opensearch_call']:.2f}s")
            
            if result.get('result') in ['created', 'updated']:
                logger.info(f"Indexed document {doc_id} in {self.documents_index}: {result.get('result')}")
                logger.info(f"Document length: {len(text_content)} chars, Keywords: {len(document_keywords)}")
                
                return {
                    'status': 'success',
                    'method': 'document_level_indexing',
                    'result': result,
                    'keywords_count': len(document_keywords),
                    'document_length': len(text_content),
                    'timing': timing
                }
            else:
                raise Exception(f"Unexpected indexing result: {result}")
                
        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {str(e)}")
            raise
    
    def publish_completion_message(self, doc_id: str, indexing_result: Dict) -> None:
        """Publish keyword indexing completion message"""
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
                        'opensearch_result': indexing_result.get('result', {}).get('result'),
                        'keywords_count': indexing_result.get('keywords_count'),
                        'document_length': indexing_result.get('document_length')
                    },
                    'integration_flags': {
                        'database_tracking_enabled': True,
                        'audit_first_design': True,
                        'managed_opensearch': True
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
        """Process a single document for keyword indexing"""
        import time
        
        doc_id = message_data['doc_id']
        timing = {}
        start_total = time.time()
        
        try:
            logger.info(f"Processing keyword indexing for doc_id: {doc_id}")
            
            # Update status to in_progress
            start = time.time()
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_indexing',
                status='in_progress'
            )
            timing['db_status_update'] = time.time() - start
            
            # Download text file
            logger.info(f"Downloading text from {message_data['text_location']}")
            start = time.time()
            text_content = self.download_s3_file(message_data['text_location'])
            timing['text_download'] = time.time() - start
            logger.info(f"Downloaded text file: {len(text_content)} characters in {timing['text_download']:.2f}s")
            
            # Download structure file
            logger.info(f"Downloading structure from {message_data['structure_location']}")
            start = time.time()
            structure_content = self.download_s3_file(message_data['structure_location'])
            structure_data = json.loads(structure_content)
            timing['structure_download'] = time.time() - start
            logger.info(f"Downloaded structure file: {len(structure_data.get('Blocks', []))} blocks in {timing['structure_download']:.2f}s")
            
            # Extract document structure
            start = time.time()
            structure_info = self.extract_document_structure(structure_content)
            timing['structure_extraction'] = time.time() - start
            logger.info(f"Extracted structure in {timing['structure_extraction']:.2f}s")
            
            # Index document in OpenSearch
            start = time.time()
            indexing_result = self.index_document_in_opensearch(
                doc_id=doc_id,
                text_content=text_content,
                structure_info=structure_info,
                metadata={
                    'processing_metadata': message_data.get('processing_metadata', {}),
                    'document_metadata': message_data.get('document_metadata', {})
                }
            )
            timing['opensearch_indexing'] = time.time() - start
            logger.info(f"OpenSearch indexing completed in {timing['opensearch_indexing']:.2f}s")
            
            # Update status to completed
            start = time.time()
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_indexing',
                status='completed'
            )
            timing['db_completion_update'] = time.time() - start
            
            # Publish completion message
            start = time.time()
            self.publish_completion_message(doc_id, indexing_result)
            timing['sns_publish'] = time.time() - start
            
            timing['total'] = time.time() - start_total
            
            # Log timing summary
            logger.info(f"⏱️  TIMING SUMMARY for {doc_id}:")
            logger.info(f"  Text download:        {timing['text_download']:6.2f}s")
            logger.info(f"  Structure download:   {timing['structure_download']:6.2f}s")
            logger.info(f"  Structure extraction: {timing['structure_extraction']:6.2f}s")
            logger.info(f"  OpenSearch indexing:  {timing['opensearch_indexing']:6.2f}s")
            logger.info(f"  DB updates:           {timing['db_status_update'] + timing['db_completion_update']:6.2f}s")
            logger.info(f"  SNS publish:          {timing['sns_publish']:6.2f}s")
            logger.info(f"  TOTAL:                {timing['total']:6.2f}s")
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'indexing_result': indexing_result,
                'timing': timing
            }
            
        except Exception as e:
            timing['total'] = time.time() - start_total
            logger.error(f"Error processing keyword indexing for {doc_id} after {timing['total']:.2f}s: {str(e)}")
            
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
                'error': str(e),
                'timing': timing
            }

def lambda_handler(event, context):
    """Lambda handler for Managed OpenSearch Keyword Indexer"""
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
