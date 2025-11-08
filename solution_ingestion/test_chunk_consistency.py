#!/usr/bin/env python3
"""
Test script to validate chunk ID consistency between RDF and chunk generators.
"""

import logging
import sys
import os
import re
from pathlib import Path

# Set up path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "database_core_layer" / "python"))
sys.path.append(str(current_dir / "knowledge_graph_layer" / "python"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chunk_id_consistency():
    """Test that chunk IDs match between RDF and chunk generators."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.production_chunk_generator import ProductionChunkGenerator
        from generators.production_rdf_generator import ProductionRDFGenerator
        
        print("Chunk ID Consistency Test")
        print("=" * 50)
        
        # Get a test solution
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        solutions = list(parser.parse_csv_file(csv_file))
        if not solutions:
            print("No solutions found!")
            return False
        
        test_solution = solutions[0]  # Use first solution
        
        print(f"Testing solution: {test_solution.name[:50]}...")
        print(f"Doc ID: {test_solution.doc_id}")
        
        # Generate pseudo document
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed = pseudo_gen.process_solutions([test_solution])
        solution = processed[0]
        
        # Generate chunks using production chunk generator
        print("\n1. Generating chunks with ProductionChunkGenerator...")
        chunk_gen = ProductionChunkGenerator()
        chunks = chunk_gen.generate_chunks(solution)
        
        print(f"Generated {len(chunks)} chunks:")
        chunk_ids_from_generator = []
        for chunk in chunks:
            print(f"  - {chunk.chunk_id}: {chunk.section_title} ({len(chunk.text)} chars)")
            chunk_ids_from_generator.append(chunk.chunk_id)
        
        # Generate RDF and extract chunk IDs
        print("\n2. Generating RDF with ProductionRDFGenerator...")
        rdf_gen = ProductionRDFGenerator()
        rdf_content = rdf_gen.generate_document_rdf(solution, chunks)
        
        # Extract paragraph chunk IDs from RDF
        print("\n3. Extracting paragraph chunk IDs from RDF...")
        chunk_ids_from_rdf = []
        
        # Find all paragraph chunk references in RDF
        paragraph_pattern = r'sg:Chunk_([^_]+_[^_]+)_(\d{4}) a sgd:Paragraph'
        matches = re.findall(paragraph_pattern, rdf_content)
        
        for doc_id_part, chunk_num in matches:
            chunk_id = f"{doc_id_part}_{chunk_num}"
            full_chunk_id = f"{solution.doc_id}_chunk_{chunk_num}"
            chunk_ids_from_rdf.append(full_chunk_id)
            print(f"  - Found in RDF: {full_chunk_id}")
        
        # Also extract from sgm:chunkId references
        chunk_id_pattern = r'sgm:chunkId "([^"]+)"'
        chunk_id_matches = re.findall(chunk_id_pattern, rdf_content)
        
        print(f"\n4. Found sgm:chunkId references:")
        for chunk_id_ref in chunk_id_matches:
            print(f"  - {chunk_id_ref}")
        
        # Compare the two sets
        print(f"\n5. Consistency Check:")
        print(f"Chunk IDs from generator: {sorted(chunk_ids_from_generator)}")
        print(f"Chunk IDs from RDF:       {sorted(chunk_ids_from_rdf)}")
        print(f"sgm:chunkId references:   {sorted(chunk_id_matches)}")
        
        # Check if they match
        generator_set = set(chunk_ids_from_generator)
        rdf_set = set(chunk_ids_from_rdf)
        sgm_set = set(chunk_id_matches)
        
        if generator_set == rdf_set == sgm_set:
            print("\n✅ SUCCESS: All chunk IDs are consistent!")
            print("   - Chunk generator IDs match RDF paragraph IDs")
            print("   - RDF sgm:chunkId references match chunk generator IDs")
        else:
            print("\n❌ INCONSISTENCY DETECTED:")
            if generator_set != rdf_set:
                print(f"   - Generator vs RDF mismatch:")
                print(f"     Only in generator: {generator_set - rdf_set}")
                print(f"     Only in RDF: {rdf_set - generator_set}")
            if generator_set != sgm_set:
                print(f"   - Generator vs sgm:chunkId mismatch:")
                print(f"     Only in generator: {generator_set - sgm_set}")
                print(f"     Only in sgm:chunkId: {sgm_set - generator_set}")
        
        # Show sample RDF structure
        print(f"\n6. Sample RDF Structure:")
        print("-" * 30)
        lines = rdf_content.split('\n')
        for i, line in enumerate(lines):
            if 'sgd:Paragraph' in line or 'sgm:chunkId' in line:
                # Show context around paragraph definitions
                start = max(0, i-2)
                end = min(len(lines), i+3)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{lines[j]}")
                print()
                break
        
        return generator_set == rdf_set == sgm_set
        
    except Exception as e:
        logger.error(f"Consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chunk_id_consistency()
    if success:
        print("\n✅ Chunk ID consistency test passed!")
    else:
        print("\n❌ Chunk ID consistency test failed!")
        sys.exit(1)
