#!/usr/bin/env python3
"""
Text Extraction Processor Lambda Handler
Clean entry point following AWS Lambda best practices
"""

import json
import logging
from typing import Dict, Any

from processors.textract_processor import TextractProcessor
from config import Config

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for text extraction processing
    
    Args:
        event: Lambda event containing SNS notification about completed Textract job
        context: Lambda context object
        
    Returns:
        Dict containing processing status and results
    """
    try:
        logger.info(f"Text extraction processor invoked with event: {json.dumps(event)}")
        
        # Initialize processor with configuration
        config = Config()
        processor = TextractProcessor(config)
        
        # Process the event
        result = processor.process_textract_completion(event)
        
        logger.info(f"Text extraction processing completed successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'result': result
            })
        }
        
    except Exception as e:
        logger.error(f"Error in text extraction processing: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
