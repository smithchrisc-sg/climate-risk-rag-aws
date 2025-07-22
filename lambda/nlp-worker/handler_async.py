#!/usr/bin/env python3
"""
Handler for Asynchronous NLP Worker Lambda
"""
import json
import logging
from src.nlp_worker_async import AsyncNLPWorker

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda handler for asynchronous NLP processing"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Initialize worker
        worker = AsyncNLPWorker()
        
        # Process event
        result = worker.process_event(event, context)
        
        logger.info(f"Processing result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }
