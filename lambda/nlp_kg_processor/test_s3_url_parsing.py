#!/usr/bin/env python3
"""
Test script for S3 URL parsing functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from data_retriever import DataRetriever

def test_s3_url_parsing():
    """Test the S3 URL parsing functionality."""
    retriever = DataRetriever()
    
    # Test cases
    test_urls = [
        "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities_by_chunk.json",
        "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases_by_chunk.json",
        "s3://solve-global-kr-dl-chunks-861276078413-us-east-1/chunks/064762102bead7b04a39/",
        "s3://my-bucket/path/to/file.txt"
    ]
    
    print("Testing S3 URL parsing...")
    print("=" * 50)
    
    for url in test_urls:
        try:
            bucket, key = retriever._parse_s3_url(url)
            print(f"✅ {url}")
            print(f"   Bucket: {bucket}")
            print(f"   Key: {key}")
            print()
        except Exception as e:
            print(f"❌ {url}")
            print(f"   Error: {str(e)}")
            print()
    
    # Test error cases
    print("Testing error cases...")
    print("=" * 50)
    
    error_urls = [
        "https://example.com/file.txt",  # Wrong scheme
        "s3://",  # No bucket or key
        "s3://bucket",  # No key
        "invalid-url",  # Invalid format
        ""  # Empty string
    ]
    
    for url in error_urls:
        try:
            bucket, key = retriever._parse_s3_url(url)
            print(f"❌ Expected error but got: bucket={bucket}, key={key} for {url}")
        except ValueError as e:
            print(f"✅ Correctly caught error: {str(e)} for {url}")
        except Exception as e:
            print(f"❌ Unexpected error type: {type(e).__name__}: {str(e)} for {url}")
        print()

if __name__ == "__main__":
    test_s3_url_parsing()
