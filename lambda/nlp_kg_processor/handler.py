"""
NLP-KG Processor Lambda Handler

Main entry point for the NLP-KG processor Lambda function.
Processes NLP results from Amazon Comprehend and creates knowledge graph triples.
"""

import logging
from src.processor import NLPKGProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Main Lambda handler for NLP-KG processing.
    
    Args:
        event: Lambda event (SNS message from nlp_processing completion)
        context: Lambda context object
        
    Returns:
        Dict with statusCode and response body
    """
    processor = NLPKGProcessor()
    return processor.process(event, context)
