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
from database_manager import DatabaseManager
from document_id_manager import DocumentIDManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class NLPWorker:
    """NLP results processor with audit-first database design"""
    
    def __init__(self):
        """Initialize NLP worker with database and AWS clients"""
        self.db_manager = DatabaseManager()
        self.doc_id_manager = DocumentIDManager(self.db_manager)
        
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
            # Parse SNS records
            records = event.get('Records', [])
            if not records:
                raise ValueError("No records found in event")
            
            results = []
            for record in records:
                result = self.process_record(record)
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
            storage_locations = self.store_results_in_data_lake(doc_id, comprehend_results, mapped_results)
            
            # Update status to completed
            self.update_status(doc_id, 'nlp_complete', 'completed', {
                'processing_results': {
                    'entities_count': len(comprehend_results.get('entities', [])),
                    'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                    'chunks_mapped': len(chunks) > 0,
                    'actual_cost': cost_analysis.get('estimated_cost', 0.0)
                },
                'output_locations': storage_locations,
                'cost_analysis': cost_analysis
            })
            
            # Publish completion message
            self.publish_completion_message(doc_id, storage_locations, comprehend_results, cost_analysis)
            
            logger.info(f"Successfully completed NLP processing for document: {doc_id}")
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'results_summary': {
                    'entities_count': len(comprehend_results.get('entities', [])),
                    'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                    'chunks_mapped': len(chunks) > 0
                },
                'storage_locations': storage_locations
            }
            
        except Exception as e:
            logger.error(f"Error processing NLP results for {doc_id}: {e}")
            
            if doc_id:
                self.update_status(doc_id, 'nlp_complete', 'failed', {
                    'error': str(e),
                    'error_type': type(e).__name__
                })
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }
    
    def get_comprehend_results(self, comprehend_jobs: Dict[str, str]) -> Dict[str, List]:
        """Wait for and retrieve Comprehend job results"""
        try:
            results = {}
            
            # Get entity detection results
            if 'entity_job_id' in comprehend_jobs:
                entity_job_id = comprehend_jobs['entity_job_id']
                logger.info(f"Retrieving entity detection results: {entity_job_id}")
                
                # Wait for job completion
                self.wait_for_job_completion(entity_job_id, 'entities')
                
                # Get job details and download results
                job_response = self.comprehend_client.describe_entities_detection_job(JobId=entity_job_id)
                output_location = job_response['EntitiesDetectionJobProperties']['OutputDataConfig']['S3Uri']
                
                results['entities'] = self.download_comprehend_results(output_location)
            
            # Get key phrases detection results
            if 'key_phrases_job_id' in comprehend_jobs:
                phrases_job_id = comprehend_jobs['key_phrases_job_id']
                logger.info(f"Retrieving key phrases results: {phrases_job_id}")
                
                # Wait for job completion
                self.wait_for_job_completion(phrases_job_id, 'key_phrases')
                
                # Get job details and download results
                job_response = self.comprehend_client.describe_key_phrases_detection_job(JobId=phrases_job_id)
                output_location = job_response['KeyPhrasesDetectionJobProperties']['OutputDataConfig']['S3Uri']
                
                results['key_phrases'] = self.download_comprehend_results(output_location)
            
            logger.info(f"Retrieved Comprehend results: {len(results.get('entities', []))} entities, {len(results.get('key_phrases', []))} key phrases")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving Comprehend results: {e}")
            raise
    
    def wait_for_job_completion(self, job_id: str, job_type: str, max_wait_time: int = 600):
        """Wait for Comprehend job to complete"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                if job_type == 'entities':
                    response = self.comprehend_client.describe_entities_detection_job(JobId=job_id)
                    status = response['EntitiesDetectionJobProperties']['JobStatus']
                elif job_type == 'key_phrases':
                    response = self.comprehend_client.describe_key_phrases_detection_job(JobId=job_id)
                    status = response['KeyPhrasesDetectionJobProperties']['JobStatus']
                else:
                    raise ValueError(f"Unknown job type: {job_type}")
                
                logger.info(f"Job {job_id} status: {status}")
                
                if status == 'COMPLETED':
                    return
                elif status in ['FAILED', 'STOP_REQUESTED', 'STOPPED']:
                    raise Exception(f"Comprehend job {job_id} failed with status: {status}")
                
                # Wait before checking again
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error checking job status: {e}")
                raise
        
        raise Exception(f"Comprehend job {job_id} did not complete within {max_wait_time} seconds")
    
    def download_comprehend_results(self, s3_output_location: str) -> List[Dict]:
        """Download and parse Comprehend results from S3"""
        try:
            # Parse S3 location
            if not s3_output_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 location: {s3_output_location}")
            
            s3_path = s3_output_location[5:]  # Remove 's3://'
            bucket, prefix = s3_path.split('/', 1)
            
            # List objects in the output location
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            results = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.out'):
                    # Download and parse the output file
                    file_response = self.s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                    content = file_response['Body'].read().decode('utf-8')
                    
                    # Parse each line as JSON
                    for line in content.strip().split('\n'):
                        if line.strip():
                            result = json.loads(line)
                            results.extend(result.get('Entities', result.get('KeyPhrases', [])))
            
            return results
            
        except Exception as e:
            logger.error(f"Error downloading Comprehend results: {e}")
            raise
    
    def load_chunks_from_s3(self, chunks_location: str) -> List[Dict]:
        """Load chunks from S3 for offset mapping"""
        try:
            if not chunks_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 location: {chunks_location}")
            
            s3_path = chunks_location[5:]  # Remove 's3://'
            bucket, prefix = s3_path.split('/', 1)
            
            # Remove trailing slash
            if prefix.endswith('/'):
                prefix = prefix[:-1]
            
            logger.info(f"Loading chunks from s3://{bucket}/{prefix}/")
            
            # List chunk files
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}/")
            
            chunks = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json') and 'chunk_' in obj['Key']:
                    # Load individual chunk
                    chunk_response = self.s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    chunks.append(chunk_data)
            
            # Sort chunks by index
            chunks.sort(key=lambda x: x.get('chunk_index', 0))
            
            logger.info(f"Successfully loaded {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error loading chunks from S3: {e}")
            return []
    
    def map_results_to_chunks(self, comprehend_results: Dict, chunks: List[Dict]) -> Dict:
        """Map Comprehend results to chunks using offset mapping"""
        if not chunks:
            logger.info("No chunks available for offset mapping")
            return {}
        
        try:
            mapped_results = {
                'entities_mapped_to_chunks': [],
                'key_phrases_mapped_to_chunks': []
            }
            
            # Simple offset mapping (can be enhanced with more sophisticated logic)
            for entity in comprehend_results.get('entities', []):
                begin_offset = entity.get('BeginOffset', 0)
                end_offset = entity.get('EndOffset', 0)
                
                # Find which chunk contains this entity
                for chunk in chunks:
                    chunk_start = chunk.get('start_char', 0)
                    chunk_end = chunk.get('end_char', chunk_start + len(chunk.get('content', '')))
                    
                    if chunk_start <= begin_offset < chunk_end:
                        mapped_entity = {
                            **entity,
                            'chunk_id': chunk.get('chunk_id'),
                            'chunk_index': chunk.get('chunk_index'),
                            'relative_offset': begin_offset - chunk_start
                        }
                        mapped_results['entities_mapped_to_chunks'].append(mapped_entity)
                        break
            
            # Map key phrases similarly
            for phrase in comprehend_results.get('key_phrases', []):
                begin_offset = phrase.get('BeginOffset', 0)
                end_offset = phrase.get('EndOffset', 0)
                
                for chunk in chunks:
                    chunk_start = chunk.get('start_char', 0)
                    chunk_end = chunk.get('end_char', chunk_start + len(chunk.get('content', '')))
                    
                    if chunk_start <= begin_offset < chunk_end:
                        mapped_phrase = {
                            **phrase,
                            'chunk_id': chunk.get('chunk_id'),
                            'chunk_index': chunk.get('chunk_index'),
                            'relative_offset': begin_offset - chunk_start
                        }
                        mapped_results['key_phrases_mapped_to_chunks'].append(mapped_phrase)
                        break
            
            logger.info(f"Mapped {len(mapped_results['entities_mapped_to_chunks'])} entities and {len(mapped_results['key_phrases_mapped_to_chunks'])} key phrases to chunks")
            return mapped_results
            
        except Exception as e:
            logger.error(f"Error mapping results to chunks: {e}")
            return {}
    
    def store_results_in_data_lake(self, doc_id: str, comprehend_results: Dict, mapped_results: Dict) -> Dict[str, str]:
        """Store NLP results in S3 data lake"""
        try:
            storage_locations = {}
            base_key = f"nlp-results/{doc_id}"
            
            # Store raw entities
            entities_key = f"{base_key}/entities.json"
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=entities_key,
                Body=json.dumps(comprehend_results.get('entities', []), indent=2),
                ContentType='application/json'
            )
            storage_locations['entities_file'] = f"s3://{self.ner_results_bucket}/{entities_key}"
            
            # Store raw key phrases
            phrases_key = f"{base_key}/key_phrases.json"
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=phrases_key,
                Body=json.dumps(comprehend_results.get('key_phrases', []), indent=2),
                ContentType='application/json'
            )
            storage_locations['key_phrases_file'] = f"s3://{self.ner_results_bucket}/{phrases_key}"
            
            # Store chunk mappings if available
            if mapped_results:
                mappings_key = f"{base_key}/chunk_mappings.json"
                self.s3_client.put_object(
                    Bucket=self.ner_results_bucket,
                    Key=mappings_key,
                    Body=json.dumps(mapped_results, indent=2),
                    ContentType='application/json'
                )
                storage_locations['chunk_mappings_file'] = f"s3://{self.ner_results_bucket}/{mappings_key}"
            
            # Store complete results summary
            summary_key = f"{base_key}/summary.json"
            summary = {
                'doc_id': doc_id,
                'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
                'results_summary': {
                    'entities_count': len(comprehend_results.get('entities', [])),
                    'key_phrases_count': len(comprehend_results.get('key_phrases', [])),
                    'chunks_mapped': len(mapped_results) > 0
                },
                'storage_locations': storage_locations
            }
            
            self.s3_client.put_object(
                Bucket=self.ner_results_bucket,
                Key=summary_key,
                Body=json.dumps(summary, indent=2),
                ContentType='application/json'
            )
            storage_locations['summary_file'] = f"s3://{self.ner_results_bucket}/{summary_key}"
            storage_locations['base_location'] = f"s3://{self.ner_results_bucket}/{base_key}/"
            
            logger.info(f"Stored NLP results in data lake: {storage_locations['base_location']}")
            return storage_locations
            
        except Exception as e:
            logger.error(f"Error storing results in data lake: {e}")
            raise
    
    def publish_completion_message(self, doc_id: str, storage_locations: Dict, results: Dict, cost_analysis: Dict):
        """Publish NLP completion message"""
        try:
            completion_message = {
                'doc_id': doc_id,
                'stage': 'nlp_complete',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'data_locations': storage_locations,
                'results_summary': {
                    'entities_count': len(results.get('entities', [])),
                    'key_phrases_count': len(results.get('key_phrases', [])),
                    'processing_completed': True
                },
                'cost_analysis': cost_analysis
            }
            
            response = self.sns_client.publish(
                TopicArn=self.completion_topic_arn,
                Message=json.dumps(completion_message, default=str),
                Subject=f"NLP processing complete: {doc_id}"
            )
            
            logger.info(f"Published completion message: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Error publishing completion message: {e}")
            # Don't raise - this shouldn't fail the main processing
    
    def update_status(self, doc_id: str, stage: str, status: str, metadata: Dict = None):
        """Update document processing status with audit trail"""
        try:
            self.doc_id_manager.set_document_processing_status(
                doc_id=doc_id,
                stage=stage,
                status=status,
                metadata=metadata or {}
            )
            logger.info(f"Set document processing status: {doc_id} -> {stage} -> {status}")
        except Exception as e:
            logger.error(f"Failed to update status for {doc_id}: {e}")
            raise
