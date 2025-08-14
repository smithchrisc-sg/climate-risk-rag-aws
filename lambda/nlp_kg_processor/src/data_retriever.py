"""
Data Retriever

Handles retrieval of NLP results and chunks data from S3.
"""

import json
import logging
import boto3
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class DataRetriever:
    """
    Retrieves processing data from S3 storage.
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
        """
        try:
            response = self.s3_client.get_object(
                Bucket=request['s3_bucket'],
                Key=request['nlp_results_key']
            )
            
            nlp_results = json.loads(response['Body'].read().decode('utf-8'))
            
            # Handle both list and dict formats for NLP results
            if isinstance(nlp_results, list):
                logger.info(f"Retrieved NLP results: {len(nlp_results)} entities (list format)")
                # Convert list format to expected dict format
                return {'entities': nlp_results}
            elif isinstance(nlp_results, dict):
                entities_count = len(nlp_results.get('entities', []))
                logger.info(f"Retrieved NLP results: {entities_count} entities (dict format)")
                return nlp_results
            else:
                logger.warning(f"Unexpected NLP results format: {type(nlp_results)}")
                return {'entities': []}
            
        except Exception as e:
            logger.error(f"Failed to retrieve NLP results from {request['nlp_results_key']}: {str(e)}")
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
