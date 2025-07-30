#!/usr/bin/env python3
"""
Handler for Comprehend Job Monitor Lambda
"""
import json
import logging
from src.job_completion_checker import JobCompletionChecker

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda handler for Comprehend job monitoring"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Initialize checker
        checker = JobCompletionChecker()
        
        # Process event
        result = checker.process_event(event, context)
        
        logger.info(f"Checker result: {result}")
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
