"""
Data Retriever

Handles retrieval of NLP results and chunks data from S3.
"""

import json
import logging
import boto3
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DataRetriever:
    """
    Retrieves data from S3 storage for NLP processing pipeline.
    
    Handles retrieval of:
    - NLP results (entities, key phrases)
    - Document chunks data
    """
    
    def __init__(self):
        """Initialize the data retriever with S3 client."""
        self.s3_client = boto3.client('s3')
    
    def retrieve_nlp_results(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve NLP results from S3.
        
        Args:
            request: Processing request with S3 location info
            
        Returns:
            Parsed NLP results from Comprehend


        Example request:
        {
            "version": "1.0",
            "timestamp": "2025-08-14T16:29:00.685614Z",
            "source": "climate-risk-rag-system",
            "stage": "nlp_processing_complete",
            "doc_id": "064762102bead7b04a39",
            "data_locations": {
                "entities_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities.json",
                "key_phrases_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases.json",
                "mapped_phrases_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases_by_chunk.json",
                "mapped_entities_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities_by_chunk.json"
            },

            "processing_metadata": {
                "entities_count": 3345,
                "key_phrases_count": 8709,
                "processing_completed": "2025-08-14T16:29:00.685614Z"
            },
            "integration_flags": {
                "database_tracking_enabled": True,
                "knowledge_graph_integration_enabled": True
            }
        }

        """
        try:
            entities_location = request['data_locations']['mapped_entities_location']
            key_phrases_location = request['data_locations']['mapped_phrases_location']

            # Parse S3 URLs to extract bucket and key
            entities_bucket, entities_key = self._parse_s3_url(entities_location)
            key_phrases_bucket, key_phrases_key = self._parse_s3_url(key_phrases_location)

            entities_response = self.s3_client.get_object(
                Bucket=entities_bucket,
                Key=entities_key
            )
            key_phrases_response = self.s3_client.get_object(
                Bucket=key_phrases_bucket,
                Key=key_phrases_key
            )
            
            # Read entities data
            entities_data = json.loads(entities_response['Body'].read().decode('utf-8'))
            
            # Handle list format from nlp-worker (entities_by_chunk.json is always a list)
            if isinstance(entities_data, list):
                logger.info(f"Retrieved NLP results: {len(entities_data)} entities (list format)")
                # Return in expected dict format with 'entities' key
                return {'entities': entities_data}
            elif isinstance(entities_data, dict):
                # Fallback for dict format (shouldn't happen with mapped_entities_location)
                entities_count = len(entities_data.get('entities', []))
                logger.info(f"Retrieved NLP results: {entities_count} entities (dict format)")
                return entities_data
            else:
                logger.warning(f"Unexpected NLP results format: {type(entities_data)}")
                return {'entities': []}
            
        except Exception as e:
            logger.error(f"Failed to retrieve NLP results: {str(e)}")
            raise
    
    def retrieve_chunks_data(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve chunks data from S3.
        
        Args:
            request: Processing request with S3 location info
            
        Returns:
            List of document chunks with metadata
        """
        try:
            response = self.s3_client.get_object(
                Bucket=request['s3_bucket'],
                Key=request['chunks_key']
            )
            
            chunks_data = json.loads(response['Body'].read().decode('utf-8'))
            logger.info(f"Retrieved chunks data: {len(chunks_data)} chunks")
            
            return chunks_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks data from {request['chunks_key']}: {str(e)}")
            raise
    
    def _parse_s3_url(self, s3_url: str) -> Tuple[str, str]:
        """
        Parse S3 URL to extract bucket and key.
        
        Args:
            s3_url: S3 URL in format s3://bucket-name/path/to/object
            
        Returns:
            Tuple of (bucket_name, object_key)
            
        Raises:
            ValueError: If URL is not a valid S3 URL
        """
        try:
            parsed = urlparse(s3_url)
            if parsed.scheme != 's3':
                raise ValueError(f"Invalid S3 URL scheme: {parsed.scheme}")
            
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            if not bucket:
                raise ValueError("No bucket name found in S3 URL")
            if not key:
                raise ValueError("No object key found in S3 URL")
                
            return bucket, key
            
        except Exception as e:
            raise ValueError(f"Failed to parse S3 URL '{s3_url}': {str(e)}")
