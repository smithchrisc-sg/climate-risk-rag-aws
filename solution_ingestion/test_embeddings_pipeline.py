#!/usr/bin/env python3
"""
Test embeddings pipeline without Neptune/OpenSearch dependencies.
Focus on: CSV → Solutions → Documents → Chunks → Embeddings → Data Lake
"""

import sys
import os
from pathlib import Path
import logging

# Setup paths and environment
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DATABASE_SECRET_NAME', 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863')
os.environ.setdefault('DB_HOST', 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com')
os.environ.setdefault('DB_NAME', 'climate_risk_rag')
os.environ.setdefault('DB_PORT', '5432')
os.environ.setdefault('DB_USER', 'postgres')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_embeddings_pipeline():
    """Test the embeddings pipeline without expensive services."""
    
    try:
        # Import components (skip Neptune/OpenSearch)
        from parsers.csv_parser import CSVParser
        from generators.pseudo_document_generator import PseudoDocumentGenerator
        from generators.chunk_generator import ChunkGenerator
        from generators.embeddings_generator import EmbeddingsGenerator
        from utils.data_lake_writer import DataLakeWriter
        
        logger.info("Starting embeddings pipeline test")
        
        # Initialize components
        csv_parser = CSVParser()
        doc_generator = PseudoDocumentGenerator()
        chunk_generator = ChunkGenerator()
        embeddings_generator = EmbeddingsGenerator()
        data_lake_writer = DataLakeWriter()
        
        logger.info("All components initialized")
        
        # Step 1: Parse CSV (limit to 2 solutions)
        input_dir = Path("input_data")
        csv_files = list(input_dir.glob("*.csv"))
        
        if not csv_files:
            logger.error("No CSV files found")
            return False
        
        solutions_iter = csv_parser.parse_csv_file(csv_files[0])
        solutions = []
        for i, solution in enumerate(solutions_iter):
            if i >= 2:  # Limit for cost control
                break
            solutions.append(solution)
        
        logger.info(f"Loaded {len(solutions)} solutions")
        
        # Step 2: Generate pseudo-documents
        logger.info("Generating pseudo-documents...")
        solutions = doc_generator.process_solutions(solutions)
        
        # Step 3: Generate chunks
        logger.info("Generating chunks...")
        all_chunks = chunk_generator.process_solutions(solutions)
        logger.info(f"Generated {len(all_chunks)} chunks")
        
        # Step 4: Generate embeddings
        logger.info("Generating embeddings...")
        solutions_with_chunks = []
        for solution in solutions:
            solution_chunks = [c for c in all_chunks if c.doc_id == solution.doc_id]
            solutions_with_chunks.append((solution, solution_chunks))
        
        enriched_solutions = embeddings_generator.process_solutions_chunks(solutions_with_chunks)
        
        # Flatten enriched chunks
        all_enriched_chunks = []
        for solution, enriched_chunks in enriched_solutions:
            all_enriched_chunks.extend(enriched_chunks)
        
        logger.info(f"Generated embeddings for {len(all_enriched_chunks)} chunks")
        
        # Step 5: Write to data lake
        logger.info("Writing to data lake...")
        data_lake_writer.write_solutions(solutions)
        data_lake_writer.write_chunks(all_chunks)
        data_lake_writer.write_embeddings(all_enriched_chunks)
        
        # Step 6: Validate outputs
        logger.info("Validating outputs...")
        
        # Check text files
        text_dir = Path("output_data/kr-dl-text/data-lake")
        text_files = list(text_dir.rglob("*.txt"))
        logger.info(f"Generated {len(text_files)} text files")
        
        # Check chunk files
        chunks_dir = Path("output_data/kr-dl-chunks/data-lake")
        chunk_files = list(chunks_dir.rglob("*.json"))
        logger.info(f"Generated {len(chunk_files)} chunk files")
        
        # Check embedding files
        embeddings_dir = Path("output_data/kr-dl-embeddings/data-lake")
        embedding_files = list(embeddings_dir.rglob("*_embedding.json"))
        logger.info(f"Generated {len(embedding_files)} embedding files")
        
        # Show cost summary
        cost_summary = embeddings_generator.get_cost_summary()
        logger.info("Cost Summary:")
        logger.info(f"  - Total tokens: {cost_summary['total_tokens_processed']}")
        logger.info(f"  - API calls: {cost_summary['total_api_calls']}")
        logger.info(f"  - Estimated cost: ${cost_summary['estimated_cost_usd']:.4f}")
        
        # Validate embedding structure
        if embedding_files:
            import json
            with open(embedding_files[0], 'r') as f:
                sample_embedding = json.load(f)
            
            embedding_vector = sample_embedding.get('embedding', [])
            logger.info(f"Sample embedding dimension: {len(embedding_vector)}")
            logger.info(f"Sample embedding preview: {embedding_vector[:5]}")
        
        logger.info("✅ Embeddings pipeline test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Embeddings Pipeline Test ===\n")
    
    success = test_embeddings_pipeline()
    
    if success:
        print("\n🎉 Embeddings pipeline test passed!")
        print("Check output_data/ directories for generated files:")
        print("  - kr-dl-text/data-lake/        (solution texts)")
        print("  - kr-dl-chunks/data-lake/      (text chunks)")
        print("  - kr-dl-embeddings/data-lake/  (embeddings)")
        sys.exit(0)
    else:
        print("\n❌ Embeddings pipeline test failed.")
        sys.exit(1)
