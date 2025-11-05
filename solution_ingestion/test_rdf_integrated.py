#!/usr/bin/env python3
"""
Integrated RDF Generation Test with Real Solution Data
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from generators.rdf_generator import RDFGenerator

def test_with_existing_chunks():
    """Test RDF generation with existing chunk data"""
    
    print("Integrated RDF Generation Test")
    print("=" * 50)
    
    # Load existing chunk data
    chunks_dir = Path("output_data/kr-dl-chunks/data-lake")
    text_dir = Path("output_data/kr-dl-text/data-lake")
    
    if not chunks_dir.exists() or not text_dir.exists():
        print("No existing chunk data found. Run test_chunks.py first.")
        return
    
    # Find chunk files
    chunk_files = list(chunks_dir.glob("*.json"))
    text_files = list(text_dir.glob("*.json"))
    
    print(f"Found {len(chunk_files)} chunk files")
    print(f"Found {len(text_files)} text files")
    
    if not chunk_files:
        print("No chunk files found. Run test_chunks.py first.")
        return
    
    # Load and process data
    rdf_gen = RDFGenerator()
    solutions_processed = set()
    
    # Group chunks by document
    doc_chunks = {}
    for chunk_file in chunk_files:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            chunk_data = json.load(f)
        
        doc_id = chunk_data['doc_id']
        if doc_id not in doc_chunks:
            doc_chunks[doc_id] = []
        doc_chunks[doc_id].append(chunk_data)
    
    # Load corresponding text documents
    doc_texts = {}
    for text_file in text_files:
        with open(text_file, 'r', encoding='utf-8') as f:
            text_data = json.load(f)
        
        doc_id = text_data['doc_id']
        doc_texts[doc_id] = text_data
    
    print(f"Processing {len(doc_chunks)} documents")
    
    # Generate RDF for each document
    for doc_id, chunks in doc_chunks.items():
        if doc_id in doc_texts:
            text_data = doc_texts[doc_id]
            
            # Create mock solution object from text data
            mock_solution = create_mock_solution_from_data(text_data)
            
            # Generate RDF
            rdf_output = rdf_gen.generate_document_rdf(mock_solution, chunks)
            
            # Save individual RDF
            rdf_file = Path("output_data/rdf") / f"{doc_id}.ttl"
            rdf_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(rdf_file, 'w', encoding='utf-8') as f:
                f.write(rdf_output)
            
            print(f"Generated RDF for {doc_id}: {len(rdf_output)} chars")
            solutions_processed.add(doc_id)
    
    print(f"\nProcessed {len(solutions_processed)} solutions")
    print("RDF files saved to output_data/rdf/")
    
    # Generate combined RDF
    if solutions_processed:
        print("\nGenerating combined RDF...")
        rdf_gen.clear_graph()
        
        solutions_with_chunks = []
        for doc_id in solutions_processed:
            if doc_id in doc_chunks and doc_id in doc_texts:
                mock_solution = create_mock_solution_from_data(doc_texts[doc_id])
                solutions_with_chunks.append((mock_solution, doc_chunks[doc_id]))
        
        combined_rdf = rdf_gen.generate_batch_rdf(solutions_with_chunks)
        
        combined_file = Path("output_data/rdf/combined_solutions.ttl")
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write(combined_rdf)
        
        print(f"Combined RDF saved: {len(combined_rdf)} chars")
        print(f"File: {combined_file}")

def create_mock_solution_from_data(text_data):
    """Create a mock Solution object from text data"""
    from models.solution import Solution
    
    # Extract metadata from text data
    metadata = text_data.get('metadata', {})
    
    # Ensure we have a valid source URL
    source_url = metadata.get('source_url', 'https://example.com/solution')
    if not source_url or source_url == '':
        source_url = 'https://example.com/solution'
    
    solution = Solution(
        id=text_data['doc_id'],
        source_file="processed_data",
        row_number=1,
        number="001",
        name=metadata.get('title', 'Climate Solution'),
        country=metadata.get('country', 'Unknown'),
        public_organisations=metadata.get('organization', 'Unknown'),
        international_organisations="",
        private_organisations="",
        type_of_risk=metadata.get('type_of_risk', 'Unknown'),
        type_of_solution=metadata.get('type_of_solution', 'Unknown'),
        ppp="Unknown",
        theme=metadata.get('theme', 'Unknown'),
        year_of_implementation=metadata.get('year', '2024'),
        description=metadata.get('description', ''),
        key_highlights=metadata.get('key_highlights', ''),
        results=metadata.get('results', ''),
        organization_sources=source_url,  # Provide valid URL
        other_sources="",
        contact_information="",
        date_added=metadata.get('date_added', '2024-01-01'),
        last_updated=metadata.get('last_updated', '2024-01-01'),
        most_recent_changes=""
    )
    
    # The Solution model will automatically set doc_id and source_url in __post_init__
    solution.pseudo_document_text = text_data.get('text', '')
    
    return solution

if __name__ == "__main__":
    test_with_existing_chunks()
