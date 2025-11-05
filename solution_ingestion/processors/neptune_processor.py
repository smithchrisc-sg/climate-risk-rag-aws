#!/usr/bin/env python3
"""
Neptune Processor for Solution Ingestion
Handles RDF storage in Neptune using production KnowledgeGraphManager.
"""

import logging
import sys
import os
from pathlib import Path

from knowledge_graph_layer.utils.KnowledgeGraphManager import KnowledgeGraphManager

logger = logging.getLogger(__name__)

class NeptuneProcessor:
    """Handles Neptune operations for solution ingestion."""
    
    def __init__(self, env):
        self.env = env
        self.kg_manager = None
        self._init_neptune()
    
    def _init_neptune(self):
        """Initialize Neptune connection."""
        try:
            # Set environment variables for KnowledgeGraphManager
            os.environ['NEPTUNE_ENDPOINT'] = self.env.neptune_endpoint
            os.environ['NEPTUNE_PORT'] = self.env.neptune_port
            os.environ['AWS_REGION'] = self.env.aws_region
            
            self.kg_manager = KnowledgeGraphManager()
            logger.info("Neptune connection initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neptune connection: {e}")
            raise
    
    def store_rdf(self, rdf_content: str):
        """Store RDF content in Neptune."""
        logger.info("Storing RDF content in Neptune")
        
        try:
            # Use bulk insert for TTL content
            result = self.kg_manager.bulk_insert_ttl(rdf_content)
            
            if result:
                logger.info("Successfully stored RDF in Neptune")
            else:
                logger.warning("RDF storage may have failed - check Neptune logs")
                
        except Exception as e:
            logger.error(f"Failed to store RDF in Neptune: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test Neptune connection."""
        try:
            # Try a simple SPARQL query to test connectivity
            query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
            result = self.kg_manager.execute_sparql_query(query)
            
            if result:
                logger.info("Neptune connection test successful")
                return True
            else:
                logger.warning("Neptune connection test returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Neptune connection test failed: {e}")
            return False
    
    def get_triple_count(self) -> int:
        """Get total number of triples in Neptune."""
        try:
            query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
            result = self.kg_manager.execute_sparql_query(query)
            
            if result and len(result) > 0:
                count = result[0].get('count', {}).get('value', '0')
                return int(count)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Failed to get triple count: {e}")
            return 0
    
    def get_document_count(self) -> int:
        """Get number of documents in Neptune."""
        try:
            query = """
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            SELECT (COUNT(DISTINCT ?doc) as ?count) 
            WHERE { 
                ?doc a sgd:Document 
            }
            """
            result = self.kg_manager.execute_sparql_query(query)
            
            if result and len(result) > 0:
                count = result[0].get('count', {}).get('value', '0')
                return int(count)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0
    
    def get_neptune_stats(self) -> dict:
        """Get Neptune statistics."""
        try:
            return {
                'total_triples': self.get_triple_count(),
                'document_count': self.get_document_count(),
                'connection_status': self.test_connection()
            }
        except Exception as e:
            logger.error(f"Failed to get Neptune stats: {e}")
            return {
                'total_triples': 0,
                'document_count': 0,
                'connection_status': False
            }