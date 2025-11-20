#!/usr/bin/env python3
"""
Test script to verify document reconstruction from chunks
"""
import sys
import os
import json
import boto3
from typing import Dict, List

# Add lambda layer paths for testing
sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/nlp-initiator/src')

def load_chunks_from_s3(doc_id: str, chunks_location: str) -> List[Dict]:
    """Load all chunk files for a document from S3."""
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # Parse S3 location
        if not chunks_location.startswith('s3://'):
            raise ValueError(f"Invalid S3 location format: {chunks_location}")
        
        s3_path = chunks_location[5:]  # Remove 's3://'
        if not s3_path.endswith('/'):
            s3_path += '/'
        
        bucket, prefix = s3_path.split('/', 1)
        
        print(f"Loading chunks from s3://{bucket}/{prefix}")
        
        # List all chunk files
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        chunks = []
        
        if 'Contents' not in response:
            print(f"No chunk files found at {chunks_location}")
            return chunks
        
        # Load each chunk file
        for obj in response['Contents']:
            key = obj['Key']
            
            # Skip non-JSON files
            if not key.endswith('.json'):
                continue
            
            # Skip if not a chunk file (should contain doc_id and 'chunk')
            if doc_id not in key or 'chunk' not in key:
                continue
            
            try:
                # Load chunk data
                chunk_response = s3_client.get_object(Bucket=bucket, Key=key)
                chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                chunks.append(chunk_data)
                
            except Exception as e:
                print(f"Failed to load chunk file {key}: {e}")
                continue
        
        print(f"Successfully loaded {len(chunks)} chunk files")
        return chunks
        
    except Exception as e:
        print(f"Error loading chunks from S3: {e}")
        return []

def reconstruct_document_from_chunks(chunks: List[Dict]) -> tuple:
    """Reconstruct full document text from chunks in proper reading order."""
    try:
        if not chunks:
            print("No chunks provided for reconstruction")
            return None, None
        
        print(f"Reconstructing document from {len(chunks)} chunks")
        
        # Sort chunks by chunk_index (which should be document reading order)
        sorted_chunks = sorted(chunks, key=lambda x: x.get('chunk_index', 999))
        
        # Reconstruct document text and create offset mapping
        reconstructed_parts = []
        chunk_offset_map = {}
        current_offset = 0
        
        for chunk in sorted_chunks:
            chunk_text = chunk.get('text', '')
            chunk_id = chunk.get('chunk_id', '')
            
            if not chunk_text or not chunk_id:
                print(f"Skipping chunk with missing text or ID: {chunk}")
                continue
            
            # Record this chunk's position in reconstructed text
            chunk_offset_map[chunk_id] = {
                'start': current_offset,
                'end': current_offset + len(chunk_text),
                'chunk_index': chunk.get('chunk_index', -1),
                'page_numbers': chunk.get('page_numbers', []),
                'section_types': chunk.get('section_types', [])
            }
            
            # Add chunk text (no separators needed - chunks are in document flow order)
            reconstructed_parts.append(chunk_text)
            current_offset += len(chunk_text)
        
        reconstructed_text = ''.join(reconstructed_parts)
        
        chunk_mapping_info = {
            'chunk_offset_map': chunk_offset_map,
            'total_length': current_offset,
            'chunk_count': len(sorted_chunks)
        }
        
        print(f"Document reconstruction complete:")
        print(f"  - Total length: {current_offset} characters")
        print(f"  - Chunks processed: {len(sorted_chunks)}")
        print(f"  - Offset mapping created for {len(chunk_offset_map)} chunks")
        
        return reconstructed_text, chunk_mapping_info
        
    except Exception as e:
        print(f"Error reconstructing document from chunks: {e}")
        return None, None

def test_document_reconstruction():
    """Test document reconstruction with the known document."""
    
    # Test with the known document
    doc_id = "064762102bead7b04a39"
    chunks_location = "s3://solve-global-kr-dl-chunks-861276078413-us-east-1/chunks/064762102bead7b04a39/"
    
    print(f"Testing document reconstruction for: {doc_id}")
    print(f"Chunks location: {chunks_location}")
    print("-" * 80)
    
    # Load chunks
    chunks = load_chunks_from_s3(doc_id, chunks_location)
    
    if not chunks:
        print("❌ Failed to load chunks")
        return False
    
    # Reconstruct document
    reconstructed_text, chunk_mapping_info = reconstruct_document_from_chunks(chunks)
    
    if not reconstructed_text:
        print("❌ Failed to reconstruct document")
        return False
    
    # Display results
    print("\n" + "=" * 80)
    print("RECONSTRUCTION RESULTS")
    print("=" * 80)
    
    print(f"✅ Successfully reconstructed document")
    print(f"   - Original chunks: {len(chunks)}")
    print(f"   - Reconstructed length: {len(reconstructed_text)} characters")
    print(f"   - Chunk mappings: {len(chunk_mapping_info['chunk_offset_map'])}")
    
    # Show first few chunks and their mappings
    print("\n📋 First 3 chunk mappings:")
    for i, (chunk_id, mapping) in enumerate(list(chunk_mapping_info['chunk_offset_map'].items())[:3]):
        print(f"   {i+1}. {chunk_id}")
        print(f"      Offset: {mapping['start']}-{mapping['end']} ({mapping['end']-mapping['start']} chars)")
        print(f"      Index: {mapping['chunk_index']}, Pages: {mapping['page_numbers']}")
    
    # Show beginning of reconstructed text
    print(f"\n📄 First 500 characters of reconstructed text:")
    print("-" * 60)
    print(reconstructed_text[:500])
    print("-" * 60)
    
    # Verify chunk order makes sense
    print(f"\n🔍 Verifying chunk order:")
    sorted_chunks = sorted(chunks, key=lambda x: x.get('chunk_index', 999))
    for i in range(min(3, len(sorted_chunks))):
        chunk = sorted_chunks[i]
        print(f"   Chunk {i}: Index {chunk['chunk_index']}, Pages {chunk.get('page_numbers', [])}")
        print(f"            Text preview: {chunk['text'][:100]}...")
    
    # Save reconstructed text for manual inspection
    output_file = f"/tmp/reconstructed_{doc_id}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(reconstructed_text)
    print(f"\n💾 Saved reconstructed text to: {output_file}")
    
    # Save chunk mapping for inspection
    mapping_file = f"/tmp/chunk_mapping_{doc_id}.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(chunk_mapping_info, f, indent=2)
    print(f"💾 Saved chunk mapping to: {mapping_file}")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Document Reconstruction")
    print("=" * 80)
    
    try:
        success = test_document_reconstruction()
        
        if success:
            print("\n✅ Document reconstruction test PASSED")
            print("\nNext steps:")
            print("1. Review the reconstructed text file to verify document flow")
            print("2. Check chunk mapping JSON for proper offset calculations")
            print("3. Deploy updated NLP initiator if results look good")
        else:
            print("\n❌ Document reconstruction test FAILED")
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
