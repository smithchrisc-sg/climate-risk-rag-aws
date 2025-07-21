"""
TextExtractor Initiator Lambda Function - Gold Standard
Starts async Textract jobs and tracks state in PostgreSQL
Uses gold standard DatabaseManager pattern
"""

import json
import boto3
import logging
import os
import hashlib
from datetime import datetime
from urllib.parse import unquote_plus
from typing import Dict, List, Any

# Import from gold standard layer
from utils.DatabaseManager import DatabaseManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class TextExtractorInitiator:
    """Initiates async Textract jobs with state tracking using gold standard patterns"""
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.s3 = boto3.client('s3')
        
        # Environment configuration
        self.textract_sns_topic = os.environ['TEXTRACT_SNS_TOPIC_ARN']
        self.textract_service_role = os.environ['TEXTRACT_SERVICE_ROLE_ARN']
        self.output_bucket = os.environ['OUTPUT_BUCKET']
        
        # Initialize DatabaseManager using gold standard pattern
        self.db_manager = DatabaseManager()
        
        logger.info("✅ TextExtractor Initiator initialized with gold standard patterns")
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
            
            # Start document analysis job
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
            logger.info(f"✅ Textract job started successfully: {job_id}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start Textract job: {str(e)}")
            raise
    
    def update_processing_status(self, doc_id: str, job_id: str, filename: str, bucket: str, key: str, status: str = 'textract_started'):
        """Update document processing status in database using gold standard pattern"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Update or insert processing status using correct column names and required fields
                    cursor.execute("""
                        INSERT INTO document_processing_status 
                        (doc_id, filename, source_bucket, source_key, textract_job_id, text_extraction_status, 
                         chunking_status, embedding_status, ner_status, vector_embeddings_status, 
                         created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (doc_id) 
                        DO UPDATE SET 
                            textract_job_id = EXCLUDED.textract_job_id,
                            text_extraction_status = EXCLUDED.text_extraction_status,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        doc_id, 
                        filename,
                        bucket,
                        key,
                        job_id, 
                        status,
                        'PENDING',  # chunking_status
                        'PENDING',  # embedding_status  
                        'PENDING',  # ner_status
                        'PENDING',  # vector_embeddings_status
                        datetime.now(),  # created_at
                        datetime.now()   # updated_at
                    ))
                    
                    conn.commit()
                    logger.info(f"✅ Updated processing status for {doc_id}: {status}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to update processing status: {str(e)}")
            raise
    
    def process_s3_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process S3 event and initiate Textract jobs"""
        results = []
        
        try:
            # Parse S3 event
            if 'Records' not in event:
                raise ValueError("Invalid S3 event format")
            
            for record in event['Records']:
                # Extract S3 information
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                
                logger.info(f"Processing S3 object: s3://{bucket}/{key}")
                
                # Skip non-PDF files
                if not key.lower().endswith('.pdf'):
                    logger.info(f"Skipping non-PDF file: {key}")
                    continue
                
                # Extract document ID
                doc_id = self.extract_doc_id_from_key(key)
                
                # Start Textract job
                job_id = self.start_textract_job(bucket, key, doc_id)
                
                # Update processing status with all required fields
                filename = key.split('/')[-1]  # Extract filename from key
                self.update_processing_status(doc_id, job_id, filename, bucket, key)
                
                results.append({
                    'doc_id': doc_id,
                    'job_id': job_id,
                    'bucket': bucket,
                    'key': key,
                    'status': 'textract_started'
                })
            
            return {
                'success': True,
                'processed_documents': len(results),
                'results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing S3 event: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_documents': len(results),
                'results': results
            }

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for text extraction initiation
    
    Args:
        event: S3 event containing document upload information
        context: Lambda context object
        
    Returns:
        Dict containing processing status and results
    """
    try:
        logger.info(f"🚀 Text extraction initiator invoked with event: {json.dumps(event, default=str)}")
        
        # Initialize initiator
        initiator = TextExtractorInitiator()
        
        # Process the event
        result = initiator.process_s3_event(event)
        
        if result['success']:
            logger.info(f"✅ Text extraction initiation completed successfully")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': f"Successfully initiated Textract jobs for {result['processed_documents']} documents",
                    'result': result
                })
            }
        else:
            logger.error(f"❌ Text extraction initiation failed: {result.get('error')}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': result.get('error'),
                    'result': result
                })
            }
        
    except Exception as e:
        logger.error(f"❌ Error in text extraction initiator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
