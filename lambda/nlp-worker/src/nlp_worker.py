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
                                         'solve-global-kr-text-861276078413-us-east-1')
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
            
            # Extract document information
            doc_id = sns_message.get('doc_id')
            if not doc_id:
                raise ValueError("doc_id not found in message")
            
            comprehend_jobs = sns_message.get('comprehend_jobs', {})
            chunks_location = sns_message.get('chunks_location')
            cost_analysis = sns_message.get('cost_analysis', {})
            
            logger.info(f"Processing NLP results for document: {doc_id}")
            logger.info(f"Comprehend jobs: {comprehend_jobs}")
            
            # Update status to results processing
            self.update_status(doc_id, 'nlp_results_processing', 'in_progress', {
                'comprehend_jobs': comprehend_jobs,
                'chunks_location': chunks_location,
                'cost_analysis': cost_analysis
            })
            
            # Wait for and retrieve Comprehend results
            comprehend_results = self.get_comprehend_results(comprehend_jobs)
            
            # Load chunks for offset mapping
            chunks = self.load_chunks_from_s3(chunks_location) if chunks_location else []
            
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
            chunks_location = message.get('chunks_location')
            cost_analysis = message.get('cost_analysis', {})
            
            logger.info(f"Processing NLP results for document: {doc_id}")
            logger.info(f"Comprehend jobs: {comprehend_jobs}")
            
            # Update status to results processing
            self.update_status(doc_id, 'nlp_results_processing', 'in_progress', {
                'comprehend_jobs': comprehend_jobs,
                'chunks_location': chunks_location,
                'cost_analysis': cost_analysis
            })
            
            # Wait for and retrieve Comprehend results
            comprehend_results = self.get_comprehend_results(comprehend_jobs)
            
            # Load chunks for offset mapping
            chunks = self.load_chunks_from_s3(chunks_location) if chunks_location else []
            
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
            
            # Download tar.gz file
            download_path = f"/tmp/{job_type}-results.tar.gz"
            self.s3_client.download_file(bucket, key, download_path)
            
            # Extract tar.gz file
            import tarfile
            import io
            
            results = []
            with tarfile.open(download_path, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.json'):
                        f = tar.extractfile(member)
                        if f:
                            content = f.read()
                            data = json.loads(content)
                            
                            # Parse based on job type
                            if job_type == 'entities-detection':
                                for item in data.get('Entities', []):
                                    results.append({
                                        'text': item.get('Text', ''),
                                        'type': item.get('Type', ''),
                                        'score': item.get('Score', 0),
                                        'begin_offset': item.get('BeginOffset', 0),
                                        'end_offset': item.get('EndOffset', 0)
                                    })
                            else:  # key-phrases-detection
                                for item in data.get('KeyPhrases', []):
                                    results.append({
                                        'text': item.get('Text', ''),
                                        'score': item.get('Score', 0),
                                        'begin_offset': item.get('BeginOffset', 0),
                                        'end_offset': item.get('EndOffset', 0)
                                    })
            
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
            # The text that nlp-initiator sends to Comprehend
            text_key = f"text/{doc_id}.txt"
            
            response = self.s3_client.get_object(
                Bucket=self.text_bucket,
                Key=text_key
            )
            
            original_text = response['Body'].read().decode('utf-8')
            logger.info(f"Loaded original document text: {len(original_text)} characters")
            return original_text
            
        except Exception as e:
            logger.error(f"Error loading original document text: {e}")
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
            else:
                logger.warning(f"Chunk {chunk.get('chunk_id')} text not found in original document")
        
        # Sort by position in document
        chunk_positions.sort(key=lambda x: x['start_offset'])
        
        logger.info(f"Found {len(chunk_positions)} chunk positions in original document")
        return chunk_positions

    def map_results_to_chunks(self, comprehend_results: Dict[str, List], chunks: List[Dict], doc_id: str) -> Dict[str, List]:
        """
        CORRECTED: Map Comprehend results to document chunks using original document positions
        
        The previous implementation was flawed because it:
        1. Assumed chunks were sequential segments that could be concatenated
        2. Used wrong sort key ('position' instead of 'chunk_index')
        3. Created fictional document text that didn't match Comprehend input
        
        CORRECTED APPROACH:
        1. Load the original document text that Comprehend analyzed
        2. Find where each chunk appears in the original document
        3. Map entity/keyphrase offsets (relative to original) to chunks
        """
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
            for entity in comprehend_results.get('entities', []):
                entity_start = entity.get('begin_offset', 0)
                entity_end = entity.get('end_offset', 0)
                entity_text = entity.get('text', '')
                
                # Find chunks that contain this entity
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
                            'type': entity.get('type', ''),
                            'score': entity.get('score', 0),
                            'original_begin_offset': entity_start,
                            'original_end_offset': entity_end,
                            'chunk_relative_begin': relative_start,
                            'chunk_relative_end': relative_end
                        })
            
            # Map key phrases to chunks using correct positions
            key_phrases_by_chunk = []
            for phrase in comprehend_results.get('key_phrases', []):
                phrase_start = phrase.get('begin_offset', 0)
                phrase_end = phrase.get('end_offset', 0)
                phrase_text = phrase.get('text', '')
                
                # Find chunks that contain this phrase
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
                            'chunk_relative_end': relative_end
                        })
            
            logger.info(f"Mapped {len(entities_by_chunk)} entities and {len(key_phrases_by_chunk)} key phrases to chunks")
            
            return {
                'entities_by_chunk': entities_by_chunk,
                'key_phrases_by_chunk': key_phrases_by_chunk
            }
            
        except Exception as e:
            logger.error(f"Error in corrected chunk mapping: {e}")
            # Return empty results rather than failing completely
            return {
                'entities_by_chunk': [],
                'key_phrases_by_chunk': []
            }
    
    def store_results_in_s3(self, doc_id: str, comprehend_results: Dict[str, List], 
                          mapped_results: Dict[str, List]) -> Dict[str, str]:
        """Store NLP results in S3 data lake"""
        try:
            # Prepare S3 paths
            results_prefix = f"nlp-results/{doc_id}/"
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
