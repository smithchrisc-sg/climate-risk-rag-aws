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
    """Initiates async Textract jobs with audit-first status tracking"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Environment configuration
        self.textract_sns_topic = os.environ['TEXTRACT_SNS_TOPIC_ARN']
        self.textract_service_role = os.environ['TEXTRACT_SERVICE_ROLE_ARN']
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        logger.info("✅ Text Extractor Initiator initialized")
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
            # Update status to in_progress before starting job
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_initiate',
                status='in_progress'
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
            
            # Update status to completed with job_id
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_initiate',
                status='completed',
                system_id=job_id
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
            
            # Start Textract job (includes status tracking)
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
