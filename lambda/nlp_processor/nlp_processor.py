"""
NLP Processor - Async initiator following vector embeddings pattern
Subscribes to chunks-ready topic and delegates NLP processing to worker
"""
import json
import boto3
import os
import logging
from datetime import datetime

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Async initiator for NLP processing:
    1. Parse chunks-ready message
    2. Validate document exists
    3. Check if NLP already processed
    4. Delegate to NLP worker via SNS
    5. Return quickly (~200ms)
    """
    doc_id = None
    
    try:
        # Parse SNS message from text chunker
        message = json.loads(event['Records'][0]['Sns']['Message'])
        doc_id = message['doc_id']
        chunks_location = message['chunks_location']
        chunks_count = message.get('chunks_count', 0)
        
        logger.info(f"NLP processor triggered for document: {doc_id}")
        
        # Quick validation using DatabaseManager pattern
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Check if document exists
                cursor.execute("SELECT 1 FROM documents WHERE doc_id = %s", (doc_id,))
                doc_exists = cursor.fetchone()
                
                if not doc_exists:
                    raise ValueError(f"Document {doc_id} not found in database")
                
                # Check if NLP already processed
                cursor.execute("SELECT status FROM nlp_processing_status WHERE doc_id = %s", (doc_id,))
                existing_status = cursor.fetchone()
                
                if existing_status and existing_status[0] == 'COMPLETED':
                    logger.info(f"Document {doc_id} already has NLP processing - skipping")
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'doc_id': doc_id,
                            'status': 'already_completed',
                            'message': 'NLP processing already exists'
                        })
                    }
                
                # Update status to PROCESSING
                cursor.execute(
                    """INSERT INTO nlp_processing_status (doc_id, status, created_at) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (doc_id) DO UPDATE SET status = %s, created_at = %s""",
                    (doc_id, 'PROCESSING', datetime.now(), 'PROCESSING', datetime.now())
                )
                conn.commit()
                
        finally:
            db_manager.return_connection(conn)
        
        # Delegate to NLP worker via SNS
        sns_client = boto3.client('sns')
        worker_topic_arn = os.environ.get('NLP_WORKER_TOPIC_ARN')
        
        if not worker_topic_arn:
            raise ValueError("NLP_WORKER_TOPIC_ARN environment variable not set")
        
        # Prepare worker message with full document text location
        # Note: We need full document text for comprehensive entity detection
        full_text_location = message.get('full_text_location', {
            'bucket': chunks_location['bucket'],
            'key': f"{doc_id}/{doc_id}_full_text.txt"  # Assume full text stored alongside chunks
        })
        
        worker_message = {
            'doc_id': doc_id,
            'chunks_location': chunks_location,
            'full_text_location': full_text_location,
            'chunks_count': chunks_count,
            'processing_type': 'entity_and_phrases',
            'nlp_provider': os.environ.get('NLP_PROVIDER', 'comprehend'),
            'initiated_at': datetime.now().isoformat()
        }
        
        # Publish to worker topic
        sns_client.publish(
            TopicArn=worker_topic_arn,
            Message=json.dumps(worker_message),
            Subject=f'NLP processing for {doc_id}'
        )
        
        logger.info(f"Successfully delegated NLP processing for {doc_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'status': 'delegated_to_worker',
                'processing_time_ms': context.get_remaining_time_in_millis(),
                'worker_topic': worker_topic_arn,
                'nlp_provider': worker_message['nlp_provider']
            })
        }
        
    except Exception as e:
        error_msg = f"NLP processor error: {str(e)}"
        logger.error(error_msg)
        
        # Update status to failed if we have doc_id
        if doc_id:
            try:
                db_manager = DatabaseManager()
                conn = db_manager.get_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO nlp_processing_status (doc_id, status, error_message) 
                               VALUES (%s, %s, %s) 
                               ON CONFLICT (doc_id) DO UPDATE SET status = %s, error_message = %s""",
                            (doc_id, 'FAILED', str(e), 'FAILED', str(e))
                        )
                        conn.commit()
                finally:
                    db_manager.return_connection(conn)
            except Exception as db_error:
                logger.error(f"Failed to update error status: {str(db_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'doc_id': doc_id
            })
        }
