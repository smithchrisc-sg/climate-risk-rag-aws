#!/usr/bin/env python3
"""
Bulk test script for Structured Pseudo Document Generator
Processes all solutions from a CSV file to validate generation across all variations.
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

def test_bulk_pseudo_document_generation():
    """Test pseudo document generation on all solutions from a CSV file."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from utils.data_lake_writer import DataLakeWriter
        
        print("Bulk Structured Pseudo Document Generator Test")
        print("=" * 60)
        
        # Parse all solutions from natural catastrophe file
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        print(f"Processing all solutions from {csv_file.name}...")
        
        # Get all solutions from the file
        solutions = list(parser.parse_csv_file(csv_file))
        
        if not solutions:
            print("No solutions found!")
            return False
        
        print(f"Found {len(solutions)} solutions to process")
        
        # Generate pseudo documents for all solutions
        generator = StructuredPseudoDocumentGenerator()
        data_lake_writer = DataLakeWriter()
        
        print("Generating structured pseudo-documents...")
        processed_solutions = generator.process_solutions(solutions)
        
        # Write to data lake and collect stats
        success_count = 0
        error_count = 0
        stats = {
            'with_contact_info': 0,
            'with_ppp': 0,
            'countries': set(),
            'risk_types': set(),
            'themes': set(),
            'avg_length': 0,
            'total_length': 0
        }
        
        print("Writing to data lake and collecting statistics...")
        
        # Write all solutions to data lake at once
        data_lake_writer.write_solutions(processed_solutions)
        
        # Collect statistics
        success_count = 0
        error_count = 0
        stats = {
            'with_contact_info': 0,
            'with_ppp': 0,
            'countries': set(),
            'risk_types': set(),
            'themes': set(),
            'avg_length': 0,
            'total_length': 0
        }
        
        for i, solution in enumerate(processed_solutions):
            try:
                # Collect statistics
                stats['total_length'] += len(solution.pseudo_document_text)
                if solution.contact_information and solution.contact_information.strip():
                    stats['with_contact_info'] += 1
                if solution.ppp and solution.ppp.strip().lower() in ['yes', 'true', '1']:
                    stats['with_ppp'] += 1
                if solution.country:
                    stats['countries'].add(solution.country)
                if solution.type_of_risk:
                    stats['risk_types'].add(solution.type_of_risk)
                if solution.theme:
                    stats['themes'].add(solution.theme)
                
                success_count += 1
                
                # Show progress every 50 solutions
                if (i + 1) % 50 == 0:
                    print(f"Processed {i + 1}/{len(processed_solutions)} solutions...")
                
            except Exception as e:
                logger.error(f"Failed to process solution {solution.id}: {e}")
                error_count += 1
        
        # Calculate final stats
        stats['avg_length'] = stats['total_length'] // len(processed_solutions) if processed_solutions else 0
        
        # Print summary
        print(f"\n" + "=" * 60)
        print("BULK PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total solutions processed: {len(processed_solutions)}")
        print(f"Successful generations: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Success rate: {(success_count/len(processed_solutions)*100):.1f}%")
        
        print(f"\nCONTENT STATISTICS:")
        print(f"Solutions with contact info: {stats['with_contact_info']}")
        print(f"Solutions with PPP: {stats['with_ppp']}")
        print(f"Average document length: {stats['avg_length']} chars")
        print(f"Countries: {len(stats['countries'])} unique")
        print(f"Risk types: {len(stats['risk_types'])} unique")
        print(f"Themes: {len(stats['themes'])} unique")
        
        # Show sample of first few solutions
        print(f"\nSAMPLE OUTPUTS (first 3 solutions):")
        print("=" * 60)
        
        for i, solution in enumerate(processed_solutions[:3]):
            print(f"\n--- Solution {i+1}: {solution.name[:40]}... ---")
            print(f"Doc ID: {solution.doc_id}")
            print(f"Length: {len(solution.pseudo_document_text)} chars")
            print(f"Has contact: {'Yes' if solution.contact_information and solution.contact_information.strip() else 'No'}")
            
            # Show first few lines
            lines = solution.pseudo_document_text.split('\n')[:8]
            for j, line in enumerate(lines):
                if line.strip():
                    print(f"  {j+1}: {line[:70]}{'...' if len(line) > 70 else ''}")
        
        print(f"\n✅ Bulk processing completed successfully!")
        print(f"Data lake files written to: output_data/kr-dl-text/data-lake/")
        
        return True
        
    except Exception as e:
        logger.error(f"Bulk test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bulk_pseudo_document_generation()
    if success:
        print("\n✅ Bulk test completed successfully")
    else:
        print("\n❌ Bulk test failed")
        sys.exit(1)
