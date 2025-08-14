#!/usr/bin/env python3
"""
Debug why chunk 064762102bead7b04a39_chunk_0004 was not found in original document
"""
import boto3
import json

def debug_missing_chunk():
    """Investigate the missing chunk issue"""
    
    doc_id = "064762102bead7b04a39"
    missing_chunk_id = "064762102bead7b04a39_chunk_0004"
    
    print(f"🔍 Debugging missing chunk: {missing_chunk_id}")
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # Load original text
        print("\n📄 Loading original document text...")
        text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        text_key = f"data-lake/{doc_id}/raw_text.txt"
        
        response = s3_client.get_object(Bucket=text_bucket, Key=text_key)
        original_text = response['Body'].read().decode('utf-8')
        print(f"✅ Original text length: {len(original_text)} characters")
        
        # Load the specific missing chunk
        print(f"\n📦 Loading missing chunk: {missing_chunk_id}")
        chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        chunk_key = f"data-lake/{doc_id}/{missing_chunk_id}.json"
        
        response = s3_client.get_object(Bucket=chunks_bucket, Key=chunk_key)
        chunk_data = json.loads(response['Body'].read().decode('utf-8'))
        
        chunk_text = chunk_data.get('text', '').strip()
        print(f"✅ Chunk text length: {len(chunk_text)} characters")
        print(f"📝 Chunk text preview (first 200 chars):")
        print(f"   '{chunk_text[:200]}...'")
        
        # Try to find the chunk text in original
        print(f"\n🔍 Searching for chunk text in original document...")
        pos = original_text.find(chunk_text)
        
        if pos != -1:
            print(f"✅ FOUND at position {pos}-{pos + len(chunk_text)}")
            return
        
        print(f"❌ NOT FOUND with exact match")
        
        # Try different approaches to find why it's not matching
        print(f"\n🔍 Investigating potential issues...")
        
        # Check for whitespace/newline differences
        chunk_text_normalized = ' '.join(chunk_text.split())
        original_text_normalized = ' '.join(original_text.split())
        
        pos_normalized = original_text_normalized.find(chunk_text_normalized)
        if pos_normalized != -1:
            print(f"✅ FOUND with normalized whitespace at position {pos_normalized}")
            print(f"   Issue: Whitespace/newline differences")
            return
        
        # Check for partial matches
        print(f"\n🔍 Checking for partial matches...")
        chunk_words = chunk_text.split()
        if len(chunk_words) > 10:
            # Try first 10 words
            first_part = ' '.join(chunk_words[:10])
            pos_partial = original_text.find(first_part)
            if pos_partial != -1:
                print(f"✅ PARTIAL MATCH found (first 10 words) at position {pos_partial}")
                print(f"   First part: '{first_part}'")
                
                # Show what's actually at that position in original
                actual_text = original_text[pos_partial:pos_partial + len(chunk_text)]
                print(f"   Actual text at position: '{actual_text[:200]}...'")
                
                # Compare character by character
                print(f"\n🔍 Character-by-character comparison:")
                for i, (c1, c2) in enumerate(zip(chunk_text[:100], actual_text[:100])):
                    if c1 != c2:
                        print(f"   Difference at position {i}: chunk='{c1}' (ord {ord(c1)}) vs actual='{c2}' (ord {ord(c2)})")
                        break
                return
        
        # Check if chunk text appears anywhere with fuzzy matching
        print(f"\n🔍 Checking for fuzzy matches...")
        chunk_start = chunk_text[:50].strip()
        pos_fuzzy = original_text.find(chunk_start)
        if pos_fuzzy != -1:
            print(f"✅ FUZZY MATCH found (first 50 chars) at position {pos_fuzzy}")
            print(f"   Chunk start: '{chunk_start}'")
            actual_at_pos = original_text[pos_fuzzy:pos_fuzzy + 100]
            print(f"   Actual at pos: '{actual_at_pos}'")
        else:
            print(f"❌ No fuzzy match found")
            
        # Show chunk metadata for more clues
        print(f"\n📋 Chunk metadata:")
        for key, value in chunk_data.items():
            if key != 'text':
                print(f"   {key}: {value}")
                
        # Check if this is a special type of chunk (table, header, etc.)
        section_type = chunk_data.get('section_type', 'unknown')
        print(f"\n🏷️  Section type: {section_type}")
        
        if section_type in ['table', 'header', 'footer', 'caption']:
            print(f"   ℹ️  This is a {section_type} chunk - may have formatting differences")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_missing_chunk()
