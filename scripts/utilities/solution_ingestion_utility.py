#!/usr/bin/env python3
"""
Solution Ingestion Utility
Processes 325 solutions from CSV into pseudo-documents with multiple chunks for search optimization
"""

import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import uuid

# Add layers to path for production utilities
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), 'layers', 'database-core-layer', 'python'))

from utils.database_manager import DatabaseManager
from utils.document_id_manager import DocumentIDManager
from utils.uri_manager import URIManager
from utils.text_normalizer import TextNormalizer
from utils.triple_manager import TripleManager

class SolutionIngestionUtility:
    """Processes solutions CSV into searchable pseudo-documents"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.doc_id_manager = DocumentIDManager()
        self.uri_manager = URIManager()
        self.text_normalizer = TextNormalizer()
        self.triple_manager = TripleManager()
        
    def process_solutions_csv(self, csv_path: str) -> Dict[str, int]:
        """Process solutions CSV file into pseudo-documents"""
        stats = {"processed": 0, "errors": 0, "chunks_created": 0}
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    solution_id = self._process_solution(row)
                    if solution_id:
                        stats["processed"] += 1
                        stats["chunks_created"] += 3  # Each solution creates 3 chunks
                except Exception as e:
                    print(f"Error processing solution {row.get('Name', 'Unknown')}: {e}")
                    stats["errors"] += 1
                    
        return stats
    
    def _process_solution(self, solution_data: Dict[str, str]) -> str:
        """Process single solution into pseudo-document with 3 chunks"""
        # Generate solution ID
        solution_id = self.doc_id_manager.generate_solution_id(solution_data.get('Name', ''))
        
        # Create metadata pseudo-document in documents_keyword
        metadata = {
            "title": solution_data.get('Name', ''),
            "country": solution_data.get('Country', ''),
            "organizations": solution_data.get('Organizations', ''),
            "risk_types": solution_data.get('Risk Types', ''),
            "content_type": "solution"
        }
        
        self.db_manager.add_or_update_document(
            document_id=solution_id,
            title=metadata["title"],
            content_type="solution",
            metadata=metadata
        )
        
        # Create 3 chunks for vector search
        chunks = self._create_solution_chunks(solution_id, solution_data)
        
        for chunk in chunks:
            self._store_chunk(chunk)
            
        return solution_id
    
    def _create_solution_chunks(self, solution_id: str, data: Dict[str, str]) -> List[Dict[str, Any]]:
        """Create 3 optimized chunks per solution for vector search"""
        chunks = []
        
        # Chunk 1: Overview and description
        overview_text = f"{data.get('Name', '')} - {data.get('Description', '')}"
        chunks.append({
            "chunk_id": f"{solution_id}_overview",
            "solution_id": solution_id,
            "chunk_type": "overview",
            "text": self.text_normalizer.normalize(overview_text),
            "metadata": {
                "country": data.get('Country', ''),
                "organizations": data.get('Organizations', '')
            }
        })
        
        # Chunk 2: Implementation details
        impl_text = f"Implementation: {data.get('Implementation', '')} Approach: {data.get('Approach', '')}"
        chunks.append({
            "chunk_id": f"{solution_id}_implementation", 
            "solution_id": solution_id,
            "chunk_type": "implementation",
            "text": self.text_normalizer.normalize(impl_text),
            "metadata": {
                "risk_types": data.get('Risk Types', ''),
                "scale": data.get('Scale', '')
            }
        })
        
        # Chunk 3: Impact and outcomes
        impact_text = f"Impact: {data.get('Impact', '')} Outcomes: {data.get('Outcomes', '')}"
        chunks.append({
            "chunk_id": f"{solution_id}_impact",
            "solution_id": solution_id, 
            "chunk_type": "impact",
            "text": self.text_normalizer.normalize(impact_text),
            "metadata": {
                "beneficiaries": data.get('Beneficiaries', ''),
                "timeframe": data.get('Timeframe', '')
            }
        })
        
        return chunks
    
    def _store_chunk(self, chunk: Dict[str, Any]):
        """Store chunk in chunks_vector index"""
        # This would integrate with existing OpenSearch indexing
        # For now, just log the chunk creation
        print(f"Created chunk: {chunk['chunk_id']} for solution: {chunk['solution_id']}")

def main():
    """Main execution function"""
    if len(sys.argv) != 2:
        print("Usage: python solution_ingestion_utility.py <solutions_csv_path>")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
        
    utility = SolutionIngestionUtility()
    stats = utility.process_solutions_csv(csv_path)
    
    print(f"Solution ingestion complete:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Chunks created: {stats['chunks_created']}")

if __name__ == "__main__":
    main()
