#!/usr/bin/env python3
"""
Text Chunker Processor - DocumentIDManager Integration
Processes text documents using smart structured chunking with DocumentIDManager integration
"""

import boto3
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextChunkerProcessor:
    def __init__(self):
        """Initialize the text chunker processor with DocumentIDManager integration"""
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Import shared utilities from lambda layer
        try:
            from DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
            self.db_manager = None
        
        # Environment variables - updated for new bucket structure
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.coordination_topic_arn = os.environ.get('COORDINATION_TOPIC_ARN') or os.environ.get('CHUNKS_READY_TOPIC_ARN')
        
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
                header_context=True         # Natural header context
            )
            logger.info("Smart structured chunker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to import smart chunker: {e}")
            # Fallback to enhanced basic chunking
            self.structured_chunker = None
            logger.info("Using enhanced basic chunking with offset tracking")
    
    def lambda_handler(self, event, context):
        """Lambda handler for processing SQS messages from corrected TextExtractor"""
        
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
                            message_body = json.loads(record['body'])
                            if 'Message' in message_body:
                                sns_message = json.loads(message_body['Message'])
                            else:
                                sns_message = message_body
                            
                            doc_id = sns_message.get('doc_id')
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
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    def process_sqs_record(self, record: Dict) -> Dict:
        """Process individual SQS record from corrected TextExtractor"""
        
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
            
            logger.info(f"Processing message for stage: {sns_message.get('stage', 'unknown')}")
            logger.info(f"DocumentIDManager integration: {sns_message.get('documentid_manager_integration', False)}")
            
            # Process based on message type from corrected TextExtractor
            if sns_message.get('stage') == 'text_ready':
                return self.process_text_ready_message(sns_message)
            else:
                # Handle direct chunking requests (for testing)
                return self.process_direct_chunking_request(sns_message)
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            raise
    
    def process_text_ready_message(self, message: Dict) -> Dict:
        """Process text_ready message from corrected TextExtractor with DocumentIDManager integration"""
        
        # Extract message components - updated for corrected TextExtractor format
        doc_id = message.get('doc_id')
        doc_hash = message.get('doc_hash')
        full_text_location = message.get('full_text_location')
        structure_location = message.get('document_structure_location')
        documentid_integration = message.get('documentid_manager_integration', False)
        selective_migration = message.get('selective_migration_used', False)
        
        if not doc_id:
            raise ValueError("Missing doc_id in message from TextExtractor")
        
        try:
            logger.info(f"Starting chunking for document {doc_id}")
            logger.info(f"DocumentIDManager integration: {documentid_integration}")
            logger.info(f"Selective migration used: {selective_migration}")
            
            # Update processing status in database
            if self.db_manager:
                self.update_processing_status(doc_id, 'PROCESSING', 0, 'Starting text chunking')
            
            # Read full text from S3 - updated path structure
            full_text = self.read_full_text(full_text_location)
            
            # Read document structure if available
            textract_structure = None
            if structure_location:
                try:
                    textract_structure = self.read_document_structure(structure_location)
                    logger.info("Successfully loaded Textract structure for smart chunking")
                except Exception as e:
                    logger.warning(f"Could not read structure data: {e}, proceeding with text-only chunking")
            
            # Create structured chunks with smart overlap
            if self.structured_chunker and textract_structure:
                logger.info("Using smart structured chunking with Textract data")
                raw_chunks = self.structured_chunker.chunk_document(textract_structure)
                # Convert StructuredChunk objects to dictionaries and enhance with offsets
                chunks_dict = [self._structured_chunk_to_dict(chunk) for chunk in raw_chunks]
                chunks = self._enhance_chunks_with_offsets(chunks_dict, full_text)
            elif self.structured_chunker:
                logger.info("Using smart structured chunking with text-only")
                raw_chunks = self.structured_chunker.chunk_text(full_text)
                # Convert StructuredChunk objects to dictionaries and enhance with offsets
                chunks_dict = [self._structured_chunk_to_dict(chunk) for chunk in raw_chunks]
                chunks = self._enhance_chunks_with_offsets(chunks_dict, full_text)
            else:
                logger.info("Using enhanced basic chunking with offset tracking")
                chunks = self.basic_chunk_text(full_text)
            
            # Store chunks in S3 with improved naming: {doc_id}/{doc_id}_chunk_NNNN.json
            chunk_s3_keys = self.store_chunks_to_s3(chunks, doc_id, message, full_text)
            
            # Update processing status in database
            if self.db_manager:
                self.update_processing_status(doc_id, 'COMPLETED', len(chunks), 'Text chunking completed successfully')
            
            # Signal coordination logic for downstream processing
            self.signal_chunking_complete(doc_id, len(chunks))
            
            logger.info(f"Successfully chunked document {doc_id}: {len(chunks)} chunks created")
            
            return {
                'success': True,
                'doc_id': doc_id,
                'chunks_created': len(chunks),
                's3_keys': chunk_s3_keys,
                'chunking_strategy': 'smart_overlap' if self.structured_chunker else 'basic_enhanced',
                'documentid_manager_integration': documentid_integration,
                'processing_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Text chunking failed for document {doc_id}: {e}")
            
            # Update database status on error
            if self.db_manager:
                self.update_processing_status(doc_id, 'FAILED', 0, str(e))
            
            raise
    
    def process_direct_chunking_request(self, message: Dict) -> Dict:
        """Process direct chunking request (for testing)"""
        
        # Extract document identifier
        doc_id = message.get('doc_id') or message.get('document_id')
        text_content = message.get('text_content')
        s3_location = message.get('s3_location')
        
        if not doc_id:
            doc_id = f"direct_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Get text content
            if text_content:
                full_text = text_content
            elif s3_location:
                full_text = self.read_full_text(s3_location)
            else:
                raise ValueError("No text content or S3 location provided")
            
            # Chunk the text
            if self.structured_chunker:
                chunks = self.structured_chunker.chunk_text(full_text)
            else:
                chunks = self.basic_chunk_text(full_text)
            
            # Store chunks
            chunk_s3_keys = self.store_chunks_to_s3(chunks, doc_id, message, full_text)
            
            return {
                'success': True,
                'doc_id': doc_id,
                'chunks_created': len(chunks),
                's3_keys': chunk_s3_keys,
                'chunking_strategy': 'smart_overlap' if self.structured_chunker else 'basic'
            }
            
        except Exception as e:
            logger.error(f"Direct chunking failed: {e}")
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
    
    def read_document_structure(self, location: Dict) -> Dict:
        """Read Textract document structure from S3"""
        
        try:
            bucket = location['bucket']
            key = location['key']
            
            logger.info(f"Reading structure from s3://{bucket}/{key}")
            
            response = self.s3.get_object(Bucket=bucket, Key=key)
            structure_data = json.loads(response['Body'].read().decode('utf-8'))
            
            return structure_data
            
        except Exception as e:
            logger.error(f"Error reading structure from S3: {e}")
            raise
    
    def basic_chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
        """Enhanced basic text chunking with precise offset tracking"""
        
        chunks = []
        text_length = len(text)
        
        for i in range(0, text_length, chunk_size - overlap):
            start_char = i
            end_char = min(i + chunk_size, text_length)
            chunk_text = text[start_char:end_char]
            
            if chunk_text.strip():
                # Calculate word boundaries for better NLP integration
                word_start_offset, word_end_offset = self._find_word_boundaries(text, start_char, end_char)
                
                # Split into sentences for sentence-level offsets
                sentences = self._split_text_into_sentences(chunk_text)
                sentence_offsets = self._calculate_sentence_offsets(chunk_text, sentences, start_char)
                
                # Split into words for word-level offsets
                words = self._split_text_into_words(chunk_text)
                word_offsets = self._calculate_word_offsets(chunk_text, words, start_char)
                
                chunks.append({
                    'chunk_id': f"chunk_{len(chunks):03d}",
                    'text': chunk_text.strip(),
                    'start_char': start_char,
                    'end_char': end_char,
                    'chunk_type': 'text',
                    'offsets': {
                        'char_start': start_char,
                        'char_end': end_char,
                        'word_start': word_start_offset,
                        'word_end': word_end_offset,
                        'sentences': sentence_offsets,
                        'words': word_offsets
                    },
                    'metadata': {
                        'chunking_method': 'basic_enhanced',
                        'chunk_size': len(chunk_text),
                        'overlap_used': overlap if i > 0 else 0,
                        'sentence_count': len(sentences),
                        'word_count': len(words),
                        'char_count': len(chunk_text)
                    }
                })
        
        return chunks
    
    def _find_word_boundaries(self, full_text: str, start_char: int, end_char: int) -> tuple:
        """Find word boundaries to avoid cutting words in half"""
        
        # Find the start of the first complete word
        word_start = start_char
        while word_start > 0 and not full_text[word_start - 1].isspace():
            word_start -= 1
        
        # Find the end of the last complete word
        word_end = end_char
        while word_end < len(full_text) and not full_text[word_end].isspace():
            word_end += 1
        
        return word_start, min(word_end, len(full_text))
    
    def _split_text_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        
        # Enhanced sentence splitting
        sentence_endings = r'[.!?]+(?:\s+|$)'
        sentences = re.split(sentence_endings, text)
        
        # Filter out empty sentences and clean up
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _calculate_sentence_offsets(self, chunk_text: str, sentences: List[str], chunk_start: int) -> List[Dict]:
        """Calculate character offsets for each sentence within the chunk"""
        
        sentence_offsets = []
        current_pos = 0
        
        for i, sentence in enumerate(sentences):
            # Find the sentence in the chunk text
            sentence_start = chunk_text.find(sentence, current_pos)
            if sentence_start != -1:
                sentence_end = sentence_start + len(sentence)
                
                sentence_offsets.append({
                    'sentence_index': i,
                    'text': sentence,
                    'chunk_offset_start': sentence_start,
                    'chunk_offset_end': sentence_end,
                    'global_offset_start': chunk_start + sentence_start,
                    'global_offset_end': chunk_start + sentence_end,
                    'length': len(sentence)
                })
                
                current_pos = sentence_end
        
        return sentence_offsets
    
    def _split_text_into_words(self, text: str) -> List[str]:
        """Split text into words"""
        import re
        
        # Split on whitespace and punctuation, keeping the words
        words = re.findall(r'\b\w+\b', text)
        
        return words
    
    def _calculate_word_offsets(self, chunk_text: str, words: List[str], chunk_start: int) -> List[Dict]:
        """Calculate character offsets for each word within the chunk"""
        
        word_offsets = []
        current_pos = 0
        
        for i, word in enumerate(words):
            # Find the word in the chunk text
            word_start = chunk_text.find(word, current_pos)
            if word_start != -1:
                word_end = word_start + len(word)
                
                word_offsets.append({
                    'word_index': i,
                    'text': word,
                    'chunk_offset_start': word_start,
                    'chunk_offset_end': word_end,
                    'global_offset_start': chunk_start + word_start,
                    'global_offset_end': chunk_start + word_end,
                    'length': len(word)
                })
                
                current_pos = word_end
        
        return word_offsets
    
    def _enhance_chunks_with_offsets(self, chunks: List[Dict], full_text: str) -> List[Dict]:
        """Enhance chunks with detailed offset information for NLP integration"""
        
        enhanced_chunks = []
        current_position = 0
        
        for chunk in chunks:
            chunk_text = chunk['text']
            
            # Find the chunk's position in the full text
            chunk_start = full_text.find(chunk_text, current_position)
            if chunk_start == -1:
                # Fallback: use approximate position
                chunk_start = current_position
            
            chunk_end = chunk_start + len(chunk_text)
            
            # Calculate detailed offsets
            sentences = self._split_text_into_sentences(chunk_text)
            sentence_offsets = self._calculate_sentence_offsets(chunk_text, sentences, chunk_start)
            
            words = self._split_text_into_words(chunk_text)
            word_offsets = self._calculate_word_offsets(chunk_text, words, chunk_start)
            
            # Enhance the chunk with offset information
            enhanced_chunk = {
                **chunk,
                'offsets': {
                    'char_start': chunk_start,
                    'char_end': chunk_end,
                    'sentences': sentence_offsets,
                    'words': word_offsets
                },
                'metadata': {
                    **chunk.get('metadata', {}),
                    'sentence_count': len(sentences),
                    'word_count': len(words),
                    'char_count': len(chunk_text),
                    'enhanced_with_offsets': True
                }
            }
            
            enhanced_chunks.append(enhanced_chunk)
            current_position = chunk_end
        
        return enhanced_chunks
    
    def _structured_chunk_to_dict(self, structured_chunk) -> Dict:
        """Convert StructuredChunk object to dictionary format"""
        
        return {
            'chunk_id': f"chunk_{structured_chunk.hierarchy_level}_{len(structured_chunk.text)//100}",
            'text': structured_chunk.text,
            'chunk_type': structured_chunk.chunk_type,
            'hierarchy_level': structured_chunk.hierarchy_level,
            'start_char': structured_chunk.start_char,
            'end_char': structured_chunk.end_char,
            'metadata': {
                **structured_chunk.metadata,
                'chunking_method': 'smart_structured',
                'chunk_size': len(structured_chunk.text)
            }
        }
    
    def store_chunks_to_s3(self, chunks: List[Dict], doc_id: str, original_message: Dict, full_text: str) -> List[str]:
        """Store chunks to S3 with improved naming: {doc_id}/{doc_id}_chunk_NNNN.json"""
        
        s3_keys = []
        
        try:
            logger.info(f"Storing {len(chunks)} chunks for document {doc_id} with improved naming structure")
            
            # Store individual chunks with doc_id in filename and 4-digit sequence
            for i, chunk in enumerate(chunks):
                # 4-digit zero-padded sequence: 0001, 0002, etc.
                chunk_sequence = f"{i+1:04d}"
                chunk_key = f"{doc_id}/{doc_id}_chunk_{chunk_sequence}.json"
                
                # Generate consistent chunk ID for URI minting and cross-references
                chunk_id = f"{doc_id}_chunk_{chunk_sequence}"
                
                # Enhanced chunk data with comprehensive metadata
                chunk_data = {
                    'doc_id': doc_id,
                    'chunk_id': chunk_id,  # Consistent ID for URI minting
                    'chunk_sequence': i + 1,
                    'text': chunk['text'],
                    'offsets': chunk.get('offsets', {}),  # Include detailed offset information
                    'metadata': {
                        **chunk.get('metadata', {}),
                        'created_at': datetime.utcnow().isoformat(),
                        'chunk_size': len(chunk['text']),
                        'chunk_filename': f"{doc_id}_chunk_{chunk_sequence}.json",
                        'uri_base': chunk_id,  # For consistent URI minting later
                        'documentid_manager_integration': original_message.get('documentid_manager_integration', False),
                        'selective_migration_used': original_message.get('selective_migration_used', False),
                        'chunking_version': 'v2_integrated'
                    }
                }
                
                # Add structure information if available
                if 'chunk_type' in chunk:
                    chunk_data['chunk_type'] = chunk['chunk_type']
                if 'start_char' in chunk:
                    chunk_data['start_char'] = chunk['start_char']
                if 'end_char' in chunk:
                    chunk_data['end_char'] = chunk['end_char']
                if 'hierarchy_level' in chunk:
                    chunk_data['hierarchy_level'] = chunk['hierarchy_level']
                
                # Store chunk
                self.s3.put_object(
                    Bucket=self.chunks_bucket,
                    Key=chunk_key,
                    Body=json.dumps(chunk_data, indent=2),
                    ContentType='application/json'
                )
                
                s3_keys.append(chunk_key)
            
            # Store document-level metadata
            metadata_key = f"{doc_id}/{doc_id}_chunks_metadata.json"
            metadata = {
                'doc_id': doc_id,
                'total_chunks': len(chunks),
                'chunk_pattern': f"{doc_id}_chunk_NNNN.json",
                'chunk_sequence_range': f"0001-{len(chunks):04d}",
                'chunking_strategy': 'smart_overlap' if self.structured_chunker else 'basic_enhanced',
                'original_text_length': len(full_text),
                'processing_timestamp': datetime.utcnow().isoformat(),
                'original_message': original_message,
                'documentid_manager_integration': original_message.get('documentid_manager_integration', False),
                'selective_migration_used': original_message.get('selective_migration_used', False),
                'chunk_files': [f"{doc_id}_chunk_{i+1:04d}.json" for i in range(len(chunks))],
                'chunk_summary': {
                    'chunk_types': list(set(chunk.get('chunk_type', 'text') for chunk in chunks)),
                    'avg_chunk_size': sum(len(chunk['text']) for chunk in chunks) / len(chunks) if chunks else 0,
                    'total_text_length': sum(len(chunk['text']) for chunk in chunks),
                    'uri_pattern': f"{doc_id}_chunk_NNNN"  # For future URI minting
                }
            }
            
            self.s3.put_object(
                Bucket=self.chunks_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            s3_keys.append(metadata_key)
            
            # Store full text reference for downstream processing
            full_text_key = f"{doc_id}/{doc_id}_full_text_reference.json"
            full_text_data = {
                'doc_id': doc_id,
                'full_text_location': original_message.get('full_text_location'),
                'text_length': len(full_text),
                'created_at': datetime.utcnow().isoformat(),
                'purpose': 'downstream_processing_reference',
                'note': 'Reference to original full text location - not duplicate storage'
            }
            
            self.s3.put_object(
                Bucket=self.chunks_bucket,
                Key=full_text_key,
                Body=json.dumps(full_text_data, indent=2),
                ContentType='application/json'
            )
            s3_keys.append(full_text_key)
            
            logger.info(f"Successfully stored {len(chunks)} chunks for {doc_id} with consistent naming")
            logger.info(f"Chunk pattern: {doc_id}_chunk_0001.json to {doc_id}_chunk_{len(chunks):04d}.json")
            
            return s3_keys
            
        except Exception as e:
            logger.error(f"Error storing chunks to S3: {e}")
            raise

    def signal_chunking_complete(self, doc_id: str, chunks_created: int):
        """Signal coordination logic that chunking is complete with improved structure"""
        
        if not self.coordination_topic_arn:
            logger.info("No coordination topic configured, skipping coordination signal")
            return
        
        try:
            coordination_message = {
                "doc_id": doc_id,
                "stage": "chunks_ready",
                "processor": "text_chunker",
                "status": "COMPLETED",
                "chunks_created": chunks_created,
                "chunks_location": {
                    "bucket": self.chunks_bucket,
                    "prefix": f"chunks/{doc_id}/",
                    "pattern": f"{doc_id}_chunk_*.json",
                    "total_chunks": chunks_created
                },
                "documentid_manager_integration": True,
                "pipeline_stage": "text_chunking_complete",
                "timestamp": datetime.utcnow().isoformat(),
                "ready_for_downstream": True
            }
            
            self.sns.publish(
                TopicArn=self.coordination_topic_arn,
                Message=json.dumps(coordination_message),
                Subject=f"Text Chunking Complete: {doc_id}",
                MessageAttributes={
                    'processor': {'DataType': 'String', 'StringValue': 'text_chunker'},
                    'doc_id': {'DataType': 'String', 'StringValue': doc_id},
                    'status': {'DataType': 'String', 'StringValue': 'COMPLETED'},
                    'chunks_created': {'DataType': 'Number', 'StringValue': str(chunks_created)}
                }
            )
            
            logger.info(f"Sent coordination signal for document {doc_id} - {chunks_created} chunks created")
            
        except Exception as e:
            logger.error(f"Error sending coordination signal: {e}")
    def update_processing_status(self, doc_id: str, status: str, chunks_created: int, notes: str = None):
        """Update processing status in database using DatabaseManager"""
        
        if not self.db_manager:
            logger.warning("DatabaseManager not available, skipping status update")
            return
        
        try:
            # Update processing status in a dedicated table for chunking operations
            update_query = """
                INSERT INTO text_chunking_status (doc_id, status, chunks_created, notes, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) 
                DO UPDATE SET 
                    status = EXCLUDED.status,
                    chunks_created = EXCLUDED.chunks_created,
                    notes = EXCLUDED.notes,
                    updated_at = EXCLUDED.updated_at
            """
            
            params = (doc_id, status, chunks_created, notes, datetime.utcnow())
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(update_query, params)
                    conn.commit()
            
            logger.info(f"Updated chunking status for {doc_id}: {status} ({chunks_created} chunks)")
            
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
            # Don't raise - chunking success shouldn't depend on status tracking


def lambda_handler(event, context):
    """Lambda entry point"""
    processor = TextChunkerProcessor()
    return processor.lambda_handler(event, context)


# For testing
if __name__ == "__main__":
    # Test with corrected TextExtractor message format
    test_event = {
        'Records': [{
            'body': json.dumps({
                'Message': json.dumps({
                    'doc_id': '0004ad39_4285ab3d',
                    'stage': 'text_ready',
                    'full_text_location': {
                        'bucket': 'solve-global-kr-text-new-861276078413-us-east-1',
                        'key': '0004ad39_4285ab3d/0004ad39_4285ab3d_full_text.txt'
                    },
                    'document_structure_location': {
                        'bucket': 'solve-global-kr-text-new-861276078413-us-east-1',
                        'key': '0004ad39_4285ab3d/metadata/textract_response.json'
                    },
                    'documentid_manager_integration': True,
                    'selective_migration_used': True
                })
            })
        }]
    }
    
    processor = TextChunkerProcessor()
    result = processor.lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
