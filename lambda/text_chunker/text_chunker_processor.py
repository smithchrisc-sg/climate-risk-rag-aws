#!/usr/bin/env python3
"""
Text Chunker Processor - STANDARDIZED MESSAGING VERSION
Processes text documents using smart structured chunking with standardized message formats
"""

import boto3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import uuid

# Import standardized messaging
from standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextChunkerProcessor:
    def __init__(self):
        """Initialize the text chunker processor with standardized messaging"""
        self.s3 = boto3.client('s3')
        
        # Import shared utilities from lambda layer
        try:
            from DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
            self.db_manager = None
        
        # Environment variables
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        self.chunks_ready_topic_arn = os.environ.get('CHUNKS_READY_TOPIC_ARN', 
                                                   'arn:aws:sns:us-east-1:861276078413:chunks-ready')
        
        # Initialize standardized messaging
        self.message_publisher = StandardizedMessagePublisher()
        self.message_parser = StandardizedMessageParser()
        
        # Import smart chunker from shared layer
        try:
            from structured_chunking_smart_complete import SmartStructuredChunker
            
            # Initialize smart structured chunker with optimized settings
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
            logger.info("Using smart structured chunker with semantic overlap")
        except ImportError:
            logger.warning("Smart chunker not available, using basic chunking")
            self.structured_chunker = None
        
        logger.info("Text Chunker Processor initialized with standardized messaging")

    def lambda_handler(self, event, context):
        """Lambda handler for processing standardized SQS messages"""
        
        results = []
        
        try:
            logger.info(f"Processing {len(event.get('Records', []))} records")
            
            for record in event.get('Records', []):
                try:
                    result = self.process_sqs_record(record)
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error processing SQS record: {e}")
                    results.append({'success': False, 'error': str(e)})
                    
                    # Update database status on error if possible
                    if self.db_manager:
                        try:
                            # Extract doc_id from record for error tracking
                            message = self.message_parser.parse_sns_message({'Records': [record]})
                            doc_id = message.get('doc_id')
                            if doc_id:
                                self.update_processing_status(doc_id, 'FAILED', 0, str(e))
                        except:
                            pass  # Don't fail on error tracking failure
            
            # Summary response
            successful = len([r for r in results if r.get('success')])
            failed = len([r for r in results if not r.get('success')])
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'processed': len(results),
                    'successful': successful,
                    'failed': failed,
                    'results': results,
                    'standardized_messaging': True
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    def process_sqs_record(self, record: Dict) -> Dict:
        """Process individual SQS record with standardized message format"""
        
        try:
            # Parse standardized message
            message = self.message_parser.parse_sns_message({'Records': [record]})
            
            # Validate message format - only accept text_ready stage
            if message.get('stage') != 'text_ready':
                raise ValueError(f"Invalid message stage: {message.get('stage')}. Expected text_ready")
            
            logger.info(f"Processing standardized message for stage: {message.get('stage')}")
            logger.info(f"Document ID: {message.get('doc_id')}")
            
            # Extract processing information
            processing_info = self.message_parser.extract_processing_info(message)
            
            # Process text chunking
            return self.process_text_chunking(processing_info)
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            raise
    
    def process_text_chunking(self, processing_info: Dict) -> Dict:
        """Process text chunking with standardized message handling"""
        
        doc_id = processing_info['doc_id']
        doc_hash = processing_info['doc_hash']
        text_folder_url = processing_info.get('text_folder_url') or processing_info.get('text_location')  # Support both
        
        if not doc_id:
            raise ValueError("Missing doc_id in message")
        
        try:
            logger.info(f"Starting chunking for document {doc_id}")
            processing_start = datetime.utcnow()
            
            # Update processing status in database
            if self.db_manager:
                self.update_processing_status(doc_id, 'PROCESSING', 0, 'Starting text chunking')
            
            # Read full text from S3 folder
            full_text = self.read_text_from_s3(text_folder_url)
            if not full_text:
                raise ValueError("No text content found")
            
            # Read document structure if available (construct path to textract_response.json)
            textract_structure = None
            if text_folder_url:
                try:
                    # Construct path to textract_response.json from folder URL
                    if text_folder_url.endswith('/'):
                        textract_response_url = f"{text_folder_url}textract_response.json"
                    else:
                        textract_response_url = f"{text_folder_url}/textract_response.json"
                    
                    textract_structure = self.read_document_structure(textract_response_url)
                    logger.info("Successfully loaded Textract structure for smart chunking")
                except Exception as e:
                    logger.warning(f"Could not read structure data: {e}, proceeding with text-only chunking")
            
            # Create chunks using smart chunker
            chunks = self.create_chunks(full_text, textract_structure, doc_id)
            
            if not chunks:
                raise ValueError("No chunks created from text")
            
            # Save chunks to S3
            chunks_location = self.save_chunks_to_s3(doc_id, chunks, full_text)
            
            # Calculate processing metadata
            processing_time = (datetime.utcnow() - processing_start).total_seconds() * 1000
            
            processing_metadata = {
                'chunks_created': len(chunks),
                'total_characters': len(full_text),
                'processing_duration_ms': int(processing_time),
                'cost_estimate': 0.0,  # Text chunking is essentially free
                'selective_migration_used': processing_info.get('integration_flags', {}).get('selective_migration_used', False)
            }
            
            # Update database status
            if self.db_manager:
                self.update_processing_status(doc_id, 'COMPLETED', len(chunks), 'Text chunking completed successfully')
            
            # Publish standardized chunks ready message
            self.publish_chunks_ready(doc_id, doc_hash, chunks_location, text_folder_url, 
                                    processing_info.get('document_metadata', {}), processing_metadata)
            
            logger.info(f"Successfully processed {len(chunks)} chunks for document {doc_id}")
            
            return {
                'success': True,
                'doc_id': doc_id,
                'chunks_created': len(chunks),
                'chunks_location': chunks_location,
                'processing_time_ms': int(processing_time),
                'standardized_messaging': True
            }
            
        except Exception as e:
            logger.error(f"Text chunking failed for document {doc_id}: {e}")
            
            # Update database status on error
            if self.db_manager:
                self.update_processing_status(doc_id, 'FAILED', 0, str(e))
            
            raise

    def read_text_from_s3(self, text_folder_url: str) -> str:
        """Read text content from S3 folder URL (constructs path to raw_text.txt)"""
        try:
            # Validate text_folder_url
            if not text_folder_url:
                raise ValueError("text_folder_url is None or empty")
            
            # Construct path to raw_text.txt file from folder URL
            if text_folder_url.endswith('/'):
                raw_text_url = f"{text_folder_url}raw_text.txt"
            else:
                raw_text_url = f"{text_folder_url}/raw_text.txt"
            
            # Parse S3 location
            if raw_text_url.startswith('s3://'):
                # Remove s3:// prefix and split bucket/key
                s3_path = raw_text_url[5:]
                bucket, key = s3_path.split('/', 1)
            else:
                raise ValueError(f"Invalid S3 location format: {raw_text_url}")
            
            logger.info(f"Reading text from s3://{bucket}/{key}")
            
            # Get object from S3
            response = self.s3.get_object(Bucket=bucket, Key=key)
            text_content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Successfully read {len(text_content)} characters from S3")
            return text_content
            
        except Exception as e:
            logger.error(f"Error reading text from S3: {e}")
            raise

    def read_document_structure(self, structure_location: str) -> Optional[Dict]:
        """Read document structure from S3 location"""
        try:
            # Validate structure_location
            if not structure_location:
                logger.warning("structure_location is None or empty, skipping structure reading")
                return None
            
            # Parse S3 location
            if structure_location.startswith('s3://'):
                s3_path = structure_location[5:]
                bucket, key = s3_path.split('/', 1)
            else:
                raise ValueError(f"Invalid S3 location format: {structure_location}")
            
            logger.info(f"Reading structure from s3://{bucket}/{key}")
            
            # Get object from S3
            response = self.s3.get_object(Bucket=bucket, Key=key)
            structure_data = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info("Successfully loaded document structure")
            return structure_data
            
        except Exception as e:
            logger.warning(f"Could not read document structure: {e}")
            return None

    def create_chunks(self, full_text: str, textract_structure: Optional[Dict], doc_id: str) -> List[Dict]:
        """Create structured chunks from text"""
        
        try:
            if self.structured_chunker and textract_structure:
                # Use smart structured chunker with Textract data
                logger.info("Using smart structured chunker with Textract structure")
                chunks = self.structured_chunker.chunk_with_structure(full_text, textract_structure)
            elif self.structured_chunker:
                # Use smart chunker without structure
                logger.info("Using smart structured chunker (text-only)")
                chunks = self.structured_chunker.chunk_text(full_text)
            else:
                # Fallback to basic chunking
                logger.info("Using basic chunking")
                chunks = self.basic_chunk_text(full_text)
            
            # Add metadata to chunks
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                # Convert StructuredChunk dataclass to dictionary if needed
                if hasattr(chunk, '__dataclass_fields__'):
                    # It's a dataclass, convert to dict
                    chunk_dict = {
                        'text': chunk.text,
                        'chunk_type': getattr(chunk, 'chunk_type', 'structured'),
                        'hierarchy_level': getattr(chunk, 'hierarchy_level', 0),
                        'page_number': getattr(chunk, 'page_number', 1),
                        'section_context': getattr(chunk, 'section_context', ''),
                        'word_count': getattr(chunk, 'word_count', len(chunk.text.split())),
                        'sentence_count': getattr(chunk, 'sentence_count', chunk.text.count('.') + chunk.text.count('!') + chunk.text.count('?')),
                        'bounding_box': getattr(chunk, 'bounding_box', {}),
                        'metadata': getattr(chunk, 'metadata', {})
                    }
                elif isinstance(chunk, dict):
                    # Already a dictionary
                    chunk_dict = chunk.copy()
                else:
                    # Fallback - create basic dictionary
                    chunk_dict = {
                        'text': str(chunk),
                        'chunk_type': 'basic'
                    }
                
                # Add standard metadata
                chunk_dict.update({
                    'chunk_id': f"{doc_id}_chunk_{i:03d}",
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'created_at': datetime.utcnow().isoformat() + 'Z'
                })
                
                processed_chunks.append(chunk_dict)
            
            # Replace chunks with processed chunks
            chunks = processed_chunks
            
            logger.info(f"Created {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating chunks: {e}")
            raise

    def basic_chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
        """Basic text chunking fallback"""
        
        chunks = []
        text_length = len(text)
        start = 0
        chunk_index = 0
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence ending within the last 100 characters
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size - 100:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'start_offset': start,
                    'end_offset': end,
                    'character_count': len(chunk_text),
                    'chunk_type': 'basic'
                })
                chunk_index += 1
            
            start = max(start + chunk_size - overlap, end)
        
        return chunks

    def save_chunks_to_s3(self, doc_id: str, chunks: List[Dict], full_text: str) -> str:
        """Save chunks to S3 with structured organization"""
        
        try:
            base_path = f"data_lake/{doc_id}"
            
            # Save individual chunk files with 4-digit padding
            chunk_files = []
            for i, chunk in enumerate(chunks):
                chunk_index = str(i).zfill(4)  # 4-digit padding: 0000, 0001, 0002, etc.
                chunk_filename = f"{doc_id}_chunk_{chunk_index}.json"
                chunk_key = f"{base_path}/{chunk_filename}"
                
                # Update chunk with proper naming
                chunk['chunk_id'] = f"{doc_id}_chunk_{chunk_index}"
                chunk['chunk_filename'] = chunk_filename
                
                self.s3.put_object(
                    Bucket=self.chunks_bucket,
                    Key=chunk_key,
                    Body=json.dumps(chunk, default=str).encode('utf-8'),
                    ContentType='application/json'
                )
                
                chunk_files.append(chunk_filename)
            
            # Save chunks summary
            summary = {
                'doc_id': doc_id,
                'total_chunks': len(chunks),
                'total_characters': len(full_text),
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'chunk_files': chunk_files
            }
            
            summary_key = f"{base_path}/summary.json"
            self.s3.put_object(
                Bucket=self.chunks_bucket,
                Key=summary_key,
                Body=json.dumps(summary, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            
            # Save full text for NLP processing
            full_text_key = f"{base_path}/full_text.json"
            full_text_data = {
                'doc_id': doc_id,
                'full_text': full_text,
                'character_count': len(full_text),
                'created_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            self.s3.put_object(
                Bucket=self.chunks_bucket,
                Key=full_text_key,
                Body=json.dumps(full_text_data, default=str).encode('utf-8'),
                ContentType='application/json'
            )
            
            chunks_location = f"s3://{self.chunks_bucket}/{base_path}/"
            logger.info(f"Saved {len(chunks)} chunks to {chunks_location}")
            
            return chunks_location
            
        except Exception as e:
            logger.error(f"Error saving chunks to S3: {e}")
            raise

    def publish_chunks_ready(self, doc_id: str, doc_hash: str, chunks_location: str, 
                           text_location: str, document_metadata: Dict, processing_metadata: Dict):
        """Publish standardized chunks ready message"""
        
        try:
            self.message_publisher.publish_chunks_ready(
                doc_id=doc_id,
                doc_hash=doc_hash,
                chunks_location=chunks_location,
                text_location=text_location,
                document_metadata=document_metadata,
                processing_metadata=processing_metadata,
                topic_arn=self.chunks_ready_topic_arn
            )
            
            logger.info(f"Published standardized chunks ready message for {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish chunks ready message: {e}")
            raise

    def update_processing_status(self, doc_id: str, status: str, chunks_created: int, notes: str):
        """Update processing status in database"""
        
        if not self.db_manager:
            return
        
        try:
            conn = self.db_manager.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO text_chunking_status (doc_id, status, chunks_created, notes, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        chunks_created = EXCLUDED.chunks_created,
                        notes = EXCLUDED.notes,
                        updated_at = EXCLUDED.updated_at
                """, (doc_id, status, chunks_created, notes, datetime.utcnow()))
                
                conn.commit()
                logger.info(f"Updated chunking status: {doc_id} -> {status}")
                
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
        finally:
            if 'conn' in locals():
                conn.close()


def lambda_handler(event, context):
    """Lambda entry point"""
    processor = TextChunkerProcessor()
    return processor.lambda_handler(event, context)


# For testing
if __name__ == "__main__":
    # Test with standardized message format
    test_event = {
        'Records': [{
            'body': json.dumps({
                "version": "1.0",
                "timestamp": "2025-07-08T20:15:00.000Z",
                "source": "climate-risk-rag-system",
                "stage": "text_ready",
                "doc_id": "test-doc-id",
                "doc_hash": "test-doc-hash",
                "document_metadata": {
                    "original_filename": "test.pdf",
                    "file_size": 142850,
                    "page_count": 3
                },
                "data_locations": {
                    "text_location": "s3://test-bucket/extracted_documents/test-hash/raw_text.txt",
                    "structure_location": "s3://test-bucket/extracted_documents/test-hash/textract_response.json"
                },
                "processing_metadata": {
                    "total_characters": 18622,
                    "processing_duration_ms": 5000
                },
                "integration_flags": {
                    "documentid_manager_integration": True,
                    "selective_migration_used": False
                }
            })
        }]
    }
    
    processor = TextChunkerProcessor()
    result = processor.lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
