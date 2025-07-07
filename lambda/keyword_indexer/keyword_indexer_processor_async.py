#!/usr/bin/env python3
"""
Asynchronous Keyword Indexer Processor
Optimized for cost efficiency - kicks off indexing and exits quickly
Uses SNS callbacks for completion tracking
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncKeywordIndexerProcessor:
    """
    Asynchronous keyword indexer - optimized for cost efficiency
    """
    
    def __init__(self):
        # AWS clients
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment variables
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.index_name = os.environ.get('INDEX_NAME', 'climate-risk-keyword-index')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-text-new-861276078413-us-east-1')
        self.completion_topic_arn = os.environ.get('INDEXING_COMPLETION_TOPIC_ARN')
        
        # Database manager
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
        except ImportError as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
            self.db_manager = None

    def lambda_handler(self, event, context):
        """Async Lambda handler - process quickly and exit"""
        
        logger.info(f"Processing {len(event['Records'])} records asynchronously")
        
        results = []
        for record in event['Records']:
            try:
                result = self.process_sqs_record_async(record)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing record: {e}")
                results.append({'success': False, 'error': str(e)})
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'initiated': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'processing_mode': 'async'
            })
        }

    def process_sqs_record_async(self, record: Dict) -> Dict:
        """Process SQS record asynchronously - quick initiation only"""
        
        try:
            # Parse message
            message_body = json.loads(record['body'])
            if 'Message' in message_body:
                sns_message = json.loads(message_body['Message'])
            else:
                sns_message = message_body
            
            if sns_message.get('stage') == 'text_ready':
                return self.initiate_async_indexing(sns_message)
            else:
                return {'success': False, 'error': 'Unexpected message stage'}
                
        except Exception as e:
            logger.error(f"Error processing SQS record: {e}")
            raise

    def initiate_async_indexing(self, message: Dict) -> Dict:
        """Initiate async indexing - prepare data and queue for background processing"""
        
        doc_id = message.get('doc_id')
        full_text_location = message.get('full_text_location')
        filename = message.get('filename', 'unknown')
        
        if not doc_id or not full_text_location:
            raise ValueError("Missing required message components")
        
        try:
            logger.info(f"Initiating async keyword indexing for {doc_id}")
            
            # Update status to PROCESSING quickly
            if self.db_manager:
                self.update_processing_status(doc_id, 'PROCESSING', 'Async indexing initiated')
            
            # Prepare indexing job data
            indexing_job = {
                'doc_id': doc_id,
                'full_text_location': full_text_location,
                'filename': filename,
                'opensearch_endpoint': self.opensearch_endpoint,
                'index_name': self.index_name,
                'initiated_at': datetime.utcnow().isoformat(),
                'completion_topic_arn': self.completion_topic_arn
            }
            
            # Option 1: Use Step Functions for async processing
            if os.environ.get('STEP_FUNCTION_ARN'):
                return self.trigger_step_function(indexing_job)
            
            # Option 2: Use SQS delay queue for async processing
            elif os.environ.get('ASYNC_PROCESSING_QUEUE_URL'):
                return self.queue_async_processing(indexing_job)
            
            # Option 3: Use Lambda async invocation
            else:
                return self.invoke_async_lambda(indexing_job)
                
        except Exception as e:
            logger.error(f"Failed to initiate async indexing for {doc_id}: {e}")
            if self.db_manager:
                self.update_processing_status(doc_id, 'FAILED', str(e))
            raise

    def trigger_step_function(self, job_data: Dict) -> Dict:
        """Trigger Step Function for async processing (most robust)"""
        
        try:
            stepfunctions = boto3.client('stepfunctions')
            
            response = stepfunctions.start_execution(
                stateMachineArn=os.environ['STEP_FUNCTION_ARN'],
                name=f"keyword-indexing-{job_data['doc_id']}-{int(datetime.utcnow().timestamp())}",
                input=json.dumps(job_data)
            )
            
            logger.info(f"Started Step Function execution: {response['executionArn']}")
            
            return {
                'success': True,
                'doc_id': job_data['doc_id'],
                'execution_arn': response['executionArn'],
                'processing_mode': 'step_function_async'
            }
            
        except Exception as e:
            logger.error(f"Step Function trigger failed: {e}")
            raise

    def queue_async_processing(self, job_data: Dict) -> Dict:
        """Queue job for async processing via SQS delay queue"""
        
        try:
            sqs = boto3.client('sqs')
            
            # Send to async processing queue with delay
            response = sqs.send_message(
                QueueUrl=os.environ['ASYNC_PROCESSING_QUEUE_URL'],
                MessageBody=json.dumps(job_data),
                DelaySeconds=5,  # Small delay to ensure Lambda exits first
                MessageAttributes={
                    'JobType': {
                        'StringValue': 'keyword_indexing',
                        'DataType': 'String'
                    },
                    'DocId': {
                        'StringValue': job_data['doc_id'],
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Queued async processing: {response['MessageId']}")
            
            return {
                'success': True,
                'doc_id': job_data['doc_id'],
                'message_id': response['MessageId'],
                'processing_mode': 'sqs_async'
            }
            
        except Exception as e:
            logger.error(f"SQS async queueing failed: {e}")
            raise

    def invoke_async_lambda(self, job_data: Dict) -> Dict:
        """Invoke separate Lambda function asynchronously"""
        
        try:
            lambda_client = boto3.client('lambda')
            
            response = lambda_client.invoke(
                FunctionName=os.environ.get('ASYNC_INDEXER_FUNCTION', 'keyword-indexer-worker'),
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(job_data)
            )
            
            logger.info(f"Invoked async Lambda: {response['StatusCode']}")
            
            return {
                'success': True,
                'doc_id': job_data['doc_id'],
                'lambda_status': response['StatusCode'],
                'processing_mode': 'lambda_async'
            }
            
        except Exception as e:
            logger.error(f"Async Lambda invocation failed: {e}")
            raise

    def update_processing_status(self, doc_id: str, status: str, notes: str = None):
        """Quick database status update"""
        
        if not self.db_manager:
            return
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO keyword_indexing_status (doc_id, status, notes, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (doc_id) 
                        DO UPDATE SET 
                            status = EXCLUDED.status,
                            notes = EXCLUDED.notes,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (doc_id, status, notes, datetime.utcnow())
                    )
                    conn.commit()
            
        except Exception as e:
            logger.error(f"Status update error: {e}")

def lambda_handler(event, context):
    """Lambda entry point"""
    processor = AsyncKeywordIndexerProcessor()
    return processor.lambda_handler(event, context)
