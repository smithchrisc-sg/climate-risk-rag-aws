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
        
        Expected message format from nlp_processing Lambda (SNS wraps in Records array):
        {
            "Records": [
                {
                    "Sns": {
                        "Message": "{
                            \"version\": \"1.0\",
                            \"timestamp\": \"2025-08-14T16:29:00.685614Z\",
                            \"source\": \"climate-risk-rag-system\",
                            \"stage\": \"nlp_processing_complete\",
                            \"doc_id\": \"064762102bead7b04a39\",
                            \"data_locations\": {
                                \"entities_location\": \"s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities.json\",
                                \"key_phrases_location\": \"s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases.json\",
                                \"mapped_phrases_location\": \"s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases_by_chunk.json\",
                                \"mapped_entities_location\": \"s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities_by_chunk.json\"
                            },
                            \"processing_metadata\": {
                                \"entities_count\": 3345,
                                \"key_phrases_count\": 8709,
                                \"processing_completed\": \"2025-08-14T16:29:00.685614Z\"
                            },
                            \"integration_flags\": {
                                \"database_tracking_enabled\": true,
                                \"knowledge_graph_integration_enabled\": true
                            }
                        }"
                    }
                }
            ]
        }
        
        Args:
            event: Lambda event containing SNS message
            
        Returns:
            List of valid processing requests (always single item from SNS)
        """
        try:
            # Handle SNS event structure
            if 'Records' in event:
                # Standard SNS event - unwrap the message
                sns_message = json.loads(event['Records'][0]['Sns']['Message'])
            else:
                # Direct invocation for testing
                sns_message = event
            
            # SNS sends single message, but we return as list for consistency
            if self._validate_request(sns_message):
                logger.info(f"Parsed valid processing request for doc_id: {sns_message.get('doc_id')}")
                return [sns_message]
            else:
                logger.warning(f"Invalid request missing required fields: {sns_message}")
                return []
            
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
        required_fields = ['doc_id', 'data_locations', 'processing_metadata', 'integration_flags']
        return all(key in request and request[key] for key in required_fields)
