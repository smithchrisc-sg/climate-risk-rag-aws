#!/usr/bin/env python3
"""
Test script to find solutions with multiple paragraphs and validate dynamic numbering.
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

def find_multi_paragraph_solutions():
    """Find solutions with multiple paragraphs in sections."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        
        print("Multi-Paragraph Solution Finder")
        print("=" * 50)
        
        # Parse solutions
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        solutions = list(parser.parse_csv_file(csv_file))
        if not solutions:
            print("No solutions found!")
            return []
        
        print(f"Scanning {len(solutions)} solutions for multi-paragraph content...")
        
        # Generate pseudo documents and analyze
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed_solutions = pseudo_gen.process_solutions(solutions)
        
        multi_para_solutions = []
        
        for solution in processed_solutions:
            para_counts = {}
            
            # Check each section for multiple paragraphs
            sections = [
                ('Description', solution.description),
                ('Key Highlights', solution.key_highlights),
                ('Results', solution.results)
            ]
            
            for section_name, content in sections:
                if content and content.strip():
                    # Split by any newline character to find paragraphs
                    paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
                    para_counts[section_name] = len(paragraphs)
            
            # Check if any section has multiple paragraphs
            max_paras = max(para_counts.values()) if para_counts else 0
            total_paras = sum(para_counts.values())
            
            if max_paras > 1 or total_paras > 3:  # More than simple 1 para per section
                multi_para_solutions.append((solution, para_counts, max_paras, total_paras))
        
        # Sort by most paragraphs first
        multi_para_solutions.sort(key=lambda x: x[3], reverse=True)
        
        print(f"\nFound {len(multi_para_solutions)} solutions with multiple paragraphs:")
        print("-" * 60)
        
        for i, (solution, para_counts, max_paras, total_paras) in enumerate(multi_para_solutions[:10]):
            print(f"{i+1}. {solution.name[:50]}...")
            print(f"   Doc ID: {solution.doc_id}")
            print(f"   Paragraph counts: {para_counts}")
            print(f"   Max in section: {max_paras}, Total: {total_paras}")
            print()
        
        return multi_para_solutions[:3]  # Return top 3 for testing
        
    except Exception as e:
        logger.error(f"Multi-paragraph finder failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_multi_paragraph_solution(solution, para_counts):
    """Test a specific solution with multiple paragraphs."""
    try:
        from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
        
        print(f"\n" + "=" * 60)
        print(f"TESTING: {solution.name[:50]}...")
        print(f"Expected paragraph structure: {para_counts}")
        print("=" * 60)
        
        # Generate RDF and chunks
        integrated_gen = IntegratedRDFChunkGenerator()
        rdf_content, chunks = integrated_gen.generate_document_rdf_and_chunks(solution)
        
        print(f"\nGenerated {len(chunks)} chunks:")
        
        # Analyze chunk structure
        section_structure = {}
        for chunk in chunks:
            section = chunk.section_title
            if section not in section_structure:
                section_structure[section] = []
            section_structure[section].append((chunk.chunk_number, chunk.chunk_id))
        
        # Show structure
        for section, chunk_list in section_structure.items():
            chunk_list.sort()  # Sort by chunk number
            print(f"\n{section} Section:")
            for chunk_num, chunk_id in chunk_list:
                print(f"  - Chunk {chunk_num:04d}: {chunk_id}")
        
        # Validate sequential numbering
        all_chunk_nums = [chunk.chunk_number for chunk in chunks]
        all_chunk_nums.sort()
        
        print(f"\nChunk numbering sequence: {all_chunk_nums}")
        
        # Calculate expected sequence based on section structure
        # Sections take odd numbers, paragraphs take subsequent numbers
        expected_nums = []
        current_num = 1
        for section_name, chunk_list in section_structure.items():
            current_num += 1  # Skip section number
            for _ in chunk_list:
                expected_nums.append(current_num)
                current_num += 1
        
        expected_nums.sort()
        if all_chunk_nums == expected_nums:
            print("✅ Sequential numbering is correct!")
        else:
            print(f"❌ Sequential numbering issue!")
            print(f"   Expected: {expected_nums}")
            print(f"   Actual:   {all_chunk_nums}")
        
        # Show RDF structure for sections
        print(f"\nRDF Section Structure:")
        section_pattern = r'sg:Chunk_([^_]+_[^_]+)_(\d{4}) a sgd:Section'
        section_matches = re.findall(section_pattern, rdf_content)
        
        for doc_id_part, section_num in section_matches:
            print(f"  - Section {section_num}: sg:Chunk_{doc_id_part}_{section_num}")
        
        # Show paragraph structure in RDF
        print(f"\nRDF Paragraph Structure:")
        para_pattern = r'sg:Chunk_([^_]+_[^_]+)_(\d{4}) a sgd:Paragraph'
        para_matches = re.findall(para_pattern, rdf_content)
        
        for doc_id_part, para_num in para_matches:
            print(f"  - Paragraph {para_num}: sg:Chunk_{doc_id_part}_{para_num}")
        
        return len(section_matches) > 0 and len(para_matches) == len(chunks)
        
    except Exception as e:
        logger.error(f"Multi-paragraph test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("Multi-Paragraph Dynamic Numbering Test")
    print("=" * 50)
    
    # Find solutions with multiple paragraphs
    multi_para_solutions = find_multi_paragraph_solutions()
    
    if not multi_para_solutions:
        print("No multi-paragraph solutions found!")
        return False
    
    # Test the top solutions
    success_count = 0
    for solution, para_counts, max_paras, total_paras in multi_para_solutions:
        success = test_multi_paragraph_solution(solution, para_counts)
        if success:
            success_count += 1
    
    print(f"\n" + "=" * 60)
    print(f"SUMMARY: {success_count}/{len(multi_para_solutions)} tests passed")
    
    if success_count == len(multi_para_solutions):
        print("✅ All multi-paragraph tests passed!")
        return True
    else:
        print("❌ Some multi-paragraph tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Multi-paragraph dynamic numbering test completed successfully!")
    else:
        print("\n❌ Multi-paragraph dynamic numbering test failed!")
        sys.exit(1)
