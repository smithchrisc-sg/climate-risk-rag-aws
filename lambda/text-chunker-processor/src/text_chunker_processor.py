"""
Text Chunker Processor Lambda Function
Processes text_ready messages and performs smart structured chunking
Uses audit-first database design with DatabaseManager
PRESERVES ALL SMART CHUNKING FUNCTIONALITY
"""

import json
import boto3
import logging
import os
import hashlib
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import from locked database core layer - DO NOT CHANGE
from utils.DatabaseManager import DatabaseManager

# Import smart structured chunker - PRESERVED FUNCTIONALITY
from smart_structured_chunker import SmartStructuredChunker

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextChunkerProcessor:
    """
    Smart structured text chunker with audit-first database design
    PRESERVES ALL CHUNKING FUNCTIONALITY
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment configuration
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.chunks_ready_topic_arn = os.environ.get('CHUNKS_READY_TOPIC_ARN')
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        # Initialize smart structured chunker - PRESERVED FUNCTIONALITY
        self.structured_chunker = SmartStructuredChunker(
            min_chunk_size=150,         # Larger for complete thoughts
            max_chunk_size=1200,        # Allow larger chunks for sections
            overlap_sentences=0,        # No fixed overlap
            semantic_overlap=True,      # Smart overlap when needed
            respect_boundaries=True,    # Respect section boundaries
            preserve_tables=True,       # Keep tables intact
            preserve_lists=True,        # Keep lists intact
            header_context=True         # Include context with headers
        )
        
        logger.info("✅ Text Chunker Processor initialized")
        logger.info(f"Text bucket: {self.text_bucket}")
        logger.info(f"Chunks bucket: {self.chunks_bucket}")
        logger.info("Using smart structured chunker with semantic overlap")
    
    def parse_text_ready_message(self, message_body: str) -> Dict[str, Any]:
        """Parse standardized text_ready message"""
        try:
            message = json.loads(message_body)
            
            # Extract key fields from standardized message
            doc_id = message.get('doc_id')
            stage = message.get('stage')
            data_locations = message.get('data_locations', {})
            
            if not doc_id:
                raise ValueError("Missing doc_id in message")
            
            if stage != 'text_ready':
                raise ValueError(f"Expected stage 'text_ready', got '{stage}'")
            
            # Extract S3 locations
            text_location = data_locations.get('text_location')
            structure_location = data_locations.get('structure_location')
            
            if not text_location or not structure_location:
                raise ValueError("Missing required S3 locations in message")
            
            return {
                'doc_id': doc_id,
                'text_location': text_location,
                'structure_location': structure_location,
                'processing_metadata': message.get('processing_metadata', {}),
                'document_metadata': message.get('document_metadata', {})
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse text_ready message: {e}")
            raise
    
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
    
    def create_smart_chunks(self, doc_id: str, raw_text: str, textract_response: Dict) -> List[Dict]:
        """Create smart structured chunks using preserved functionality"""
        try:
            logger.info(f"Creating smart structured chunks for doc_id: {doc_id}")
            
            # Use smart structured chunker - PRESERVED FUNCTIONALITY
            chunks = self.structured_chunker.create_smart_chunks(
                raw_text=raw_text,
                textract_response=textract_response,
                doc_id=doc_id
            )
            
            logger.info(f"Created {len(chunks)} smart structured chunks")
            
            # Log chunk statistics
            total_chars = sum(chunk['character_count'] for chunk in chunks)
            avg_chunk_size = total_chars / len(chunks) if chunks else 0
            
            logger.info(f"Chunk statistics:")
            logger.info(f"  Total chunks: {len(chunks)}")
            logger.info(f"  Total characters: {total_chars}")
            logger.info(f"  Average chunk size: {avg_chunk_size:.0f} characters")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to create smart chunks: {e}")
            raise
    
    def upload_chunks_to_s3(self, doc_id: str, chunks: List[Dict]) -> Dict[str, str]:
        """Upload chunks and metadata to S3"""
        try:
            # Create S3 paths
            chunks_prefix = f"chunks/{doc_id}/"
            
            # Upload individual chunks
            chunk_locations = []
            for chunk in chunks:
                chunk_key = f"{chunks_prefix}{chunk['chunk_id']}.json"
                
                # Upload chunk
                self.s3.put_object(
                    Bucket=self.chunks_bucket,
                    Key=chunk_key,
                    Body=json.dumps(chunk, indent=2),
                    ContentType='application/json'
                )
                
                chunk_locations.append(f"s3://{self.chunks_bucket}/{chunk_key}")
            
            # Create and upload metadata
            metadata = {
                'doc_id': doc_id,
                'total_chunks': len(chunks),
                'total_characters': sum(chunk['character_count'] for chunk in chunks),
                'chunk_locations': chunk_locations,
                'chunking_method': 'smart_structured',
                'chunking_settings': {
                    'min_chunk_size': self.structured_chunker.min_chunk_size,
                    'max_chunk_size': self.structured_chunker.max_chunk_size,
                    'semantic_overlap': self.structured_chunker.semantic_overlap,
                    'respect_boundaries': self.structured_chunker.respect_boundaries,
                    'preserve_tables': self.structured_chunker.preserve_tables,
                    'preserve_lists': self.structured_chunker.preserve_lists,
                    'header_context': self.structured_chunker.header_context
                },
                'created_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            metadata_key = f"{chunks_prefix}metadata.json"
            self.s3.put_object(
                Bucket=self.chunks_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Uploaded {len(chunks)} chunks and metadata to S3")
            
            return {
                'chunks_location': f"s3://{self.chunks_bucket}/{chunks_prefix}",
                'chunk_metadata_location': f"s3://{self.chunks_bucket}/{metadata_key}"
            }
            
        except Exception as e:
            logger.error(f"Failed to upload chunks to S3: {e}")
            raise
    
    def publish_completion_message(self, doc_id: str, s3_locations: Dict[str, str], 
                                 chunks_count: int, processing_metadata: Dict) -> None:
        """Publish chunks_ready completion message"""
        try:
            # Create standardized completion message
            message = {
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "climate-risk-rag-system",
                "stage": "chunks_ready",
                "doc_id": doc_id,
                "data_locations": {
                    "chunks_location": s3_locations['chunks_location'],
                    "chunk_metadata_location": s3_locations['chunk_metadata_location']
                },
                "processing_metadata": {
                    "chunks_created": chunks_count,
                    "chunking_method": "smart_structured",
                    "total_characters": processing_metadata.get('total_characters', 0),
                    "processing_completed": datetime.utcnow().isoformat() + "Z"
                },
                "integration_flags": {
                    "database_tracking_enabled": True,
                    "audit_first_design": True,
                    "smart_structured_chunking": True
                }
            }
            
            # Publish to SNS (if topic configured)
            if self.chunks_ready_topic_arn:
                response = self.sns.publish(
                    TopicArn=self.chunks_ready_topic_arn,
                    Message=json.dumps(message, default=str),
                    Subject=f"Text chunking complete: {doc_id}",
                    MessageAttributes={
                        'stage': {
                            'DataType': 'String',
                            'StringValue': 'chunks_ready'
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
                
                logger.info(f"Published chunks_ready message for {doc_id}: {response['MessageId']}")
            else:
                logger.info(f"No completion topic configured, skipping message publication for {doc_id}")
                
        except Exception as e:
            logger.error(f"Failed to publish completion message for {doc_id}: {e}")
            # Don't raise - this is not critical for the chunking process
    
    def process_text_ready_message(self, message_body: str) -> Dict[str, Any]:
        """Process a single text_ready message"""
        try:
            # Parse the standardized message
            parsed_message = self.parse_text_ready_message(message_body)
            doc_id = parsed_message['doc_id']
            
            logger.info(f"Processing text chunking for doc_id: {doc_id}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='chunking',
                status='in_progress'
            )
            
            # Download text and structure files
            files_data = self.download_text_files(
                text_location=parsed_message['text_location'],
                structure_location=parsed_message['structure_location']
            )
            
            # Create smart structured chunks - PRESERVED FUNCTIONALITY
            chunks = self.create_smart_chunks(
                doc_id=doc_id,
                raw_text=files_data['raw_text'],
                textract_response=files_data['textract_response']
            )
            
            # Upload chunks to S3
            s3_locations = self.upload_chunks_to_s3(doc_id, chunks)
            
            # Publish completion message
            processing_metadata = {
                'total_characters': len(files_data['raw_text']),
                'textract_blocks': len(files_data['textract_response'].get('blocks', []))
            }
            
            self.publish_completion_message(
                doc_id=doc_id,
                s3_locations=s3_locations,
                chunks_count=len(chunks),
                processing_metadata=processing_metadata
            )
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='chunking',
                status='completed'
            )
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'chunks_created': len(chunks),
                'chunks_location': s3_locations['chunks_location'],
                'chunk_metadata_location': s3_locations['chunk_metadata_location']
            }
            
        except Exception as e:
            # Extract doc_id for error status if possible
            doc_id = 'unknown'
            try:
                parsed = json.loads(message_body)
                doc_id = parsed.get('doc_id', 'unknown')
            except:
                pass
            
            logger.error(f"Error processing text_ready message for {doc_id}: {str(e)}")
            
            # Update status to failed if we have a doc_id
            if doc_id != 'unknown':
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='chunking',
                    status='failed',
                    error_message=str(e)
                )
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }

def lambda_handler(event, context):
    """Lambda handler for Text Chunker Processor"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        processor = TextChunkerProcessor()
        results = []
        
        # Handle SNS notifications (text extraction complete messages)
        if 'Records' in event:
            for record in event['Records']:
                if record.get('EventSource') == 'aws:sns':
                    # Parse SNS message
                    sns_message = record['Sns']['Message']
                    
                    logger.info(f"Processing SNS message for text chunking")
                    result = processor.process_text_ready_message(sns_message)
                    results.append(result)
                    
                elif record.get('eventSource') == 'aws:sqs':
                    # Handle SQS-wrapped SNS messages
                    try:
                        sqs_body = json.loads(record['body'])
                        if sqs_body.get('Type') == 'Notification':
                            sns_message = sqs_body['Message']
                            
                            logger.info(f"Processing SQS-wrapped SNS message for text chunking")
                            result = processor.process_text_ready_message(sns_message)
                            results.append(result)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message: {e}")
                        results.append({'status': 'error', 'error': f'SQS parse error: {e}'})
        
        # Handle direct invocation for testing
        elif 'doc_id' in event:
            logger.info("Processing direct invocation")
            # Convert direct event to message format for testing
            test_message = json.dumps(event)
            result = processor.process_text_ready_message(test_message)
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Text chunking jobs processed',
                'processed_records': len(results),
                'results': results
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
