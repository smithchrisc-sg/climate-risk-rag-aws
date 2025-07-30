#!/usr/bin/env python3
"""
NLP Initiator - Audit-First Database Integration
Processes chunks_ready messages and initiates async Comprehend jobs
"""
import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import urlparse

# Import from lambda layers
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class NLPInitiator:
    """NLP processing initiator with audit-first database design"""
    
    def __init__(self):
        """Initialize NLP initiator with database and AWS clients"""
        self.db_manager = DatabaseManager()
        
        # AWS clients
        self.s3_client = boto3.client('s3')
        self.comprehend_client = boto3.client('comprehend', region_name=os.environ.get('COMPREHEND_REGION', 'us-east-1'))
        self.sns_client = boto3.client('sns')
        
        # Configuration
        self.cost_threshold = float(os.environ.get('NLP_COST_THRESHOLD', '0.50'))
        self.nlp_worker_topic_arn = os.environ.get('NLP_WORKER_TOPIC_ARN', 
                                                  'arn:aws:sns:us-east-1:861276078413:nlp-worker')
        self.comprehend_data_access_role = os.environ.get('COMPREHEND_DATA_ACCESS_ROLE_ARN')
        self.comprehend_output_bucket = os.environ.get('COMPREHEND_OUTPUT_BUCKET',
                                                      'solve-global-kr-dl-comprehend-output-861276078413-us-east-1')
        self.entity_completion_topic_arn = os.environ.get('ENTITY_COMPLETION_TOPIC_ARN',
                                                         'arn:aws:sns:us-east-1:861276078413:comprehend-entity-completion')
        self.keyphrase_completion_topic_arn = os.environ.get('KEYPHRASE_COMPLETION_TOPIC_ARN',
                                                            'arn:aws:sns:us-east-1:861276078413:comprehend-keyphrase-completion')
        
        logger.info("✅ NLP Initiator initialized")
        logger.info(f"Cost threshold: ${self.cost_threshold}")
        logger.info(f"Comprehend region: {os.environ.get('COMPREHEND_REGION', 'us-east-1')}")
        logger.info(f"Output bucket: {self.comprehend_output_bucket}")
    
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
                    'message': 'NLP processing initiated',
                    'processed_records': len(results),
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            raise
    
    def process_direct_message(self, message):
        """Process a direct message (not SNS)"""
        doc_id = None
        
        try:
            # Extract document information
            doc_id = message.get('doc_id')
            if not doc_id:
                raise ValueError("doc_id not found in message")
            
            # Extract data locations
            data_locations = message.get('data_locations', {})
            chunks_location = data_locations.get('chunks_location')
            
            # Derive text_location from chunks_location if not provided
            text_location = data_locations.get('text_location')
            if not text_location and chunks_location:
                # Convert chunks location to text location
                # Example: s3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/doc_id/ 
                # -> s3://solve-global-kr-dl-text-861276078413-us-east-1/data-lake/doc_id/raw_text.txt
                chunks_path = chunks_location.rstrip('/')
                
                # Extract the document ID and path parts
                path_parts = chunks_path.split('/')
                bucket_name = path_parts[2]
                doc_id_from_path = path_parts[-1]
                
                # Replace 'chunks' with 'text' in the bucket name
                text_bucket = bucket_name.replace('-dl-chunks-', '-dl-text-')
                
                # Construct the text location
                path_without_bucket = '/'.join(path_parts[3:])
                text_location = f"s3://{text_bucket}/{path_without_bucket}/raw_text.txt"
                logger.info(f"Derived text_location from chunks_location: {text_location}")
            
            if not chunks_location:
                raise ValueError("chunks_location is required")
            
            # Continue with normal processing
            return self._process_document(doc_id, chunks_location, text_location, message.get('processing_metadata', {}))
            
        except Exception as e:
            logger.error(f"Error processing direct message for {doc_id}: {e}")
            
            if doc_id:
                self.update_status(doc_id, 'nlp_initiate', 'failed', error_message=str(e))
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }
    
    def process_record(self, record):
        """Process individual SNS record"""
        doc_id = None
        
        try:
            # Parse SNS message
            sns_message = json.loads(record['Sns']['Message'])
            
            # Extract document information
            doc_id = sns_message.get('doc_id')
            if not doc_id:
                raise ValueError("doc_id not found in message")
            
            # Extract data locations
            data_locations = sns_message.get('data_locations', {})
            chunks_location = data_locations.get('chunks_location')
            
            # Derive text_location from chunks_location if not provided
            text_location = data_locations.get('text_location')
            if not text_location and chunks_location:
                # Convert chunks location to text location
                # Example: s3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/doc_id/ 
                # -> s3://solve-global-kr-dl-text-861276078413-us-east-1/data-lake/doc_id/raw_text.txt
                chunks_path = chunks_location.rstrip('/')
                
                # Extract the document ID and path parts
                path_parts = chunks_path.split('/')
                bucket_name = path_parts[2]
                doc_id_from_path = path_parts[-1]
                
                # Replace 'chunks' with 'text' in the bucket name
                text_bucket = bucket_name.replace('-dl-chunks-', '-dl-text-')
                
                # Construct the text location
                path_without_bucket = '/'.join(path_parts[3:])
                text_location = f"s3://{text_bucket}/{path_without_bucket}/raw_text.txt"
                logger.info(f"Derived text_location from chunks_location: {text_location}")
            
            if not chunks_location:
                raise ValueError("chunks_location is required")
            
            # Continue with normal processing
            return self._process_document(doc_id, chunks_location, text_location, sns_message.get('processing_metadata', {}))
            
        except Exception as e:
            logger.error(f"Error processing NLP initiation for {doc_id}: {e}")
            
            if doc_id:
                self.update_status(doc_id, 'nlp_initiate', 'failed', error_message=str(e))
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }
    
    def _process_document(self, doc_id, chunks_location, text_location, processing_metadata):
        """Common document processing logic"""
        logger.info(f"Processing NLP initiation for document: {doc_id}")
        logger.info(f"Text location: {text_location}")
        logger.info(f"Chunks location: {chunks_location}")
        
        # Update status to processing
        self.update_status(doc_id, 'nlp_initiate', 'in_progress', metadata={
            'input_data': {
                'chunks_location': chunks_location,
                'text_location': text_location
            },
            'processing_metadata': processing_metadata
        })
        
        # Load and validate text
        full_text = self.load_text_from_s3(text_location)
        if not full_text:
            raise ValueError("Could not load text content for NLP processing")
        
        character_count = len(full_text)
        logger.info(f"Loaded text: {character_count} characters")
        
        # Validate cost before processing
        estimated_cost = self.estimate_comprehend_cost(character_count)
        if estimated_cost > self.cost_threshold:
            raise ValueError(f"Estimated cost ${estimated_cost:.4f} exceeds threshold ${self.cost_threshold}")
        
        logger.info(f"Cost validation passed: ${estimated_cost:.4f} <= ${self.cost_threshold}")
        
        # Start async Comprehend jobs
        comprehend_jobs = self.start_comprehend_jobs(doc_id, full_text)
        
        # Update status to processing with job information
        self.update_status(doc_id, 'nlp_processing', 'in_progress', metadata={
            'comprehend_jobs': comprehend_jobs,
            'cost_analysis': {
                'estimated_cost': estimated_cost,
                'character_count': character_count,
                'threshold': self.cost_threshold,
                'approved_for_processing': True
            },
            'text_metadata': {
                'character_count': character_count,
                'text_location': text_location
            }
        })
        
        # Update status to completed (initiator done)
        self.update_status(doc_id, 'nlp_initiate', 'completed', 
                         system_id='nlp-processor',
                         metadata={
                             'comprehend_jobs_started': comprehend_jobs,
                             'worker_notified': True,
                             'estimated_cost': estimated_cost
                         })
        
        logger.info(f"Successfully initiated NLP processing for document: {doc_id}")
        
        return {
            'status': 'success',
            'doc_id': doc_id,
            'comprehend_jobs': comprehend_jobs,
            'estimated_cost': estimated_cost,
            'character_count': character_count
        }
    
    def load_text_from_s3(self, text_location: str) -> str:
        """Load full text from S3 location"""
        try:
            # Parse S3 location
            if not text_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 location format: {text_location}")
            
            # Handle both folder and direct file paths
            s3_path = text_location[5:]  # Remove 's3://'
            
            if s3_path.endswith('/') or not s3_path.split('/')[-1].endswith('.txt'):
                # This is a folder, construct path to raw_text.txt
                if s3_path.endswith('/'):
                    file_path = f"{s3_path}raw_text.txt"
                else:
                    file_path = f"{s3_path}/raw_text.txt"
            else:
                # This is already a direct file path
                file_path = s3_path
            
            bucket, key = file_path.split('/', 1)
            
            logger.info(f"Loading text from s3://{bucket}/{key}")
            
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            text_content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Successfully loaded {len(text_content)} characters")
            return text_content
            
        except Exception as e:
            logger.error(f"Error loading text from S3: {e}")
            raise
    
    def estimate_comprehend_cost(self, character_count: int) -> float:
        """Estimate Comprehend processing cost"""
        # Amazon Comprehend pricing: $0.0001 per 100 characters for entities + key phrases
        # So $0.0002 per 100 characters for both services
        cost_per_100_chars = 0.0002
        estimated_cost = (character_count / 100.0) * cost_per_100_chars
        return round(estimated_cost, 4)
    
    def start_comprehend_jobs(self, doc_id: str, text: str) -> Dict[str, str]:
        """Start async Comprehend entity and key phrase detection jobs"""
        try:
            # Prepare S3 input location for Comprehend
            input_key = f"comprehend-input/{doc_id}/input.txt"
            input_bucket = self.comprehend_output_bucket  # Use same bucket for input/output
            
            # Upload text to S3 for Comprehend processing
            self.s3_client.put_object(
                Bucket=input_bucket,
                Key=input_key,
                Body=text.encode('utf-8'),
                ContentType='text/plain'
            )
            
            input_s3_uri = f"s3://{input_bucket}/{input_key}"
            output_s3_uri = f"s3://{self.comprehend_output_bucket}/comprehend-output/{doc_id}/"
            
            logger.info(f"Starting Comprehend jobs for {doc_id}")
            logger.info(f"Input: {input_s3_uri}")
            logger.info(f"Output: {output_s3_uri}")
            
            jobs = {}
            
            # Start entity detection job
            entity_response = self.comprehend_client.start_entities_detection_job(
                InputDataConfig={
                    'S3Uri': input_s3_uri,
                    'InputFormat': 'ONE_DOC_PER_FILE'
                },
                OutputDataConfig={
                    'S3Uri': output_s3_uri + 'entities/'
                },
                DataAccessRoleArn=self.comprehend_data_access_role,
                JobName=f"entities-{doc_id}-{int(datetime.utcnow().timestamp())}",
                LanguageCode='en',
                NotificationConfig={
                    'JobCompletionNotificationTopicArn': self.entity_completion_topic_arn
                }
            )
            
            jobs['entity_job_id'] = entity_response['JobId']
            
            # Start key phrases detection job
            phrases_response = self.comprehend_client.start_key_phrases_detection_job(
                InputDataConfig={
                    'S3Uri': input_s3_uri,
                    'InputFormat': 'ONE_DOC_PER_FILE'
                },
                OutputDataConfig={
                    'S3Uri': output_s3_uri + 'key-phrases/'
                },
                DataAccessRoleArn=self.comprehend_data_access_role,
                JobName=f"phrases-{doc_id}-{int(datetime.utcnow().timestamp())}",
                LanguageCode='en',
                NotificationConfig={
                    'JobCompletionNotificationTopicArn': self.keyphrase_completion_topic_arn
                }
            )
            
            jobs['key_phrases_job_id'] = phrases_response['JobId']
            
            logger.info(f"Started Comprehend jobs: {jobs}")
            return jobs
            
        except Exception as e:
            logger.error(f"Error starting Comprehend jobs: {e}")
            raise
    
    def update_status(self, doc_id: str, stage: str, status: str, error_message: str = None, system_id: str = None, metadata: Dict = None):
        """Update document processing status with audit trail"""
        try:
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage=stage,
                status=status,
                error_message=error_message,
                system_id=system_id,
                metadata=metadata or {}
            )
            logger.info(f"Set document processing status: {doc_id} -> {stage} -> {status}")
        except Exception as e:
            logger.error(f"Failed to update status for {doc_id}: {e}")
            raise
