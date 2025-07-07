#!/usr/bin/env python3
"""
Simple Async Keyword Indexer - Cost-Efficient Callback Approach
No Step Functions needed - just async Lambda invocation with SNS callbacks
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleAsyncKeywordIndexer:
    """
    Simple async processor - quick initiation + callback completion
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        self.lambda_client = boto3.client('lambda')
        
        # Environment variables
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
        self.worker_function_name = os.environ.get('WORKER_FUNCTION_NAME', 'keyword-indexer-worker')
        
        # Database manager
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
        except ImportError:
            self.db_manager = None

    def lambda_handler(self, event, context):
        """Main handler - quick processing and async delegation"""
        
        logger.info(f"Processing {len(event['Records'])} records with simple async approach")
        
        results = []
        for record in event['Records']:
            try:
                result = self.process_record_quickly(record)
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
                'approach': 'simple_async_callback'
            })
        }

    def process_record_quickly(self, record: Dict) -> Dict:
        """Quick processing - just validate and delegate"""
        
        try:
            # Parse message
            message_body = json.loads(record['body'])
            if 'Message' in message_body:
                sns_message = json.loads(message_body['Message'])
            else:
                sns_message = message_body
            
            if sns_message.get('stage') != 'text_ready':
                return {'success': False, 'error': 'Unexpected message stage'}
            
            doc_id = sns_message.get('doc_id')
            if not doc_id:
                return {'success': False, 'error': 'Missing doc_id'}
            
            # Quick status update
            if self.db_manager:
                self.quick_status_update(doc_id, 'PROCESSING', 'Async indexing initiated')
            
            # Delegate to worker function asynchronously
            worker_payload = {
                'action': 'index_document',
                'doc_id': doc_id,
                'full_text_location': sns_message.get('full_text_location'),
                'filename': sns_message.get('filename', 'unknown'),
                'completion_topic_arn': self.completion_topic_arn,
                'initiated_at': datetime.utcnow().isoformat()
            }
            
            # Async Lambda invocation (fire and forget)
            response = self.lambda_client.invoke(
                FunctionName=self.worker_function_name,
                InvocationType='Event',  # Async
                Payload=json.dumps(worker_payload)
            )
            
            logger.info(f"Delegated {doc_id} to worker function: {response['StatusCode']}")
            
            return {
                'success': True,
                'doc_id': doc_id,
                'delegated_to': self.worker_function_name,
                'lambda_status': response['StatusCode']
            }
            
        except Exception as e:
            logger.error(f"Quick processing error: {e}")
            raise

    def quick_status_update(self, doc_id: str, status: str, notes: str):
        """Ultra-fast status update"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO keyword_indexing_status (doc_id, status, notes, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (doc_id) 
                        DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes, updated_at = EXCLUDED.updated_at
                        """,
                        (doc_id, status, notes, datetime.utcnow())
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Quick status update error: {e}")

def lambda_handler(event, context):
    """Lambda entry point"""
    processor = SimpleAsyncKeywordIndexer()
    return processor.lambda_handler(event, context)
