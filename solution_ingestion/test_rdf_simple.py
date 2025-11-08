#!/usr/bin/env python3
"""
Simple RDF generation test with better debug output
"""

import logging
import sys
import os
from pathlib import Path

# Set up path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "database_core_layer" / "python"))
sys.path.append(str(current_dir / "knowledge_graph_layer" / "python"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_rdf():
    """Simple RDF generation test."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.chunk_generator import ChunkGenerator
        from generators.rdf_generator import RDFGenerator
        
        print("Simple RDF Generation Test")
        print("=" * 50)
        
        # Get first solution with contact info
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        solution = None
        for i, sol in enumerate(parser.parse_csv_file(csv_file)):
            if sol.contact_information and sol.contact_information.strip():
                solution = sol
                print(f"Using solution: {solution.name[:50]}...")
                break
            if i >= 10:  # Just check first 10
                break
        
        if not solution:
            print("No solution with contact info found!")
            return False
        
        # Generate pseudo document
        print("\n1. Generating pseudo document...")
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed = pseudo_gen.process_solutions([solution])
        solution = processed[0]
        print(f"   Generated {len(solution.pseudo_document_text)} chars")
        
        # Generate chunks
        print("\n2. Generating chunks...")
        chunk_gen = ChunkGenerator()
        chunks = chunk_gen.generate_chunks(solution)
        print(f"   Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            chunk_id = getattr(chunk, 'chunk_id', f'chunk_{i}')
            text = getattr(chunk, 'text', '')[:50]
            print(f"   - {chunk_id}: {text}...")
        
        # Convert to dict format
        print("\n3. Converting chunks to dict format...")
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'chunk_id': getattr(chunk, 'chunk_id', ''),
                'text': getattr(chunk, 'text', ''),
                'chunk_index': getattr(chunk, 'chunk_index', 0),
                'character_count': len(getattr(chunk, 'text', '')),
                'section_type': getattr(chunk, 'section_type', 'section'),
            }
            chunk_dicts.append(chunk_dict)
        print(f"   Converted {len(chunk_dicts)} chunks")
        
        # Generate RDF
        print("\n4. Generating Production-Aligned RDF...")
        from generators.production_rdf_generator import ProductionRDFGenerator
        rdf_gen = ProductionRDFGenerator()
        try:
            rdf_content = rdf_gen.generate_document_rdf(solution, chunks)
            print(f"   Generated RDF: {len(rdf_content)} chars")
            
            # Show first part of RDF
            print("\n5. RDF Preview (first 2000 chars):")
            print("-" * 50)
            print(rdf_content[:2000])
            if len(rdf_content) > 2000:
                print("...")
            print("-" * 50)
            
        except Exception as e:
            print(f"   RDF generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Write to data lake
        print("\n6. Writing to data lake...")
        try:
            output_dir = Path("output_data/kr-dl-neptune-ttl/data-lake") / solution.doc_id
            output_dir.mkdir(parents=True, exist_ok=True)
            
            ttl_file = output_dir / f"{solution.doc_id}.ttl"
            with open(ttl_file, 'w', encoding='utf-8') as f:
                f.write(rdf_content)
            
            print(f"   Written to: {ttl_file}")
            print(f"   File size: {ttl_file.stat().st_size} bytes")
            
        except Exception as e:
            print(f"   Data lake writing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n✅ Simple RDF test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_rdf()
