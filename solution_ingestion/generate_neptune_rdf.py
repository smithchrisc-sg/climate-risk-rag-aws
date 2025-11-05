#!/usr/bin/env python3
"""
Generate Neptune RDF Files
Creates document structure RDF in kr-neptune-ttl format
"""

import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from utils.rdf_writer import RDFWriter

def generate_neptune_rdf():
    """Generate RDF files for Neptune in correct directory structure"""
    
    # Load existing chunk and text data
    chunks_dir = Path("output_data/kr-dl-chunks/data-lake")
    text_dir = Path("output_data/kr-dl-text/data-lake")
    
    chunk_files = list(chunks_dir.glob("*.json"))
    text_files = list(text_dir.glob("*.json"))
    
    print(f"Neptune RDF Generation")
    print(f"Found {len(chunk_files)} chunk files, {len(text_files)} text files")
    
    # Group chunks by document
    doc_chunks = {}
    for chunk_file in chunk_files:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            chunk_data = json.load(f)
        doc_id = chunk_data['doc_id']
        if doc_id not in doc_chunks:
            doc_chunks[doc_id] = []
        doc_chunks[doc_id].append(chunk_data)
    
    # Load text documents
    doc_texts = {}
    for text_file in text_files:
        with open(text_file, 'r', encoding='utf-8') as f:
            text_data = json.load(f)
        doc_texts[text_data['doc_id']] = text_data
    
    # Generate RDF files
    rdf_writer = RDFWriter()
    
    for doc_id, chunks in doc_chunks.items():
        if doc_id in doc_texts:
            # Create mock solution
            from test_rdf_integrated import create_mock_solution_from_data
            solution = create_mock_solution_from_data(doc_texts[doc_id])
            
            # Write RDF
            rdf_file = rdf_writer.write_document_structure_rdf(solution, chunks)
            print(f"Generated: {rdf_file}")

if __name__ == "__main__":
    generate_neptune_rdf()
