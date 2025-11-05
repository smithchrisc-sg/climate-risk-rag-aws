#!/usr/bin/env python3
"""
Data Lake Writer for Solution Ingestion
Writes solutions, chunks, and RDF to local data lake structure for debugging.
"""

import json
import logging
from pathlib import Path
from typing import List, Any

logger = logging.getLogger(__name__)

class DataLakeWriter:
    """Writes data to local data lake structure for debugging."""
    
    def __init__(self, base_path: str = "output_data"):
        self.base_path = Path(base_path)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure data lake directories exist."""
        dirs = [
            "kr-dl-text/data-lake",
            "kr-dl-chunks/data-lake", 
            "kr-dl-embeddings/data-lake",
            "kr-dl-neptune-ttl/data-lake"
        ]
        
        for dir_path in dirs:
            (self.base_path / dir_path).mkdir(parents=True, exist_ok=True)
    
    def write_solutions(self, solutions: List[Any]):
        """Write solutions as text files."""
        logger.info(f"Writing {len(solutions)} solutions to data lake")
        
        for solution in solutions:
            doc_dir = self.base_path / "kr-dl-text" / "data-lake" / solution.doc_id
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            text_file = doc_dir / "raw_text.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
                    f.write(solution.pseudo_document_text)
                else:
                    f.write(solution.get_full_text())
    
    def write_chunks(self, chunks: List[Any]):
        """Write chunks as JSON files."""
        logger.info(f"Writing {len(chunks)} chunks to data lake")
        
        for chunk in chunks:
            doc_dir = self.base_path / "kr-dl-chunks" / "data-lake" / chunk.doc_id
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            chunk_file = doc_dir / f"{chunk.chunk_id}.json"
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk.__dict__, f, indent=2, ensure_ascii=False)
    
    def write_rdf(self, rdf_content: str, filename: str = "batch_solutions.ttl"):
        """Write RDF content to TTL file."""
        logger.info(f"Writing RDF content to data lake: {filename}")
        
        rdf_dir = self.base_path / "kr-dl-neptune-ttl" / "data-lake"
        rdf_dir.mkdir(parents=True, exist_ok=True)
        
        rdf_file = rdf_dir / filename
        with open(rdf_file, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
    
    def write_embeddings(self, embeddings: List[dict]):
        """Write embeddings as JSON files."""
        logger.info(f"Writing {len(embeddings)} embeddings to data lake")
        
        for embedding in embeddings:
            doc_id = embedding.get('doc_id')
            chunk_id = embedding.get('chunk_id')
            
            if doc_id and chunk_id:
                doc_dir = self.base_path / "kr-dl-embeddings" / "data-lake" / doc_id
                doc_dir.mkdir(parents=True, exist_ok=True)
                
                embedding_file = doc_dir / f"{chunk_id}_embedding.json"
                with open(embedding_file, 'w', encoding='utf-8') as f:
                    json.dump(embedding, f, indent=2, ensure_ascii=False)