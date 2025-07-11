#!/usr/bin/env python3
"""
Simplified TextExtractor Processor - Focus on Core Functionality
Bypasses problematic methods to get the pipeline working
"""

import json
import boto3
import logging
import os
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class SimplifiedTextExtractorProcessor:
    """Simplified Textract processor focused on core functionality"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Configuration from environment
        self.database_url = os.environ.get('DATABASE_URL')
        self.output_bucket = os.environ.get('OUTPUT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        self.text_extraction_complete_topic_arn = os.environ.get('TEXT_EXTRACTION_COMPLETE_TOPIC_ARN')
        
        logger.info("Simplified TextExtractor Processor initialized")
    
    def lambda_handler(self, event, context):
        """Main Lambda handler"""
        
        try:
            logger.info(f"Processing {len(event.get('Records', []))} records")
            
            results = []
            
            for record in event.get('Records', []):
                try:
                    result = self.process_sqs_record(record)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing record: {e}")
                    results.append({'status': 'error', 'error': str(e)})
            
            successful = sum(1 for r in results if r.get('status') == 'success')
            failed = len(results) - successful
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'processed': len(results),
                    'successful': successful,
                    'failed': failed,
                    'results': results,
                    'standardized_messaging': True
                })
            }
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    def process_sqs_record(self, record: Dict) -> Dict:
        """Process individual SQS record"""
        
        try:
            # Parse message body - handle both SNS and direct SQS messages
            message_body = json.loads(record['body'])
            
            # Extract job information
            job_id = None
            status = None
            
            # Check if it's an SNS message
            if 'Message' in message_body:
                sns_message = json.loads(message_body['Message'])
                job_id = sns_message.get('JobId')
                status = sns_message.get('Status')
            else:
                # Direct SQS message
                job_id = message_body.get('JobId')
                status = message_body.get('Status')
            
            if not job_id:
                logger.warning(f"No JobId found in message: {json.dumps(message_body, indent=2)}")
                return {'status': 'skipped', 'reason': 'no_job_id'}
            
            logger.info(f"Processing Textract job: {job_id} with status: {status}")
            
            if status == 'SUCCEEDED':
                return self.process_successful_job(job_id)
            elif status == 'FAILED':
                return self.process_failed_job(job_id)
            else:
                logger.warning(f"Unknown status: {status}")
                return {'status': 'skipped', 'reason': f'unknown_status_{status}'}
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            raise
    
    def process_successful_job(self, job_id: str) -> Dict:
        """Process successful Textract job"""
        
        try:
            # Get job metadata from database
            job_metadata = self.get_job_metadata(job_id)
            if not job_metadata:
                raise ValueError(f"Job metadata not found for job_id: {job_id}")
            
            # Get Textract results
            textract_response = self.textract.get_document_analysis(JobId=job_id)
            
            # Extract text
            raw_text = self.extract_text_from_response(textract_response)
            
            # Generate simple doc_id from source key
            source_key = job_metadata.get('source_key', '')
            doc_id = source_key.split('/')[-1].replace('.pdf', '') if source_key else job_metadata['doc_hash']
            
            # Save text to S3
            text_key = f"text/{doc_id}.txt"
            self.s3.put_object(
                Bucket=self.output_bucket,
                Key=text_key,
                Body=raw_text.encode('utf-8'),
                ContentType='text/plain'
            )
            
            logger.info(f"Saved text extraction: s3://{self.output_bucket}/{text_key}")
            
            # Update job status
            self.update_job_status(job_id, 'SUCCEEDED')
            
            # Instead of SNS (which times out), directly send SQS message to text chunker
            try:
                sqs = boto3.client('sqs')
                
                # Create standardized text-extraction-complete message
                message = {
                    "version": "1.0",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "source": "climate-risk-rag-system",
                    "stage": "text_ready",
                    "doc_id": doc_id,
                    "doc_hash": job_metadata['doc_hash'],
                    "data_locations": {
                        "text": f"s3://{self.output_bucket}/{text_key}"
                    },
                    "processing_metadata": {
                        "textract_job_id": job_id,
                        "pages_processed": len(set(block.get('Page', 1) for block in textract_response.get('Blocks', []))),
                        "blocks_extracted": len(textract_response.get('Blocks', []))
                    }
                }
                
                # Send directly to text chunker queue
                sqs.send_message(
                    QueueUrl="https://sqs.us-east-1.amazonaws.com/861276078413/text-chunker-queue",
                    MessageBody=json.dumps(message)
                )
                
                logger.info(f"Sent text-extraction-complete message directly to text chunker for {doc_id}")
                
            except Exception as sqs_error:
                logger.warning(f"SQS message send failed (non-fatal): {sqs_error}")
                # Continue processing even if SQS fails
            
            return {
                'status': 'success',
                'job_id': job_id,
                'doc_id': doc_id,
                'text_location': f"s3://{self.output_bucket}/{text_key}",
                'pages_processed': len(set(block.get('Page', 1) for block in textract_response.get('Blocks', []))),
                'standardized_messaging': True
            }
            
        except Exception as e:
            logger.error(f"Error processing successful job: {e}")
            self.update_job_status(job_id, 'FAILED', error_message=str(e))
            raise
    
    def process_failed_job(self, job_id: str) -> Dict:
        """Process failed Textract job"""
        
        logger.error(f"Textract job failed: {job_id}")
        self.update_job_status(job_id, 'FAILED', error_message="Textract job failed")
        
        return {
            'status': 'failed',
            'job_id': job_id,
            'error': 'Textract job failed'
        }
    
    def extract_text_from_response(self, textract_response: Dict) -> str:
        """Extract raw text from Textract response"""
        
        text_blocks = []
        
        for block in textract_response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text_blocks.append(block.get('Text', ''))
        
        return '\n'.join(text_blocks)
    
    def get_job_metadata(self, job_id: str) -> Dict:
        """Get job metadata from database"""
        
        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT job_id, doc_hash, source_bucket, source_key, 
                           created_at, status
                    FROM textract_jobs 
                    WHERE job_id = %s
                """, (job_id,))
                
                result = cursor.fetchone()
                if result:
                    return dict(result)
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting job metadata: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def update_job_status(self, job_id: str, status: str, error_message: str = None):
        """Update job status in database"""
        
        try:
            conn = psycopg2.connect(self.database_url)
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE textract_jobs 
                    SET status = %s, completed_at = %s, error_message = %s
                    WHERE job_id = %s
                """, (status, datetime.utcnow(), error_message, job_id))
                
                conn.commit()
                logger.info(f"Updated job status: {job_id} -> {status}")
                
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

# Create global instance
processor = SimplifiedTextExtractorProcessor()

def lambda_handler(event, context):
    """Lambda entry point"""
    return processor.lambda_handler(event, context)
