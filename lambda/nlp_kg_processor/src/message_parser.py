"""
Message Parser

Handles parsing and validation of SNS messages from the nlp_processing Lambda.
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class MessageParser:
    """
    Parses SNS messages containing NLP processing completion notifications.
    """
    
    def parse_sns_message(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse SNS message to extract processing requests.
        
        Expected message format from nlp_processing Lambda:
        {
            "processing_requests": [
                {
                    "document_id": "doc123",
                    "s3_bucket": "bucket-name",
                    "nlp_results_key": "nlp-results/doc123/comprehend_results.json",
                    "chunks_key": "chunks/doc123/chunks.json"
                }
            ]
        }
        
        Args:
            event: Lambda event containing SNS message
            
        Returns:
            List of valid processing requests
        """
        try:
            # Handle SNS event structure
            if 'Records' in event:
                # Standard SNS event
                sns_message = json.loads(event['Records'][0]['Sns']['Message'])
            else:
                # Direct invocation for testing
                sns_message = event
            
            processing_requests = sns_message.get('processing_requests', [])
            
            # Validate each request has required fields
            valid_requests = []
            for request in processing_requests:
                if self._validate_request(request):
                    valid_requests.append(request)
                else:
                    logger.warning(f"Invalid request missing required fields: {request}")
            
            logger.info(f"Parsed {len(valid_requests)} valid processing requests")
            return valid_requests
            
        except Exception as e:
            logger.error(f"Failed to parse SNS message: {str(e)}")
            return []
    
    def _validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Validate that a processing request has all required fields.
        
        Args:
            request: Processing request to validate
            
        Returns:
            True if request is valid, False otherwise
        """
        required_fields = ['document_id', 's3_bucket', 'nlp_results_key', 'chunks_key']
        return all(key in request and request[key] for key in required_fields)
