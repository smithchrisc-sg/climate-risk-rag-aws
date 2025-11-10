#!/usr/bin/env python3
"""
Test Neptune RDF Loading
Tests RDF loading using production KnowledgeGraphManager utilities.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from parsers.csv_parser import CSVParser
from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
from knowledge_graph_layer.utils.KnowledgeGraphManager import KnowledgeGraphManager
from config.environment import Environment

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_neptune_loading():
    """Test Neptune RDF loading with a single solution's RDF."""
    
    # Initialize components
    env = Environment()
    csv_parser = CSVParser()
    rdf_generator = IntegratedRDFChunkGenerator()
    
    # Set Neptune environment variables for KnowledgeGraphManager
    os.environ['NEPTUNE_ENDPOINT'] = env.neptune_endpoint
    os.environ['NEPTUNE_PORT'] = env.neptune_port
    os.environ['AWS_REGION'] = env.aws_region
    
    logger.info(f"Neptune endpoint: {env.neptune_endpoint}:{env.neptune_port}")
    
    # Initialize KnowledgeGraphManager
    try:
        kg_manager = KnowledgeGraphManager()
        logger.info("✅ KnowledgeGraphManager initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize KnowledgeGraphManager: {e}")
        return
    
    # Parse single solution from CSV
    csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return
    
    logger.info(f"Parsing CSV file: {csv_file}")
    solutions = list(csv_parser.parse_csv_file(csv_file))
    
    # Test with first solution
    test_solution = solutions[0]
    logger.info(f"Testing with solution: {test_solution.name[:50]}...")
    
    # Generate RDF content
    logger.info("Generating RDF content...")
    rdf_content, chunks = rdf_generator.generate_document_rdf_and_chunks(test_solution)
    
    logger.info(f"Generated RDF: {len(rdf_content)} characters")
    logger.info(f"Generated chunks: {len(chunks)} chunks")
    
    # Show RDF preview
    lines = rdf_content.split('\n')[:15]
    logger.info("RDF Preview:")
    for line in lines:
        if line.strip():
            logger.info(f"  {line}")
    
    # Test Neptune connection using existing method
    logger.info("Testing Neptune connection...")
    try:
        health_status = kg_manager.get_health_status()
        if health_status.get('status') == 'healthy':
            logger.info("✅ Neptune connection successful")
        else:
            logger.warning(f"⚠️  Neptune health status: {health_status}")
    except Exception as e:
        logger.error(f"❌ Neptune connection error: {e}")
        # Try a simple SPARQL query as connection test
        try:
            logger.info("Trying simple SPARQL query as connection test...")
            count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o } LIMIT 1"
            result = kg_manager.execute_sparql_query(count_query)
            if result is not None:
                logger.info("✅ Neptune SPARQL connection working")
            else:
                logger.error("❌ Neptune SPARQL connection failed")
                return
        except Exception as e2:
            logger.error(f"❌ Neptune SPARQL connection failed: {e2}")
            return
    
    # Get current Neptune statistics using SPARQL
    logger.info("Getting Neptune statistics...")
    try:
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        result = kg_manager.execute_sparql_query(count_query)
        if result and len(result) > 0:
            total_triples = result[0].get('count', '0')
            logger.info(f"Current total triples in Neptune: {total_triples}")
        else:
            logger.warning("Could not get Neptune statistics")
    except Exception as e:
        logger.warning(f"Could not get Neptune stats: {e}")
    
    # Test SPARQL query capability
    logger.info("Testing SPARQL query capability...")
    try:
        # Simple count query
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        result = kg_manager.execute_sparql_query(count_query)
        
        if result and len(result) > 0:
            total_triples = result[0].get('count', '0')
            logger.info(f"Current total triples in Neptune: {total_triples}")
        else:
            logger.warning("SPARQL query returned no results")
            
    except Exception as e:
        logger.error(f"SPARQL query failed: {e}")
        return
    
    # Load RDF into Neptune
    logger.info("Loading RDF into Neptune...")
    try:
        # Use bulk_insert_ttl method from KnowledgeGraphManager
        load_result = kg_manager.bulk_insert_ttl(rdf_content)
        
        if load_result:
            logger.info("✅ RDF loaded successfully into Neptune")
            
            # Wait a moment for indexing
            import time
            logger.info("Waiting for Neptune indexing...")
            time.sleep(5)
            
            # Test if our data is queryable
            logger.info("Testing if loaded data is queryable...")
            
            # Query for our specific solution
            solution_query = f"""
            PREFIX sg: <http://solve.global/knowledge-commons/>
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            
            SELECT ?title ?identifier WHERE {{
                ?doc a sgd:Solution ;
                     dcterms:identifier "{test_solution.doc_id}" ;
                     dcterms:title ?title ;
                     dcterms:identifier ?identifier .
            }}
            """
            
            query_result = kg_manager.execute_sparql_query(solution_query)
            
            if query_result and len(query_result) > 0:
                # Handle the actual result format
                result_item = query_result[0]
                if isinstance(result_item, dict):
                    doc_title = result_item.get('title', 'Unknown')
                    doc_id = result_item.get('identifier', 'Unknown')
                else:
                    # If it's a string, log it for debugging
                    logger.info(f"Query result item type: {type(result_item)}")
                    logger.info(f"Query result item: {result_item}")
                    doc_title = str(result_item)
                    doc_id = "Unknown"
                    
                logger.info(f"✅ Successfully queried loaded solution:")
                logger.info(f"   Title: {doc_title}")
                logger.info(f"   ID: {doc_id}")
                
                # Query for chunks
                chunk_query = f"""
                PREFIX sg: <http://solve.global/knowledge-commons/>
                PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
                
                SELECT (COUNT(?chunk) as ?chunk_count) WHERE {{
                    sg:Document_{test_solution.doc_id} sgd:hasChild ?chunk .
                }}
                """
                
                chunk_result = kg_manager.execute_sparql_query(chunk_query)
                if chunk_result and len(chunk_result) > 0:
                    chunk_count = chunk_result[0].get('chunk_count', '0')
                    logger.info(f"   Chunks in Neptune: {chunk_count}")
                
            else:
                logger.warning("⚠️  Could not query loaded solution - may need more time for indexing")
                
        else:
            logger.error("❌ RDF loading failed")
            
    except Exception as e:
        logger.error(f"❌ RDF loading error: {e}")
        import traceback
        traceback.print_exc()
    
    # Final Neptune statistics
    logger.info("Getting final Neptune statistics...")
    try:
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        result = kg_manager.execute_sparql_query(count_query)
        if result and len(result) > 0:
            final_count = result[0].get('count', '0')
            logger.info(f"Final total triples in Neptune: {final_count}")
    except Exception as e:
        logger.warning(f"Could not get final Neptune stats: {e}")

if __name__ == "__main__":
    test_neptune_loading()
