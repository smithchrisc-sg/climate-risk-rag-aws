#!/usr/bin/env python3
"""
Neptune Stream Poller Lambda Function
Processes Neptune Streams and indexes data to OpenSearch for full-text search

This is the main entry point for the Neptune-to-OpenSearch integration.
The actual processing logic is handled by the configured StreamRecordsHandler.
"""

import json
import logging
import os
import sys
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.getenv('LoggingLevel', 'INFO'))

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Neptune Stream processing
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Response dictionary
    """
    
    try:
        logger.info(f"Neptune Stream Poller started with event: {json.dumps(event, default=str)}")
        
        # Get configuration from environment variables
        stream_records_handler = os.getenv('StreamRecordsHandler', 
                                         'neptune_to_es.neptune_sparql_es_handler.ElasticSearchSparqlHandler')
        
        # Import and instantiate the configured handler
        module_name, class_name = stream_records_handler.rsplit('.', 1)
        module = __import__(module_name, fromlist=[class_name])
        handler_class = getattr(module, class_name)
        
        # Create handler instance
        handler = handler_class()
        
        # Process the event
        result = handler.process_event(event, context)
        
        logger.info("Neptune Stream Poller completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Neptune Stream processing completed',
                'result': result
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Neptune Stream Poller: {str(e)}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Neptune Stream processing failed'
            })
        }

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'test': True,
        'source': 'local'
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = 'neptune-stream-poller'
            self.memory_limit_in_mb = 1024
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:neptune-stream-poller'
            self.aws_request_id = 'test-request-id'
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
