#!/usr/bin/env python3
"""
NLP Processor - STANDARDIZED MESSAGING VERSION
Async initiator that handles standardized chunks-ready messages and delegates to NLP worker
"""
import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict

# Import standardized messaging
from standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Async initiator for NLP processing with standardized messaging:
    1. Parse standardized chunks-ready message
    2. Validate document exists
    3. Check if NLP already processed
    4. Delegate to NLP worker via SNS with standardized format
    5. Return quickly (~200ms)
    """
    doc_id = None
    
    try:
        # Initialize standardized message components
        message_parser = StandardizedMessageParser()
        message_publisher = StandardizedMessagePublisher()
        
        # Parse standardized SNS message
        message = message_parser.parse_sns_message(event)
        
        # Validate message format
        if not message_parser.validate_message_format(message, 'chunks_ready'):
            raise ValueError("Invalid message format - expected chunks_ready stage")
        
        # Extract processing information
        processing_info = message_parser.extract_processing_info(message)
        doc_id = processing_info['doc_id']
        chunks_location = processing_info['chunks_location']
        text_location = processing_info['text_location']
        
        logger.info(f"NLP processor triggered for document: {doc_id}")
        logger.info(f"Chunks location: {chunks_location}")
        
        # Quick validation using DatabaseManager pattern
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Check if document exists
                cursor.execute("SELECT 1 FROM documents WHERE doc_id = %s", (doc_id,))
                doc_exists = cursor.fetchone()
                
                if not doc_exists:
                    logger.warning(f"Document {doc_id} not found in database - proceeding anyway")
                
                # Check if NLP already processed
                cursor.execute("SELECT status FROM nlp_processing_status WHERE doc_id = %s", (doc_id,))
                existing_status = cursor.fetchone()
                
                if existing_status and existing_status[0] == 'COMPLETED':
                    logger.info(f"Document {doc_id} already has NLP results - skipping")
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'NLP already completed',
                            'doc_id': doc_id,
                            'status': 'skipped',
                            'standardized_messaging': True
                        })
                    }
                
                # Update status to processing
                cursor.execute("""
                    INSERT INTO nlp_processing_status (doc_id, status, message, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        message = EXCLUDED.message,
                        updated_at = EXCLUDED.updated_at
                """, (doc_id, 'INITIATED', 'NLP processing initiated', datetime.utcnow()))
                
                conn.commit()
                
        finally:
            conn.close()
        
        # Prepare NLP configuration
        nlp_config = {
            'provider': os.environ.get('NLP_PROVIDER', 'comprehend'),
            'processing_type': 'entity_and_phrases',
            'language': 'auto',
            'cost_threshold': float(os.environ.get('COST_THRESHOLD_PER_DOC', '0.50')),
            'chunks_count': processing_info.get('processing_metadata', {}).get('chunks_count', 0),
            'total_characters': processing_info.get('processing_metadata', {}).get('total_characters', 0)
        }
        
        # Delegate to NLP worker with standardized message
        nlp_worker_topic_arn = os.environ.get('NLP_WORKER_TOPIC_ARN', 
                                            'arn:aws:sns:us-east-1:861276078413:nlp-worker')
        
        message_publisher.publish_nlp_worker_task(
            doc_id=doc_id,
            doc_hash=processing_info['doc_hash'],
            chunks_location=chunks_location,
            text_location=text_location,
            document_metadata=processing_info.get('document_metadata', {}),
            nlp_config=nlp_config,
            topic_arn=nlp_worker_topic_arn
        )
        
        logger.info(f"Successfully delegated NLP processing for document: {doc_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'NLP processing initiated',
                'doc_id': doc_id,
                'chunks_location': chunks_location,
                'nlp_provider': nlp_config['provider'],
                'estimated_cost': estimate_nlp_cost(nlp_config),
                'standardized_messaging': True
            })
        }
        
    except Exception as e:
        logger.error(f"NLP processor error for document {doc_id}: {e}")
        
        # Update status to failed if we have doc_id
        if doc_id:
            try:
                db_manager = DatabaseManager()
                conn = db_manager.get_connection()
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO nlp_processing_status (doc_id, status, message, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (doc_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            message = EXCLUDED.message,
                            updated_at = EXCLUDED.updated_at
                    """, (doc_id, 'FAILED', str(e), datetime.utcnow()))
                    conn.commit()
                conn.close()
            except:
                pass  # Don't fail on error tracking failure
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'doc_id': doc_id,
                'standardized_messaging': True
            })
        }

def estimate_nlp_cost(nlp_config: Dict) -> float:
    """Estimate NLP processing cost"""
    
    total_characters = nlp_config.get('total_characters', 0)
    provider = nlp_config.get('provider', 'comprehend')
    
    if provider == 'comprehend':
        # Amazon Comprehend pricing: $0.0001 per 100 characters for entities + key phrases
        # So $0.0002 per 100 characters for both
        cost_per_100_chars = 0.0002
        estimated_cost = (total_characters / 100.0) * cost_per_100_chars
        return round(estimated_cost, 4)
    
    return 0.0
