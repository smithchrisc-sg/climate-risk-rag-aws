#!/usr/bin/env python3
"""
Compare chunk text vs original text to find exact differences
"""
import boto3
import json

def compare_texts():
    """Compare the chunk text with the original text at the found position"""
    
    doc_id = "064762102bead7b04a39"
    missing_chunk_id = "064762102bead7b04a39_chunk_0004"
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Load original text
    text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
    text_key = f"data-lake/{doc_id}/raw_text.txt"
    response = s3_client.get_object(Bucket=text_bucket, Key=text_key)
    original_text = response['Body'].read().decode('utf-8')
    
    # Load chunk
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    chunk_key = f"data-lake/{doc_id}/{missing_chunk_id}.json"
    response = s3_client.get_object(Bucket=chunks_bucket, Key=chunk_key)
    chunk_data = json.loads(response['Body'].read().decode('utf-8'))
    chunk_text = chunk_data.get('text', '').strip()
    
    # We know the fuzzy match is at position 95
    fuzzy_pos = 95
    
    print(f"🔍 Detailed text comparison at position {fuzzy_pos}")
    print(f"📦 Chunk text length: {len(chunk_text)}")
    
    # Extract the corresponding section from original text
    original_section = original_text[fuzzy_pos:fuzzy_pos + len(chunk_text)]
    print(f"📄 Original section length: {len(original_section)}")
    
    print(f"\n📝 CHUNK TEXT:")
    print(f"'{chunk_text}'")
    
    print(f"\n📄 ORIGINAL TEXT (same length):")
    print(f"'{original_section}'")
    
    print(f"\n🔍 Character-by-character comparison:")
    differences = []
    
    min_len = min(len(chunk_text), len(original_section))
    for i in range(min_len):
        c1 = chunk_text[i]
        c2 = original_section[i]
        if c1 != c2:
            differences.append({
                'position': i,
                'chunk_char': c1,
                'original_char': c2,
                'chunk_ord': ord(c1),
                'original_ord': ord(c2)
            })
    
    if differences:
        print(f"❌ Found {len(differences)} character differences:")
        for diff in differences[:10]:  # Show first 10 differences
            print(f"   Position {diff['position']}: chunk='{diff['chunk_char']}' (ord {diff['chunk_ord']}) vs original='{diff['original_char']}' (ord {diff['original_ord']})")
    else:
        print(f"✅ No character differences found in first {min_len} characters")
    
    # Check if lengths are different
    if len(chunk_text) != len(original_section):
        print(f"\n📏 Length difference:")
        print(f"   Chunk: {len(chunk_text)} characters")
        print(f"   Original: {len(original_section)} characters")
        print(f"   Difference: {len(original_section) - len(chunk_text)}")
        
        if len(original_section) > len(chunk_text):
            extra_text = original_section[len(chunk_text):]
            print(f"   Extra text in original: '{extra_text}'")
        else:
            extra_text = chunk_text[len(original_section):]
            print(f"   Extra text in chunk: '{extra_text}'")
    
    # Try to find the exact match with different approaches
    print(f"\n🔍 Testing different matching approaches:")
    
    # 1. Normalize whitespace
    chunk_normalized = ' '.join(chunk_text.split())
    original_normalized = ' '.join(original_text.split())
    pos_normalized = original_normalized.find(chunk_normalized)
    print(f"   Normalized whitespace match: {'✅ Found' if pos_normalized != -1 else '❌ Not found'}")
    
    # 2. Remove all whitespace
    chunk_no_space = ''.join(chunk_text.split())
    original_no_space = ''.join(original_text.split())
    pos_no_space = original_no_space.find(chunk_no_space)
    print(f"   No whitespace match: {'✅ Found' if pos_no_space != -1 else '❌ Not found'}")
    
    # 3. Case insensitive
    pos_case_insensitive = original_text.lower().find(chunk_text.lower())
    print(f"   Case insensitive match: {'✅ Found' if pos_case_insensitive != -1 else '❌ Not found'}")
    
    # 4. Try finding a longer exact match from the fuzzy position
    print(f"\n🔍 Finding longest exact match from position {fuzzy_pos}:")
    exact_match_length = 0
    for i in range(min(len(chunk_text), len(original_text) - fuzzy_pos)):
        if chunk_text[i] == original_text[fuzzy_pos + i]:
            exact_match_length = i + 1
        else:
            break
    
    print(f"   Exact match length: {exact_match_length} characters")
    if exact_match_length < len(chunk_text):
        print(f"   First difference at position {exact_match_length}:")
        if exact_match_length < len(chunk_text) and fuzzy_pos + exact_match_length < len(original_text):
            chunk_char = chunk_text[exact_match_length]
            orig_char = original_text[fuzzy_pos + exact_match_length]
            print(f"     Chunk: '{chunk_char}' (ord {ord(chunk_char)})")
            print(f"     Original: '{orig_char}' (ord {ord(orig_char)})")

if __name__ == "__main__":
    compare_texts()
