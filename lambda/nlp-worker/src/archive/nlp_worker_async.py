#!/usr/bin/env python3
"""
Asynchronous NLP Worker - Processes Comprehend job completion notifications
Handles entity detection and key phrase detection results independently
"""
import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import tarfile
import io

# Import from lambda layers
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AsyncNLPWorker:
    """Asynchronous NLP results processor"""
    
    def __init__(self):
        """Initialize NLP worker with database and AWS clients"""
        self.db_manager = DatabaseManager()
        
        # AWS clients
        self.s3_client = boto3.client('s3')
        self.comprehend_client = boto3.client('comprehend', region_name=os.environ.get('COMPREHEND_REGION', 'us-east-1'))
        
        # Configuration
        self.ner_results_bucket = os.environ.get('NER_RESULTS_BUCKET',
                                                'solve-global-kr-dl-ner-results-861276078413-us-east-1')
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET',
                                           'solve-global-kr-dl-chunks-861276078413-us-east-1')
        
        logger.info("✅ Async NLP Worker initialized")
        logger.info(f"NER results bucket: {self.ner_results_bucket}")
        logger.info(f"Chunks bucket: {self.chunks_bucket}")
    
    def process_event(self, event, context):
        """Process Lambda event with proper error handling"""
        try:
            # Parse records
            records = event.get('Records', [])
            if not records:
                raise ValueError("No records found in event")
            
            results = []
            for record in records:
                # Handle SQS-wrapped SNS messages
                if 'body' in record:
                    logger.info(f"Processing SQS message: {record.get('messageId', 'unknown')}")
                    try:
                        # Parse as SNS message wrapped in SQS
                        body = json.loads(record['body'])
                        if 'Type' in body and body['Type'] == 'Notification':
                            logger.info("Processing SQS-wrapped SNS message")
                            # Parse the Comprehend notification
                            comprehend_message = json.loads(body['Message'])
                            result = self.process_comprehend_notification(comprehend_message)
                        else:
                            logger.error(f"Unknown SQS message format: {body}")
                            result = {'status': 'error', 'error': 'Unknown SQS message format'}
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message body as JSON: {e}")
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
    
    def process_comprehend_notification(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process Comprehend job completion notification"""
        try:
            job_id = message.get('JobId')
            job_status = message.get('JobStatus')
            job_name = message.get('JobName')
            
            if not all([job_id, job_status, job_name]):
                raise ValueError(f"Missing required fields in notification: {message}")
            
            logger.info(f"Processing Comprehend notification - Job: {job_name}, Status: {job_status}")
            
            # Extract doc_id and job type from job name (e.g., "entities-038c909d361bdadb165c-1753214282")
            parts = job_name.split('-')
            if len(parts) < 2:
                raise ValueError(f"Invalid job name format: {job_name}")
            
            job_type = parts[0]  # "entities" or "phrases"
            doc_id = parts[1]
            
            if job_status != 'COMPLETED':
                logger.warning(f"Job {job_id} for {doc_id} completed with status {job_status}")
                # Update status to failed
                stage = 'nlp_entity_processing' if job_type == 'entities' else 'nlp_keyphrase_processing'
                self.update_status(doc_id, stage, 'failed', error_message=f"Comprehend job failed with status: {job_status}")
                return {
                    'status': 'failed',
                    'doc_id': doc_id,
                    'job_type': job_type,
                    'job_status': job_status
                }
            
            # Process based on job type
            if job_type == 'entities':
                return self.process_entity_results(doc_id, job_id)
            elif job_type == 'phrases':
                return self.process_key_phrase_results(doc_id, job_id)
            else:
                raise ValueError(f"Unknown job type: {job_type}")
                
        except Exception as e:
            logger.error(f"Error processing Comprehend notification: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def process_entity_results(self, doc_id: str, job_id: str) -> Dict[str, Any]:
        """Process entity detection results"""
        try:
            logger.info(f"Processing entity results for document: {doc_id}")
            
            # Update status
            self.update_status(doc_id, 'nlp_entity_processing', 'in_progress')
            
            # Retrieve entity results
            entities = self.retrieve_comprehend_results(job_id, 'entities-detection')
            logger.info(f"Retrieved {len(entities)} entities")
            
            # Load chunks for offset mapping
            chunks_location = f"s3://{self.chunks_bucket}/data-lake/{doc_id}/"
            chunks = self.load_chunks_from_s3(chunks_location)
            
            # Map entities to chunks
            mapped_entities = self.map_entities_to_chunks(entities, chunks)
            
            # Store results in S3
            s3_locations = self.store_entity_results(doc_id, entities, mapped_entities)
            
            # Update status to completed
            self.update_status(doc_id, 'nlp_entity_processing', 'completed', {
                'entities_count': len(entities),
                'results_locations': s3_locations,
                'chunks_mapped': len(chunks) > 0
            })
            
            logger.info(f"Successfully processed entity results for document: {doc_id}")
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'job_type': 'entities',
                'entities_count': len(entities),
                'results_locations': s3_locations
            }
            
        except Exception as e:
            logger.error(f"Error processing entity results for {doc_id}: {e}")
            self.update_status(doc_id, 'nlp_entity_processing', 'failed', error_message=str(e))
            return {
                'status': 'error',
                'doc_id': doc_id,
                'job_type': 'entities',
                'error': str(e)
            }
    
    def process_key_phrase_results(self, doc_id: str, job_id: str) -> Dict[str, Any]:
        """Process key phrase detection results"""
        try:
            logger.info(f"Processing key phrase results for document: {doc_id}")
            
            # Update status
            self.update_status(doc_id, 'nlp_keyphrase_processing', 'in_progress')
            
            # Retrieve key phrase results
            key_phrases = self.retrieve_comprehend_results(job_id, 'key-phrases-detection')
            logger.info(f"Retrieved {len(key_phrases)} key phrases")
            
            # Load chunks for offset mapping
            chunks_location = f"s3://{self.chunks_bucket}/data-lake/{doc_id}/"
            chunks = self.load_chunks_from_s3(chunks_location)
            
            # Map key phrases to chunks
            mapped_phrases = self.map_keyphrases_to_chunks(key_phrases, chunks)
            
            # Store results in S3
            s3_locations = self.store_keyphrase_results(doc_id, key_phrases, mapped_phrases)
            
            # Update status to completed
            self.update_status(doc_id, 'nlp_keyphrase_processing', 'completed', {
                'key_phrases_count': len(key_phrases),
                'results_locations': s3_locations,
                'chunks_mapped': len(chunks) > 0
            })
            
            logger.info(f"Successfully processed key phrase results for document: {doc_id}")
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'job_type': 'key_phrases',
                'key_phrases_count': len(key_phrases),
                'results_locations': s3_locations
            }
            
        except Exception as e:
            logger.error(f"Error processing key phrase results for {doc_id}: {e}")
            self.update_status(doc_id, 'nlp_keyphrase_processing', 'failed', error_message=str(e))
            return {
                'status': 'error',
                'doc_id': doc_id,
                'job_type': 'key_phrases',
                'error': str(e)
            }
    
    def retrieve_comprehend_results(self, job_id: str, job_type: str) -> List[Dict]:
        """Retrieve and parse Comprehend job results from S3"""
        try:
            # Get job details to find output location
            if job_type == 'entities-detection':
                response = self.comprehend_client.describe_entities_detection_job(JobId=job_id)
                output_uri = response['EntitiesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            else:  # key-phrases-detection
                response = self.comprehend_client.describe_key_phrases_detection_job(JobId=job_id)
                output_uri = response['KeyPhrasesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            
            logger.info(f"Retrieving results from: {output_uri}")
            
            # Parse S3 URI
            uri_parts = output_uri.replace('s3://', '').split('/')
            bucket = uri_parts[0]
            key = '/'.join(uri_parts[1:])
            
            # Download tar.gz file
            download_path = f"/tmp/{job_type}-results-{job_id}.tar.gz"
            self.s3_client.download_file(bucket, key, download_path)
            
            # Extract and parse results
            results = []
            with tarfile.open(download_path, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile() and member.name.endswith('.json'):
                        f = tar.extractfile(member)
                        if f:
                            content = f.read().decode('utf-8')
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
            
            logger.info(f"Retrieved {len(results)} results from Comprehend job")
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
    
    def map_entities_to_chunks(self, entities: List[Dict], chunks: List[Dict]) -> List[Dict]:
        """Map entities to document chunks"""
        if not chunks:
            logger.info("No chunks available for entity mapping, skipping")
            return []
        
        # Sort chunks by position
        chunks.sort(key=lambda x: x.get('position', 0))
        
        # Calculate chunk offsets
        chunk_offsets = []
        current_offset = 0
        for chunk in chunks:
            text = chunk.get('text', '')
            chunk_offsets.append({
                'chunk_id': chunk.get('chunk_id', ''),
                'start': current_offset,
                'end': current_offset + len(text),
                'text': text
            })
            current_offset += len(text)
        
        # Map entities to chunks
        entities_by_chunk = []
        for entity in entities:
            begin_offset = entity.get('begin_offset', 0)
            end_offset = entity.get('end_offset', 0)
            
            for chunk_offset in chunk_offsets:
                if (begin_offset >= chunk_offset['start'] and 
                    begin_offset < chunk_offset['end']):
                    # Entity starts in this chunk
                    relative_begin = begin_offset - chunk_offset['start']
                    relative_end = min(end_offset - chunk_offset['start'], 
                                      len(chunk_offset['text']))
                    
                    entities_by_chunk.append({
                        'chunk_id': chunk_offset['chunk_id'],
                        'entity': entity.get('text', ''),
                        'type': entity.get('type', ''),
                        'score': entity.get('score', 0),
                        'begin_offset': relative_begin,
                        'end_offset': relative_end
                    })
                    break
        
        logger.info(f"Mapped {len(entities_by_chunk)} entities to chunks")
        return entities_by_chunk
    
    def map_keyphrases_to_chunks(self, key_phrases: List[Dict], chunks: List[Dict]) -> List[Dict]:
        """Map key phrases to document chunks"""
        if not chunks:
            logger.info("No chunks available for key phrase mapping, skipping")
            return []
        
        # Sort chunks by position
        chunks.sort(key=lambda x: x.get('position', 0))
        
        # Calculate chunk offsets
        chunk_offsets = []
        current_offset = 0
        for chunk in chunks:
            text = chunk.get('text', '')
            chunk_offsets.append({
                'chunk_id': chunk.get('chunk_id', ''),
                'start': current_offset,
                'end': current_offset + len(text),
                'text': text
            })
            current_offset += len(text)
        
        # Map key phrases to chunks
        key_phrases_by_chunk = []
        for phrase in key_phrases:
            begin_offset = phrase.get('begin_offset', 0)
            end_offset = phrase.get('end_offset', 0)
            
            for chunk_offset in chunk_offsets:
                if (begin_offset >= chunk_offset['start'] and 
                    begin_offset < chunk_offset['end']):
                    # Phrase starts in this chunk
                    relative_begin = begin_offset - chunk_offset['start']
                    relative_end = min(end_offset - chunk_offset['start'], 
                                      len(chunk_offset['text']))
                    
                    key_phrases_by_chunk.append({
                        'chunk_id': chunk_offset['chunk_id'],
                        'phrase': phrase.get('text', ''),
                        'score': phrase.get('score', 0),
                        'begin_offset': relative_begin,
                        'end_offset': relative_end
                    })
                    break
        
        logger.info(f"Mapped {len(key_phrases_by_chunk)} key phrases to chunks")
        return key_phrases_by_chunk
    
    def store_entity_results(self, doc_id: str, entities: List[Dict], mapped_entities: List[Dict]) -> Dict[str, str]:
        """Store entity results in S3 data lake"""
        try:
            # Prepare S3 paths
            results_prefix = f"nlp-results/{doc_id}/"
            entities_key = f"{results_prefix}entities.json"
            mapped_entities_key = f"{results_prefix}entities_by_chunk.json"
            
            # Store entities
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=entities_key,
                Body=json.dumps(entities, indent=2),
                ContentType='application/json'
            )
            
            # Store mapped entities
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=mapped_entities_key,
                Body=json.dumps(mapped_entities, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Stored entity results in S3: {self.ner_results_bucket}/{results_prefix}")
            
            return {
                'entities_location': f"s3://{self.ner_results_bucket}/{entities_key}",
                'mapped_entities_location': f"s3://{self.ner_results_bucket}/{mapped_entities_key}"
            }
            
        except Exception as e:
            logger.error(f"Error storing entity results in S3: {e}")
            raise
    
    def store_keyphrase_results(self, doc_id: str, key_phrases: List[Dict], mapped_phrases: List[Dict]) -> Dict[str, str]:
        """Store key phrase results in S3 data lake"""
        try:
            # Prepare S3 paths
            results_prefix = f"nlp-results/{doc_id}/"
            key_phrases_key = f"{results_prefix}key_phrases.json"
            mapped_phrases_key = f"{results_prefix}key_phrases_by_chunk.json"
            
            # Store key phrases
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=key_phrases_key,
                Body=json.dumps(key_phrases, indent=2),
                ContentType='application/json'
            )
            
            # Store mapped key phrases
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=mapped_phrases_key,
                Body=json.dumps(mapped_phrases, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Stored key phrase results in S3: {self.ner_results_bucket}/{results_prefix}")
            
            return {
                'key_phrases_location': f"s3://{self.ner_results_bucket}/{key_phrases_key}",
                'mapped_phrases_location': f"s3://{self.ner_results_bucket}/{mapped_phrases_key}"
            }
            
        except Exception as e:
            logger.error(f"Error storing key phrase results in S3: {e}")
            raise
    
    def update_status(self, doc_id: str, stage: str, status: str, metadata: Dict = None, error_message: str = None):
        """Update document processing status with audit trail"""
        try:
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage=stage,
                status=status,
                error_message=error_message,
                system_id='nlp-worker-async',
                metadata=metadata or {}
            )
            logger.info(f"Set document processing status: {doc_id} -> {stage} -> {status}")
        except Exception as e:
            logger.error(f"Failed to update status for {doc_id}: {e}")
            # Don't raise here to allow processing to continue
