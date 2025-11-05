#!/usr/bin/env python3
"""
Test chunk generation and data lake output
"""

import logging
from parsers.csv_parser import CSVParser
from generators.pseudo_document_generator import PseudoDocumentGenerator
from generators.chunk_generator import ChunkGenerator
from utils.data_lake_writer import DataLakeWriter

def main():
    """Test complete pipeline: CSV → Solutions → Pseudo-docs → Chunks → Data Lake"""
    print("Complete Chunk Pipeline Test")
    print("=" * 50)
    
    # Parse solutions (first 3 for testing)
    parser = CSVParser()
    solutions = list(parser.parse_all_files())[:3]
    print(f"Parsed {len(solutions)} solutions for testing")
    
    # Generate pseudo-documents
    doc_generator = PseudoDocumentGenerator()
    processed_solutions = doc_generator.process_solutions(solutions)
    print(f"Generated pseudo-documents for {len(processed_solutions)} solutions")
    
    # Generate chunks
    chunk_generator = ChunkGenerator()
    chunks = chunk_generator.process_solutions(processed_solutions)
    print(f"Generated {len(chunks)} chunks")
    
    # Write to data lake
    writer = DataLakeWriter()
    writer.write_pseudo_documents(processed_solutions)
    writer.write_chunks(chunks)
    
    # Show stats
    stats = writer.get_stats()
    print(f"\nData Lake Stats:")
    print(f"  Text documents: {stats['text_documents']}")
    print(f"  Chunks: {stats['chunks']}")
    print(f"  Text size: {stats['text_size_mb']} MB")
    print(f"  Chunk size: {stats['chunk_size_mb']} MB")
    print(f"  Total size: {stats['total_size_mb']} MB")
    
    # Show chunk breakdown by solution
    print(f"\nChunk Breakdown:")
    chunk_by_doc = {}
    for chunk in chunks:
        doc_id = chunk.doc_id
        if doc_id not in chunk_by_doc:
            chunk_by_doc[doc_id] = []
        chunk_by_doc[doc_id].append(chunk)
    
    for doc_id, doc_chunks in chunk_by_doc.items():
        solution_name = doc_chunks[0].metadata['solution_name']
        chunk_types = [c.chunk_type for c in doc_chunks]
        print(f"  {doc_id}: {len(doc_chunks)} chunks ({', '.join(chunk_types)}) - {solution_name[:40]}...")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
