#!/usr/bin/env python3
"""
NLP Worker - Audit-First Database Integration
Processes Comprehend job results and stores in S3 data lake
"""
import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import time

# Import from lambda layers
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class NLPWorker:
    """NLP results processor with audit-first database design"""
    
    def __init__(self):
        """Initialize NLP worker with database and AWS clients"""
        self.db_manager = DatabaseManager()
        
        # AWS clients
        self.s3_client = boto3.client('s3')
        self.comprehend_client = boto3.client('comprehend', region_name=os.environ.get('COMPREHEND_REGION', 'us-east-1'))
        self.sns_client = boto3.client('sns')
        
        # Configuration
        self.ner_results_bucket = os.environ.get('NER_RESULTS_BUCKET',
                                                'solve-global-kr-dl-ner-results-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET',
                                         'solve-global-kr-dl-text-861276078413-us-east-1')
        self.completion_topic_arn = os.environ.get('NLP_COMPLETION_TOPIC_ARN',
                                                  'arn:aws:sns:us-east-1:861276078413:nlp-processing-complete')
        
        logger.info("✅ NLP Worker initialized")
        logger.info(f"NER results bucket: {self.ner_results_bucket}")
        logger.info(f"Text bucket: {self.text_bucket}")
        logger.info(f"Completion topic: {self.completion_topic_arn}")
    
    def process_event(self, event, context):
        """Process Lambda event with proper error handling"""
        try:
            # Parse records
            logger.info(f"DEBUG: Event received: {event}")
            records = event.get('Records', [])
            if not records:
                raise ValueError("No records found in event")
            
            results = []
            for record in records:
                # Handle both direct SNS and SQS-wrapped SNS messages
                if 'Sns' in record:
                    # Direct SNS message
                    result = self.process_record(record)
                elif 'body' in record:
                    # SQS message - could be wrapped SNS
                    logger.info(f"Processing SQS message: {record.get('messageId', 'unknown')}")
                    try:
                        # Try to parse as SNS message wrapped in SQS
                        body = json.loads(record['body'])
                        if 'Type' in body and body['Type'] == 'Notification':
                            logger.info("Processing SQS-wrapped SNS message")
                            # Create a synthetic SNS record
                            sns_record = {
                                'Sns': {
                                    'Message': body['Message'],
                                    'MessageAttributes': body.get('MessageAttributes', {})
                                }
                            }
                            result = self.process_record(sns_record)
                        else:
                            # Direct SQS message
                            logger.info("Processing direct SQS message")
                            result = self.process_direct_message(body)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse SQS message body as JSON: {record['body']}")
                        result = {'status': 'error', 'error': 'Invalid JSON in SQS message body'}
                else:
                    logger.error(f"Unknown record format: {record}")
                    result = {'status': 'error', 'error': 'Unknown record format'}
                
                results.append(result)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'NLP processing completed',
                    'processed_records': len(results),
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            raise
    
    def process_record(self, record):
        """Process individual SNS record with Comprehend job information"""
        doc_id = None
        
        try:
            # Parse SNS message
            sns_message = json.loads(record['Sns']['Message'])
            logger.info(f"DEBUG: SNS message received: {sns_message}")
            
            # Extract document information
            doc_id = sns_message.get('doc_id')
            if not doc_id:
                raise ValueError("doc_id not found in message")
            
            comprehend_jobs = sns_message.get('comprehend_jobs', {})
            chunks_location = sns_message.get('data_locations', {}).get('chunks_location')
            cost_analysis = sns_message.get('cost_analysis', {})
            
            logger.info(f"Processing NLP results for document: {doc_id}")
            logger.info(f"Comprehend jobs: {comprehend_jobs}")
            logger.info(f"DEBUG: chunks_location received: {chunks_location}")
            
            # Update status to results processing
            self.update_status(doc_id, 'nlp_results_processing', 'in_progress', {
                'comprehend_jobs': comprehend_jobs,
                'chunks_location': chunks_location,
                'cost_analysis': cost_analysis
            })
            
            # Wait for and retrieve Comprehend results
            comprehend_results = self.get_comprehend_results(comprehend_jobs)
            logger.info(f"COMPREHEND_DEBUG_RAW results_type={type(comprehend_results)} results_keys={list(comprehend_results.keys()) if isinstance(comprehend_results, dict) else 'NOT_DICT'}")

            if isinstance(comprehend_results, dict):
                entities = comprehend_results.get('entities', [])
                key_phrases = comprehend_results.get('key_phrases', [])
                
                logger.info(f"COMPREHEND_DEBUG_COUNTS entities={len(entities)} key_phrases={len(key_phrases)}")
                
                # Log first entity and key phrase with full details
                if entities:
                    first_entity = entities[0]
                    logger.info(f"COMPREHEND_DEBUG_FIRST_ENTITY {json.dumps(first_entity)}")
                    logger.info(f"COMPREHEND_DEBUG_ENTITY_RANGE begin={first_entity.get('begin_offset')} end={first_entity.get('end_offset')} text='{first_entity.get('text', '')}'")
                
                if key_phrases:
                    first_phrase = key_phrases[0]
                    logger.info(f"COMPREHEND_DEBUG_FIRST_PHRASE {json.dumps(first_phrase)}")
                    logger.info(f"COMPREHEND_DEBUG_PHRASE_RANGE begin={first_phrase.get('begin_offset')} end={first_phrase.get('end_offset')} text='{first_phrase.get('text', '')}'")
            else:
                logger.error(f"COMPREHEND_DEBUG_ERROR results_not_dict={comprehend_results}")
            
            # Load chunks for offset mapping
            logger.info(f"DEBUG: About to load chunks. chunks_location = {chunks_location}")
            chunks = self.load_chunks_from_s3(chunks_location) if chunks_location else []
            logger.info(f"DEBUG: Loaded {len(chunks)} chunks from S3")
            
            # Update status to offset mapping
            self.update_status(doc_id, 'nlp_offset_mapping', 'in_progress', {
                'entities_count': len(comprehend_results.get('entities', [])),
                'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                'chunks_count': len(chunks)
            })
            
            # Map results to chunks
            mapped_results = self.map_results_to_chunks(comprehend_results, chunks, doc_id)
            
            # Update status to storage
            self.update_status(doc_id, 'nlp_storage', 'in_progress', {
                'results_summary': {
                    'entities_count': len(comprehend_results.get('entities', [])),
                    'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                    'chunks_mapped': len(chunks) > 0
                }
            })
            
            # Store results in S3 data lake
            s3_locations = self.store_results_in_s3(doc_id, comprehend_results, mapped_results)
            
            # Publish completion message
            self.publish_completion_message(doc_id, s3_locations, comprehend_results)
            
            # Update status to completed
            self.update_status(doc_id, 'nlp_processing', 'completed', {
                'results_locations': s3_locations,
                'entities_count': len(comprehend_results.get('entities', [])),
                'key_phrases_count': len(comprehend_results.get('key_phrases', []))
            })
            
            logger.info(f"Successfully processed NLP results for document: {doc_id}")
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'entities_count': len(comprehend_results.get('entities', [])),
                'key_phrases_count': len(comprehend_results.get('key_phrases', []))
            }
            
        except Exception as e:
            logger.error(f"Error processing NLP results for {doc_id}: {e}")
            
            if doc_id:
                self.update_status(doc_id, 'nlp_processing', 'failed', error_message=str(e))
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }
    
    def process_direct_message(self, message):
        """Process a direct message (not SNS)"""
        doc_id = None
        
        try:
            # Extract document information
            doc_id = message.get('doc_id')
            if not doc_id:
                raise ValueError("doc_id not found in message")
            
            comprehend_jobs = message.get('comprehend_jobs', {})
            chunks_location = message.get('data_locations', {}).get('chunks_location')
            cost_analysis = message.get('cost_analysis', {})
            
            logger.info(f"Processing NLP results for document: {doc_id}")
            logger.info(f"Comprehend jobs: {comprehend_jobs}")
            logger.info(f"DEBUG: chunks_location received: {chunks_location}")
            
            # Update status to results processing
            self.update_status(doc_id, 'nlp_results_processing', 'in_progress', {
                'comprehend_jobs': comprehend_jobs,
                'chunks_location': chunks_location,
                'cost_analysis': cost_analysis
            })
            
            # Wait for and retrieve Comprehend results
            comprehend_results = self.get_comprehend_results(comprehend_jobs)
            
            # Load chunks for offset mapping
            logger.info(f"DEBUG: About to load chunks. chunks_location = {chunks_location}")
            chunks = self.load_chunks_from_s3(chunks_location) if chunks_location else []
            logger.info(f"DEBUG: Loaded {len(chunks)} chunks from S3")
            
            # Update status to offset mapping
            self.update_status(doc_id, 'nlp_offset_mapping', 'in_progress', {
                'entities_count': len(comprehend_results.get('entities', [])),
                'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                'chunks_count': len(chunks)
            })
            
            # Map results to chunks
            mapped_results = self.map_results_to_chunks(comprehend_results, chunks, doc_id)
            
            # Update status to storage
            self.update_status(doc_id, 'nlp_storage', 'in_progress', {
                'results_summary': {
                    'entities_count': len(comprehend_results.get('entities', [])),
                    'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                    'chunks_mapped': len(chunks) > 0
                }
            })
            
            # Store results in S3 data lake
            s3_locations = self.store_results_in_s3(doc_id, comprehend_results, mapped_results)
            
            # Publish completion message
            self.publish_completion_message(doc_id, s3_locations, comprehend_results)
            
            # Update status to completed
            self.update_status(doc_id, 'nlp_processing', 'completed', {
                'results_locations': s3_locations,
                'entities_count': len(comprehend_results.get('entities', [])),
                'key_phrases_count': len(comprehend_results.get('key_phrases', []))
            })
            
            logger.info(f"Successfully processed NLP results for document: {doc_id}")
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'entities_count': len(comprehend_results.get('entities', [])),
                'key_phrases_count': len(comprehend_results.get('key_phrases', []))
            }
            
        except Exception as e:
            logger.error(f"Error processing NLP results for {doc_id}: {e}")
            
            if doc_id:
                self.update_status(doc_id, 'nlp_processing', 'failed', error_message=str(e))
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }
    
    def get_comprehend_results(self, comprehend_jobs: Dict[str, str]) -> Dict[str, List]:
        """Wait for and retrieve Comprehend job results"""
        entity_job_id = comprehend_jobs.get('entity_job_id')
        key_phrases_job_id = comprehend_jobs.get('key_phrases_job_id')
        
        results = {
            'entities': [],
            'key_phrases': []
        }
        
        # Wait for entity detection job to complete
        if entity_job_id:
            logger.info(f"Waiting for entity detection job to complete: {entity_job_id}")
            entities = self.wait_for_comprehend_job(
                job_id=entity_job_id,
                job_type='entities-detection'
            )
            results['entities'] = entities
            logger.info(f"Retrieved {len(entities)} entities")
        
        # Wait for key phrases detection job to complete
        if key_phrases_job_id:
            logger.info(f"Waiting for key phrases detection job to complete: {key_phrases_job_id}")
            key_phrases = self.wait_for_comprehend_job(
                job_id=key_phrases_job_id,
                job_type='key-phrases-detection'
            )
            results['key_phrases'] = key_phrases
            logger.info(f"Retrieved {len(key_phrases)} key phrases")
        
        return results
    
    def wait_for_comprehend_job(self, job_id: str, job_type: str) -> List[Dict]:
        """Wait for Comprehend job to complete and retrieve results"""
        max_attempts = 60  # Increased from 30 to 60
        attempt = 0
        
        while attempt < max_attempts:
            # Check job status
            if job_type == 'entities-detection':
                response = self.comprehend_client.describe_entities_detection_job(
                    JobId=job_id
                )
                job_status = response['EntitiesDetectionJobProperties']['JobStatus']
                output_uri = response['EntitiesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            else:  # key-phrases-detection
                response = self.comprehend_client.describe_key_phrases_detection_job(
                    JobId=job_id
                )
                job_status = response['KeyPhrasesDetectionJobProperties']['JobStatus']
                output_uri = response['KeyPhrasesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            
            logger.info(f"Job {job_id} status: {job_status}")
            
            if job_status == 'COMPLETED':
                # Job completed, retrieve results
                return self.retrieve_comprehend_results(output_uri, job_type)
            elif job_status in ['FAILED', 'STOP_REQUESTED', 'STOPPED']:
                # Job failed
                raise ValueError(f"Comprehend job {job_id} failed with status: {job_status}")
            
            # Job still in progress, wait and retry
            attempt += 1
            logger.info(f"Waiting for job to complete, attempt {attempt}/{max_attempts}")
            time.sleep(10)
        
        # If we reach here, the job is still running but we've timed out
        # Instead of failing, let's return an empty list and log a warning
        logger.warning(f"Comprehend job {job_id} is still running after timeout period. Returning empty results.")
        return []
    
    def retrieve_comprehend_results(self, output_uri: str, job_type: str) -> List[Dict]:
        """Retrieve and parse Comprehend job results from S3"""
        try:
            # Parse S3 URI
            uri_parts = output_uri.replace('s3://', '').split('/')
            bucket = uri_parts[0]
            key = '/'.join(uri_parts[1:])
            logger.info(f"COMPREHEND_DEBUG: Comprehend results S3 URI: s3://{bucket}/{key}")
            
            # Download tar.gz file
            download_path = f"/tmp/{job_type}-results.tar.gz"
            logger.info(f"COMPREHEND_DEBUG: Downloading results to: {download_path}")
            self.s3_client.download_file(bucket, key, download_path)
            
            # Extract tar.gz file
            import tarfile
            import io
            
            results = []
            with tarfile.open(download_path, 'r:gz') as tar:
                for member in tar.getmembers():
                    logger.info(f"COMPREHEND_DEBUG: Extracting member: {member.name}")
                    # Comprehend creates 'output' file (JSON without .json extension) or .json files
                    if member.name.endswith('output') or member.name.endswith('.json'):
                        logger.info(f"COMPREHEND_DEBUG: Member matches criteria, attempting extraction")
                        try:
                            f = tar.extractfile(member)
                            logger.info(f"COMPREHEND_DEBUG: Extracted file object: {f}")
                            if f:
                                logger.info(f"COMPREHEND_DEBUG: Reading file content...")
                                content = f.read()
                                logger.info(f"COMPREHEND_DEBUG: Content length: {len(content)} bytes")
                                logger.info(f"COMPREHEND_DEBUG: Content preview: {content[:200]}...")
                                
                                logger.info(f"COMPREHEND_DEBUG: Parsing JSON...")
                                data = json.loads(content)
                                logger.info(f"COMPREHEND_DEBUG: JSON parsed successfully, keys: {list(data.keys())}")
                                
                                # Parse based on job type
                                if job_type == 'entities-detection':
                                    entities_list = data.get('Entities', [])
                                    logger.info(f"COMPREHEND_DEBUG: Found {len(entities_list)} entities in data")
                                    for item in entities_list:
                                        results.append({
                                            'text': item.get('Text', ''),
                                            'type': item.get('Type', ''),
                                            'score': item.get('Score', 0),
                                            'begin_offset': item.get('BeginOffset', 0),
                                            'end_offset': item.get('EndOffset', 0)
                                        })
                                else:  # key-phrases-detection
                                    keyphrases_list = data.get('KeyPhrases', [])
                                    logger.info(f"COMPREHEND_DEBUG: Found {len(keyphrases_list)} key phrases in data")
                                    for item in keyphrases_list:
                                        results.append({
                                            'text': item.get('Text', ''),
                                            'score': item.get('Score', 0),
                                            'begin_offset': item.get('BeginOffset', 0),
                                            'end_offset': item.get('EndOffset', 0)
                                        })
                                
                                logger.info(f"COMPREHEND_DEBUG: Added {len(results)} results total")
                                
                                # Log the first 3 results for debugging
                                if len(results) <= 3:
                                    logger.info(f"COMPREHEND_DEBUG: All {len(results)} results: {results}")
                                else:
                                    logger.info(f"COMPREHEND_DEBUG: First 3 results: {results[:3]}")
                            else:
                                logger.error(f"COMPREHEND_DEBUG: tar.extractfile returned None for {member.name}")
                        except json.JSONDecodeError as e:
                            logger.error(f"COMPREHEND_DEBUG: JSON decode error: {e}")
                        except Exception as e:
                            logger.error(f"COMPREHEND_DEBUG: Unexpected error processing {member.name}: {e}")
                    else:
                        logger.info(f"COMPREHEND_DEBUG: Skipping member {member.name} (doesn't match criteria)")
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving Comprehend results: {e}")
            raise
    
    def load_chunks_from_s3(self, chunks_location: str) -> List[Dict]:
        """Load chunks from S3 for offset mapping"""
        try:
            # Parse S3 location
            if not chunks_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 location format: {chunks_location}")
            
            s3_path = chunks_location[5:]  # Remove 's3://'
            bucket, prefix = s3_path.split('/', 1)
            
            # Ensure prefix ends with /
            if not prefix.endswith('/'):
                prefix += '/'
            
            # List all chunk files
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            chunks = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.json') and 'chunk_' in key:
                    # Download and parse chunk
                    obj_response = self.s3_client.get_object(
                        Bucket=bucket,
                        Key=key
                    )
                    chunk_data = json.loads(obj_response['Body'].read().decode('utf-8'))
                    chunks.append(chunk_data)
            
            logger.info(f"Loaded {len(chunks)} chunks from S3")
            return chunks
            
        except Exception as e:
            logger.error(f"Error loading chunks from S3: {e}")
            return []
    
    def load_original_document_text(self, doc_id: str) -> str:
        """Load the original document text that was sent to Comprehend"""
        try:
            # CORRECTED: Use data-lake path structure
            text_key = f"data-lake/{doc_id}/raw_text.txt"
            
            response = self.s3_client.get_object(
                Bucket=self.text_bucket,
                Key=text_key
            )
            
            original_text = response['Body'].read().decode('utf-8')
            logger.info(f"Loaded original document text: {len(original_text)} characters from {text_key}")
            return original_text
            
        except Exception as e:
            logger.error(f"Error loading original document text from {text_key}: {e}")
            raise
    
    def find_chunk_positions_in_original_text(self, chunks: List[Dict], original_text: str) -> List[Dict]:
        """Find where each chunk's text appears in the original document"""
        chunk_positions = []
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '').strip()
            if not chunk_text:
                continue
            
            # Find where this chunk's text appears in the original document
            pos = original_text.find(chunk_text)
            if pos != -1:
                chunk_position = {
                    'chunk_id': chunk.get('chunk_id', ''),
                    'chunk_text': chunk_text,
                    'start_offset': pos,
                    'end_offset': pos + len(chunk_text),
                    'chunk_index': chunk.get('chunk_index', 0),
                    'section_type': chunk.get('section_type', 'unknown'),
                    'hierarchy_level': chunk.get('hierarchy_level', 0),
                    'parent_chunk_id': chunk.get('parent_chunk_id')
                }
                chunk_positions.append(chunk_position)
                # After finding chunk positions
                logger.info(f"CHUNK_DEBUG_SAMPLE first_3_chunks={chunk_positions[:3] if len(chunk_positions) >= 3 else chunk_positions}")
                logger.info(f"CHUNK_DEBUG_RANGES min_start={min([c['start_offset'] for c in chunk_positions]) if chunk_positions else 'NONE'} max_end={max([c['end_offset'] for c in chunk_positions]) if chunk_positions else 'NONE'}")

                # Log original text length for coordinate system validation
                text_preview = original_text[:100].replace(chr(10), '\\n').replace(chr(13), '\\r')
                logger.info(f"ORIGINAL_TEXT_DEBUG length={len(original_text)} first_100_chars='{text_preview}'")
            else:
                logger.warning(f"Chunk {chunk.get('chunk_id')} text not found in original document")
        
        # Sort by position in document
        chunk_positions.sort(key=lambda x: x['start_offset'])
        
        logger.info(f"Found {len(chunk_positions)} chunk positions in original document")
        return chunk_positions


    # Add debug to your ranges_overlap function
    def ranges_overlap(start1, end1, start2, end2):
        overlap = not (end1 <= start2 or end2 <= start1)
        # Temporarily log overlap checks for debugging
        if logger.level <= logging.INFO:
            logger.info(f"OVERLAP_CHECK ({start1},{end1}) vs ({start2},{end2}) = {overlap}")
        return overlap


    def map_results_to_chunks(self, comprehend_results: Dict[str, List], chunks: List[Dict], doc_id: str) -> Dict[str, List]:
        """
        CORRECTED: Map Comprehend results to document chunks using original document positions
        Enhanced with comprehensive observability metrics for semantic search optimization
        
        The previous implementation was flawed because it:
        1. Assumed chunks were sequential segments that could be concatenated
        2. Used wrong sort key ('position' instead of 'chunk_index')
        3. Created fictional document text that didn't match Comprehend input
        
        CORRECTED APPROACH:
        1. Load the original document text that Comprehend analyzed
        2. Find where each chunk appears in the original document
        3. Map entity/keyphrase offsets (relative to original) to chunks
        4. Track comprehensive metrics for search system optimization
        """
        # Add this at the start of the mapping function
        logger.info(f"ENVIRONMENT_DEBUG lambda_env={os.environ.get('LAMBDA_ENVIRONMENT', 'NOT_SET')} aws_region={os.environ.get('AWS_REGION', 'NOT_SET')}")

        if not chunks:
            logger.info("No chunks available for mapping, skipping")
            return {
                'entities_by_chunk': [],
                'key_phrases_by_chunk': []
            }

        try:
            # Load the original document text that Comprehend analyzed
            original_text = self.load_original_document_text(doc_id)
            
            # Find where each chunk appears in the original document
            chunk_positions = self.find_chunk_positions_in_original_text(chunks, original_text)
            
            if not chunk_positions:
                logger.error("Could not find any chunk positions in original document")
                return {
                    'entities_by_chunk': [],
                    'key_phrases_by_chunk': []
                }

            # Map entities to chunks using correct positions
            entities_by_chunk = []
            entities_unmapped = []

            entities = comprehend_results.get('entities', [])
            
            for entity in entities:
                entity_start = entity.get('begin_offset', 0)
                entity_end = entity.get('end_offset', 0)
                entity_text = entity.get('text', '')
                entity_type = entity.get('type', '')


                for i, entity in enumerate(entities):
                    entity_start = entity.get('begin_offset')
                    entity_end = entity.get('end_offset')
                    entity_text = entity.get('text', '')
                    
                    logger.info(f"ENTITY_MAPPING_DEBUG_{i} text='{entity_text}' start={entity_start} end={entity_end}")
                    
                    # Check if entity coordinates are valid
                    if entity_start is not None and entity_end is not None:
                        if entity_end <= len(original_text):
                            actual_text = original_text[entity_start:entity_end]
                            logger.info(f"ENTITY_MAPPING_DEBUG_{i} actual_text_at_position='{actual_text}' matches={actual_text == entity_text}")
                        else:
                            logger.error(f"ENTITY_MAPPING_DEBUG_{i} INVALID_COORDINATES entity_end={entity_end} > text_length={len(original_text)}")
                    
                    # Count overlapping chunks for this entity
                    overlapping_count = 0
                    for chunk_pos in chunk_positions:
                        if self.ranges_overlap(entity_start, entity_end, chunk_pos['start_offset'], chunk_pos['end_offset']):
                            overlapping_count += 1
                            logger.info(f"ENTITY_MAPPING_DEBUG_{i} OVERLAP_FOUND chunk_id={chunk_pos['chunk_id']} chunk_range=({chunk_pos['start_offset']}, {chunk_pos['end_offset']})")
                    
                    logger.info(f"ENTITY_MAPPING_DEBUG_{i} total_overlaps={overlapping_count}")
                    
                    # Break after first 3 entities to avoid log spam
                    if i >= 2:
                        logger.info(f"ENTITY_MAPPING_DEBUG truncated_after_3_entities total_entities={len(entities)}")
                        break

                
                # Find chunks that contain this entity
                mapped_to_chunks = False
                for chunk_pos in chunk_positions:
                    # Check if entity overlaps with this chunk
                    if (entity_start < chunk_pos['end_offset'] and 
                        entity_end > chunk_pos['start_offset']):
                        
                        # Calculate relative position within chunk
                        relative_start = max(0, entity_start - chunk_pos['start_offset'])
                        relative_end = min(len(chunk_pos['chunk_text']), 
                                         entity_end - chunk_pos['start_offset'])
                        
                        entities_by_chunk.append({
                            'chunk_id': chunk_pos['chunk_id'],
                            'chunk_index': chunk_pos['chunk_index'],
                            'section_type': chunk_pos['section_type'],
                            'hierarchy_level': chunk_pos['hierarchy_level'],
                            'parent_chunk_id': chunk_pos['parent_chunk_id'],
                            'entity': entity_text,
                            'type': entity_type,
                            'score': entity.get('score', 0),
                            'original_begin_offset': entity_start,
                            'original_end_offset': entity_end,
                            'chunk_relative_begin': relative_start,
                            'chunk_relative_end': relative_end,
                            'mapping_type': 'exact_chunk',
                            'mapping_confidence': 1.0
                        })
                        mapped_to_chunks = True
                
                # Track unmapped entities for metrics
                if not mapped_to_chunks:
                    entities_unmapped.append({
                        'entity': entity_text,
                        'type': entity_type,
                        'score': entity.get('score', 0),
                        'original_begin_offset': entity_start,
                        'original_end_offset': entity_end,
                        'reason': 'no_chunk_overlap'
                    })

            # Map key phrases to chunks using correct positions
            key_phrases_by_chunk = []
            keyphrases_unmapped = []
            
            for phrase in comprehend_results.get('key_phrases', []):
                phrase_start = phrase.get('begin_offset', 0)
                phrase_end = phrase.get('end_offset', 0)
                phrase_text = phrase.get('text', '')
                
                # Find chunks that contain this phrase
                mapped_to_chunks = False
                for chunk_pos in chunk_positions:
                    # Check if phrase overlaps with this chunk
                    if (phrase_start < chunk_pos['end_offset'] and 
                        phrase_end > chunk_pos['start_offset']):
                        
                        # Calculate relative position within chunk
                        relative_start = max(0, phrase_start - chunk_pos['start_offset'])
                        relative_end = min(len(chunk_pos['chunk_text']), 
                                         phrase_end - chunk_pos['start_offset'])
                        
                        key_phrases_by_chunk.append({
                            'chunk_id': chunk_pos['chunk_id'],
                            'chunk_index': chunk_pos['chunk_index'],
                            'section_type': chunk_pos['section_type'],
                            'hierarchy_level': chunk_pos['hierarchy_level'],
                            'parent_chunk_id': chunk_pos['parent_chunk_id'],
                            'phrase': phrase_text,
                            'score': phrase.get('score', 0),
                            'original_begin_offset': phrase_start,
                            'original_end_offset': phrase_end,
                            'chunk_relative_begin': relative_start,
                            'chunk_relative_end': relative_end,
                            'mapping_type': 'exact_chunk',
                            'mapping_confidence': 1.0
                        })
                        mapped_to_chunks = True
                
                # Track unmapped key phrases for metrics
                if not mapped_to_chunks:
                    keyphrases_unmapped.append({
                        'phrase': phrase_text,
                        'score': phrase.get('score', 0),
                        'original_begin_offset': phrase_start,
                        'original_end_offset': phrase_end,
                        'reason': 'no_chunk_overlap'
                    })
            
            # Generate comprehensive mapping metrics
            mapping_metrics = self.generate_mapping_metrics(
                doc_id=doc_id,
                chunks=chunks,
                chunk_positions=chunk_positions,
                comprehend_results=comprehend_results,
                entities_mapped=entities_by_chunk,
                entities_unmapped=entities_unmapped,
                keyphrases_mapped=key_phrases_by_chunk,
                keyphrases_unmapped=keyphrases_unmapped
            )
            
            # Log metrics for observability
            self.log_mapping_metrics(mapping_metrics)
            
            # Store metrics in database for analysis
            self.store_mapping_metrics(mapping_metrics)
            
            logger.info(f"Mapped {len(entities_by_chunk)} entities and {len(key_phrases_by_chunk)} key phrases to chunks")
            logger.info(f"Mapping success rate: Entities {mapping_metrics['entity_mapping_success_rate']:.1f}%, Key phrases {mapping_metrics['keyphrase_mapping_success_rate']:.1f}%")
            logger.info(f"Search quality impact score: {mapping_metrics['estimated_search_quality_impact']:.2f}")
            
            return {
                'entities_by_chunk': entities_by_chunk,
                'key_phrases_by_chunk': key_phrases_by_chunk,
                'mapping_metrics': mapping_metrics  # Include metrics in response
            }
            
        except Exception as e:
            logger.error(f"Error in corrected chunk mapping: {e}")
            # Return empty results rather than failing completely
            return {
                'entities_by_chunk': [],
                'key_phrases_by_chunk': [],
                'mapping_metrics': self.generate_error_metrics(doc_id, str(e))
            }
    
    def store_results_in_s3(self, doc_id: str, comprehend_results: Dict[str, List], 
                          mapped_results: Dict[str, List]) -> Dict[str, str]:
        """Store NLP results in S3 data lake"""
        try:
            # Prepare S3 paths
            results_prefix = f"data-lake/{doc_id}/"
            entities_key = f"{results_prefix}entities.json"
            key_phrases_key = f"{results_prefix}key_phrases.json"
            mapped_entities_key = f"{results_prefix}entities_by_chunk.json"
            mapped_phrases_key = f"{results_prefix}key_phrases_by_chunk.json"
            
            # Store entities
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=entities_key,
                Body=json.dumps(comprehend_results.get('entities', []), indent=2),
                ContentType='application/json'
            )
            
            # Store key phrases
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=key_phrases_key,
                Body=json.dumps(comprehend_results.get('key_phrases', []), indent=2),
                ContentType='application/json'
            )
            
            # Store mapped entities
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=mapped_entities_key,
                Body=json.dumps(mapped_results.get('entities_by_chunk', []), indent=2),
                ContentType='application/json'
            )
            
            # Store mapped key phrases
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=mapped_phrases_key,
                Body=json.dumps(mapped_results.get('key_phrases_by_chunk', []), indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Stored NLP results in S3: {self.ner_results_bucket}/{results_prefix}")
            
            return {
                'entities_location': f"s3://{self.ner_results_bucket}/{entities_key}",
                'key_phrases_location': f"s3://{self.ner_results_bucket}/{key_phrases_key}",
                'mapped_entities_location': f"s3://{self.ner_results_bucket}/{mapped_entities_key}",
                'mapped_phrases_location': f"s3://{self.ner_results_bucket}/{mapped_phrases_key}"
            }
            
        except Exception as e:
            logger.error(f"Error storing results in S3: {e}")
            raise
    
    def publish_completion_message(self, doc_id: str, s3_locations: Dict[str, str], 
                                 comprehend_results: Dict[str, List]) -> None:
        """Publish NLP completion message to SNS"""
        try:
            # Create standardized completion message
            message = {
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "climate-risk-rag-system",
                "stage": "nlp_processing_complete",
                "doc_id": doc_id,
                "data_locations": s3_locations,
                "processing_metadata": {
                    "entities_count": len(comprehend_results.get('entities', [])),
                    "key_phrases_count": len(comprehend_results.get('key_phrases', [])),
                    "processing_completed": datetime.utcnow().isoformat() + "Z"
                },
                "integration_flags": {
                    "database_tracking_enabled": True,
                    "knowledge_graph_integration_enabled": True
                }
            }
            
            # Publish to SNS
            response = self.sns_client.publish(
                TopicArn=self.completion_topic_arn,
                Message=json.dumps(message, default=str),
                Subject=f"NLP processing complete: {doc_id}"
            )
            
            logger.info(f"Published completion message: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Error publishing completion message: {e}")
            raise
    
    def generate_mapping_metrics(self, doc_id: str, chunks: List[Dict], chunk_positions: List[Dict], 
                               comprehend_results: Dict[str, List], entities_mapped: List[Dict], 
                               entities_unmapped: List[Dict], keyphrases_mapped: List[Dict], 
                               keyphrases_unmapped: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive mapping metrics for semantic search optimization"""
        
        entities = comprehend_results.get('entities', [])
        keyphrases = comprehend_results.get('key_phrases', [])
        
        # Basic mapping metrics
        total_entities = len(entities)
        total_keyphrases = len(keyphrases)
        entities_mapped_count = len(entities_mapped)
        keyphrases_mapped_count = len(keyphrases_mapped)
        
        # Calculate success rates
        entity_success_rate = (entities_mapped_count / total_entities * 100) if total_entities > 0 else 0
        keyphrase_success_rate = (keyphrases_mapped_count / total_keyphrases * 100) if total_keyphrases > 0 else 0
        
        # Chunk coverage metrics
        chunks_with_entities = len(set(e['chunk_id'] for e in entities_mapped))
        chunks_with_keyphrases = len(set(k['chunk_id'] for k in keyphrases_mapped))
        total_chunks = len(chunks)
        chunks_found = len(chunk_positions)
        
        # Entity type analysis for search impact
        entity_type_analysis = self.analyze_entity_types(entities_mapped, entities_unmapped)
        
        # Search quality impact estimation
        search_quality_impact = self.estimate_search_quality_impact(
            entities_mapped, keyphrases_mapped, entity_type_analysis
        )
        
        # Chunk finding analysis
        chunk_finding_analysis = self.analyze_chunk_finding(chunks, chunk_positions)
        
        metrics = {
            # Document identification
            'doc_id': doc_id,
            'timestamp': datetime.utcnow().isoformat(),
            'processing_stage': 'nlp_entity_mapping',
            
            # Basic counts
            'total_entities': total_entities,
            'total_keyphrases': total_keyphrases,
            'total_chunks': total_chunks,
            'chunks_found_in_original': chunks_found,
            
            # Mapping success metrics
            'entities_mapped': entities_mapped_count,
            'entities_unmapped': len(entities_unmapped),
            'keyphrases_mapped': keyphrases_mapped_count,
            'keyphrases_unmapped': len(keyphrases_unmapped),
            
            # Success rates (key metrics for monitoring)
            'entity_mapping_success_rate': round(entity_success_rate, 2),
            'keyphrase_mapping_success_rate': round(keyphrase_success_rate, 2),
            'chunk_finding_success_rate': round((chunks_found / total_chunks * 100) if total_chunks > 0 else 0, 2),
            
            # Chunk coverage for search system
            'chunks_with_entities': chunks_with_entities,
            'chunks_with_keyphrases': chunks_with_keyphrases,
            'chunk_entity_coverage_rate': round((chunks_with_entities / total_chunks * 100) if total_chunks > 0 else 0, 2),
            'chunk_keyphrase_coverage_rate': round((chunks_with_keyphrases / total_chunks * 100) if total_chunks > 0 else 0, 2),
            
            # Entity type analysis (critical for search quality)
            'entity_types_mapped': entity_type_analysis['mapped_by_type'],
            'entity_types_unmapped': entity_type_analysis['unmapped_by_type'],
            'critical_entities_mapped': entity_type_analysis['critical_mapped'],
            'critical_entities_unmapped': entity_type_analysis['critical_unmapped'],
            'critical_entity_success_rate': entity_type_analysis['critical_success_rate'],
            
            # Search system impact estimation
            'estimated_search_quality_impact': round(search_quality_impact, 3),
            'search_impact_breakdown': self.calculate_search_impact_breakdown(entities_mapped, keyphrases_mapped),
            
            # Chunk finding analysis
            'chunk_finding_issues': chunk_finding_analysis['issues'],
            'chunks_not_found': chunk_finding_analysis['not_found_chunks'],
            'potential_ocr_artifacts': chunk_finding_analysis['potential_ocr_issues'],
            
            # Unmapped entity analysis
            'unmapped_entity_sample': entities_unmapped[:5],  # Sample for analysis
            'unmapped_keyphrase_sample': keyphrases_unmapped[:5],  # Sample for analysis
            
            # Performance metrics
            'avg_entities_per_chunk': round(entities_mapped_count / chunks_with_entities if chunks_with_entities > 0 else 0, 2),
            'avg_keyphrases_per_chunk': round(keyphrases_mapped_count / chunks_with_keyphrases if chunks_with_keyphrases > 0 else 0, 2)
        }
        
        return metrics
    
    def analyze_entity_types(self, entities_mapped: List[Dict], entities_unmapped: List[Dict]) -> Dict[str, Any]:
        """Analyze entity types for search system impact assessment"""
        
        # Define critical entity types for search system
        critical_types = ['LOCATION', 'ORGANIZATION', 'PERSON']
        useful_types = ['DATE', 'QUANTITY', 'TITLE']
        
        # Count mapped entities by type
        mapped_by_type = {}
        critical_mapped = 0
        
        for entity in entities_mapped:
            entity_type = entity.get('type', 'UNKNOWN')
            mapped_by_type[entity_type] = mapped_by_type.get(entity_type, 0) + 1
            if entity_type in critical_types:
                critical_mapped += 1
        
        # Count unmapped entities by type
        unmapped_by_type = {}
        critical_unmapped = 0
        
        for entity in entities_unmapped:
            entity_type = entity.get('type', 'UNKNOWN')
            unmapped_by_type[entity_type] = unmapped_by_type.get(entity_type, 0) + 1
            if entity_type in critical_types:
                critical_unmapped += 1
        
        # Calculate critical entity success rate
        total_critical = critical_mapped + critical_unmapped
        critical_success_rate = (critical_mapped / total_critical * 100) if total_critical > 0 else 0
        
        return {
            'mapped_by_type': mapped_by_type,
            'unmapped_by_type': unmapped_by_type,
            'critical_mapped': critical_mapped,
            'critical_unmapped': critical_unmapped,
            'critical_success_rate': round(critical_success_rate, 2),
            'critical_types': critical_types,
            'useful_types': useful_types
        }
    
    def estimate_search_quality_impact(self, entities_mapped: List[Dict], keyphrases_mapped: List[Dict], 
                                     entity_type_analysis: Dict[str, Any]) -> float:
        """Estimate the impact on search quality based on mapped entities and keyphrases"""
        
        impact_score = 0.0
        
        # Entity impact scoring
        for entity in entities_mapped:
            entity_type = entity.get('type', '')
            entity_score = entity.get('score', 0)
            
            # Weight by entity type importance for search
            if entity_type in ['LOCATION', 'ORGANIZATION']:
                type_weight = 1.0  # Highest impact
            elif entity_type == 'PERSON':
                type_weight = 0.8  # High impact
            elif entity_type in ['DATE', 'QUANTITY', 'TITLE']:
                type_weight = 0.6  # Medium impact
            else:
                type_weight = 0.4  # Lower impact
            
            # Combine Comprehend confidence with type importance
            entity_impact = entity_score * type_weight
            impact_score += entity_impact
        
        # Keyphrase impact scoring (generally lower weight than entities)
        for keyphrase in keyphrases_mapped:
            keyphrase_score = keyphrase.get('score', 0)
            keyphrase_impact = keyphrase_score * 0.5  # Keyphrases have moderate impact
            impact_score += keyphrase_impact
        
        return impact_score
    
    def calculate_search_impact_breakdown(self, entities_mapped: List[Dict], keyphrases_mapped: List[Dict]) -> Dict[str, float]:
        """Calculate detailed breakdown of search impact by category"""
        
        breakdown = {
            'location_impact': 0.0,
            'organization_impact': 0.0,
            'person_impact': 0.0,
            'temporal_impact': 0.0,  # Dates, quantities
            'keyphrase_impact': 0.0,
            'other_impact': 0.0
        }
        
        for entity in entities_mapped:
            entity_type = entity.get('type', '')
            entity_score = entity.get('score', 0)
            
            if entity_type == 'LOCATION':
                breakdown['location_impact'] += entity_score
            elif entity_type == 'ORGANIZATION':
                breakdown['organization_impact'] += entity_score
            elif entity_type == 'PERSON':
                breakdown['person_impact'] += entity_score
            elif entity_type in ['DATE', 'QUANTITY']:
                breakdown['temporal_impact'] += entity_score
            else:
                breakdown['other_impact'] += entity_score
        
        for keyphrase in keyphrases_mapped:
            keyphrase_score = keyphrase.get('score', 0)
            breakdown['keyphrase_impact'] += keyphrase_score * 0.5
        
        # Round all values
        return {k: round(v, 3) for k, v in breakdown.items()}
    
    def analyze_chunk_finding(self, chunks: List[Dict], chunk_positions: List[Dict]) -> Dict[str, Any]:
        """Analyze chunk finding success and identify potential issues"""
        
        found_chunk_ids = set(pos['chunk_id'] for pos in chunk_positions)
        all_chunk_ids = set(chunk.get('chunk_id', '') for chunk in chunks)
        not_found_chunk_ids = all_chunk_ids - found_chunk_ids
        
        # Analyze not found chunks for patterns
        not_found_chunks = [chunk for chunk in chunks if chunk.get('chunk_id') in not_found_chunk_ids]
        
        # Identify potential OCR/formatting issues
        potential_ocr_issues = []
        for chunk in not_found_chunks:
            section_type = chunk.get('section_type', '')
            text = chunk.get('text', '')
            
            # Check for indicators of OCR/formatting issues
            if any(indicator in text.lower() for indicator in ['public disclosure', 'authorized', 'document of']):
                potential_ocr_issues.append({
                    'chunk_id': chunk.get('chunk_id'),
                    'section_type': section_type,
                    'issue_type': 'document_watermark',
                    'text_preview': text[:100]
                })
            elif section_type in ['header', 'footer', 'table']:
                potential_ocr_issues.append({
                    'chunk_id': chunk.get('chunk_id'),
                    'section_type': section_type,
                    'issue_type': 'structural_element',
                    'text_preview': text[:100]
                })
        
        return {
            'issues': len(not_found_chunk_ids),
            'not_found_chunks': list(not_found_chunk_ids),
            'potential_ocr_issues': potential_ocr_issues,
            'success_rate': round((len(found_chunk_ids) / len(all_chunk_ids) * 100) if all_chunk_ids else 0, 2)
        }
    
    def generate_error_metrics(self, doc_id: str, error_message: str) -> Dict[str, Any]:
        """Generate error metrics when mapping fails completely"""
        
        return {
            'doc_id': doc_id,
            'timestamp': datetime.utcnow().isoformat(),
            'processing_stage': 'nlp_entity_mapping',
            'status': 'error',
            'error_message': error_message,
            'entity_mapping_success_rate': 0.0,
            'keyphrase_mapping_success_rate': 0.0,
            'chunk_finding_success_rate': 0.0,
            'estimated_search_quality_impact': 0.0
        }
    
    def log_mapping_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log mapping metrics for CloudWatch observability"""
        
        doc_id = metrics.get('doc_id', 'unknown')
        
        # Log key metrics as structured log entries for CloudWatch
        logger.info(f"ENTITY_MAPPING_METRICS doc_id={doc_id} "
                   f"entity_success_rate={metrics.get('entity_mapping_success_rate', 0)} "
                   f"keyphrase_success_rate={metrics.get('keyphrase_mapping_success_rate', 0)} "
                   f"chunk_success_rate={metrics.get('chunk_finding_success_rate', 0)} "
                   f"search_impact={metrics.get('estimated_search_quality_impact', 0)}")
        
        # Log critical entity metrics (most important for search quality)
        logger.info(f"CRITICAL_ENTITY_METRICS doc_id={doc_id} "
                   f"critical_mapped={metrics.get('critical_entities_mapped', 0)} "
                   f"critical_unmapped={metrics.get('critical_entities_unmapped', 0)} "
                   f"critical_success_rate={metrics.get('critical_entity_success_rate', 0)}")
        
        # Log chunk coverage metrics
        logger.info(f"CHUNK_COVERAGE_METRICS doc_id={doc_id} "
                   f"chunks_with_entities={metrics.get('chunks_with_entities', 0)} "
                   f"total_chunks={metrics.get('total_chunks', 0)} "
                   f"coverage_rate={metrics.get('chunk_entity_coverage_rate', 0)}")
        
        # Log any significant issues
        chunk_issues = metrics.get('chunk_finding_issues', 0)
        if chunk_issues > 0:
            logger.warning(f"CHUNK_FINDING_ISSUES doc_id={doc_id} "
                          f"chunks_not_found={chunk_issues} "
                          f"potential_ocr_issues={len(metrics.get('potential_ocr_artifacts', []))}")
        
        # Log search impact breakdown for detailed analysis
        impact_breakdown = metrics.get('search_impact_breakdown', {})
        logger.info(f"SEARCH_IMPACT_BREAKDOWN doc_id={doc_id} "
                   f"location={impact_breakdown.get('location_impact', 0)} "
                   f"organization={impact_breakdown.get('organization_impact', 0)} "
                   f"person={impact_breakdown.get('person_impact', 0)} "
                   f"keyphrase={impact_breakdown.get('keyphrase_impact', 0)}")
    
    def store_mapping_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store mapping metrics in database for analysis and monitoring"""
        
        try:
            # Store in document_processing_status table with metrics
            self.update_status(
                doc_id=metrics['doc_id'],
                stage='nlp_entity_mapping_metrics',
                status='completed',
                metadata={
                    'entity_mapping_success_rate': metrics.get('entity_mapping_success_rate'),
                    'keyphrase_mapping_success_rate': metrics.get('keyphrase_mapping_success_rate'),
                    'chunk_finding_success_rate': metrics.get('chunk_finding_success_rate'),
                    'estimated_search_quality_impact': metrics.get('estimated_search_quality_impact'),
                    'critical_entity_success_rate': metrics.get('critical_entity_success_rate'),
                    'chunks_with_entities': metrics.get('chunks_with_entities'),
                    'total_chunks': metrics.get('total_chunks'),
                    'chunk_finding_issues': metrics.get('chunk_finding_issues'),
                    'entity_types_mapped': metrics.get('entity_types_mapped'),
                    'search_impact_breakdown': metrics.get('search_impact_breakdown')
                }
            )
            
            # Also store detailed metrics in a separate table if it exists
            # This allows for more detailed analysis without cluttering the main status table
            try:
                self.store_detailed_metrics(metrics)
            except Exception as e:
                # Don't fail if detailed metrics storage fails
                logger.warning(f"Could not store detailed metrics: {e}")
                
        except Exception as e:
            logger.error(f"Failed to store mapping metrics: {e}")
            # Don't raise exception - metrics storage failure shouldn't break processing
    
    def store_detailed_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store detailed metrics in dedicated metrics table (if available)"""
        
        # This method can be enhanced later to store in a dedicated metrics table
        # For now, we'll store key metrics as a JSON blob in the status table
        
        detailed_metrics_json = json.dumps({
            'timestamp': metrics['timestamp'],
            'doc_id': metrics['doc_id'],
            'mapping_metrics': {
                'entity_success_rates': {
                    'overall': metrics.get('entity_mapping_success_rate'),
                    'critical_types': metrics.get('critical_entity_success_rate'),
                    'by_type': metrics.get('entity_types_mapped')
                },
                'chunk_metrics': {
                    'finding_success_rate': metrics.get('chunk_finding_success_rate'),
                    'coverage_rate': metrics.get('chunk_entity_coverage_rate'),
                    'issues_count': metrics.get('chunk_finding_issues')
                },
                'search_impact': {
                    'overall_score': metrics.get('estimated_search_quality_impact'),
                    'breakdown': metrics.get('search_impact_breakdown')
                },
                'unmapped_samples': {
                    'entities': metrics.get('unmapped_entity_sample', []),
                    'keyphrases': metrics.get('unmapped_keyphrase_sample', [])
                }
            }
        })
        
        # Store as metadata in a separate status entry for detailed analysis
        self.update_status(
            doc_id=metrics['doc_id'],
            stage='nlp_mapping_detailed_metrics',
            status='completed',
            metadata={'detailed_metrics': detailed_metrics_json}
        )

    def update_status(self, doc_id: str, stage: str, status: str, metadata: Dict = None, error_message: str = None):
        """Update document processing status with audit trail"""
        try:
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage=stage,
                status=status,
                error_message=error_message,
                system_id='nlp-worker',
                metadata=metadata or {}
            )
            logger.info(f"Set document processing status: {doc_id} -> {stage} -> {status}")
        except Exception as e:
            logger.error(f"Failed to update status for {doc_id}: {e}")
            # Don't raise here to allow processing to continue
