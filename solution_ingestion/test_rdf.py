#!/usr/bin/env python3
"""
Test RDF Generation for Solution Documents
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from parsers.csv_parser import CSVParser
from generators.pseudo_document_generator import PseudoDocumentGenerator
from generators.chunk_generator import ChunkGenerator
from generators.rdf_generator import RDFGenerator

def test_rdf_generation():
    """Test RDF generation with sample solutions"""
    
    print("RDF Generation Test")
    print("=" * 50)
    
    # Parse solutions (limit to 2 for testing)
    parser = CSVParser()
    all_solutions = parser.parse_all_files()
    test_solutions = all_solutions[:2]
    
    print(f"Testing with {len(test_solutions)} solutions")
    
    # Generate pseudo-documents
    pseudo_gen = PseudoDocumentGenerator()
    for solution in test_solutions:
        pseudo_gen.generate_pseudo_document(solution)
    
    # Generate chunks
    chunk_gen = ChunkGenerator()
    solutions_with_chunks = []
    
    for solution in test_solutions:
        chunks = chunk_gen.generate_chunks(solution)
        solutions_with_chunks.append((solution, chunks))
        print(f"Generated {len(chunks)} chunks for {solution.doc_id}")
    
    # Generate RDF
    rdf_gen = RDFGenerator()
    
    # Test single document RDF
    solution, chunks = solutions_with_chunks[0]
    single_rdf = rdf_gen.generate_document_rdf(solution, chunks)
    
    print(f"\nSingle Document RDF for {solution.doc_id}:")
    print("-" * 40)
    print(single_rdf[:1000] + "..." if len(single_rdf) > 1000 else single_rdf)
    
    # Test batch RDF generation
    rdf_gen.clear_graph()
    batch_rdf = rdf_gen.generate_batch_rdf(solutions_with_chunks)
    
    print(f"\nBatch RDF Statistics:")
    print("-" * 40)
    print(f"Total RDF length: {len(batch_rdf)} characters")
    print(f"Documents processed: {len(solutions_with_chunks)}")
    
    # Save RDF to file for inspection
    output_dir = Path("output_data/rdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rdf_file = output_dir / "test_documents.ttl"
    with open(rdf_file, 'w', encoding='utf-8') as f:
        f.write(batch_rdf)
    
    print(f"RDF saved to: {rdf_file}")
    
    # Show sample triples
    print(f"\nSample RDF Triples:")
    print("-" * 40)
    lines = batch_rdf.split('\n')
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('@') and not line.startswith('#'):
            print(line)
            if i > 20:  # Show first 20 content lines
                break
    
    return batch_rdf

if __name__ == "__main__":
    test_rdf_generation()
