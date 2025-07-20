"""
TextExtractor Initiator Lambda Function
Starts async Textract jobs and tracks state in PostgreSQL
"""

import json
import boto3
import logging
import os
import hashlib
from datetime import datetime
from urllib.parse import unquote_plus
from typing import Dict, List, Any
from utils.DatabaseManager import DatabaseManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorInitiator:
    """Initiates async Textract jobs with state tracking"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Environment configuration
        self.textract_sns_topic = os.environ['TEXTRACT_SNS_TOPIC_ARN']
        self.textract_service_role = os.environ['TEXTRACT_SERVICE_ROLE_ARN']
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        
        # Initialize DatabaseManager
        self.db_manager = DatabaseManager()
        
        logger.info("TextExtractor Initiator initialized")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"SNS Topic: {self.textract_sns_topic}")
    
    def extract_doc_id_from_key(self, key: str) -> str:
        """Extract document ID from S3 key"""
        # Remove path prefix and file extension
        filename = key.split('/')[-1]
        doc_id = filename.replace('.pdf', '')
        
        logger.info(f"Extracted doc_id: {doc_id} from key: {key}")
        return doc_id
    
    def start_textract_job(self, bucket: str, key: str, doc_id: str) -> str:
        """Start async Textract document analysis job"""
        try:
            logger.info(f"Starting Textract job for s3://{bucket}/{key}")
            
            response = self.textract.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS'],
                NotificationChannel={
                    'SNSTopicArn': self.textract_sns_topic,
                    'RoleArn': self.textract_service_role
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id}")
            
            # Store job metadata in database using DatabaseManager
            self.store_job_metadata(job_id, doc_id, bucket, key)
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to start Textract job: {str(e)}")
            raise
    
    def store_job_metadata(self, job_id: str, doc_id: str, source_bucket: str, source_key: str):
        """Store Textract job metadata in database using DatabaseManager"""
        try:
            filename = source_key.split('/')[-1]  # Extract filename from key
            
            # Store job metadata
            self.db_manager.store_textract_job_metadata(
                job_id, doc_id, source_bucket, source_key, self.output_bucket
            )
            
            # Update document processing status
            self.db_manager.update_document_processing_status(
                doc_id, filename, source_bucket, source_key, 'IN_PROGRESS', job_id
            )
            
            logger.info(f"Stored job metadata: {job_id} -> {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to store job metadata: {str(e)}")
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
            
            # Check if already processed
            if self.is_already_processed(doc_id):
                logger.info(f"Document already processed: {doc_id}")
                return {
                    'status': 'skipped',
                    'reason': 'already_processed',
                    'doc_id': doc_id,
                    'file': key
                }
            
            # Start Textract job
            job_id = self.start_textract_job(bucket, key, doc_id)
            
            return {
                'status': 'success',
                'job_id': job_id,
                'doc_id': doc_id,
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

    def is_already_processed(self, doc_id: str) -> bool:
        """Check if document is already processed or in progress using DatabaseManager"""
        try:
            status = self.db_manager.get_text_extraction_status(doc_id)
            
            if status:
                return status in ['IN_PROGRESS', 'COMPLETED']
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking processing status: {str(e)}")
            return False  # Assume not processed on error

def lambda_handler(event, context):
    """Lambda handler for TextExtractor Initiator"""
    try:
        logger.info(f"TextExtractor Initiator triggered with event: {json.dumps(event)}")
        
        initiator = TextExtractorInitiator()
        results = []
        
        # Process SQS messages containing SNS notifications with S3 events
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:sqs':
                    # Parse SQS message body (contains SNS notification)
                    result = initiator.process_sqs_record(record)
                    results.append(result)
                else:
                    logger.warning(f"Unsupported event source: {record.get('eventSource')}")
        
        else:
            logger.error("No SQS records found in event")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid event format - expected SQS records',
                    'event_keys': list(event.keys())
                })
            }
        
        # Summary statistics
        success_count = len([r for r in results if r['status'] == 'success'])
        error_count = len([r for r in results if r['status'] == 'error'])
        skipped_count = len([r for r in results if r['status'] == 'skipped'])
        
        logger.info(f"Processing complete: {success_count} success, {error_count} errors, {skipped_count} skipped")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'success': success_count,
                'errors': error_count,
                'skipped': skipped_count,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"TextExtractor Initiator error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
