#!/usr/bin/env python3
"""
Bulk test script to process the full natural catastrophe CSV file.
Creates pseudo documents, chunks, and RDF for all solutions.
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Set up path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "database_core_layer" / "python"))
sys.path.append(str(current_dir / "knowledge_graph_layer" / "python"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_full_csv():
    """Process the full natural catastrophe CSV file."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
        integrated_gen = IntegratedRDFChunkGenerator()
        
        print("Bulk Processing: Natural Catastrophe Solutions")
        print("=" * 60)
        
        # Parse all solutions
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        print(f"Parsing CSV file: {csv_file}")
        solutions = list(parser.parse_csv_file(csv_file))
        
        if not solutions:
            print("No solutions found!")
            return False
        
        print(f"Found {len(solutions)} solutions to process")
        
        # Generate pseudo documents
        print("\n1. Generating structured pseudo documents...")
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed_solutions = pseudo_gen.process_solutions(solutions)
        
        # Write pseudo document files
        pseudo_output_dir = Path("output_data/kr-dl-text/data-lake")
        pseudo_output_dir.mkdir(parents=True, exist_ok=True)
        
        for solution in processed_solutions:
            solution_pseudo_dir = pseudo_output_dir / solution.doc_id
            solution_pseudo_dir.mkdir(parents=True, exist_ok=True)
            pseudo_file = solution_pseudo_dir / f"{solution.doc_id}.txt"
            
            with open(pseudo_file, 'w', encoding='utf-8') as f:
                f.write(solution.pseudo_document_text)
        
        print(f"Generated {len(processed_solutions)} pseudo documents")
        
        # Process with integrated generator
        print("\n2. Generating RDF and chunks for all solutions...")
        integrated_gen = IntegratedRDFChunkGenerator()

        total_chunks = 0
        total_rdf_size = 0
        rdf_output_dir = Path("output_data/kr-dl-neptune-ttl/data-lake")
        rdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, solution in enumerate(processed_solutions, 1):
            print(f"Processing {i}/{len(processed_solutions)}: {solution.name[:50]}...")
            
            # Generate RDF and chunks
            rdf_content, chunks = integrated_gen.generate_document_rdf_and_chunks(solution)
            
            # Write RDF file
            solution_rdf_dir = rdf_output_dir / solution.doc_id
            solution_rdf_dir.mkdir(parents=True, exist_ok=True)
            rdf_file = solution_rdf_dir / f"{solution.doc_id}.ttl"
            
            with open(rdf_file, 'w', encoding='utf-8') as f:
                f.write(rdf_content)
            
            total_chunks += len(chunks)
            total_rdf_size += len(rdf_content)
            
            if i % 10 == 0:  # Progress update every 10 solutions
                print(f"  Progress: {i}/{len(processed_solutions)} solutions processed")
        
        print(f"\n3. Processing Summary:")
        print(f"   Solutions processed: {len(processed_solutions)}")
        print(f"   Total chunks created: {total_chunks}")
        print(f"   Total RDF size: {total_rdf_size:,} characters")
        print(f"   Average chunks per solution: {total_chunks / len(processed_solutions):.1f}")
        
        # Validate output directories
        print(f"\n4. Output Validation:")
        
        # Check pseudo document files
        pseudo_dir = Path("output_data/kr-dl-text/data-lake")
        if pseudo_dir.exists():
            pseudo_subdirs = [d for d in pseudo_dir.iterdir() if d.is_dir()]
            total_pseudo_files = sum(len(list(d.glob("*.txt"))) for d in pseudo_subdirs)
            print(f"   Pseudo doc directories: {len(pseudo_subdirs)}")
            print(f"   Pseudo doc TXT files: {total_pseudo_files}")
        else:
            print("   ❌ Pseudo document directory not found!")
            return False
        
        # Check chunk files
        chunk_dir = Path("output_data/kr-dl-chunks/data-lake")
        if chunk_dir.exists():
            chunk_subdirs = [d for d in chunk_dir.iterdir() if d.is_dir()]
            total_chunk_files = sum(len(list(d.glob("*.json"))) for d in chunk_subdirs)
            print(f"   Chunk directories: {len(chunk_subdirs)}")
            print(f"   Chunk JSON files: {total_chunk_files}")
        else:
            print("   ❌ Chunk directory not found!")
            return False
        
        # Check RDF files
        if rdf_output_dir.exists():
            rdf_subdirs = [d for d in rdf_output_dir.iterdir() if d.is_dir()]
            total_rdf_files = sum(len(list(d.glob("*.ttl"))) for d in rdf_subdirs)
            print(f"   RDF directories: {len(rdf_subdirs)}")
            print(f"   RDF TTL files: {total_rdf_files}")
        else:
            print("   ❌ RDF directory not found!")
            return False
        
        # Validate consistency
        if len(pseudo_subdirs) == len(chunk_subdirs) == len(rdf_subdirs) == len(processed_solutions):
            print("   ✅ Directory structure consistent")
        else:
            print(f"   ❌ Directory mismatch: pseudo={len(pseudo_subdirs)}, chunks={len(chunk_subdirs)}, rdf={len(rdf_subdirs)}, solutions={len(processed_solutions)}")
            return False
        
        if total_pseudo_files == len(processed_solutions):
            print("   ✅ Pseudo document file count matches solutions")
        else:
            print(f"   ❌ Pseudo document file mismatch: files={total_pseudo_files}, solutions={len(processed_solutions)}")
            return False
        
        if total_chunk_files == total_chunks:
            print("   ✅ Chunk file count matches generated chunks")
        else:
            print(f"   ❌ Chunk file mismatch: files={total_chunk_files}, generated={total_chunks}")
            return False
        
        if total_rdf_files == len(processed_solutions):
            print("   ✅ RDF file count matches solutions")
        else:
            print(f"   ❌ RDF file mismatch: files={total_rdf_files}, solutions={len(processed_solutions)}")
            return False
        
        print(f"\n✅ Bulk processing completed successfully!")
        print(f"   Ready for embeddings generation with {total_chunks} chunks")
        
        return True
        
    except Exception as e:
        logger.error(f"Bulk processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"Started at: {start_time}")
    
    success = process_full_csv()
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"Completed at: {end_time}")
    print(f"Duration: {duration}")
    
    if success:
        print("\n✅ Bulk processing test completed successfully!")
    else:
        print("\n❌ Bulk processing test failed!")
        sys.exit(1)
