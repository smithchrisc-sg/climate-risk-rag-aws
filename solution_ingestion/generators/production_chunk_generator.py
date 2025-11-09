#!/usr/bin/env python3
"""
DEPRECATED: Production-Aligned Chunk Generator for Solution Ingestion

⚠️  WARNING: This generator is DEPRECATED and should not be used.
⚠️  Use IntegratedRDFChunkGenerator instead for all chunk generation.
⚠️  This file is kept for reference only.

Creates chunks with sequential numbering that matches the RDF structure exactly.
Only generates paragraph-level chunks (the ones that get embeddings).
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
class ProductionChunk:
    """Represents a paragraph-level chunk for embeddings with production-aligned IDs."""
    chunk_id: str           # e.g., "sol_abc123_chunk_0002"
    doc_id: str            # e.g., "sol_abc123"
    chunk_number: int      # e.g., 2 (for sequential numbering)
    text: str              # The actual content
    section_title: str     # e.g., "Introduction", "Description"
    character_count: int
    metadata: Dict[str, Any]

class ProductionChunkGenerator:
    """Generates production-aligned chunks that match RDF structure."""
    
    def generate_chunks(self, solution: Solution) -> List[ProductionChunk]:
        """Generate paragraph-level chunks with sequential numbering matching RDF."""
        chunks = []
        
        # Calculate the same section structure as RDF generator
        section_info = self._calculate_section_numbers(solution)
        
        # Generate chunks only for paragraph-level items
        for title, section_num, para_count, content in section_info:
            if content or title == 'Introduction':  # Always include Introduction
                # Generate paragraph chunks for this section
                paragraph_chunks = self._generate_paragraph_chunks(
                    solution, title, section_num, para_count, content
                )
                chunks.extend(paragraph_chunks)
        
        logger.debug(f"Generated {len(chunks)} production-aligned chunks for solution {solution.id}")
        return chunks
    
    def _calculate_section_numbers(self, solution) -> List[tuple]:
        """Calculate section numbers using same logic as RDF generator."""
        # Get introduction text from pseudo document
        intro_text = ""
        if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
            sections = solution.pseudo_document_text.split('\n\n')
            for i, section in enumerate(sections):
                if section.strip() == "Introduction" and i + 1 < len(sections):
                    intro_text = sections[i + 1]
                    break
        
        # Build sections with content (same as RDF generator)
        sections_data = [
            ('Introduction', intro_text),
            ('Description', solution.description if solution.description else ''),
            ('Key Highlights', solution.key_highlights if solution.key_highlights else ''),
            ('Results', solution.results if solution.results else '')
        ]
        
        # Calculate dynamic numbering (same logic as RDF generator)
        current_num = 1
        section_info = []
        
        for title, content in sections_data:
            section_num = current_num
            current_num += 1  # Section takes one number
            
            # Count paragraphs for this section
            if title == 'Introduction':
                para_count = 1  # Always 1 paragraph
            else:
                # Split content into paragraphs
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()] if content else []
                para_count = max(1, len(paragraphs))  # At least 1 paragraph
            
            section_info.append((title, section_num, para_count, content))
            current_num += para_count  # Paragraphs take subsequent numbers
        
        return section_info
    
    def _generate_paragraph_chunks(self, solution: Solution, section_title: str, 
                                 section_num: int, para_count: int, content: str) -> List[ProductionChunk]:
        """Generate paragraph chunks for a section."""
        chunks = []
        
        # Generate paragraph numbers (sequential after section)
        paragraph_nums = [section_num + 1 + i for i in range(para_count)]
        
        # Split content into paragraphs
        if section_title == 'Introduction':
            paragraphs = [content] if content else [""]
        else:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()] if content else []
            # Ensure we have at least the expected number of paragraphs
            while len(paragraphs) < para_count:
                paragraphs.append("")
        
        # Create chunk for each paragraph
        for i, (para_num, paragraph_text) in enumerate(zip(paragraph_nums, paragraphs)):
            chunk_id = f"{solution.doc_id}_chunk_{para_num:04d}"
            
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
                'section_title': section_title,
                'section_number': section_num,
                'paragraph_number': para_num,
                'paragraph_index': i,
                'content_type': 'solution_paragraph',
                's3_key': f"data-lake/{solution.doc_id}/{chunk_id}.json",
                's3_location': f"s3://kr-dl-chunks/data-lake/{solution.doc_id}/{chunk_id}.json"
            }
            
            chunk = ProductionChunk(
                chunk_id=chunk_id,
                doc_id=solution.doc_id,
                chunk_number=para_num,
                text=paragraph_text,
                section_title=section_title,
                character_count=len(paragraph_text),
                metadata=metadata
            )
            
            chunks.append(chunk)
        
        return chunks

def main():
    """Test the production chunk generator."""
    print("Production Chunk Generator Test")
    print("This would be called from the main test script")

if __name__ == "__main__":
    main()
