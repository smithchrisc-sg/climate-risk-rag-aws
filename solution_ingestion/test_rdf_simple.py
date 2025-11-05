#!/usr/bin/env python3
"""
Simple RDF Generation Test
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from models.solution import Solution
from generators.rdf_generator import RDFGenerator

def create_test_solution():
    """Create a test solution for RDF generation"""
    solution = Solution(
        id="test123",
        source_file="test.csv",
        row_number=1,
        number="001",
        name="Test Climate Solution",
        country="Test Country",
        public_organisations="Test Public Org",
        international_organisations="Test Intl Org",
        private_organisations="Test Private Org",
        type_of_risk="Physical Risk",
        type_of_solution="Adaptation",
        ppp="Public",
        theme="Infrastructure",
        year_of_implementation="2024",
        description="This is a test climate solution for RDF generation",
        key_highlights="Key highlights of the solution",
        results="Positive results achieved",
        organization_sources="https://example.com/test-solution",
        other_sources="",
        contact_information="test@example.com",
        date_added="2024-01-01",
        last_updated="2024-01-01",
        most_recent_changes=""
    )
    
    # Add derived fields
    solution.doc_id = "sol_test123"
    solution.source_url = "https://example.com/test-solution"
    
    # Add pseudo-document text
    solution.pseudo_document_text = (
        "Climate Solution: Test Climate Solution\n\n"
        "This comprehensive climate solution addresses key environmental challenges "
        "through innovative approaches and sustainable practices. The solution "
        "demonstrates significant impact in reducing carbon emissions and "
        "promoting environmental sustainability."
    )
    
    return solution

def create_test_chunks(solution):
    """Create test chunks for the solution"""
    chunks = [
        {
            "chunk_id": f"{solution.doc_id}_desc",
            "text": "This is the description chunk containing the main overview of the climate solution.",
            "character_count": 95,
            "metadata": {"type": "description"}
        },
        {
            "chunk_id": f"{solution.doc_id}_highlights", 
            "text": "Key highlights include innovative technology, measurable impact, and scalable implementation.",
            "character_count": 98,
            "metadata": {"type": "highlights"}
        },
        {
            "chunk_id": f"{solution.doc_id}_results",
            "text": "Results show 30% reduction in emissions and positive environmental outcomes.",
            "character_count": 78,
            "metadata": {"type": "results"}
        }
    ]
    return chunks

def test_rdf_generation():
    """Test RDF generation with mock data"""
    
    print("Simple RDF Generation Test")
    print("=" * 50)
    
    # Create test data
    solution = create_test_solution()
    chunks = create_test_chunks(solution)
    
    print(f"Test solution: {solution.name}")
    print(f"Generated {len(chunks)} test chunks")
    
    # Generate RDF
    rdf_gen = RDFGenerator()
    rdf_output = rdf_gen.generate_document_rdf(solution, chunks)
    
    print(f"\nGenerated RDF:")
    print("-" * 40)
    print(rdf_output)
    
    # Save to file
    output_dir = Path("output_data/rdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rdf_file = output_dir / "test_simple.ttl"
    with open(rdf_file, 'w', encoding='utf-8') as f:
        f.write(rdf_output)
    
    print(f"\nRDF saved to: {rdf_file}")
    print(f"RDF length: {len(rdf_output)} characters")
    
    # Test batch generation
    print(f"\nTesting batch generation...")
    rdf_gen.clear_graph()
    
    # Create second test solution
    solution2 = create_test_solution()
    solution2.doc_id = "sol_test456"
    solution2.name = "Second Test Solution"
    chunks2 = create_test_chunks(solution2)
    
    batch_rdf = rdf_gen.generate_batch_rdf([(solution, chunks), (solution2, chunks2)])
    
    batch_file = output_dir / "test_batch.ttl"
    with open(batch_file, 'w', encoding='utf-8') as f:
        f.write(batch_rdf)
    
    print(f"Batch RDF saved to: {batch_file}")
    print(f"Batch RDF length: {len(batch_rdf)} characters")
    
    return rdf_output

if __name__ == "__main__":
    test_rdf_generation()
