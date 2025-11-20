"""
Text Extractor Initiator Lambda Function
Starts async Textract jobs and tracks state using audit-first database design
"""

import json
import boto3
import logging
import os
from datetime import datetime
from urllib.parse import unquote_plus
from typing import Dict, List, Any

# Import from locked database core layer - DO NOT CHANGE
from utils.DatabaseManager import DatabaseManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorInitiator:
    """Initiates async Textract jobs with audit-first status tracking and deduplication"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment configuration
        self.textract_sns_topic = os.environ['TEXTRACT_SNS_TOPIC_ARN']
        self.textract_service_role = os.environ['TEXTRACT_SERVICE_ROLE_ARN']
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        self.text_extraction_complete_topic = os.environ.get('TEXT_EXTRACTION_COMPLETE_TOPIC_ARN')
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        logger.info("✅ Text Extractor Initiator initialized with deduplication")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"SNS Topic: {self.textract_sns_topic}")
    
    def calculate_document_hash(self, bucket: str, key: str) -> str:
        """
        Calculate document hash using ETag for single-part uploads
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Hash string in format "md5:hash" or "sha256:hash"
        """
        try:
            # Get object metadata
            response = self.s3.head_object(Bucket=bucket, Key=key)
            etag = response['ETag'].strip('"')
            file_size = response['ContentLength']
            
            # Check if multipart upload (has hyphen in ETag)
            if '-' in etag:
                logger.warning(f"Multipart upload detected for {key}, calculating full hash")
                # Download and hash full content
                obj = self.s3.get_object(Bucket=bucket, Key=key)
                content = obj['Body'].read()
                
                import hashlib
                hash_value = hashlib.sha256(content).hexdigest()
                return f"sha256:{hash_value}"
            else:
                # Single-part upload - ETag is MD5
                return f"md5:{etag}"
                
        except Exception as e:
            logger.error(f"Failed to calculate document hash: {e}")
            raise
    
    def check_force_reprocess(self, bucket: str, key: str) -> bool:
        """
        Check if document has force reprocess flag set via S3 tags
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            True if force reprocess flag is set
        """
        try:
            tags = self.s3.get_object_tagging(Bucket=bucket, Key=key)
            force_reprocess = any(
                tag['Key'] == 'ForceReprocess' and tag['Value'].lower() == 'true'
                for tag in tags.get('TagSet', [])
            )
            
            if force_reprocess:
                logger.info(f"Force reprocess flag detected for {key}")
            
            return force_reprocess
            
        except Exception as e:
            # If tagging fails, assume no force reprocess
            logger.debug(f"Could not check tags for {key}: {e}")
            return False
    
    def publish_text_extraction_complete(self, doc_id: str, text_location: str, 
                                        structure_location: str, skipped: bool = False):
        """
        Publish text extraction complete message to trigger next pipeline stage
        
        Args:
            doc_id: Document ID
            text_location: S3 location of extracted text
            structure_location: S3 location of Textract structure
            skipped: Whether processing was skipped due to deduplication
        """
        try:
            if not self.text_extraction_complete_topic:
                logger.warning("TEXT_EXTRACTION_COMPLETE_TOPIC_ARN not configured")
                return
            
            message = {
                'version': '1.0',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'source': 'climate-risk-rag-system',
                'stage': 'text_ready',
                'doc_id': doc_id,
                'data_locations': {
                    'text_location': text_location,
                    'structure_location': structure_location
                },
                'processing_metadata': {
                    'skipped_duplicate': skipped
                }
            }
            
            response = self.sns.publish(
                TopicArn=self.text_extraction_complete_topic,
                Message=json.dumps(message),
                Subject=f'Text extraction {"skipped" if skipped else "complete"}: {doc_id}',
                MessageAttributes={
                    'stage': {'DataType': 'String', 'StringValue': 'text_ready'},
                    'doc_id': {'DataType': 'String', 'StringValue': doc_id}
                }
            )
            
            logger.info(f"Published text extraction complete message for {doc_id} (skipped={skipped})")
            
        except Exception as e:
            logger.error(f"Failed to publish completion message: {e}")
            # Don't raise - this is not critical
    
    def extract_doc_id_from_key(self, key: str) -> str:
        """Extract document ID from S3 key"""
        # Remove path prefix and file extension
        filename = key.split('/')[-1]
        doc_id = filename.replace('.pdf', '')
        
        logger.info(f"Extracted doc_id: {doc_id} from key: {key}")
        return doc_id
    
    def process_document(self, bucket: str, key: str, doc_id: str) -> Dict[str, Any]:
        """
        Process document with deduplication check before starting Textract
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            doc_id: Document ID
            
        Returns:
            Dict with status and details
        """
        try:
            # Check for force reprocess flag
            force_reprocess = self.check_force_reprocess(bucket, key)
            
            if not force_reprocess:
                # Calculate document hash
                doc_hash = self.calculate_document_hash(bucket, key)
                logger.info(f"Document hash for {doc_id}: {doc_hash}")
                
                # Check if already processed
                previous = self.db_manager.get_latest_stage_status(
                    doc_id=doc_id,
                    stage='textract_complete',
                    status='completed'
                )
                
                logger.info(f"Previous processing check: previous={previous is not None}")
                if previous:
                    has_metadata = previous.get('metadata') is not None
                    logger.info(f"Has metadata: {has_metadata}")
                    if has_metadata:
                        logger.info(f"Metadata keys: {list(previous['metadata'].keys())}")
                
                if previous and previous.get('metadata'):
                    stored_hash = previous['metadata'].get('document_hash')
                    logger.info(f"Comparing hashes - stored: {stored_hash}, current: {doc_hash}")
                    
                    if stored_hash == doc_hash:
                        # DUPLICATE - Skip Textract
                        logger.info(f"Duplicate document detected: {doc_id}, skipping Textract")
                        
                        # Record skip in database
                        self.db_manager.set_processing_status(
                            doc_id=doc_id,
                            stage='textract_initiate',
                            status='skipped',
                            metadata={
                                'skip_reason': 'duplicate_hash',
                                'document_hash': doc_hash,
                                'previous_processing': previous['timestamp'].isoformat()
                            }
                        )
                        
                        # Construct S3 paths deterministically
                        text_location = f"s3://{self.output_bucket}/data-lake/{doc_id}/raw_text.txt"
                        structure_location = f"s3://{self.output_bucket}/data-lake/{doc_id}/textract_response.json"
                        
                        # Publish completion message to trigger next stage
                        self.publish_text_extraction_complete(
                            doc_id=doc_id,
                            text_location=text_location,
                            structure_location=structure_location,
                            skipped=True
                        )
                        
                        return {
                            'status': 'skipped',
                            'reason': 'duplicate_hash',
                            'doc_id': doc_id,
                            'hash': doc_hash
                        }
                    else:
                        logger.info(f"Document hash changed for {doc_id}, reprocessing")
                        logger.info(f"  Old: {stored_hash}")
                        logger.info(f"  New: {doc_hash}")
            else:
                logger.info(f"Force reprocess flag set for {doc_id}, skipping deduplication")
                doc_hash = self.calculate_document_hash(bucket, key)
            
            # Start Textract job (new, changed, or forced)
            job_id = self.start_textract_job(bucket, key, doc_id, doc_hash)
            
            return {
                'status': 'started',
                'job_id': job_id,
                'doc_id': doc_id,
                'hash': doc_hash
            }
            
        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {e}")
            raise
    
    def start_textract_job(self, bucket: str, key: str, doc_id: str, doc_hash: str) -> str:
        """Start async Textract document analysis job"""
        try:
            # Update status to in_progress before starting job
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_initiate',
                status='in_progress',
                metadata={'document_hash': doc_hash}
            )
            
            # Start Textract job
            response = self.textract.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS', 'LAYOUT'],
                NotificationChannel={
                    'SNSTopicArn': self.textract_sns_topic,
                    'RoleArn': self.textract_service_role
                },
                OutputConfig={
                    'S3Bucket': self.output_bucket,
                    'S3Prefix': f'textract-output/{doc_id}/'
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id} for document: {doc_id}")
            
            # Update status to completed with job_id and hash
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_initiate',
                status='completed',
                system_id=job_id,
                metadata={'document_hash': doc_hash}
            )
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to start Textract job for {doc_id}: {str(e)}")
            
            # Update status to failed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_initiate',
                status='failed',
                error_message=str(e)
            )
            
            raise

    def process_s3_event(self, record: Dict) -> Dict[str, Any]:
        """Process a single S3 event record"""
        try:
            # Parse S3 event
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processing S3 event: s3://{bucket}/{key}")
            
            # Skip non-PDF files
            if not key.lower().endswith('.pdf'):
                logger.info(f"Skipping non-PDF file: {key}")
                return {
                    'status': 'skipped',
                    'reason': 'not_pdf',
                    'file': key
                }
            
            # Extract document ID from filename
            doc_id = self.extract_doc_id_from_key(key)
            
            # Process document with deduplication check
            result = self.process_document(bucket, key, doc_id)
            
            return {
                **result,
                'file': key,
                'bucket': bucket
            }
            
        except Exception as e:
            logger.error(f"Error processing S3 event: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'file': record.get('s3', {}).get('object', {}).get('key', 'unknown')
            }

    def process_sqs_record(self, sqs_record):
        """Process SQS record containing SNS notification with S3 event"""
        try:
            # Parse SQS message body (JSON string)
            message_body = json.loads(sqs_record['body'])
            
            # Verify it's an SNS notification
            if message_body.get('Type') != 'Notification':
                logger.error(f"Expected SNS notification, got: {message_body.get('Type')}")
                return {'status': 'error', 'message': 'Invalid message type'}
            
            # Parse the SNS Message field (contains S3 event JSON)
            sns_message = json.loads(message_body['Message'])
            
            # Process S3 records from the SNS message
            results = []
            for s3_record in sns_message.get('Records', []):
                if s3_record.get('eventSource') == 'aws:s3':
                    result = self.process_s3_event(s3_record)
                    results.append(result)
            
            return {
                'status': 'success',
                'processed_records': len(results),
                'results': results
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SQS message: {e}")
            return {'status': 'error', 'message': f'JSON parse error: {e}'}
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            return {'status': 'error', 'message': str(e)}

def lambda_handler(event, context):
    """Lambda handler for Text Extractor Initiator"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        initiator = TextExtractorInitiator()
        results = []
        
        # Handle SQS events (SNS notifications with S3 events)
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:sqs':
                    result = initiator.process_sqs_record(record)
                    results.append(result)
                elif record.get('eventSource') == 'aws:s3':
                    # Direct S3 event
                    result = initiator.process_s3_event(record)
                    results.append(result)
        
        # Return results
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Text extraction jobs initiated',
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
