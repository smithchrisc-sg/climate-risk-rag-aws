#!/usr/bin/env python3
"""
Test embeddings generation with Bedrock Titan.
"""

import sys
import os
from pathlib import Path
import json

# Setup paths
sys.path.append(str(Path(__file__).parent))

def test_embeddings_generation():
    """Test embeddings generation with sample chunks."""
    print("Testing embeddings generation...")
    
    try:
        from generators.embeddings_generator import EmbeddingsGenerator
        from parsers.csv_parser import CSVParser
        from generators.pseudo_document_generator import PseudoDocumentGenerator
        from generators.chunk_generator import ChunkGenerator
        
        # Initialize components
        csv_parser = CSVParser()
        doc_generator = PseudoDocumentGenerator()
        chunk_generator = ChunkGenerator()
        embeddings_generator = EmbeddingsGenerator()
        
        print("[OK] All generators initialized")
        
        # Get sample solutions (limit to 2 for cost control)
        input_dir = Path("input_data")
        csv_files = list(input_dir.glob("*.csv"))
        
        if not csv_files:
            print("[WARN] No CSV files found")
            return False
        
        # Parse limited solutions
        solutions_iter = csv_parser.parse_csv_file(csv_files[0])
        solutions = []
        for i, solution in enumerate(solutions_iter):
            if i >= 2:  # Limit to 2 solutions for cost control
                break
            solutions.append(solution)
        
        print(f"[OK] Loaded {len(solutions)} solutions")
        
        # Generate documents and chunks
        solutions = doc_generator.process_solutions(solutions)
        print(f"[OK] Generated pseudo-documents")
        
        all_chunks = chunk_generator.process_solutions(solutions)
        print(f"[OK] Generated {len(all_chunks)} chunks")
        
        # Prepare solutions with chunks for embeddings
        solutions_with_chunks = []
        for solution in solutions:
            solution_chunks = [c for c in all_chunks if c.doc_id == solution.doc_id]
            solutions_with_chunks.append((solution, solution_chunks))
        
        # Generate embeddings
        print(f"[INFO] Generating embeddings (this may take a moment)...")
        enriched_solutions = embeddings_generator.process_solutions_chunks(solutions_with_chunks)
        
        # Validate results
        total_embeddings = 0
        for solution, enriched_chunks in enriched_solutions:
            for chunk in enriched_chunks:
                if 'embedding' in chunk:
                    total_embeddings += 1
                    # Validate embedding structure
                    embedding = chunk['embedding']
                    if len(embedding) != 1536:
                        print(f"[WARN] Unexpected embedding dimension: {len(embedding)}")
                    
        print(f"[OK] Generated {total_embeddings} embeddings")
        
        # Show cost summary
        cost_summary = embeddings_generator.get_cost_summary()
        print(f"[OK] Cost Summary:")
        print(f"  - Total tokens: {cost_summary['total_tokens_processed']}")
        print(f"  - API calls: {cost_summary['total_api_calls']}")
        print(f"  - Estimated cost: ${cost_summary['estimated_cost_usd']:.4f}")
        
        # Save sample to output directory
        output_dir = Path("output_data/kr-dl-embeddings/data-lake")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save first solution's embeddings as sample
        if enriched_solutions:
            solution, enriched_chunks = enriched_solutions[0]
            sample_file = output_dir / f"{solution.doc_id}_embeddings_sample.json"
            
            sample_data = {
                'solution_name': solution.name,
                'doc_id': solution.doc_id,
                'chunks_count': len(enriched_chunks),
                'embedding_model': enriched_chunks[0].get('embedding_model') if enriched_chunks else None,
                'embedding_dimension': enriched_chunks[0].get('embedding_dimension') if enriched_chunks else None,
                'sample_chunk': {
                    'text': enriched_chunks[0].get('text', '')[:200] + '...' if enriched_chunks else '',
                    'embedding_preview': enriched_chunks[0].get('embedding', [])[:5] if enriched_chunks else []
                }
            }
            
            with open(sample_file, 'w') as f:
                json.dump(sample_data, f, indent=2)
            
            print(f"[OK] Sample embeddings saved to: {sample_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Embeddings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Embeddings Generation Test ===\n")
    
    # Set environment variables for database access
    os.environ.setdefault('DATABASE_SECRET_NAME', 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863')
    os.environ.setdefault('DB_HOST', 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com')
    os.environ.setdefault('DB_NAME', 'climate_risk_rag')
    os.environ.setdefault('DB_PORT', '5432')
    os.environ.setdefault('DB_USER', 'postgres')
    
    success = test_embeddings_generation()
    
    if success:
        print("\n🎉 Embeddings generation test passed!")
        print("Check output_data/kr-dl-embeddings/ for generated files.")
        sys.exit(0)
    else:
        print("\n❌ Embeddings generation test failed.")
        sys.exit(1)
