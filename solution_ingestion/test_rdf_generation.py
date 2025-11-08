#!/usr/bin/env python3
"""
Test script for RDF Document Structure Generation
Finds solutions with rich contact information and generates production-aligned RDF.
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_solution_with_rich_contact_info():
    """Find a solution with rich contact information for RDF testing."""
    try:
        from parsers.csv_parser import CSVParser
        
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        print(f"Searching {csv_file.name} for solution with rich contact information...")
        
        # Look for specific solution or rich contact examples
        target_solutions = [
            "PUB's 2025 Drainage Upgrading Works",
            "Drainage Upgrading Works",
            "PUB"
        ]
        
        best_solution = None
        best_contact_score = 0
        
        if not csv_file.exists():
            print(f"CSV file not found: {csv_file}")
            return None
        
        for i, solution in enumerate(parser.parse_csv_file(csv_file)):
            if i >= 100:  # Check first 100 solutions
                break
            
            # Check for target solution names
            for target in target_solutions:
                if target.lower() in solution.name.lower():
                    print(f"Found target solution: {solution.name}")
                    return solution
            
            # Score contact information richness
            contact_score = 0
            if solution.contact_information and solution.contact_information.strip():
                contact_info = solution.contact_information
                # Count indicators of rich contact info
                contact_score += contact_info.count("@")  # Email addresses
                contact_score += contact_info.count("Organization:")  # Multiple orgs
                contact_score += contact_info.count("Email:")  # Email fields
                contact_score += contact_info.count("Contact Number:")  # Phone fields
                contact_score += len([c for c in contact_info if c.isdigit()]) // 10  # Phone numbers
                
                if contact_score > best_contact_score:
                    best_contact_score = contact_score
                    best_solution = solution
        
        if best_solution:
            print(f"Found solution with rich contact info (score: {best_contact_score}): {best_solution.name[:50]}...")
            return best_solution
        
        # Fallback to first solution with any contact info
        for solution in parser.parse_csv_file(csv_file):
            if solution.contact_information and solution.contact_information.strip():
                print(f"Using fallback solution: {solution.name[:50]}...")
                return solution
        
        return None
        
    except Exception as e:
        logger.error(f"Error finding solution: {e}")
        return None

def test_rdf_generation():
    """Test RDF generation on a solution with rich contact information."""
    try:
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.chunk_generator import ChunkGenerator
        from generators.rdf_generator import RDFGenerator
        
        print("RDF Document Structure Generation Test")
        print("=" * 60)
        
        # Find solution with rich contact info
        solution = find_solution_with_rich_contact_info()
        if not solution:
            print("No suitable solution found!")
            return False
        
        print(f"\n--- Testing Solution: {solution.name} ---")
        print(f"Country: {solution.country}")
        print(f"Type of Risk: {solution.type_of_risk}")
        print(f"Year: {solution.year_of_implementation}")
        print(f"Doc ID: {solution.doc_id}")
        print(f"Source URL: {solution.source_url}")
        
        # Show contact information
        if solution.contact_information:
            print(f"\nContact Information Preview:")
            contact_lines = solution.contact_information.split('\n')[:5]
            for line in contact_lines:
                if line.strip():
                    print(f"  {line.strip()}")
            if len(solution.contact_information.split('\n')) > 5:
                print("  ...")
        
        # Generate structured pseudo document
        print(f"\n--- Generating Structured Pseudo Document ---")
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed = pseudo_gen.process_solutions([solution])
        solution = processed[0]
        
        print(f"Generated pseudo document ({len(solution.pseudo_document_text)} chars)")
        
        # Generate hierarchical chunks
        print(f"\n--- Generating Hierarchical Chunks ---")
        chunk_gen = ChunkGenerator()
        chunks = chunk_gen.generate_chunks(solution)
        
        print(f"Generated {len(chunks)} chunks:")
        for chunk in chunks:
            # Handle Chunk objects properly
            chunk_id = getattr(chunk, 'chunk_id', 'unknown')
            text = getattr(chunk, 'text', '')
            print(f"  {chunk_id}: {text[:60]}...")
        
        # Convert chunks to dict format for RDF generator if needed
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                'chunk_id': getattr(chunk, 'chunk_id', ''),
                'text': getattr(chunk, 'text', ''),
                'chunk_index': getattr(chunk, 'chunk_index', 0),
                'character_count': getattr(chunk, 'character_count', 0),
                'section_type': getattr(chunk, 'section_type', ''),
            }
            chunk_dicts.append(chunk_dict)
        
        # Generate RDF
        print(f"\n--- Generating Document Structure RDF ---")
        rdf_gen = RDFGenerator()
        rdf_content = rdf_gen.generate_document_rdf(solution, chunk_dicts)
        
        print(f"Generated RDF ({len(rdf_content)} chars):")
        print("=" * 60)
        print(rdf_content)
        
        # Write to data lake
        print(f"\n--- Writing to Data Lake ---")
        from utils.data_lake_writer import DataLakeWriter
        writer = DataLakeWriter()
        
        # Write RDF to TTL file
        ttl_dir = writer.base_path / "kr-dl-neptune-ttl" / "data-lake" / solution.doc_id
        ttl_dir.mkdir(parents=True, exist_ok=True)
        ttl_file = ttl_dir / f"{solution.doc_id}.ttl"
        
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
        
        print(f"RDF written to: {ttl_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"RDF generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rdf_generation()
    if success:
        print("\n✅ RDF generation test completed successfully")
    else:
        print("\n❌ RDF generation test failed")
        sys.exit(1)
