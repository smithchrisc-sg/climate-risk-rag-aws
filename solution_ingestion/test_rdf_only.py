#!/usr/bin/env python3
"""
Simple test for IntegratedRDFChunkGenerator only
Tests RDF generation without indexing components
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_rdf_generation():
    """Test RDF generation with a few solutions from CSV."""
    
    # Import required modules
    from parsers.csv_parser import CSVParser
    from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
    
    # Initialize components
    csv_parser = CSVParser()
    rdf_generator = IntegratedRDFChunkGenerator()
    
    # Parse CSV file
    csv_file = "input_data/natural_catastrophe_26-Sep-2025.csv"
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        return
    
    logger.info(f"Parsing CSV file: {csv_file}")
    solutions = list(csv_parser.parse_csv_file(Path(csv_file)))
    
    # Test with first 3 solutions
    test_solutions = solutions[:3]
    logger.info(f"Testing with {len(test_solutions)} solutions")
    
    for i, solution in enumerate(test_solutions):
        logger.info(f"\n=== Processing Solution {i+1}: {solution.name[:50]}... ===")
        
        try:
            # Generate RDF and chunks
            rdf_content, chunks = rdf_generator.generate_document_rdf_and_chunks(solution)
            
            # Write RDF to file
            output_dir = Path("output_data/kr-dl-neptune-ttl/data-lake")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            rdf_file = output_dir / f"{solution.doc_id}.ttl"
            with open(rdf_file, 'w', encoding='utf-8') as f:
                f.write(rdf_content)
            
            logger.info(f"✅ Generated RDF: {len(rdf_content)} chars, {len(chunks)} chunks")
            logger.info(f"   Written to: {rdf_file}")
            
            # Show first few lines of RDF
            lines = rdf_content.split('\n')[:10]
            logger.info("   RDF Preview:")
            for line in lines:
                if line.strip():
                    logger.info(f"     {line}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process solution {solution.doc_id}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n✅ Test completed. Check output_data/kr-dl-neptune-ttl/data-lake/ for TTL files")

if __name__ == "__main__":
    test_rdf_generation()
