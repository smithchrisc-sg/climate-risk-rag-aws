#!/usr/bin/env python3
"""
Test script for embeddings generation with one-to-one chunk-to-embedding file mapping.
"""

import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Set up path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "database_core_layer" / "python"))
sys.path.append(str(current_dir / "knowledge_graph_layer" / "python"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_chunk_files_for_embeddings():
    """Process existing chunk files and generate corresponding embedding files."""
    try:
        from generators.embeddings_generator import EmbeddingsGenerator
        
        print("Embeddings Generation Test")
        print("=" * 50)
        
        # Initialize embeddings generator
        embeddings_gen = EmbeddingsGenerator()
        
        # Find all chunk files
        chunk_base_dir = Path("output_data/kr-dl-chunks/data-lake")
        if not chunk_base_dir.exists():
            print(f"Chunk directory not found: {chunk_base_dir}")
            return False
        
        # Get all chunk files
        chunk_files = []
        for solution_dir in chunk_base_dir.iterdir():
            if solution_dir.is_dir():
                for chunk_file in solution_dir.glob("*.json"):
                    chunk_files.append(chunk_file)
        
        print(f"Found {len(chunk_files)} chunk files to process")
        
        if not chunk_files:
            print("No chunk files found!")
            return False
        
        # Set up embeddings output directory
        embeddings_base_dir = Path("output_data/kr-dl-embeddings/data-lake")
        embeddings_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Process chunks in batches for efficiency
        batch_size = 10  # Process 10 chunks at a time
        total_processed = 0
        
        for i in range(0, len(chunk_files), batch_size):
            batch_files = chunk_files[i:i + batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(len(chunk_files)-1)//batch_size + 1}")
            
            # Load chunk data
            batch_chunks = []
            batch_metadata = []
            
            for chunk_file in batch_files:
                try:
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        chunk_data = json.load(f)
                    
                    batch_chunks.append(chunk_data)
                    batch_metadata.append({
                        'file_path': chunk_file,
                        'doc_id': chunk_data['doc_id'],
                        'chunk_id': chunk_data['chunk_id']
                    })
                    
                except Exception as e:
                    logger.error(f"Error loading chunk file {chunk_file}: {e}")
                    continue
            
            if not batch_chunks:
                continue
            
            # Generate embeddings for batch
            print(f"  Generating embeddings for {len(batch_chunks)} chunks...")
            enriched_chunks = embeddings_gen.process_chunks(batch_chunks)
            
            # Write embedding files (one per chunk)
            for enriched_chunk, metadata in zip(enriched_chunks, batch_metadata):
                doc_id = metadata['doc_id']
                chunk_id = metadata['chunk_id']
                
                # Create solution-specific embeddings directory
                solution_embeddings_dir = embeddings_base_dir / doc_id
                solution_embeddings_dir.mkdir(parents=True, exist_ok=True)
                
                # Create embedding file with proper naming convention
                embedding_file = solution_embeddings_dir / f"{chunk_id}_embedding.json"
                
                # Prepare embedding data
                embedding_data = {
                    'chunk_id': enriched_chunk['chunk_id'],
                    'doc_id': enriched_chunk['doc_id'],
                    'chunk_number': enriched_chunk['chunk_number'],
                    'text': enriched_chunk['text'],
                    'section_title': enriched_chunk['section_title'],
                    'character_count': enriched_chunk['character_count'],
                    'embedding': enriched_chunk['embedding'],
                    'embedding_model': enriched_chunk['embedding_model'],
                    'embedding_dimension': enriched_chunk['embedding_dimension'],
                    'metadata': enriched_chunk['metadata'],
                    's3_key': enriched_chunk['s3_key'],
                    's3_location': enriched_chunk['s3_location'],
                    'embedding_generated_at': datetime.now().isoformat() + "+00:00"
                }
                
                # Write embedding file
                with open(embedding_file, 'w', encoding='utf-8') as f:
                    json.dump(embedding_data, f, indent=2, ensure_ascii=False)
                
                total_processed += 1
            
            print(f"  Processed {len(enriched_chunks)} chunks in batch")
        
        print(f"\n" + "=" * 50)
        print(f"Embeddings Generation Summary:")
        print(f"  Total chunk files processed: {total_processed}")
        print(f"  Total embedding files created: {total_processed}")
        
        # Validate output
        print(f"\nValidation:")
        
        # Count embedding files
        embedding_files = []
        for solution_dir in embeddings_base_dir.iterdir():
            if solution_dir.is_dir():
                for embedding_file in solution_dir.glob("*.json"):
                    embedding_files.append(embedding_file)
        
        print(f"  Embedding files found: {len(embedding_files)}")
        print(f"  Chunk files found: {len(chunk_files)}")
        
        if len(embedding_files) == len(chunk_files):
            print("  ✅ One-to-one mapping achieved!")
        else:
            print("  ❌ Mapping mismatch!")
            return False
        
        # Cost summary
        cost_summary = embeddings_gen.get_cost_summary()
        print(f"\nCost Summary:")
        print(f"  Total API calls: {cost_summary['total_api_calls']}")
        print(f"  Total tokens processed: {cost_summary['total_tokens_processed']}")
        print(f"  Estimated cost: ${cost_summary['estimated_cost_usd']:.4f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Embeddings generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_time = datetime.now()
    print(f"Started at: {start_time}")
    
    success = process_chunk_files_for_embeddings()
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"Completed at: {end_time}")
    print(f"Duration: {duration}")
    
    if success:
        print("\n✅ Embeddings generation test completed successfully!")
    else:
        print("\n❌ Embeddings generation test failed!")
        sys.exit(1)
