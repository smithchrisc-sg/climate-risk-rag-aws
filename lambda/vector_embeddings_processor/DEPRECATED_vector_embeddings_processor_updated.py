"""
Vector Embeddings Processor - Updated for Standardized Messaging
Async initiator that processes chunks_ready messages in standardized format
"""
import json
import boto3
import os
import logging
from datetime import datetime

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

# Import standardized messaging components
from standardized_messaging import StandardizedMessageParser, StandardizedMessagePublisher

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Vector embeddings processor with standardized messaging:
    1. Parse standardized chunks_ready message
    2. Validate document and chunks exist
    3. Delegate to worker via SNS with standardized format
    4. Return quickly (~200ms)
    """
    doc_id = None
    
    try:
        # Parse standardized SNS message
        parser = StandardizedMessageParser()
        message = parser.parse_sns_message(event)
        
        # Validate this is a chunks_ready message
        if message.get('stage') != 'chunks_ready':
            raise ValueError(f"Expected chunks_ready message, got: {message.get('stage')}")
        
        doc_id = message['doc_id']
        doc_hash = message['doc_hash']
        
        logger.info(f"Vector embeddings processor triggered for document: {doc_id}")
        
        # Extract data locations from standardized format
        data_locations = message.get('data_locations', {})
        chunks_location = data_locations.get('chunks_location')
        text_location = data_locations.get('text_location')
        
        if not chunks_location:
            raise ValueError("chunks_location not found in message data_locations")
        
        # Extract processing metadata
        processing_metadata = message.get('processing_metadata', {})
        chunks_count = processing_metadata.get('chunks_count', 0)
        
        logger.info(f"Processing {chunks_count} chunks from: {chunks_location}")
        
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
                            'message': 'Vector embeddings already exist',
                            'standardized_messaging': True
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
        
        # Delegate to worker via SNS with standardized message format
        publisher = StandardizedMessagePublisher()
        worker_topic_arn = os.environ.get('VECTOR_WORKER_TOPIC_ARN')
        
        if not worker_topic_arn:
            raise ValueError("VECTOR_WORKER_TOPIC_ARN environment variable not set")
        
        # Publish standardized vector embeddings ready message
        publisher.publish_vector_embeddings_ready(
            doc_id=doc_id,
            doc_hash=doc_hash,
            chunks_location=chunks_location,
            text_location=text_location,
            document_metadata=message.get('document_metadata', {}),
            processing_metadata={
                'chunks_count': chunks_count,
                'initiated_from': 'chunks_ready',
                'processing_started': datetime.now().isoformat(),
                'cost_threshold': float(os.environ.get('COST_THRESHOLD_PER_DOC', '0.50'))
            },
            topic_arn=worker_topic_arn
        )
        
        logger.info(f"Successfully delegated vector embeddings processing for {doc_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'status': 'delegated_to_worker',
                'chunks_count': chunks_count,
                'processing_time_ms': context.get_remaining_time_in_millis(),
                'worker_topic': worker_topic_arn,
                'standardized_messaging': True
            })
        }
        
    except Exception as e:
        error_msg = f"Vector embeddings processor error: {str(e)}"
        logger.error(error_msg)
        
        # Update status to failed if we have doc_id
        if doc_id:
            try:
                db_manager = DatabaseManager()
                conn = db_manager.get_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """INSERT INTO vector_embeddings_status (doc_id, status, error_message) 
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
                'doc_id': doc_id,
                'standardized_messaging': True
            })
        }
