#!/usr/bin/env python3
"""
Simple SPARQL query testing for Neptune
Run interactive SPARQL queries from EC2 where Neptune connectivity works.
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

def run_sparql_query(query):
    """Execute a SPARQL query and return results."""
    try:
        result = kg_manager.execute_sparql_query(query)
        return result
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return None

def main():
    """Interactive SPARQL query testing."""
    global kg_manager
    
    # Initialize components
    env = Environment()
    
    # Set Neptune environment variables
    os.environ['NEPTUNE_ENDPOINT'] = env.neptune_endpoint
    os.environ['NEPTUNE_PORT'] = env.neptune_port
    os.environ['AWS_REGION'] = env.aws_region
    
    logger.info(f"Neptune endpoint: {env.neptune_endpoint}:{env.neptune_port}")
    
    # Initialize KnowledgeGraphManager
    try:
        kg_manager = KnowledgeGraphManager()
        logger.info("✅ KnowledgeGraphManager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize KnowledgeGraphManager: {e}")
        return
    
    # Test connection
    logger.info("Testing Neptune connection...")
    count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o } LIMIT 1"
    result = run_sparql_query(count_query)
    
    if result:
        logger.info("✅ Neptune connection working")
        total_triples = result[0].get('count', '0')
        logger.info(f"Total triples in Neptune: {total_triples}")
    else:
        logger.error("❌ Neptune connection failed")
        return
    
    # Predefined useful queries
    queries = {
        "1": ("Count all triples", "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"),
        "2": ("List document types", """
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            SELECT DISTINCT ?type (COUNT(?doc) as ?count) WHERE {
                ?doc a ?type .
                FILTER(STRSTARTS(STR(?type), "http://solve.global/knowledge-commons/document-structure#"))
            } GROUP BY ?type ORDER BY DESC(?count)
        """),
        "3": ("Recent solutions", """
            PREFIX sg: <http://solve.global/knowledge-commons/>
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT ?doc ?title ?id WHERE {
                ?doc a sgd:Solution ;
                     dcterms:title ?title ;
                     dcterms:identifier ?id .
            } LIMIT 10
        """),
        "4": ("Count chunks", """
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            SELECT (COUNT(?chunk) as ?chunk_count) WHERE {
                ?chunk a sgd:Chunk .
            }
        """),
        "5": ("Organizations", """
            PREFIX sg: <http://solve.global/knowledge-commons/>
            SELECT DISTINCT ?org WHERE {
                ?doc sg:associatedOrganization ?org .
            } LIMIT 10
        """)
    }
    
    print("\n=== Neptune SPARQL Query Testing ===")
    print("Available queries:")
    for key, (desc, _) in queries.items():
        print(f"  {key}: {desc}")
    print("  c: Custom query")
    print("  q: Quit")
    
    while True:
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'c':
            print("Enter SPARQL query (end with empty line):")
            query_lines = []
            while True:
                line = input().strip()
                if line == "":
                    break
                query_lines.append(line)
            
            custom_query = " ".join(query_lines)
            if custom_query:
                print(f"\nExecuting: {custom_query}")
                result = run_sparql_query(custom_query)
                if result:
                    print(f"Results ({len(result)} rows):")
                    for i, row in enumerate(result[:10]):  # Show first 10 results
                        print(f"  {i+1}: {row}")
                    if len(result) > 10:
                        print(f"  ... and {len(result)-10} more rows")
        elif choice in queries:
            desc, query = queries[choice]
            print(f"\nExecuting: {desc}")
            print(f"Query: {query}")
            result = run_sparql_query(query)
            if result:
                print(f"Results ({len(result)} rows):")
                for i, row in enumerate(result):
                    print(f"  {i+1}: {row}")
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
