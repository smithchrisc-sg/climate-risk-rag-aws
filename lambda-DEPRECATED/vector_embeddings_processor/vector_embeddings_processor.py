"""
Vector Embeddings Processor - Fixed version with resilient error handling
Phase A.5: Surgical fix for error handling path
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
        
        # Extract chunks location - support both standardized and legacy formats
        chunks_location = None
        if 'data_locations' in message:
            # Standardized format
            data_locations = message['data_locations']
            chunks_location = data_locations.get('chunks_folder_url') or data_locations.get('chunks_location')
        else:
            # Legacy format
            chunks_location = message.get('chunks_location')
        
        if not chunks_location:
            raise ValueError("chunks_location or chunks_folder_url not found in message")
        
        logger.info(f"Processing chunks from: {chunks_location}")
        
        # Quick validation
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Check if document exists
                cursor.execute("SELECT 1 FROM documents WHERE doc_id = %s", (doc_id,))
                doc_exists = cursor.fetchone()
                
                if not doc_exists:
                    raise ValueError(f"Document {doc_id} not found in database")
                
                # Check if already processed
                cursor.execute("SELECT status FROM vector_embeddings_status WHERE doc_id = %s", (doc_id,))
                existing_status = cursor.fetchone()
                
                if existing_status and existing_status[0] == 'COMPLETED':
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
                cursor.execute(
                    """INSERT INTO vector_embeddings_status (doc_id, status, created_at) 
                       VALUES (%s, %s, %s) 
                       ON CONFLICT (doc_id) DO UPDATE SET status = %s, created_at = %s""",
                    (doc_id, 'PROCESSING', datetime.now(), 'PROCESSING', datetime.now())
                )
                conn.commit()
                
        finally:
            db_manager.return_connection(conn)
        
        # Delegate to worker via SNS
        sns_client = boto3.client('sns')
        worker_topic_arn = os.environ.get('VECTOR_WORKER_TOPIC_ARN')
        
        if not worker_topic_arn:
            raise ValueError("VECTOR_WORKER_TOPIC_ARN environment variable not set")
        
        # Prepare worker message with standardized format
        worker_message = {
            'doc_id': doc_id,
            'doc_hash': message.get('doc_hash', 'unknown'),
            'stage': 'chunks_ready',
            'data_locations': {
                'chunks_folder_url': chunks_location,
                'chunks_location': chunks_location  # Backward compatibility
            },
            'document_metadata': message.get('document_metadata', {}),
            'processing_metadata': message.get('processing_metadata', {}),
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
        
        # Phase A.5: Resilient error handling - only attempt database update if we have doc_id
        # and the error is not database-related
        if doc_id and not _is_database_related_error(e):
            try:
                _update_error_status_resilient(doc_id, str(e))
            except Exception as db_error:
                # Phase A.5: Don't let error status update failures crash the response
                logger.warning(f"Could not update error status (non-critical): {str(db_error)}")
        else:
            logger.info(f"Skipping error status update due to database-related error or missing doc_id")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'doc_id': doc_id
            })
        }

def _is_database_related_error(error):
    """Check if the error is database-related and we shouldn't try more database operations"""
    error_str = str(error).lower()
    database_error_indicators = [
        'connection pool is closed',
        'connection failed',
        'authentication failed',
        'database initialization failed',
        'no results to fetch',
        'connection timeout'
    ]
    
    return any(indicator in error_str for indicator in database_error_indicators)

def _update_error_status_resilient(doc_id, error_message):
    """Resilient error status update with connection pool recovery"""
    max_attempts = 2
    
    for attempt in range(max_attempts):
        try:
            # Create fresh DatabaseManager instance for error handling
            db_manager = DatabaseManager()
            
            # Force pool reinitialization if this is a retry
            if attempt > 0:
                logger.info("Forcing connection pool reinitialization for error status update")
                # Reset pool state to force fresh initialization
                db_manager.__class__._connection_pool = None
                db_manager.__class__._pool_initialized = False
            
            conn = db_manager.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO vector_embeddings_status (doc_id, status, error_message, updated_at) 
                           VALUES (%s, %s, %s, CURRENT_TIMESTAMP) 
                           ON CONFLICT (doc_id) DO UPDATE SET 
                               status = EXCLUDED.status, 
                               error_message = EXCLUDED.error_message,
                               updated_at = CURRENT_TIMESTAMP""",
                        (doc_id, 'FAILED', error_message)
                    )
                    conn.commit()
                    logger.info(f"Successfully updated error status for {doc_id}")
                    return  # Success - exit function
                    
            finally:
                db_manager.return_connection(conn)
                
        except Exception as db_error:
            logger.warning(f"Error status update attempt {attempt + 1} failed: {str(db_error)}")
            if attempt == max_attempts - 1:
                # Final attempt failed - raise the error
                raise
            # Otherwise, continue to next attempt
