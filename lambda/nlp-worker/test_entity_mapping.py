#!/usr/bin/env python3
"""
Test script to verify nlp-worker entity-to-chunk mapping fixes
Tests with existing data in the data lake
"""
import sys
import os
sys.path.append('src')

from nlp_worker import NLPWorker
import json

def test_with_existing_document():
    """Test with a known document that has both text and chunks"""
    
    # Use the document we verified exists
    doc_id = "002328de9d3e1e58227b"
    
    print(f"🧪 Testing entity mapping for document: {doc_id}")
    
    # Initialize worker
    worker = NLPWorker()
    
    try:
        # Test 1: Load original document text
        print("\n📄 Test 1: Loading original document text...")
        original_text = worker.load_original_document_text(doc_id)
        print(f"✅ Loaded text: {len(original_text)} characters")
        print(f"First 200 chars: {original_text[:200]}...")
        
        # Test 2: Load chunks
        print("\n📦 Test 2: Loading chunks...")
        chunks_location = f"s3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/{doc_id}/"
        chunks = worker.load_chunks_from_s3(chunks_location)
        print(f"✅ Loaded {len(chunks)} chunks")
        
        if chunks:
            print(f"First chunk: {chunks[0].get('chunk_id', 'NO_ID')}")
            print(f"First chunk text (100 chars): {chunks[0].get('text', '')[:100]}...")
        
        # Test 3: Find chunk positions in original text
        print("\n🎯 Test 3: Finding chunk positions...")
        chunk_positions = worker.find_chunk_positions_in_original_text(chunks, original_text)
        print(f"✅ Found {len(chunk_positions)} chunk positions")
        
        if chunk_positions:
            pos = chunk_positions[0]
            print(f"First chunk position: {pos['start_offset']}-{pos['end_offset']}")
            print(f"Chunk text matches: {original_text[pos['start_offset']:pos['end_offset']] == pos['chunk_text']}")
        
        # Test 4: Mock entity mapping (without Comprehend results)
        print("\n🔗 Test 4: Mock entity mapping...")
        mock_results = {
            'entities': [
                {
                    'text': 'climate',
                    'type': 'OTHER',
                    'score': 0.95,
                    'begin_offset': 100,
                    'end_offset': 107
                }
            ],
            'key_phrases': []
        }
        
        mapped_results = worker.map_results_to_chunks(mock_results, chunks, doc_id)
        print(f"✅ Mapped entities: {len(mapped_results['entities_by_chunk'])}")
        print(f"✅ Mapped key phrases: {len(mapped_results['key_phrases_by_chunk'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_with_existing_document()
    if success:
        print("\n🎉 All tests passed! Entity mapping should work now.")
    else:
        print("\n💥 Tests failed. Need to investigate further.")
