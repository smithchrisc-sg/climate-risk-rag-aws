"""
Vector Embeddings Processor - Async initiator following keyword indexer pattern
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
    Async initiator following keyword indexer pattern:
    1. Parse chunks-ready message
    2. Validate document exists
    3. Delegate to worker via SNS
    4. Return quickly (~200ms)
    """
    doc_id = None
    
    try:
        # Parse SNS message from text chunker
        message = json.loads(event['Records'][0]['Sns']['Message'])
        doc_id = message['doc_id']
        
        logger.info(f"Vector embeddings processor triggered for document: {doc_id}")
        
        # Quick validation
        db_manager = DatabaseManager()
        
        # Check if document exists
        doc_exists = db_manager.execute_query(
            "SELECT 1 FROM documents WHERE doc_id = %s",
            (doc_id,)
        )
        
        if not doc_exists:
            raise ValueError(f"Document {doc_id} not found in database")
        
        # Check if already processed
        existing_status = db_manager.execute_query(
            "SELECT status FROM vector_embeddings_status WHERE doc_id = %s",
            (doc_id,)
        )
        
        if existing_status and existing_status[0][0] == 'COMPLETED':
            logger.info(f"Document {doc_id} already has vector embeddings - skipping")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'doc_id': doc_id,
                    'status': 'already_completed',
                    'message': 'Vector embeddings already exist'
                })
            }
        
        # Update status to PROCESSING
        db_manager.execute_query(
            """INSERT INTO vector_embeddings_status (doc_id, status, created_at) 
               VALUES (%s, %s, %s) 
               ON CONFLICT (doc_id) DO UPDATE SET status = %s, created_at = %s""",
            (doc_id, 'PROCESSING', datetime.now(), 'PROCESSING', datetime.now())
        )
        
        # Delegate to worker via SNS
        sns_client = boto3.client('sns')
        worker_topic_arn = os.environ.get('VECTOR_WORKER_TOPIC_ARN')
        
        if not worker_topic_arn:
            raise ValueError("VECTOR_WORKER_TOPIC_ARN environment variable not set")
        
        # Prepare worker message
        worker_message = {
            'doc_id': doc_id,
            'chunks_location': message['chunks_location'],
            'processing_type': 'vector_embeddings',
            'initiated_at': datetime.now().isoformat()
        }
        
        # Publish to worker topic
        sns_client.publish(
            TopicArn=worker_topic_arn,
            Message=json.dumps(worker_message),
            Subject=f'Vector embeddings processing for {doc_id}'
        )
        
        logger.info(f"Successfully delegated vector embeddings processing for {doc_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'status': 'delegated_to_worker',
                'processing_time_ms': context.get_remaining_time_in_millis(),
                'worker_topic': worker_topic_arn
            })
        }
        
    except Exception as e:
        error_msg = f"Vector embeddings processor error: {str(e)}"
        logger.error(error_msg)
        
        # Update status to failed if we have doc_id
        if doc_id:
            try:
                db_manager = DatabaseManager()
                db_manager.execute_query(
                    """INSERT INTO vector_embeddings_status (doc_id, status, error_message) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (doc_id) DO UPDATE SET status = %s, error_message = %s""",
                    (doc_id, 'FAILED', str(e), 'FAILED', str(e))
                )
            except Exception as db_error:
                logger.error(f"Failed to update error status: {str(db_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'doc_id': doc_id
            })
        }
