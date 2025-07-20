#!/usr/bin/env python3
"""
Simple Async Keyword Indexer - Cost-Efficient Callback Approach
Updated to use DatabaseManager methods instead of direct SQL
"""

import os
import json
import logging
import sys
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging for Lambda
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class SimpleAsyncKeywordIndexer:
    """
    Simple async processor - quick initiation + callback completion
    Updated to use DatabaseManager methods for all database operations
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        self.lambda_client = boto3.client('lambda')
        
        # Environment variables
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
        self.worker_function_name = os.environ.get('WORKER_FUNCTION_NAME', 'keyword-indexer-worker')
        
        # Database manager - updated to use proper DatabaseManager methods
        try:
            # from DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            # logger.info("DatabaseManager initialized from direct import")
        except ImportError:
            try:
                from utils.DatabaseManager import DatabaseManager
                self.db_manager = DatabaseManager()
                logger.info("DatabaseManager initialized from utils import")
            except ImportError:
                self.db_manager = None
                logger.warning("DatabaseManager not available - status updates disabled")

    def lambda_handler(self, event, context):
        """Main handler - quick processing and async delegation"""
        logger.info(f"Keyword indexer processor triggered with {len(event.get('Records', []))} records")
        
        results = {
            'processed': 0,
            'errors': 0,
            'delegated': 0
        }
        
        for record in event.get('Records', []):
            try:
                # Parse the record to extract document information
                doc_info = self.parse_record(record)
                if not doc_info:
                    logger.warning("Could not parse record - skipping")
                    continue
                
                doc_id = doc_info['doc_id']
                logger.info(f"Processing keyword indexing request for document: {doc_id}")
                
                # Quick status update using DatabaseManager
                if self.db_manager:
                    self.update_status_via_db_manager(doc_id, 'PROCESSING', 'Async indexing initiated')
                
                # Delegate to worker function asynchronously
                self.delegate_to_worker(doc_info)
                
                results['processed'] += 1
                results['delegated'] += 1
                
                logger.info(f"Successfully delegated keyword indexing for document: {doc_id}")
                
            except Exception as e:
                logger.error(f"Error processing record: {str(e)}")
                logger.error(f"Record: {json.dumps(record, default=str)}")
                results['errors'] += 1
        
        logger.info(f"Keyword indexer processor completed: {results}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Keyword indexing requests processed',
                'results': results
            })
        }
    
    def parse_record(self, record) -> Optional[Dict[str, Any]]:
        """Parse incoming record to extract document information"""
        try:
            # Handle different record types (SNS, SQS, direct invocation)
            if record.get('eventSource') == 'aws:sns':
                # SNS record
                message = json.loads(record['Sns']['Message'])
                return self.extract_doc_info_from_message(message)
            
            elif record.get('eventSource') == 'aws:sqs':
                # SQS record
                body = json.loads(record['body'])
                if body.get('Type') == 'Notification':
                    # SNS message wrapped in SQS
                    message = json.loads(body['Message'])
                    return self.extract_doc_info_from_message(message)
                else:
                    # Direct SQS message
                    return self.extract_doc_info_from_message(body)
            
            else:
                # Direct invocation or other event types
                return self.extract_doc_info_from_message(record)
                
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            return None
    
    def extract_doc_info_from_message(self, message: Dict) -> Optional[Dict[str, Any]]:
        """Extract document information from message"""
        try:
            # Look for common document identifier patterns
            doc_id = (
                message.get('doc_id') or 
                message.get('document_id') or
                message.get('docId') or
                message.get('textract_job_id')  # Fallback for text extraction complete messages
            )
            
            if not doc_id:
                logger.warning("No document ID found in message")
                return None
            
            return {
                'doc_id': doc_id,
                'source_message': message,
                'text_bucket': message.get('text_s3_bucket', self.text_bucket),
                'text_key': message.get('text_s3_key'),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting document info: {e}")
            return None
    
    def update_status_via_db_manager(self, doc_id: str, status: str, notes: str):
        """Update keyword indexing status using DatabaseManager methods"""
        try:
            if not self.db_manager:
                logger.warning("DatabaseManager not available - skipping status update")
                return
            
            # Use the new DatabaseManager method instead of direct SQL
            self.db_manager.update_keyword_indexing_status(
                doc_id=doc_id,
                status=status,
                notes=notes
            )
            
            logger.info(f"Updated keyword indexing status via DatabaseManager: {doc_id} -> {status}")
            
        except Exception as e:
            logger.error(f"DatabaseManager status update error: {e}")
            # Don't raise - this shouldn't block the main processing
    
    def delegate_to_worker(self, doc_info: Dict[str, Any]):
        """Delegate processing to worker function asynchronously"""
        try:
            # Prepare payload for worker
            worker_payload = {
                'doc_id': doc_info['doc_id'],
                'text_bucket': doc_info.get('text_bucket', self.text_bucket),
                'text_key': doc_info.get('text_key'),
                'completion_topic_arn': self.completion_topic_arn,
                'processing_metadata': {
                    'initiated_at': doc_info['processing_timestamp'],
                    'initiated_by': 'keyword-indexer-processor'
                }
            }
            
            # Invoke worker function asynchronously
            response = self.lambda_client.invoke(
                FunctionName=self.worker_function_name,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(worker_payload)
            )
            
            logger.info(f"Successfully delegated to worker: {self.worker_function_name}")
            logger.debug(f"Worker response status: {response.get('StatusCode')}")
            
        except Exception as e:
            logger.error(f"Error delegating to worker: {e}")
            # Update status to failed using DatabaseManager
            if self.db_manager:
                self.update_status_via_db_manager(
                    doc_info['doc_id'], 
                    'FAILED', 
                    f'Failed to delegate to worker: {str(e)}'
                )
            raise
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get keyword indexing processing statistics using DatabaseManager"""
        try:
            if not self.db_manager:
                return {'error': 'DatabaseManager not available'}
            
            # Use DatabaseManager method to get statistics
            stats = self.db_manager.get_keyword_indexing_statistics()
            
            logger.info("Retrieved keyword indexing statistics via DatabaseManager")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting processing statistics: {e}")
            return {'error': str(e)}


def lambda_handler(event, context):
    """Lambda entry point"""
    try:
        processor = SimpleAsyncKeywordIndexer()
        return processor.lambda_handler(event, context)
    except Exception as e:
        logger.error(f"Keyword indexer processor error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
# Updated Fri Jul 18 13:23:26 PDT 2025
