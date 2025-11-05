#!/usr/bin/env python3
"""
Chunk Generator for Solution Ingestion
Creates 3 chunks per solution: Description, Key Highlights, Results for vector search optimization.
"""

import logging
import sys
import os
from typing import List, Dict, Any
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.solution import Solution

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    """Represents a text chunk for vector processing."""
    chunk_id: str
    doc_id: str
    text: str
    chunk_type: str
    character_count: int
    metadata: Dict[str, Any]

class ChunkGenerator:
    """Generates chunks from solution documents for vector search."""
    
    def __init__(self):
        self.chunk_types = ['desc', 'highlights', 'results']
    
    def generate_chunks(self, solution: Solution) -> List[Chunk]:
        """Generate 3 chunks from solution: description, highlights, results."""
        chunks = []
        
        # Description chunk
        if solution.description and solution.description.strip():
            chunk = self._create_chunk(
                solution, 
                'desc', 
                solution.description.strip(),
                'Description'
            )
            chunks.append(chunk)
        
        # Key Highlights chunk
        if solution.key_highlights and solution.key_highlights.strip():
            chunk = self._create_chunk(
                solution,
                'highlights', 
                solution.key_highlights.strip(),
                'Key Highlights'
            )
            chunks.append(chunk)
        
        # Results chunk
        if solution.results and solution.results.strip():
            chunk = self._create_chunk(
                solution,
                'results',
                solution.results.strip(), 
                'Results'
            )
            chunks.append(chunk)
        
        logger.debug(f"Generated {len(chunks)} chunks for solution {solution.id}")
        return chunks
    
    def _create_chunk(self, solution: Solution, chunk_type: str, text: str, section_name: str) -> Chunk:
        """Create a chunk object with metadata."""
        chunk_id = f"{solution.doc_id}_{chunk_type}"
        
        # Create chunk metadata
        metadata = {
            'solution_id': solution.id,
            'source_file': solution.source_file,
            'row_number': solution.row_number,
            'solution_name': solution.name,
            'country': solution.country,
            'type_of_risk': solution.type_of_risk,
            'type_of_solution': solution.type_of_solution,
            'theme': solution.theme,
            'year_of_implementation': solution.year_of_implementation,
            'ppp': solution.ppp,
            'source_url': solution.source_url,
            'section_name': section_name,
            'chunk_type': chunk_type,
            'content_type': 'solution_chunk'
        }
        
        return Chunk(
            chunk_id=chunk_id,
            doc_id=solution.doc_id,
            text=text,
            chunk_type=chunk_type,
            character_count=len(text),
            metadata=metadata
        )
    
    def process_solutions(self, solutions: List[Solution]) -> List[Chunk]:
        """Process multiple solutions to generate all chunks."""
        all_chunks = []
        
        for solution in solutions:
            try:
                chunks = self.generate_chunks(solution)
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.error(f"Failed to generate chunks for {solution.id}: {e}")
        
        logger.info(f"Generated {len(all_chunks)} total chunks from {len(solutions)} solutions")
        return all_chunks

def main():
    """Test chunk generation."""
    from parsers.csv_parser import CSVParser
    from generators.pseudo_document_generator import PseudoDocumentGenerator
    
    print("Chunk Generator Test")
    print("=" * 50)
    
    # Parse solutions
    parser = CSVParser()
    solutions = list(parser.parse_all_files())[:3]  # Test with first 3
    
    # Generate pseudo-documents
    doc_generator = PseudoDocumentGenerator()
    processed_solutions = doc_generator.process_solutions(solutions)
    
    # Generate chunks
    chunk_generator = ChunkGenerator()
    chunks = chunk_generator.process_solutions(processed_solutions)
    
    print(f"\nGenerated {len(chunks)} chunks from {len(solutions)} solutions")
    
    # Show chunk details
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1}: {chunk.chunk_id} ---")
        print(f"Type: {chunk.chunk_type}")
        print(f"Length: {chunk.character_count} chars")
        print(f"Solution: {chunk.metadata['solution_name'][:50]}...")
        print(f"Section: {chunk.metadata['section_name']}")
        print(f"Text preview: {chunk.text[:100]}...")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
