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
import psycopg2
from psycopg2.extras import RealDictCursor

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
        self.database_url = os.environ['DATABASE_URL']
        
        logger.info(f"TextExtractor Initiator initialized")
        logger.info(f"Output bucket: {self.output_bucket}")
        logger.info(f"SNS Topic: {self.textract_sns_topic}")

    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        try:
            conn = psycopg2.connect(self.database_url)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def generate_doc_hash(self, bucket: str, key: str) -> str:
        """Generate unique document hash from S3 object"""
        try:
            # Get object metadata for ETag (content hash)
            response = self.s3.head_object(Bucket=bucket, Key=key)
            etag = response['ETag'].strip('"')
            
            # Combine bucket, key, and etag for unique hash
            content = f"{bucket}/{key}/{etag}"
            doc_hash = hashlib.sha256(content.encode()).hexdigest()
            
            logger.info(f"Generated doc_hash: {doc_hash} for s3://{bucket}/{key}")
            return doc_hash
            
        except Exception as e:
            logger.error(f"Error generating doc hash: {str(e)}")
            # Fallback to key-based hash
            content = f"{bucket}/{key}"
            return hashlib.sha256(content.encode()).hexdigest()

    def start_textract_job(self, bucket: str, key: str, doc_hash: str) -> str:
        """Start async Textract job with rich feature analysis"""
        try:
            logger.info(f"Starting Textract job for s3://{bucket}/{key}")
            
            # Use AnalyzeDocument for rich structure analysis
            response = self.textract.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS', 'LAYOUT'],  # Rich analysis
                NotificationChannel={
                    'SNSTopicArn': self.textract_sns_topic,
                    'RoleArn': self.textract_service_role
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error starting Textract job: {str(e)}")
            raise

    def store_job_metadata(self, job_id: str, doc_hash: str, bucket: str, key: str):
        """Store job metadata in PostgreSQL"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Insert job record
            insert_query = """
                INSERT INTO textract_jobs (
                    job_id, doc_hash, source_bucket, source_key, output_bucket,
                    status, feature_types, started_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            
            cursor.execute(insert_query, (
                job_id,
                doc_hash,
                bucket,
                key,
                self.output_bucket,
                'IN_PROGRESS',
                json.dumps(['TABLES', 'FORMS', 'LAYOUT']),
                datetime.utcnow()
            ))
            
            # Update document processing status
            upsert_doc_status = """
                INSERT INTO document_processing_status (
                    doc_hash, filename, source_bucket, source_key,
                    text_extraction_status, text_extraction_job_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (doc_hash) DO UPDATE SET
                    text_extraction_status = EXCLUDED.text_extraction_status,
                    text_extraction_job_id = EXCLUDED.text_extraction_job_id,
                    updated_at = NOW()
            """
            
            filename = os.path.basename(key)
            cursor.execute(upsert_doc_status, (
                doc_hash,
                filename,
                bucket,
                key,
                'IN_PROGRESS',
                job_id
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Stored job metadata for {job_id}")
            
        except Exception as e:
            logger.error(f"Error storing job metadata: {str(e)}")
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
            
            # Generate document hash
            doc_hash = self.generate_doc_hash(bucket, key)
            
            # Check if already processed
            if self.is_already_processed(doc_hash):
                logger.info(f"Document already processed: {doc_hash}")
                return {
                    'status': 'skipped',
                    'reason': 'already_processed',
                    'doc_hash': doc_hash,
                    'file': key
                }
            
            # Start Textract job
            job_id = self.start_textract_job(bucket, key, doc_hash)
            
            # Store job metadata
            self.store_job_metadata(job_id, doc_hash, bucket, key)
            
            return {
                'status': 'success',
                'job_id': job_id,
                'doc_hash': doc_hash,
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

    def is_already_processed(self, doc_hash: str) -> bool:
        """Check if document is already processed or in progress"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT text_extraction_status 
                FROM document_processing_status 
                WHERE doc_hash = %s
            """
            
            cursor.execute(query, (doc_hash,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                status = result[0]
                return status in ['IN_PROGRESS', 'COMPLETED']
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking processing status: {str(e)}")
            return False  # Assume not processed on error

def lambda_handler(event, context):
    """Lambda function handler for TextExtractor Initiator"""
    try:
        logger.info(f"TextExtractor Initiator triggered with event: {json.dumps(event, default=str)}")
        
        initiator = TextExtractorInitiator()
        results = []
        
        # Process S3 events
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:s3':
                    result = initiator.process_s3_event(record)
                    results.append(result)
                else:
                    logger.warning(f"Unsupported event source: {record.get('eventSource')}")
        
        # Handle direct invocation for testing
        elif 'bucket' in event and 'key' in event:
            # Create mock S3 record for direct testing
            mock_record = {
                's3': {
                    'bucket': {'name': event['bucket']},
                    'object': {'key': event['key']}
                }
            }
            result = initiator.process_s3_event(mock_record)
            results.append(result)
        
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid event format. Expected S3 event or direct invocation.'
                })
            }
        
        # Summary statistics
        success_count = len([r for r in results if r['status'] == 'success'])
        error_count = len([r for r in results if r['status'] == 'error'])
        skipped_count = len([r for r in results if r['status'] == 'skipped'])
        
        response_body = {
            'message': f'Processed {len(results)} documents',
            'summary': {
                'success': success_count,
                'errors': error_count,
                'skipped': skipped_count
            },
            'results': results
        }
        
        logger.info(f"Processing complete: {success_count} success, {error_count} errors, {skipped_count} skipped")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, default=str)
        }
        
    except Exception as e:
        logger.error(f"TextExtractor Initiator error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'TextExtractor Initiator failed: {str(e)}'
            })
        }
