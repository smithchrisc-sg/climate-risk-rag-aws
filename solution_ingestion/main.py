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
from generators.integrated_rdf_chunk_generator import IntegratedRDFChunkGenerator
from generators.embeddings_generator import EmbeddingsGenerator
from processors.database_processor import DatabaseProcessor
from indexers.opensearch_keyword_indexer import OpenSearchKeywordIndexer
from indexers.opensearch_vector_indexer import OpenSearchVectorIndexer
from knowledge_graph_layer.utils.KnowledgeGraphManager import KnowledgeGraphManager
from utils.data_lake_writer import DataLakeWriter
from config.environment import Environment

logger = logging.getLogger(__name__)

class SolutionIngestionCLI:
    """Main CLI application for solution ingestion."""
    
    def __init__(self):
        self.env = Environment()
        
        # Create shared database manager instance
        from database_core_layer.utils.DatabaseManager import DatabaseManager
        from database_core_layer.utils.DocumentIDManager import DocumentIDManager
        self.shared_db_manager = DatabaseManager()
        self.shared_doc_id_manager = DocumentIDManager()
        
        self.csv_parser = CSVParser()
        self.csv_parser.shared_doc_id_manager = self.shared_doc_id_manager
        self.doc_generator = PseudoDocumentGenerator()
        self.integrated_generator = IntegratedRDFChunkGenerator()
        self.embeddings_generator = EmbeddingsGenerator()
        self.db_processor = DatabaseProcessor(self.env)
        self.keyword_indexer = OpenSearchKeywordIndexer(self.env)
        self.vector_indexer = OpenSearchVectorIndexer(self.env)
        
        # Set up Neptune environment for KnowledgeGraphManager
        os.environ['NEPTUNE_ENDPOINT'] = self.env.neptune_endpoint
        os.environ['NEPTUNE_PORT'] = self.env.neptune_port
        os.environ['AWS_REGION'] = self.env.aws_region
        self.kg_manager = KnowledgeGraphManager()
        
        self.data_lake_writer = DataLakeWriter()
    
    def run(self, csv_path: str = None, limit: int = None, dry_run: bool = False):
        """Run the complete ingestion pipeline."""
        
        logger.info("Starting solution ingestion pipeline")
        
        try:
            # Step 1: Parse CSV files
            if csv_path:
                solutions_iter = self.csv_parser.parse_csv_file(Path(csv_path))
            else:
                # Process all CSV files
                input_files = self.csv_parser.load_csv_files()
                if not input_files:
                    logger.error("No CSV files found")
                    return
                
                logger.info(f"Found {len(input_files)} CSV files to process")
                solutions_iter = []
                for csv_file in input_files:
                    logger.info(f"Processing CSV file: {csv_file}")
                    file_solutions = list(self.csv_parser.parse_csv_file(csv_file))
                    logger.info(f"  Found {len(file_solutions)} solutions")
                    solutions_iter.extend(file_solutions)
            
            # Apply limit early to avoid connection issues
            solutions = []
            for i, solution in enumerate(solutions_iter):
                if limit and i >= limit:
                    break
                solutions.append(solution)
            
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
            
            # Step 3: Generate RDF and chunks using integrated generator
            logger.info("Generating RDF and chunks...")
            all_chunks = []
            all_rdf_content = []
            
            for solution in solutions:
                rdf_content, chunks = self.integrated_generator.generate_document_rdf_and_chunks(solution)
                all_chunks.extend(chunks)
                all_rdf_content.append(rdf_content)
            
            # Step 4: Generate embeddings for chunks
            logger.info("Generating embeddings...")
            solutions_with_chunks = []
            for solution in solutions:
                solution_chunks = [c for c in all_chunks if c.doc_id == solution.doc_id]
                solutions_with_chunks.append((solution, solution_chunks))
            
            enriched_solutions = self.embeddings_generator.process_solutions_chunks(solutions_with_chunks)
            
            # Update all_chunks with embeddings
            all_enriched_chunks = []
            for solution, enriched_chunks in enriched_solutions:
                all_enriched_chunks.extend(enriched_chunks)
            
            # Step 5: Store in PostgreSQL
            logger.info("Storing in PostgreSQL...")
            self.db_processor.store_solutions(solutions)
            self.db_processor.store_chunks(all_chunks)
            
            # Step 6: Index in OpenSearch
            logger.info("Indexing documents (keyword) in OpenSearch...")
            self.keyword_indexer.index_documents(solutions)
            
            logger.info("Indexing chunks (vector) in OpenSearch...")
            self.vector_indexer.create_vector_index_if_not_exists()
            self.vector_indexer.index_chunks_with_vectors(all_enriched_chunks)
            
            # Step 7: Store RDF in Neptune (one document at a time)
            logger.info("Storing RDF in Neptune...")
            successful_loads = 0
            failed_loads = 0
            
            for i, rdf_content in enumerate(all_rdf_content):
                try:
                    load_result = self.kg_manager.bulk_insert_ttl(rdf_content)
                    if load_result:
                        successful_loads += 1
                        logger.info(f"✅ Document {i+1}/{len(all_rdf_content)} loaded successfully")
                    else:
                        failed_loads += 1
                        logger.error(f"❌ Document {i+1}/{len(all_rdf_content)} loading failed")
                except Exception as e:
                    failed_loads += 1
                    logger.error(f"❌ Document {i+1}/{len(all_rdf_content)} loading error: {e}")
            
            logger.info(f"Neptune loading complete: {successful_loads} successful, {failed_loads} failed")
            
            # Step 8: Write to data lake
            logger.info("Writing to local data lake...")
            self.data_lake_writer.write_solutions(solutions)
            self.data_lake_writer.write_chunks(all_chunks)
            self.data_lake_writer.write_embeddings(all_enriched_chunks)
            
            # Write individual TTL files per solution in correct directory structure
            logger.info("Writing individual TTL files...")
            for i, (solution, rdf_content) in enumerate(zip(solutions, all_rdf_content)):
                ttl_filename = f"{solution.doc_id}.ttl"
                self.data_lake_writer.write_solution_rdf(solution.doc_id, rdf_content, ttl_filename)
                if (i + 1) % 100 == 0:
                    logger.info(f"Written {i + 1}/{len(solutions)} TTL files")
            
            logger.info(f"Successfully ingested {len(solutions)} solutions with {len(all_chunks)} chunks")
            
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