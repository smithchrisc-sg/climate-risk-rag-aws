#!/usr/bin/env python3
"""
Bulk RDF generation test for all solutions from CSV file.
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

def test_bulk_rdf_generation():
    """Test RDF generation on all solutions from CSV file."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.chunk_generator import ChunkGenerator
        from generators.production_rdf_generator import ProductionRDFGenerator
        
        print("Bulk RDF Generation Test")
        print("=" * 50)
        
        # Parse all solutions from natural catastrophe file
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        print(f"Processing all solutions from {csv_file.name}...")
        solutions = list(parser.parse_csv_file(csv_file))
        
        if not solutions:
            print("No solutions found!")
            return False
        
        print(f"Found {len(solutions)} solutions to process")
        
        # First, find and test one with rich contact info
        print("\n1. Finding solution with rich contact information...")
        rich_contact_solution = None
        best_score = 0
        
        for solution in solutions[:50]:  # Check first 50
            if solution.contact_information and solution.contact_information.strip():
                contact_info = solution.contact_information
                score = contact_info.count("@") + contact_info.count("Contact Number:") + contact_info.count("Email:")
                if score > best_score:
                    best_score = score
                    rich_contact_solution = solution
        
        if rich_contact_solution:
            print(f"Found rich contact solution: {rich_contact_solution.name[:50]}... (score: {best_score})")
            
            # Test RDF generation on rich contact solution
            print("\n2. Testing RDF generation on rich contact solution...")
            pseudo_gen = StructuredPseudoDocumentGenerator()
            chunk_gen = ChunkGenerator()
            rdf_gen = ProductionRDFGenerator()
            
            # Process the rich contact solution
            processed = pseudo_gen.process_solutions([rich_contact_solution])
            solution = processed[0]
            chunks = chunk_gen.generate_chunks(solution)
            rdf_content = rdf_gen.generate_document_rdf(solution, chunks)
            
            # Show contact section
            print("\nContact Information Section:")
            print("-" * 30)
            lines = rdf_content.split('\n')
            in_contact_section = False
            for line in lines:
                if 'org:Organization' in line or 'schema:ContactPoint' in line:
                    in_contact_section = True
                if in_contact_section:
                    print(line)
                    if line.strip() == "" and in_contact_section:
                        break
        
        # Now process all solutions
        print(f"\n3. Processing all {len(solutions)} solutions...")
        
        pseudo_gen = StructuredPseudoDocumentGenerator()
        chunk_gen = ChunkGenerator()
        rdf_gen = ProductionRDFGenerator()
        
        # Generate pseudo documents for all
        print("   Generating pseudo documents...")
        processed_solutions = pseudo_gen.process_solutions(solutions)
        
        # Generate RDF for all solutions
        success_count = 0
        error_count = 0
        total_rdf_size = 0
        
        print("   Generating RDF and writing to data lake...")
        
        for i, solution in enumerate(processed_solutions):
            try:
                # Generate chunks and RDF
                chunks = chunk_gen.generate_chunks(solution)
                rdf_content = rdf_gen.generate_document_rdf(solution, chunks)
                
                # Write to data lake
                output_dir = Path("output_data/kr-dl-neptune-ttl/data-lake") / solution.doc_id
                output_dir.mkdir(parents=True, exist_ok=True)
                
                ttl_file = output_dir / f"{solution.doc_id}.ttl"
                with open(ttl_file, 'w', encoding='utf-8') as f:
                    f.write(rdf_content)
                
                total_rdf_size += len(rdf_content)
                success_count += 1
                
                # Show progress every 50 solutions
                if (i + 1) % 50 == 0:
                    print(f"   Processed {i + 1}/{len(processed_solutions)} solutions...")
                
            except Exception as e:
                logger.error(f"Failed to process solution {solution.id}: {e}")
                error_count += 1
        
        # Print summary
        print(f"\n" + "=" * 50)
        print("BULK RDF GENERATION SUMMARY")
        print("=" * 50)
        print(f"Total solutions processed: {len(processed_solutions)}")
        print(f"Successful RDF generations: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Success rate: {(success_count/len(processed_solutions)*100):.1f}%")
        print(f"Average RDF size: {total_rdf_size//success_count if success_count > 0 else 0} chars")
        print(f"Total RDF generated: {total_rdf_size:,} chars")
        
        # Show sample of generated files
        print(f"\nSample RDF files written to:")
        ttl_files = list(Path("output_data/kr-dl-neptune-ttl/data-lake").glob("*/sol_*.ttl"))
        for ttl_file in ttl_files[:5]:
            file_size = ttl_file.stat().st_size
            print(f"  {ttl_file}: {file_size} bytes")
        
        print(f"\n✅ Bulk RDF generation completed!")
        print(f"RDF files written to: output_data/kr-dl-neptune-ttl/data-lake/")
        
        return True
        
    except Exception as e:
        logger.error(f"Bulk RDF test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bulk_rdf_generation()
    if success:
        print("\n✅ Bulk RDF test completed successfully")
    else:
        print("\n❌ Bulk RDF test failed")
        sys.exit(1)
