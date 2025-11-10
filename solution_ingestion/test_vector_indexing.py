#!/usr/bin/env python3
"""
Test OpenSearch Vector Indexing
Tests vector indexing with chunks and embeddings.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from parsers.csv_parser import CSVParser
from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
from generators.embeddings_generator import EmbeddingsGenerator
from indexers.opensearch_vector_indexer import OpenSearchVectorIndexer
from config.environment import Environment

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_vector_indexing():
    """Test vector indexing with a single solution's chunks."""
    
    # Initialize components
    env = Environment()
    csv_parser = CSVParser()
    rdf_generator = IntegratedRDFChunkGenerator()
    embeddings_generator = EmbeddingsGenerator()
    vector_indexer = OpenSearchVectorIndexer(env)
    
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
    
    # Generate RDF and chunks
    logger.info("Generating RDF and chunks...")
    rdf_content, chunks = rdf_generator.generate_document_rdf_and_chunks(test_solution)
    
    logger.info(f"Generated {len(chunks)} chunks")
    for i, chunk in enumerate(chunks[:3]):
        logger.info(f"  Chunk {i+1}: {chunk.text[:100]}...")
    
    # Generate embeddings
    logger.info("Generating embeddings...")
    chunk_dicts = [chunk.__dict__ for chunk in chunks]
    enriched_chunks = embeddings_generator.process_chunks(chunk_dicts)
    
    logger.info(f"Generated embeddings for {len(enriched_chunks)} chunks")
    logger.info(f"Embedding dimension: {len(enriched_chunks[0]['embedding'])}")
    
    # Test OpenSearch vector connection
    logger.info("Testing OpenSearch vector connection...")
    if not vector_indexer.test_connection():
        logger.error("OpenSearch vector connection failed")
        return
    
    # Check current vector index stats
    logger.info("Checking vector index statistics...")
    try:
        stats = vector_indexer.get_index_stats()
        logger.info(f"Current vector index contains {stats.get('doc_count', 0)} chunks")
    except Exception as e:
        logger.warning(f"Could not get index stats: {e}")
    
    # Index the chunks
    logger.info("Indexing chunks in OpenSearch vector index...")
    try:
        success_count = vector_indexer.index_chunks(enriched_chunks)
        logger.info(f"✅ Successfully indexed {success_count}/{len(enriched_chunks)} chunks")
        
        # Wait for index refresh
        import time
        logger.info("Waiting for index refresh...")
        time.sleep(3)
        
        # Test vector search with the first chunk's text
        test_query = enriched_chunks[0]['text'][:200]  # First 200 chars
        logger.info(f"Testing vector search with query: '{test_query[:100]}...'")
        
        search_results = vector_indexer.search_similar(test_query, limit=10)
        logger.info(f"Vector search results: {len(search_results)} chunks found")
        
        # Analyze results by content type
        content_type_counts = {}
        for i, result in enumerate(search_results[:5]):
            content_type = result.get('content_type', 'unknown')
            content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
            
            logger.info(f"  Result {i+1}: {result.get('text', 'No text')[:80]}... "
                       f"(score: {result.get('score', 0):.3f}, type: {content_type})")
        
        logger.info(f"Results by content type: {content_type_counts}")
        
        # Test search for solution-specific content
        logger.info("Testing search for solution-specific terms...")
        solution_terms = ["flood mitigation", "infrastructure", "NFMIP"]
        
        for term in solution_terms:
            logger.info(f"Searching for '{term}'...")
            term_results = vector_indexer.search_similar(term, limit=5)
            logger.info(f"  Found {len(term_results)} results for '{term}'")
            
            # Show content types in results
            term_types = {}
            for result in term_results:
                content_type = result.get('content_type', 'unknown')
                term_types[content_type] = term_types.get(content_type, 0) + 1
            
            if term_types:
                logger.info(f"  Content types: {term_types}")
                
                # Show if our solution chunks appear in results
                solution_chunks = [r for r in term_results if r.get('content_type') == 'solution']
                if solution_chunks:
                    logger.info(f"  ✅ Found {len(solution_chunks)} solution chunks in results")
                else:
                    logger.info(f"  ⚠️  No solution chunks in top results")
        
    except Exception as e:
        logger.error(f"❌ Vector indexing error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vector_indexing()
