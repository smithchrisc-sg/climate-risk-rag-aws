#!/usr/bin/env python3
"""
Test simple Neptune RDF loading with minimal content
"""

import sys
import os
import logging

# Add current directory to path
sys.path.append('.')

from knowledge_graph_layer.utils.KnowledgeGraphManager import KnowledgeGraphManager
from config.environment import Environment

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_simple_load():
    """Test Neptune loading with minimal RDF."""
    
    # Initialize components
    env = Environment()
    
    # Set Neptune environment variables
    os.environ['NEPTUNE_ENDPOINT'] = env.neptune_endpoint
    os.environ['NEPTUNE_PORT'] = env.neptune_port
    os.environ['AWS_REGION'] = env.aws_region
    
    # Initialize KnowledgeGraphManager
    kg_manager = KnowledgeGraphManager()
    
    # Test with minimal RDF
    minimal_rdf = """@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix sg: <http://solve.global/knowledge-commons/> .

sg:TestDocument_001 a sg:Document ;
    dcterms:title "Test Document" ;
    dcterms:identifier "test_001" .
"""
    
    logger.info("Testing minimal RDF load...")
    logger.info(f"RDF content:\n{minimal_rdf}")
    
    try:
        result = kg_manager.bulk_insert_ttl(minimal_rdf)
        if result:
            logger.info("✅ Minimal RDF loaded successfully")
            
            # Query it back
            query = """
            PREFIX sg: <http://solve.global/knowledge-commons/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            
            SELECT ?title WHERE {
                sg:TestDocument_001 dcterms:title ?title .
            }
            """
            
            query_result = kg_manager.execute_sparql_query(query)
            if query_result:
                logger.info(f"✅ Query successful: {query_result}")
            else:
                logger.warning("⚠️ Query returned no results")
                
        else:
            logger.error("❌ Minimal RDF loading failed")
            
    except Exception as e:
        logger.error(f"❌ Exception during loading: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_load()
