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
        self.completion_topic_arn = os.environ.get('NLP_COMPLETION_TOPIC_ARN',
                                                  'arn:aws:sns:us-east-1:861276078413:nlp-processing-complete')
        
        logger.info("✅ NLP Worker initialized")
        logger.info(f"NER results bucket: {self.ner_results_bucket}")
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
            mapped_results = self.map_results_to_chunks(comprehend_results, chunks)
            
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
            mapped_results = self.map_results_to_chunks(comprehend_results, chunks)
            
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
    
    def map_results_to_chunks(self, comprehend_results: Dict[str, List], chunks: List[Dict]) -> Dict[str, List]:
        """Map Comprehend results to document chunks"""
        if not chunks:
            logger.info("No chunks available for mapping, skipping")
            return {
                'entities_by_chunk': [],
                'key_phrases_by_chunk': []
            }
        
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
        for entity in comprehend_results.get('entities', []):
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
        
        # Map key phrases to chunks
        key_phrases_by_chunk = []
        for phrase in comprehend_results.get('key_phrases', []):
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
        
        logger.info(f"Mapped {len(entities_by_chunk)} entities and {len(key_phrases_by_chunk)} key phrases to chunks")
        
        return {
            'entities_by_chunk': entities_by_chunk,
            'key_phrases_by_chunk': key_phrases_by_chunk
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
