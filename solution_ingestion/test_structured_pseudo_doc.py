#!/usr/bin/env python3
"""
Test script for Structured Pseudo Document Generator
Run this on EC2 instance with VPC connectivity.
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

def test_structured_pseudo_document():
    """Test the structured pseudo document generator."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from pathlib import Path
        
        print("Structured Pseudo Document Generator Test")
        print("=" * 60)
        
        # Parse multiple CSV files to find good contact info
        parser = CSVParser()
        csv_files = [
            "input_data/natural_catastrophe_26-Sep-2025.csv",
            "input_data/health_26-Sep-2025.csv",
            "input_data/retirement_original.csv"
        ]
        
        print("Searching for solution with complete contact information...")
        
        # Search across files for solution with good contact info
        test_solution = None
        for csv_file in csv_files:
            csv_path = Path(csv_file)
            if not csv_path.exists():
                print(f"Skipping {csv_file} (not found)")
                continue
                
            print(f"Checking {csv_path.name}...")
            
            # Check first 10 solutions from each file
            for i, solution in enumerate(parser.parse_csv_file(csv_path)):
                if i >= 10:  # Limit per file
                    break
                    
                # Look for contact info with actual email or phone
                if (solution.contact_information and solution.contact_information.strip() and
                    ("@" in solution.contact_information or 
                     any(char.isdigit() for char in solution.contact_information))):
                    test_solution = solution
                    print(f"Found solution with contact details: {solution.name[:50]}...")
                    break
            
            if test_solution:
                break
        
        # If no solution with good contact info, use first from natural_catastrophe
        if not test_solution:
            csv_path = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
            solutions = list(parser.parse_csv_file(csv_path))
            if solutions:
                test_solution = solutions[0]
                print(f"No solutions with complete contact info found, using: {test_solution.name[:50]}...")
        
        if not test_solution:
            print("No solutions found!")
            return
        
        # Test with selected solution
        generator = StructuredPseudoDocumentGenerator()
        
        print(f"\n--- Testing Solution: {test_solution.name[:50]}... ---")
        print(f"Country: {test_solution.country}")
        print(f"Type of Risk: {test_solution.type_of_risk}")
        print(f"PPP: {test_solution.ppp}")
        print(f"Year: {test_solution.year_of_implementation}")
        print(f"Theme: {test_solution.theme}")
        print(f"Has Contact Info: {'Yes' if test_solution.contact_information and test_solution.contact_information.strip() else 'No'}")
        
        # Generate structured pseudo-document
        processed = generator.process_solutions([test_solution])
        solution = processed[0]
        
        print(f"\nGenerated doc_id: {solution.doc_id}")
        print(f"Source URL: {solution.source_url}")
        
        print(f"\nStructured Pseudo-Document ({len(solution.pseudo_document_text)} chars):")
        print("=" * 60)
        print(solution.pseudo_document_text)
        
        # Compare with target example structure
        print(f"\n" + "=" * 60)
        print("STRUCTURE ANALYSIS:")
        print("=" * 60)
        
        lines = solution.pseudo_document_text.split('\n')
        for i, line in enumerate(lines[:25]):  # Show more lines to see contact info
            if line.strip():
                print(f"Line {i+1:2d}: {line[:80]}{'...' if len(line) > 80 else ''}")
        
        if len(lines) > 25:
            print(f"... ({len(lines) - 25} more lines)")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_structured_pseudo_document()
    if success:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed")
        sys.exit(1)
