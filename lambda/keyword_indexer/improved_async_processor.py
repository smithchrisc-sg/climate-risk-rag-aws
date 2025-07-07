#!/usr/bin/env python3
"""
Improved Async Keyword Indexer - Fixed Status Update Issue
Enhanced error handling and logging for proper status tracking
"""

import os
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedAsyncKeywordIndexer:
    """
    Improved async processor with fixed status update and enhanced logging
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        self.lambda_client = boto3.client('lambda')
        
        # Environment variables
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
        self.worker_function_name = os.environ.get('WORKER_FUNCTION_NAME', 'async-keyword-indexer-worker')
        
        # Database manager with enhanced error handling
        self.db_manager = None
        try:
            from utils.DatabaseManager import DatabaseManager
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import DatabaseManager: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize DatabaseManager: {e}")

    def lambda_handler(self, event, context):
        """Main handler with enhanced logging"""
        
        logger.info(f"🚀 Processing {len(event['Records'])} records with improved async approach")
        
        results = []
        for i, record in enumerate(event['Records'], 1):
            try:
                logger.info(f"📝 Processing record {i}/{len(event['Records'])}")
                result = self.process_record_with_enhanced_logging(record)
                results.append(result)
                logger.info(f"✅ Record {i} processed successfully: {result.get('doc_id', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Error processing record {i}: {e}")
                results.append({'success': False, 'error': str(e), 'record_index': i})
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'initiated': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'approach': 'improved_async_callback'
            })
        }
        
        logger.info(f"🎯 Batch processing complete: {response['body']}")
        return response

    def process_record_with_enhanced_logging(self, record: Dict) -> Dict:
        """Process record with detailed logging"""
        
        try:
            # Parse message with logging
            logger.info("📨 Parsing SQS message...")
            message_body = json.loads(record['body'])
            
            if 'Message' in message_body:
                sns_message = json.loads(message_body['Message'])
                logger.info("📬 Parsed SNS-wrapped message")
            else:
                sns_message = message_body
                logger.info("📬 Parsed direct message")
            
            # Validate message
            if sns_message.get('stage') != 'text_ready':
                error_msg = f"Unexpected message stage: {sns_message.get('stage')}"
                logger.error(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg}
            
            doc_id = sns_message.get('doc_id')
            if not doc_id:
                error_msg = "Missing doc_id in message"
                logger.error(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg}
            
            logger.info(f"📄 Processing document: {doc_id}")
            
            # Enhanced status update with detailed logging
            status_updated = self.enhanced_status_update(doc_id, 'PROCESSING', 'Async indexing initiated')
            
            if status_updated:
                logger.info(f"✅ Initial status updated for {doc_id}")
            else:
                logger.warning(f"⚠️ Initial status update failed for {doc_id} (continuing anyway)")
            
            # Prepare worker payload
            worker_payload = {
                'action': 'index_document',
                'doc_id': doc_id,
                'full_text_location': sns_message.get('full_text_location'),
                'filename': sns_message.get('filename', 'unknown'),
                'completion_topic_arn': self.completion_topic_arn,
                'initiated_at': datetime.utcnow().isoformat(),
                'initiator_status_updated': status_updated
            }
            
            logger.info(f"🔄 Delegating to worker function: {self.worker_function_name}")
            
            # Async Lambda invocation
            response = self.lambda_client.invoke(
                FunctionName=self.worker_function_name,
                InvocationType='Event',  # Async
                Payload=json.dumps(worker_payload)
            )
            
            if response['StatusCode'] == 202:  # Async invocation success
                logger.info(f"✅ Successfully delegated {doc_id} to worker (Status: {response['StatusCode']})")
                
                return {
                    'success': True,
                    'doc_id': doc_id,
                    'delegated_to': self.worker_function_name,
                    'lambda_status': response['StatusCode'],
                    'status_updated': status_updated
                }
            else:
                error_msg = f"Unexpected Lambda invocation status: {response['StatusCode']}"
                logger.error(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg, 'doc_id': doc_id}
            
        except Exception as e:
            logger.error(f"❌ Record processing error: {e}")
            raise

    def enhanced_status_update(self, doc_id: str, status: str, notes: str) -> bool:
        """Enhanced status update with detailed error handling"""
        
        if not self.db_manager:
            logger.warning("⚠️ DatabaseManager not available - skipping status update")
            return False
        
        try:
            logger.info(f"💾 Updating status for {doc_id}: {status}")
            
            with self.db_manager.get_connection() as conn:
                logger.debug("🔗 Database connection established")
                
                with conn.cursor() as cursor:
                    logger.debug("📝 Executing status update query")
                    
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
                    
                    logger.debug("💾 Committing transaction")
                    conn.commit()
                    
                    logger.info(f"✅ Status updated successfully for {doc_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Status update failed for {doc_id}: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error details: {str(e)}")
            return False

def lambda_handler(event, context):
    """Lambda entry point with enhanced logging"""
    logger.info("🚀 Improved Async Keyword Indexer starting...")
    
    try:
        processor = ImprovedAsyncKeywordIndexer()
        result = processor.lambda_handler(event, context)
        logger.info("✅ Processing completed successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Fatal error in lambda_handler: {e}")
        raise
