#!/usr/bin/env python3
"""
Debug Processor - Simple version to isolate the issue
"""

import json
import logging
import boto3
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """Simple debug handler"""
    
    logger.info("🔍 DEBUG: Function started")
    logger.info(f"🔍 DEBUG: Event received: {json.dumps(event)}")
    
    try:
        # Basic processing
        records = event.get('Records', [])
        logger.info(f"🔍 DEBUG: Processing {len(records)} records")
        
        results = []
        
        for i, record in enumerate(records):
            logger.info(f"🔍 DEBUG: Processing record {i+1}")
            
            try:
                # Parse message
                message_body = json.loads(record['body'])
                logger.info(f"🔍 DEBUG: Parsed message body")
                
                if 'Message' in message_body:
                    sns_message = json.loads(message_body['Message'])
                    logger.info(f"🔍 DEBUG: Parsed SNS message")
                else:
                    sns_message = message_body
                    logger.info(f"🔍 DEBUG: Using direct message")
                
                doc_id = sns_message.get('doc_id', 'unknown')
                stage = sns_message.get('stage', 'unknown')
                
                logger.info(f"🔍 DEBUG: Document {doc_id}, Stage {stage}")
                
                if stage == 'text_ready':
                    logger.info(f"✅ DEBUG: Valid text_ready message for {doc_id}")
                    
                    # Try database update
                    try:
                        logger.info(f"💾 DEBUG: Attempting database update for {doc_id}")
                        
                        # Import database manager
                        from utils.DatabaseManager import DatabaseManager
                        db_manager = DatabaseManager()
                        logger.info(f"✅ DEBUG: DatabaseManager imported successfully")
                        
                        # Update status
                        with db_manager.get_connection() as conn:
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
                                    (doc_id, 'PROCESSING', 'DEBUG: Async indexing initiated', datetime.utcnow())
                                )
                                conn.commit()
                        
                        logger.info(f"✅ DEBUG: Database updated successfully for {doc_id}")
                        
                    except Exception as db_error:
                        logger.error(f"❌ DEBUG: Database error: {db_error}")
                    
                    # Try worker invocation
                    try:
                        logger.info(f"🔄 DEBUG: Attempting worker invocation for {doc_id}")
                        
                        lambda_client = boto3.client('lambda')
                        
                        worker_payload = {
                            'action': 'index_document',
                            'doc_id': doc_id,
                            'full_text_location': sns_message.get('full_text_location'),
                            'filename': sns_message.get('filename', 'unknown'),
                            'completion_topic_arn': None,  # Skip for debug
                            'debug_test': True
                        }
                        
                        response = lambda_client.invoke(
                            FunctionName='async-keyword-indexer-worker',
                            InvocationType='Event',
                            Payload=json.dumps(worker_payload)
                        )
                        
                        logger.info(f"✅ DEBUG: Worker invoked successfully: {response['StatusCode']}")
                        
                    except Exception as worker_error:
                        logger.error(f"❌ DEBUG: Worker invocation error: {worker_error}")
                    
                    results.append({
                        'success': True,
                        'doc_id': doc_id,
                        'debug': True
                    })
                    
                else:
                    logger.warning(f"⚠️ DEBUG: Unexpected stage: {stage}")
                    results.append({
                        'success': False,
                        'error': f'Unexpected stage: {stage}',
                        'debug': True
                    })
                
            except Exception as record_error:
                logger.error(f"❌ DEBUG: Record processing error: {record_error}")
                results.append({
                    'success': False,
                    'error': str(record_error),
                    'debug': True
                })
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'processed': len(results),
                'successful': sum(1 for r in results if r.get('success')),
                'failed': sum(1 for r in results if not r.get('success')),
                'debug_mode': True
            })
        }
        
        logger.info(f"✅ DEBUG: Function completed successfully: {response}")
        return response
        
    except Exception as e:
        logger.error(f"❌ DEBUG: Fatal error: {e}")
        logger.error(f"❌ DEBUG: Error type: {type(e).__name__}")
        raise
