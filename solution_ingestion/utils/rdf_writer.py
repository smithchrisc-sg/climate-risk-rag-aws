#!/usr/bin/env python3
"""
RDF Writer for Solution Ingestion
Writes RDF content to files for debugging and Neptune loading.
"""

import logging
from pathlib import Path
from typing import List, Any

logger = logging.getLogger(__name__)

class RDFWriter:
    """Writes RDF content to files."""
    
    def __init__(self, output_dir: str = "output_data/kr-dl-neptune-ttl/data-lake"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def write_solution_rdf(self, doc_id: str, rdf_content: str):
        """Write RDF for a single solution."""
        doc_dir = self.output_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        rdf_file = doc_dir / f"{doc_id}.ttl"
        with open(rdf_file, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
        
        logger.debug(f"Wrote RDF for {doc_id} to {rdf_file}")
    
    def write_batch_rdf(self, rdf_content: str, filename: str = "batch_solutions.ttl"):
        """Write RDF for multiple solutions."""
        rdf_file = self.output_dir / filename
        with open(rdf_file, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
        
        logger.info(f"Wrote batch RDF to {rdf_file}")
    
    def append_rdf(self, rdf_content: str, filename: str = "incremental_solutions.ttl"):
        """Append RDF content to existing file."""
        rdf_file = self.output_dir / filename
        with open(rdf_file, 'a', encoding='utf-8') as f:
            f.write(rdf_content)
            f.write('\n')
        
        logger.debug(f"Appended RDF to {rdf_file}")