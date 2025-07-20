#!/usr/bin/env python3
"""
TextExtractor Processor Lambda Function - CLEAN VERSION
Processes completed Textract jobs and publishes standardized messages
Uses proper DatabaseManager pattern for database connections
"""

import json
import boto3
import logging
import os
import csv
import io
from datetime import datetime
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Import standardized messaging
from standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser

# Import DatabaseManager from shared layer
from utils.DatabaseManager import DatabaseManager

# Import DocumentIDManager from shared layer
from DocumentIDManager import DocumentIDManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorProcessor:
    """Processes completed Textract jobs with standardized messaging"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Initialize database manager and get connection string
        self.db_manager = DatabaseManager()
        database_url = self.db_manager.get_connection_string()
        
        # Environment configuration
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        
        # Initialize DocumentIDManager with database connection
        self.doc_id_manager = DocumentIDManager(database_url=database_url)
        
        # Standardized messaging - use SNS instead of SQS
        self.text_extraction_complete_topic_arn = os.environ.get(
            'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN',
            'arn:aws:sns:us-east-1:861276078413:text-extraction-complete'
        )
        
        # Initialize standardized message publisher
        self.message_publisher = StandardizedMessagePublisher()
        
        logger.info("TextExtractor Processor initialized")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"Text extraction complete topic: {self.text_extraction_complete_topic_arn}")
    
    def get_db_connection(self):
        """Get PostgreSQL database connection using DatabaseManager"""
        return self.db_manager.get_connection()
    
    def lambda_handler(self, event, context):
        """Main Lambda handler"""
        logger.info(f"Processing {len(event.get('Records', []))} records")
        
        results = {
            'processed': 0,
            'errors': 0,
            'skipped': 0
        }
        
        for record in event.get('Records', []):
            try:
                if record.get('eventSource') == 'aws:sqs':
                    # Process SQS message (Textract completion notification)
                    self.process_sqs_record(record)
                    results['processed'] += 1
                else:
                    logger.warning(f"Unsupported event source: {record.get('eventSource')}")
                    results['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing record: {str(e)}")
                logger.error(f"Record: {json.dumps(record, indent=2)}")
                results['errors'] += 1
        
        logger.info(f"Processing complete: {results['processed']} success, {results['errors']} errors, {results['skipped']} skipped")
        
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
    
    def process_sqs_record(self, record):
        """Process SQS record containing Textract completion notification"""
        try:
            # Parse the SQS message body
            message_body = json.loads(record['body'])
            
            # Handle both direct SQS messages and SNS-wrapped messages
            if message_body.get('Type') == 'Notification':
                # SNS notification wrapped in SQS
                sns_message = json.loads(message_body['Message'])
                logger.info(f"Processing SNS message: {sns_message}")
                self.process_textract_completion(sns_message)
            else:
                # Direct SQS message
                logger.info(f"Processing direct SQS message: {message_body}")
                self.process_textract_completion(message_body)
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {str(e)}")
            raise
    
    def process_textract_completion(self, completion_data):
        """Process Textract job completion"""
        job_id = completion_data.get('JobId')
        status = completion_data.get('Status')
        
        logger.info(f"Processing Textract completion: {job_id} -> {status}")
        
        if status != 'SUCCEEDED':
            logger.error(f"Textract job failed: {job_id} with status {status}")
            return
        
        try:
            # Get job metadata from database
            job_metadata = self.get_job_metadata(job_id)
            if not job_metadata:
                logger.error(f"Job metadata not found for job_id: {job_id}")
                raise Exception(f"Job metadata not found for job_id: {job_id}")
            
            # Extract text from Textract results
            extracted_text = self.extract_text_from_textract(job_id)
            
            # Store extracted text in S3
            text_s3_key = self.store_extracted_text(job_metadata, extracted_text)
            
            # Update job status in database
            self.update_job_status(job_id, 'COMPLETED', text_s3_key)
            
            # Publish completion message
            self.publish_text_extraction_complete(job_metadata, text_s3_key)
            
            logger.info(f"Successfully processed Textract job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing Textract completion: {str(e)}")
            # Update job status to failed
            try:
                self.update_job_status(job_id, 'FAILED', error_message=str(e))
            except Exception as update_error:
                logger.error(f"Error updating job status: {str(update_error)}")
            raise
    
    def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """Get job metadata from database"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT job_id, doc_id, s3_bucket, s3_key, created_at, status
                        FROM textract_jobs 
                        WHERE job_id = %s
                    """
                    cursor.execute(query, (job_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return dict(result)
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting job metadata: {str(e)}")
            raise
    
    def extract_text_from_textract(self, job_id: str) -> str:
        """Extract text from Textract job results"""
        try:
            # Get Textract results
            response = self.textract.get_document_analysis(JobId=job_id)
            
            # Extract text blocks
            text_blocks = []
            
            # Process all pages
            while True:
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        text_blocks.append(block.get('Text', ''))
                
                # Check for more pages
                next_token = response.get('NextToken')
                if not next_token:
                    break
                
                response = self.textract.get_document_analysis(
                    JobId=job_id,
                    NextToken=next_token
                )
            
            # Join all text blocks
            extracted_text = '\n'.join(text_blocks)
            
            logger.info(f"Extracted {len(extracted_text)} characters from job {job_id}")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error extracting text from Textract: {str(e)}")
            raise
    
    def store_extracted_text(self, job_metadata: Dict, extracted_text: str) -> str:
        """Store extracted text in S3"""
        try:
            doc_id = job_metadata['doc_id']
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Create S3 key for extracted text
            text_s3_key = f"extracted_text/{doc_id}/{timestamp}_full_text.txt"
            
            # Store in S3
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=text_s3_key,
                Body=extracted_text.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'doc_id': doc_id,
                    'extraction_timestamp': timestamp,
                    'textract_job_id': job_metadata['job_id'],
                    'character_count': str(len(extracted_text))
                }
            )
            
            logger.info(f"Stored extracted text: s3://{self.output_bucket}/{text_s3_key}")
            return text_s3_key
            
        except Exception as e:
            logger.error(f"Error storing extracted text: {str(e)}")
            raise
    
    def update_job_status(self, job_id: str, status: str, text_s3_key: str = None, error_message: str = None):
        """Update job status in database"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cursor:
                    if status == 'COMPLETED':
                        query = """
                            UPDATE textract_jobs 
                            SET status = %s, completed_at = %s, text_s3_key = %s
                            WHERE job_id = %s
                        """
                        cursor.execute(query, (status, datetime.utcnow(), text_s3_key, job_id))
                    else:
                        query = """
                            UPDATE textract_jobs 
                            SET status = %s, completed_at = %s, error_message = %s
                            WHERE job_id = %s
                        """
                        cursor.execute(query, (status, datetime.utcnow(), error_message, job_id))
                    
                    conn.commit()
                    logger.info(f"Updated job status: {job_id} -> {status}")
                    
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            raise
    
    def publish_text_extraction_complete(self, job_metadata: Dict, text_s3_key: str):
        """Publish text extraction completion message"""
        try:
            message_data = {
                'event_type': 'text_extraction_complete',
                'doc_id': job_metadata['doc_id'],
                'textract_job_id': job_metadata['job_id'],
                'text_s3_bucket': self.output_bucket,
                'text_s3_key': text_s3_key,
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'source_s3_bucket': job_metadata['s3_bucket'],
                'source_s3_key': job_metadata['s3_key']
            }
            
            # Publish using standardized messaging
            self.message_publisher.publish_message(
                topic_arn=self.text_extraction_complete_topic_arn,
                message_data=message_data,
                message_type='text_extraction_complete'
            )
            
            logger.info(f"Published text extraction completion: {job_metadata['doc_id']}")
            
        except Exception as e:
            logger.error(f"Error publishing completion message: {str(e)}")
            raise


# Lambda handler function
def lambda_handler(event, context):
    """Lambda entry point"""
    try:
        processor = TextExtractorProcessor()
        return processor.lambda_handler(event, context)
    except Exception as e:
        logger.error(f"TextExtractor Processor error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
