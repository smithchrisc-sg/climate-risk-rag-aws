#!/usr/bin/env python3
"""
Test OpenSearch Keyword Indexing
Tests keyword indexing with a single pseudo-document.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from parsers.csv_parser import CSVParser
from generators.pseudo_document_generator import PseudoDocumentGenerator
from indexers.opensearch_keyword_indexer import OpenSearchKeywordIndexer
from config.environment import Environment

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_keyword_indexing():
    """Test keyword indexing with a single solution."""
    
    # Initialize components
    env = Environment()
    csv_parser = CSVParser()
    doc_generator = PseudoDocumentGenerator()
    keyword_indexer = OpenSearchKeywordIndexer(env)
    
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
    
    # Generate pseudo-document
    logger.info("Generating pseudo-document...")
    pseudo_doc = doc_generator.generate_pseudo_document(test_solution)
    
    logger.info(f"Generated pseudo-document: {len(pseudo_doc)} characters")
    logger.info(f"Preview: {pseudo_doc[:200]}...")
    
    # Test OpenSearch connection
    logger.info("Testing OpenSearch connection...")
    if not keyword_indexer.test_connection():
        logger.error("OpenSearch connection failed")
        return
    
    # Index the document
    logger.info("Indexing document in OpenSearch...")
    try:
        result = keyword_indexer.index_document(test_solution, pseudo_doc)
        if result:
            logger.info("✅ Document indexed successfully")
            
            # Wait for index refresh
            import time
            logger.info("Waiting for index refresh...")
            time.sleep(2)
            
            # Check what was indexed by retrieving the document
            try:
                doc_response = keyword_indexer.client.get(
                    index='documents_keyword',
                    id=test_solution.doc_id
                )
                indexed_doc = doc_response.get('_source', {})
                logger.info(f"Indexed document fields: {list(indexed_doc.keys())}")
                logger.info(f"Title: {indexed_doc.get('title', 'No title')}")
                logger.info(f"Full text length: {len(indexed_doc.get('full_text', ''))}")
            except Exception as e:
                logger.warning(f"Could not retrieve indexed document: {e}")
            
            # Test search with different terms
            search_terms = ["flood", "infrastructure", "mitigation", test_solution.name.split()[0].lower()]
            
            for term in search_terms:
                logger.info(f"Testing search for '{term}'...")
                search_results = keyword_indexer.search(term, limit=15)  # Increase limit
                logger.info(f"Search results for '{term}': {len(search_results)} documents found")
                
                if search_results:
                    for i, result in enumerate(search_results[:5]):  # Show first 5
                        content_type = result.get('content_type', 'unknown')
                        logger.info(f"  Result {i+1}: {result.get('title', 'No title')[:50]}... (score: {result.get('score', 0):.2f}, type: {content_type})")
                    break  # Found results, stop testing other terms
        else:
            logger.error("❌ Document indexing failed")
            
    except Exception as e:
        logger.error(f"❌ Indexing error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_keyword_indexing()
