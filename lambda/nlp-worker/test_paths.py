#!/usr/bin/env python3
"""
Simple test to verify S3 paths are correct for nlp-worker
"""
import boto3
import json

def test_s3_paths():
    """Test that the corrected S3 paths work"""
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    doc_id = "064762102bead7b04a39"
    
    print(f"🧪 Testing S3 paths for document: {doc_id}")
    
    # Test 1: Text bucket and path
    print("\n📄 Test 1: Text loading path...")
    text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
    text_key = f"data-lake/{doc_id}/raw_text.txt"
    
    try:
        response = s3_client.get_object(Bucket=text_bucket, Key=text_key)
        text_content = response['Body'].read().decode('utf-8')
        print(f"✅ Text loaded: {len(text_content)} characters")
        print(f"First 100 chars: {text_content[:100]}...")
    except Exception as e:
        print(f"❌ Text loading failed: {e}")
        return False
    
    # Test 2: Chunks bucket and path
    print("\n📦 Test 2: Chunks loading path...")
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    chunks_prefix = f"data-lake/{doc_id}/"
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=chunks_bucket,
            Prefix=chunks_prefix
        )
        
        chunk_files = [obj['Key'] for obj in response.get('Contents', []) 
                      if obj['Key'].endswith('.json') and 'chunk_' in obj['Key']]
        
        print(f"✅ Found {len(chunk_files)} chunk files")
        
        if chunk_files:
            # Load first chunk to verify structure
            first_chunk_key = chunk_files[0]
            chunk_response = s3_client.get_object(Bucket=chunks_bucket, Key=first_chunk_key)
            chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
            
            print(f"First chunk ID: {chunk_data.get('chunk_id', 'NO_ID')}")
            print(f"First chunk text (100 chars): {chunk_data.get('text', '')[:100]}...")
            
            # Test if chunk text appears in original text
            chunk_text = chunk_data.get('text', '').strip()
            if chunk_text and chunk_text in text_content:
                print(f"✅ Chunk text found in original document")
            else:
                print(f"⚠️  Chunk text not found in original document")
                
    except Exception as e:
        print(f"❌ Chunks loading failed: {e}")
        return False
    
    print("\n🎉 Path verification complete!")
    return True

if __name__ == "__main__":
    success = test_s3_paths()
    if success:
        print("✅ S3 paths are working correctly")
    else:
        print("❌ S3 path issues need to be resolved")
