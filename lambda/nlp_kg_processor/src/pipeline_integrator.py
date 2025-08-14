"""
Pipeline Integrator

Handles data persistence and integration with downstream pipeline components.
"""

import json
import logging
import os
import boto3
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PipelineIntegrator:
    """
    Manages output persistence and pipeline integration.
    """
    
    def __init__(self):
        """Initialize the pipeline integrator with AWS clients."""
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
    
    def persist_knowledge_graph_data(self, document_id: str, triples: List[Dict[str, Any]], bucket: str) -> str:
        """
        Persist knowledge graph triples to S3 in TTL format.
        
        Args:
            document_id: Document identifier
            triples: List of RDF triples
            bucket: S3 bucket name
            
        Returns:
            S3 key where TTL file was stored
        """
        try:
            # Convert triples to TTL format
            ttl_content = self._convert_triples_to_ttl(triples)
            
            # Generate S3 key for TTL file
            s3_key = f"knowledge-graph/{document_id}/triples.ttl"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=ttl_content.encode('utf-8'),
                ContentType='text/turtle'
            )
            
            logger.info(f"Persisted TTL file to s3://{bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to persist knowledge graph data: {str(e)}")
            raise
    
    def trigger_kg_triple_loader(self, document_id: str, ttl_s3_key: str):
        """
        Trigger the kg-triple-loader Lambda to load triples into Neptune.
        
        Args:
            document_id: Document identifier
            ttl_s3_key: S3 key of the TTL file to load
        """
        try:
            # Get SNS topic ARN from environment
            kg_loader_topic_arn = os.environ.get('KG_LOADER_SNS_TOPIC_ARN')
            
            if not kg_loader_topic_arn:
                logger.warning("KG_LOADER_SNS_TOPIC_ARN not configured, skipping kg-triple-loader trigger")
                return
            
            message = {
                'document_id': document_id,
                'ttl_s3_key': ttl_s3_key,
                'processing_stage': 'kg_loading'
            }
            
            self.sns_client.publish(
                TopicArn=kg_loader_topic_arn,
                Message=json.dumps(message),
                Subject=f'KG Loading Request for {document_id}'
            )
            
            logger.info(f"Triggered kg-triple-loader for {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger kg-triple-loader: {str(e)}")
            # Don't raise - this is not critical for the main processing
    
    def _convert_triples_to_ttl(self, triples: List[Dict[str, Any]]) -> str:
        """
        Convert triples to TTL (Turtle) format.
        
        This is a simplified conversion - the actual implementation
        would be in the TripleManager layer component.
        
        Args:
            triples: List of RDF triples
            
        Returns:
            TTL formatted string
        """
        ttl_lines = [
            "@prefix cro: <http://example.org/climate-risk-ontology#> .",
            "@prefix geo: <http://www.geonames.org/ontology#> .",
            "@prefix doc: <http://example.org/documents#> .",
            ""
        ]
        
        for triple in triples:
            subject = triple.get('subject', '')
            predicate = triple.get('predicate', '')
            object_val = triple.get('object', '')
            
            ttl_lines.append(f"{subject} {predicate} {object_val} .")
        
        return "\n".join(ttl_lines)
