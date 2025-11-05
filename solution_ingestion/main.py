#!/usr/bin/env python3
"""
Solution Ingestion CLI
Main entry point for ingesting solutions from CSV into GAIP Knowledge Repository.
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import List

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# No complex layer imports needed - direct imports now work

from parsers.csv_parser import CSVParser
from generators.pseudo_document_generator import PseudoDocumentGenerator
from generators.chunk_generator import ChunkGenerator
from generators.rdf_generator import RDFGenerator
from processors.database_processor import DatabaseProcessor
from indexers.opensearch_indexer import OpenSearchIndexer
from processors.neptune_processor import NeptuneProcessor
from utils.data_lake_writer import DataLakeWriter
from config.environment import Environment

logger = logging.getLogger(__name__)

class SolutionIngestionCLI:
    """Main CLI application for solution ingestion."""
    
    def __init__(self):
        self.env = Environment()
        self.csv_parser = CSVParser()
        self.doc_generator = PseudoDocumentGenerator()
        self.chunk_generator = ChunkGenerator()
        self.rdf_generator = RDFGenerator()
        self.db_processor = DatabaseProcessor(self.env)
        self.opensearch_indexer = OpenSearchIndexer(self.env)
        self.neptune_processor = NeptuneProcessor(self.env)
        self.data_lake_writer = DataLakeWriter()
    
    def run(self, csv_path: str = None, limit: int = None, dry_run: bool = False):
        """Run the complete ingestion pipeline."""
        
        logger.info("Starting solution ingestion pipeline")
        
        try:
            # Step 1: Parse CSV files
            if csv_path:
                solutions = list(self.csv_parser.parse_csv_file(Path(csv_path)))
            else:
                solutions = list(self.csv_parser.parse_all_files())
            
            if limit:
                solutions = solutions[:limit]
            
            logger.info(f"Loaded {len(solutions)} solutions")
            
            if dry_run:
                logger.info("DRY RUN: Would process the following solutions:")
                for i, solution in enumerate(solutions[:5], 1):
                    logger.info(f"  {i}. {solution.name} ({solution.country})")
                if len(solutions) > 5:
                    logger.info(f"  ... and {len(solutions) - 5} more")
                return
            
            # Step 2: Generate pseudo-documents
            logger.info("Generating pseudo-documents...")
            solutions = self.doc_generator.process_solutions(solutions)
            
            # Step 3: Generate chunks
            logger.info("Generating chunks...")
            all_chunks = self.chunk_generator.process_solutions(solutions)
            
            # Step 4: Store in PostgreSQL
            logger.info("Storing in PostgreSQL...")
            self.db_processor.store_solutions(solutions)
            self.db_processor.store_chunks(all_chunks)
            
            # Step 5: Index in OpenSearch
            logger.info("Indexing in OpenSearch...")
            self.opensearch_indexer.index_documents(solutions)
            self.opensearch_indexer.index_chunks(all_chunks)
            
            # Step 6: Generate and store RDF
            logger.info("Generating RDF...")
            solutions_with_chunks = []
            for solution in solutions:
                solution_chunks = [c for c in all_chunks if c.doc_id == solution.doc_id]
                solutions_with_chunks.append((solution, [c.__dict__ for c in solution_chunks]))
            
            rdf_content = self.rdf_generator.generate_batch_rdf(solutions_with_chunks)
            
            # Step 7: Store in Neptune
            logger.info("Storing RDF in Neptune...")
            self.neptune_processor.store_rdf(rdf_content)
            
            # Step 8: Write to data lake (for debugging)
            logger.info("Writing to local data lake...")
            self.data_lake_writer.write_solutions(solutions)
            self.data_lake_writer.write_chunks(all_chunks)
            self.data_lake_writer.write_rdf(rdf_content, "batch_solutions.ttl")
            
            logger.info(f"Successfully ingested {len(solutions)} solutions")
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Ingest solutions from CSV into GAIP Knowledge Repository")
    
    parser.add_argument(
        "--csv-path", 
        type=str,
        help="Path to specific CSV file (default: process all files in input_data/)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of solutions to process (for testing)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually doing it"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run ingestion
    cli = SolutionIngestionCLI()
    cli.run(
        csv_path=args.csv_path,
        limit=args.limit,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()