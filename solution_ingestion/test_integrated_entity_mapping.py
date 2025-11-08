#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Set up path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def test_integrated_mapping():
    """Test integrated entity mapping with natural catastrophe CSV."""
    
    try:
        from parsers.csv_parser import CSVParser
        from generators.production_rdf_generator import ProductionRDFGenerator
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        
        print("Integrated Entity Mapping Test")
        print("=" * 50)
        
        # Get test solution from CSV
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        solutions = list(parser.parse_csv_file(csv_file))
        if not solutions:
            print("No solutions found!")
            return
        
        test_solution = solutions[0]
        print(f"Testing solution: {test_solution.name[:50]}...")
        print(f"Public orgs: {test_solution.public_organisations}")
        print(f"Country: {test_solution.country}")
        print(f"Type of risk: {test_solution.type_of_risk}")
        print(f"Type of solution: {test_solution.type_of_solution}")
        
        # Generate pseudo document
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed = pseudo_gen.process_solutions([test_solution])
        solution = processed[0]
        
        # Generate chunks (mock for this test)
        chunks = []
        
        # Generate RDF with integrated mapping
        rdf_generator = ProductionRDFGenerator()
        rdf_output = rdf_generator.generate_document_rdf(solution, chunks)
        
        # Save output
        output_file = f"output_data/integrated_rdf_{solution.doc_id}.ttl"
        with open(output_file, 'w') as f:
            f.write(rdf_output)
        
        print(f"\nRDF saved to: {output_file}")
        print(f"RDF length: {len(rdf_output)} characters")
        
        # Show sample of RDF
        print("\nSample RDF output:")
        print("=" * 50)
        print(rdf_output[:1000])
        print("=" * 50)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integrated_mapping()
