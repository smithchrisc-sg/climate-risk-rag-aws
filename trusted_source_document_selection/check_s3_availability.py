#!/usr/bin/env python3
"""Check if document IDs from lexical list exist in S3 bucket"""

import json
import subprocess
import sys

def get_s3_document_ids():
    """Get all document IDs from S3 bucket"""
    print("Fetching all document IDs from S3 bucket...")
    
    # Get all objects in the documents/ prefix
    cmd = [
        "aws", "s3api", "list-objects-v2",
        "--bucket", "solve-global-kr-documents-861276078413-us-east-1",
        "--prefix", "documents/",
        "--query", "Contents[].Key",
        "--output", "json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        s3_keys = json.loads(result.stdout)
        
        # Extract doc_ids from keys like "documents/doc_id.pdf"
        s3_doc_ids = set()
        for key in s3_keys:
            if key.startswith("documents/") and key.endswith(".pdf"):
                doc_id = key[10:-4]  # Remove "documents/" and ".pdf"
                s3_doc_ids.add(doc_id)
        
        return s3_doc_ids
    
    except subprocess.CalledProcessError as e:
        print(f"Error fetching S3 objects: {e}")
        print(f"stderr: {e.stderr}")
        return set()

def get_lexical_document_ids():
    """Get document IDs from lexical manifest"""
    lexical_doc_ids = set()
    
    with open("wb_natcat_tsd_manifest_lexical.jsonl", "r") as f:
        for line in f:
            doc = json.loads(line.strip())
            lexical_doc_ids.add(doc["doc_id"])
    
    return lexical_doc_ids

def main():
    print("=== S3 DOCUMENT AVAILABILITY CHECK ===")
    
    # Get document IDs from both sources
    lexical_doc_ids = get_lexical_document_ids()
    s3_doc_ids = get_s3_document_ids()
    
    print(f"Lexical manifest contains: {len(lexical_doc_ids)} documents")
    print(f"S3 bucket contains: {len(s3_doc_ids)} documents")
    
    # Check availability
    available_docs = lexical_doc_ids.intersection(s3_doc_ids)
    missing_docs = lexical_doc_ids - s3_doc_ids
    
    print(f"\nAvailable in S3: {len(available_docs)} documents ({len(available_docs)/len(lexical_doc_ids)*100:.1f}%)")
    print(f"Missing from S3: {len(missing_docs)} documents ({len(missing_docs)/len(lexical_doc_ids)*100:.1f}%)")
    
    if missing_docs:
        print(f"\nMissing document IDs:")
        for doc_id in sorted(missing_docs):
            print(f"  {doc_id}")
    else:
        print("\n✅ All documents from lexical manifest are available in S3!")

if __name__ == "__main__":
    main()
