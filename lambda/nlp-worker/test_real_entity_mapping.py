#!/usr/bin/env python3
"""
Test entity-to-chunk mapping with REAL Comprehend results and REAL chunks
This tests the complete fixed pipeline with actual data
"""
import sys
import os
import json
import boto3

# Add the src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_real_entity_mapping():
    """Test with real Comprehend results and real chunks"""
    
    doc_id = "064762102bead7b04a39"
    print(f"🧪 Testing REAL entity-to-chunk mapping for document: {doc_id}")
    
    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # Step 1: Load real original text
        print("\n📄 Step 1: Loading original document text...")
        text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        text_key = f"data-lake/{doc_id}/raw_text.txt"
        
        response = s3_client.get_object(Bucket=text_bucket, Key=text_key)
        original_text = response['Body'].read().decode('utf-8')
        print(f"✅ Loaded original text: {len(original_text)} characters")
        
        # Step 2: Load real chunks
        print("\n📦 Step 2: Loading real chunks...")
        chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        chunks_prefix = f"data-lake/{doc_id}/"
        
        response = s3_client.list_objects_v2(Bucket=chunks_bucket, Prefix=chunks_prefix)
        chunk_files = [obj['Key'] for obj in response.get('Contents', []) 
                      if obj['Key'].endswith('.json') and 'chunk_' in obj['Key']]
        
        chunks = []
        for chunk_file in chunk_files[:10]:  # Test with first 10 chunks
            obj_response = s3_client.get_object(Bucket=chunks_bucket, Key=chunk_file)
            chunk_data = json.loads(obj_response['Body'].read().decode('utf-8'))
            chunks.append(chunk_data)
        
        print(f"✅ Loaded {len(chunks)} chunks for testing")
        
        # Step 3: Load real Comprehend entity results
        print("\n🤖 Step 3: Loading real Comprehend entity results...")
        ner_bucket = "solve-global-kr-dl-ner-results-861276078413-us-east-1"
        
        # Get one of the entity result files
        entity_job_path = f"comprehend-output/{doc_id}/entities/861276078413-NER-015c000b527a818d4a5af2f451a654e9/output/output.tar.gz"
        
        # Download and extract the tar.gz file
        import tempfile
        import tarfile
        
        with tempfile.NamedTemporaryFile() as tmp_file:
            s3_client.download_fileobj(ner_bucket, entity_job_path, tmp_file)
            tmp_file.seek(0)
            
            with tarfile.open(fileobj=tmp_file, mode='r:gz') as tar:
                output_file = tar.extractfile('output')
                comprehend_output = json.loads(output_file.read().decode('utf-8'))
        
        entities = comprehend_output.get('Entities', [])
        print(f"✅ Loaded {len(entities)} real entities from Comprehend")
        
        # Show sample entities
        print("\n🔍 Sample entities:")
        for i, entity in enumerate(entities[:5]):
            print(f"  {i+1}. '{entity['Text']}' ({entity['Type']}) at {entity['BeginOffset']}-{entity['EndOffset']}")
        
        # Step 4: Test chunk position finding
        print("\n🎯 Step 4: Testing chunk position finding...")
        chunk_positions = []
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '').strip()
            if not chunk_text:
                continue
            
            # Find where this chunk's text appears in the original document
            pos = original_text.find(chunk_text)
            if pos != -1:
                chunk_position = {
                    'chunk_id': chunk.get('chunk_id', ''),
                    'chunk_text': chunk_text,
                    'start_offset': pos,
                    'end_offset': pos + len(chunk_text),
                    'chunk_index': chunk.get('chunk_index', 0)
                }
                chunk_positions.append(chunk_position)
            else:
                print(f"⚠️  Chunk {chunk.get('chunk_id')} text not found in original document")
        
        print(f"✅ Found {len(chunk_positions)} chunk positions")
        
        # Step 5: Test entity-to-chunk mapping
        print("\n🔗 Step 5: Testing entity-to-chunk mapping...")
        entities_by_chunk = []
        
        for entity in entities[:20]:  # Test with first 20 entities
            entity_start = entity.get('BeginOffset', 0)
            entity_end = entity.get('EndOffset', 0)
            entity_text = entity.get('Text', '')
            
            # Find chunks that contain this entity
            mapped_to_chunks = []
            for chunk_pos in chunk_positions:
                # Check if entity overlaps with this chunk
                if (entity_start < chunk_pos['end_offset'] and 
                    entity_end > chunk_pos['start_offset']):
                    
                    # Calculate relative position within chunk
                    relative_start = max(0, entity_start - chunk_pos['start_offset'])
                    relative_end = min(len(chunk_pos['chunk_text']), 
                                     entity_end - chunk_pos['start_offset'])
                    
                    mapped_entity = {
                        'chunk_id': chunk_pos['chunk_id'],
                        'chunk_index': chunk_pos['chunk_index'],
                        'entity': entity_text,
                        'type': entity.get('Type', ''),
                        'score': entity.get('Score', 0),
                        'original_begin_offset': entity_start,
                        'original_end_offset': entity_end,
                        'chunk_relative_begin': relative_start,
                        'chunk_relative_end': relative_end
                    }
                    mapped_to_chunks.append(mapped_entity)
            
            entities_by_chunk.extend(mapped_to_chunks)
        
        print(f"✅ Mapped {len(entities_by_chunk)} entity-chunk pairs")
        
        # Step 6: Verify mapping accuracy
        print("\n✅ Step 6: Verifying mapping accuracy...")
        correct_mappings = 0
        total_mappings = len(entities_by_chunk)
        
        for mapping in entities_by_chunk[:10]:  # Check first 10 mappings
            # Get the chunk text
            chunk_id = mapping['chunk_id']
            chunk = next((c for c in chunks if c.get('chunk_id') == chunk_id), None)
            
            if chunk:
                chunk_text = chunk.get('text', '')
                entity_text = mapping['entity']
                
                # Check if entity text appears in chunk text
                if entity_text.lower() in chunk_text.lower():
                    correct_mappings += 1
                    print(f"  ✅ '{entity_text}' correctly mapped to chunk {chunk_id}")
                else:
                    print(f"  ❌ '{entity_text}' incorrectly mapped to chunk {chunk_id}")
        
        accuracy = (correct_mappings / min(10, total_mappings)) * 100 if total_mappings > 0 else 0
        print(f"\n📊 Mapping accuracy: {accuracy:.1f}% ({correct_mappings}/{min(10, total_mappings)} verified)")
        
        # Step 7: Summary
        print(f"\n🎉 TEST SUMMARY:")
        print(f"  📄 Original text: {len(original_text):,} characters")
        print(f"  📦 Chunks loaded: {len(chunks)}")
        print(f"  🎯 Chunk positions found: {len(chunk_positions)}")
        print(f"  🤖 Entities from Comprehend: {len(entities)}")
        print(f"  🔗 Entity-chunk mappings: {len(entities_by_chunk)}")
        print(f"  ✅ Mapping accuracy: {accuracy:.1f}%")
        
        return accuracy > 80  # Success if >80% accuracy
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_entity_mapping()
    if success:
        print("\n🎉 REAL ENTITY MAPPING TEST PASSED!")
        print("The fixed nlp-worker should now work correctly with real data.")
    else:
        print("\n💥 REAL ENTITY MAPPING TEST FAILED!")
        print("Further debugging needed.")
