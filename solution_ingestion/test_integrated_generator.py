#!/usr/bin/env python3
"""
Test script for the integrated RDF and chunk generator.
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

def test_integrated_generator():
    """Test the integrated RDF and chunk generator."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
        
        print("Integrated RDF and Chunk Generator Test")
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
        
        # Generate RDF and chunks simultaneously
        print("\n1. Generating RDF and chunks with IntegratedRDFChunkGenerator...")
        integrated_gen = IntegratedRDFChunkGenerator()
        rdf_content, chunks = integrated_gen.generate_document_rdf_and_chunks(solution)
        
        print(f"Generated RDF: {len(rdf_content)} chars")
        print(f"Generated chunks: {len(chunks)}")
        
        # Show chunk details
        print(f"\n2. Generated Chunks:")
        for chunk in chunks:
            print(f"  - {chunk.chunk_id}: {chunk.section_title} ({chunk.character_count} chars)")
            print(f"    File: {chunk.s3_key}")
        
        # Extract chunk IDs from RDF
        print(f"\n3. Chunk IDs in RDF:")
        chunk_id_pattern = r'sgm:chunkId "([^"]+)"'
        chunk_ids_in_rdf = re.findall(chunk_id_pattern, rdf_content)
        
        for chunk_id in chunk_ids_in_rdf:
            print(f"  - {chunk_id}")
        
        # Check consistency
        chunk_ids_from_generator = [chunk.chunk_id for chunk in chunks]
        
        print(f"\n4. Consistency Check:")
        print(f"Chunk IDs from generator: {sorted(chunk_ids_from_generator)}")
        print(f"Chunk IDs from RDF:       {sorted(chunk_ids_in_rdf)}")
        
        if set(chunk_ids_from_generator) == set(chunk_ids_in_rdf):
            print("\n✅ SUCCESS: Chunk IDs are perfectly consistent!")
        else:
            print("\n❌ INCONSISTENCY DETECTED:")
            generator_set = set(chunk_ids_from_generator)
            rdf_set = set(chunk_ids_in_rdf)
            print(f"   Only in generator: {generator_set - rdf_set}")
            print(f"   Only in RDF: {rdf_set - generator_set}")
        
        # Show RDF structure sample
        print(f"\n5. RDF Structure Sample:")
        print("-" * 30)
        lines = rdf_content.split('\n')
        for i, line in enumerate(lines[:25]):  # First 25 lines
            print(line)
        print("...")
        
        # Check chunk files were created
        print(f"\n6. Chunk Files Created:")
        chunk_dir = Path("output_data/kr-dl-chunks/data-lake") / solution.doc_id
        if chunk_dir.exists():
            chunk_files = list(chunk_dir.glob("*.json"))
            print(f"Found {len(chunk_files)} chunk files:")
            for chunk_file in chunk_files:
                file_size = chunk_file.stat().st_size
                print(f"  - {chunk_file.name}: {file_size} bytes")
        else:
            print("  No chunk files found!")
        
        # Write RDF to file
        print(f"\n7. Writing RDF to file...")
        rdf_dir = Path("output_data/kr-dl-neptune-ttl/data-lake") / solution.doc_id
        rdf_dir.mkdir(parents=True, exist_ok=True)
        rdf_file = rdf_dir / f"{solution.doc_id}.ttl"
        
        with open(rdf_file, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
        
        print(f"RDF written to: {rdf_file}")
        print(f"RDF file size: {rdf_file.stat().st_size} bytes")
        
        return set(chunk_ids_from_generator) == set(chunk_ids_in_rdf)
        
    except Exception as e:
        logger.error(f"Integrated generator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_integrated_generator()
    if success:
        print("\n✅ Integrated generator test passed!")
    else:
        print("\n❌ Integrated generator test failed!")
        sys.exit(1)
