#!/usr/bin/env python3
"""
Test Neptune loading with partial RDF content to identify size limits
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

def test_partial_load():
    """Test Neptune loading with partial RDF content."""
    
    # Initialize components
    env = Environment()
    
    # Set Neptune environment variables
    os.environ['NEPTUNE_ENDPOINT'] = env.neptune_endpoint
    os.environ['NEPTUNE_PORT'] = env.neptune_port
    os.environ['AWS_REGION'] = env.aws_region
    
    # Initialize KnowledgeGraphManager
    kg_manager = KnowledgeGraphManager()
    
    # Read the generated RDF file
    with open('debug_rdf_output.ttl', 'r') as f:
        full_rdf = f.read()
    
    logger.info(f"Full RDF size: {len(full_rdf)} characters")
    
    # Test with first half
    lines = full_rdf.split('\n')
    half_point = len(lines) // 2
    
    # Find a good break point (after a complete triple)
    for i in range(half_point, len(lines)):
        if lines[i].strip() == '' and i < len(lines) - 1:
            break_point = i
            break
    else:
        break_point = half_point
    
    partial_rdf = '\n'.join(lines[:break_point])
    
    logger.info(f"Testing partial RDF ({len(partial_rdf)} chars, {break_point} lines)...")
    
    try:
        result = kg_manager.bulk_insert_ttl(partial_rdf)
        if result:
            logger.info("✅ Partial RDF loaded successfully")
            
            # Now try the full RDF
            logger.info("Testing full RDF...")
            result2 = kg_manager.bulk_insert_ttl(full_rdf)
            if result2:
                logger.info("✅ Full RDF loaded successfully")
            else:
                logger.error("❌ Full RDF loading failed - size issue")
                
        else:
            logger.error("❌ Even partial RDF loading failed")
            
    except Exception as e:
        logger.error(f"❌ Exception during loading: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_partial_load()
