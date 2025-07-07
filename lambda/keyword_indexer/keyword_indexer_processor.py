#!/usr/bin/env python3
"""
Keyword Indexer Processor
Ports OpenSearch keyword indexing functionality from POC to AWS Lambda
Processes text-extraction-complete messages and indexes documents in OpenSearch
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeywordIndexerProcessor:
    """
    Keyword indexer processor that ports POC OpenSearchIndexer functionality
    """
    
    def __init__(self):
        # AWS clients
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment variables
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.index_name = os.environ.get('INDEX_NAME', 'climate-risk-keyword-index')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Database manager (imported from layer)
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
        except ImportError as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
            self.db_manager = None
        
        # Initialize OpenSearch client
        self.opensearch_client = self._create_opensearch_client()
        
        # Create index if it doesn't exist
        self._ensure_index_exists()

    def _create_opensearch_client(self):
        """Create OpenSearch client with AWS authentication"""
        try:
            if not self.opensearch_endpoint:
                raise ValueError("OPENSEARCH_ENDPOINT environment variable not set")
            
            # Extract host from endpoint URL
            host = self.opensearch_endpoint.replace('https://', '').replace('http://', '')
            
            # AWS authentication for OpenSearch Serverless
            auth = AWSRequestsAuth(
                aws_access_key=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                aws_token=os.environ.get('AWS_SESSION_TOKEN'),
                aws_host=host,
                aws_region=self.region,
                aws_service='aoss'  # OpenSearch Serverless
            )
            
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=auth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
            
            logger.info(f"OpenSearch client created for endpoint: {self.opensearch_endpoint}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client: {e}")
            raise

    def _ensure_index_exists(self):
        """Create index with enhanced mapping from POC if it doesn't exist"""
        try:
            if self.opensearch_client.indices.exists(index=self.index_name):
                logger.info(f"Index {self.index_name} already exists")
                return
            
            # Enhanced mapping ported from POC OpenSearchIndexer.py
            mapping = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 1
                    },
                    "analysis": {
                        "analyzer": {
                            "path_analyzer": {
                                "type": "custom",
                                "tokenizer": "path_hierarchy"
                            },
                            "metadata_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "asciifolding"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        # Core document fields
                        "doc_id": {"type": "keyword"},
                        "content": {
                            "type": "text",
                            "analyzer": "standard",
                            "term_vector": "with_positions_offsets"
                        },
                        
                        # Enhanced metadata fields from POC
                        "title": {
                            "type": "text",
                            "analyzer": "metadata_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "suggest": {
                                    "type": "completion"
                                }
                            }
                        },
                        "title_metadata": {
                            "properties": {
                                "confidence": {"type": "float"},
                                "source": {"type": "keyword"}
                            }
                        },
                        
                        "author": {
                            "type": "text",
                            "analyzer": "metadata_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "author_metadata": {
                            "properties": {
                                "confidence": {"type": "float"},
                                "source": {"type": "keyword"}
                            }
                        },
                        
                        # Date fields
                        "dates": {
                            "properties": {
                                "creation_date": {
                                    "type": "date",
                                    "format": "strict_date_optional_time||epoch_millis"
                                },
                                "modification_date": {
                                    "type": "date",
                                    "format": "strict_date_optional_time||epoch_millis"
                                },
                                "processing_date": {
                                    "type": "date",
                                    "format": "strict_date_optional_time||epoch_millis"
                                }
                            }
                        },
                        
                        # Language and structural metadata
                        "language": {"type": "keyword"},
                        "structural": {
                            "properties": {
                                "has_toc": {"type": "boolean"},
                                "section_count": {"type": "integer"},
                                "has_references": {"type": "boolean"},
                                "figure_count": {"type": "integer"},
                                "table_count": {"type": "integer"}
                            }
                        },
                        
                        # Source information
                        "source": {
                            "properties": {
                                "producer": {"type": "keyword"},
                                "pdf_version": {"type": "keyword"},
                                "pages": {"type": "integer"}
                            }
                        },
                        
                        # Processing information
                        "processing": {
                            "properties": {
                                "overall_confidence": {"type": "float"},
                                "status": {"type": "keyword"},
                                "word_count": {"type": "integer"},
                                "warnings": {"type": "keyword"}
                            }
                        },
                        
                        # Path fields with specialized analyzer
                        "pdf_path": {
                            "type": "text",
                            "analyzer": "path_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "text_path": {
                            "type": "text",
                            "analyzer": "path_analyzer",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        
                        # Indexing metadata
                        "indexed_at": {"type": "date"}
                    }
                }
            }
            
            # Create index
            self.opensearch_client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Created index {self.index_name} with enhanced mapping")
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise

    def lambda_handler(self, event, context):
        """Main Lambda handler for processing SQS messages"""
        
        logger.info(f"Processing {len(event['Records'])} records")
        
        results = []
        successful = 0
        failed = 0
        
        for record in event['Records']:
            try:
                result = self.process_sqs_record(record)
                results.append(result)
                
                if result.get('success'):
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing SQS record: {e}")
                results.append({'success': False, 'error': str(e)})
                failed += 1
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            })
        }

    def process_sqs_record(self, record: Dict) -> Dict:
        """Process individual SQS record from text-extraction-complete topic"""
        
        try:
            # Parse SQS message (from SNS)
            message_body = json.loads(record['body'])
            
            # Handle both direct SNS messages and SNS-wrapped messages
            if 'Message' in message_body:
                # SNS message wrapped in SQS
                sns_message = json.loads(message_body['Message'])
            else:
                # Direct message
                sns_message = message_body
            
            logger.info(f"Processing keyword indexing for stage: {sns_message.get('stage', 'unknown')}")
            
            # Process text_ready message for keyword indexing
            if sns_message.get('stage') == 'text_ready':
                return self.process_text_ready_message(sns_message)
            else:
                logger.warning(f"Unexpected message stage: {sns_message.get('stage')}")
                return {'success': False, 'error': 'Unexpected message stage'}
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            raise

    def process_text_ready_message(self, message: Dict) -> Dict:
        """Process text_ready message for keyword indexing"""
        
        # Extract message components
        doc_id = message.get('doc_id')
        full_text_location = message.get('full_text_location')
        filename = message.get('filename', 'unknown')
        
        if not doc_id:
            raise ValueError("Missing doc_id in message")
        
        if not full_text_location:
            raise ValueError("Missing full_text_location in message")
        
        try:
            logger.info(f"Starting keyword indexing for document {doc_id}")
            
            # Update processing status in database
            if self.db_manager:
                self.update_processing_status(doc_id, 'PROCESSING', 'Starting keyword indexing')
            
            # Read full text from S3
            full_text = self.read_full_text(full_text_location)
            
            # Get document metadata from DocumentIDManager
            metadata = self.get_document_metadata(doc_id)
            
            # Prepare document for indexing (port from POC)
            doc_data = self.prepare_document_for_indexing(doc_id, full_text, metadata, filename)
            
            # Index document in OpenSearch
            success = self.index_document(doc_id, doc_data)
            
            if success:
                # Update success status
                if self.db_manager:
                    self.update_processing_status(doc_id, 'COMPLETED', 'Keyword indexing completed successfully')
                
                logger.info(f"Successfully indexed document {doc_id} for keyword search")
                
                return {
                    'success': True,
                    'doc_id': doc_id,
                    'indexed_at': datetime.utcnow().isoformat()
                }
            else:
                raise Exception("Document indexing failed")
                
        except Exception as e:
            logger.error(f"Keyword indexing failed for document {doc_id}: {e}")
            
            # Update error status
            if self.db_manager:
                self.update_processing_status(doc_id, 'FAILED', str(e))
            
            raise

    def read_full_text(self, location: Dict) -> str:
        """Read full text from S3 location"""
        
        try:
            bucket = location['bucket']
            key = location['key']
            
            logger.info(f"Reading text from s3://{bucket}/{key}")
            
            response = self.s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            # Handle different content types
            if isinstance(content, bytes):
                text = content.decode('utf-8')
            else:
                text = str(content)
            
            logger.info(f"Successfully read {len(text)} characters")
            return text
            
        except Exception as e:
            logger.error(f"Error reading text from S3: {e}")
            raise

    def get_document_metadata(self, doc_id: str) -> Dict:
        """Get document metadata from DocumentIDManager"""
        
        try:
            if self.db_manager:
                metadata = self.db_manager.get_document_metadata(doc_id)
                if metadata:
                    return metadata
            
            # Return minimal metadata if database not available
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
        """Prepare document for indexing with enhanced metadata (ported from POC)"""
        
        try:
            # Extract metadata values with nested dictionary handling (from POC)
            title = metadata.get('title', {})
            if isinstance(title, dict) and 'value' in title:
                title_value = title['value']
                if isinstance(title_value, dict) and 'value' in title_value:
                    title_value = title_value['value']
            else:
                title_value = filename or 'Untitled'

            author = metadata.get('author', {})
            if isinstance(author, dict) and 'value' in author:
                author_value = author['value']
            else:
                author_value = None

            language = metadata.get('language', {})
            if isinstance(language, dict) and 'value' in language:
                language_value = language['value']
                if isinstance(language_value, dict) and 'value' in language_value:
                    language_value = language_value['value']
            else:
                language_value = 'en'

            # Calculate word count
            word_count = len(full_text.split()) if full_text else 0

            # Prepare document with enhanced metadata structure (from POC)
            doc_data = {
                "doc_id": doc_id,
                "content": full_text,
                "title": title_value,
                "title_metadata": {
                    "confidence": title.get('confidence', 0.8) if isinstance(title, dict) else 0.8,
                    "source": "textract"
                },
                "author": author_value,
                "author_metadata": {
                    "confidence": author.get('confidence', 0.8) if isinstance(author, dict) else 0.8,
                    "source": "textract"
                },
                "language": language_value,
                "dates": {
                    "processing_date": datetime.utcnow().isoformat()
                },
                "processing": {
                    "overall_confidence": metadata.get('processing', {}).get('overall_confidence', 0.8),
                    "status": "indexed",
                    "word_count": word_count
                },
                "indexed_at": datetime.utcnow().isoformat()
            }

            return doc_data

        except Exception as e:
            logger.error(f"Error preparing document {doc_id}: {e}")
            raise

    def index_document(self, doc_id: str, doc_data: Dict) -> bool:
        """Index document in OpenSearch"""
        
        try:
            # Index document (remove refresh=True for OpenSearch Serverless)
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
        """Update processing status in database"""
        
        if not self.db_manager:
            logger.warning("Database manager not available for status update")
            return
        
        try:
            # Update keyword indexing status using proper DatabaseManager method
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
            
            logger.info(f"Updated keyword indexing status for {doc_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")

def lambda_handler(event, context):
    """Lambda entry point"""
    processor = KeywordIndexerProcessor()
    return processor.lambda_handler(event, context)
