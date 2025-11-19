#!/usr/bin/env python3
"""Upload missing documents from simple list to S3 bucket"""

import json
import subprocess
import os
import sys
from pathlib import Path

# Configuration
S3_BUCKET = "solve-global-kr-documents-861276078413-us-east-1"
LOCAL_PDF_DIR = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/data/raw"
SIMPLE_MANIFEST = "wb_natcat_tsd_simple.jsonl"

def get_s3_document_ids():
    """Get existing document IDs from S3 bucket"""
    print("Fetching existing S3 document IDs...")
    
    cmd = [
        "aws", "s3api", "list-objects-v2",
        "--bucket", S3_BUCKET,
        "--prefix", "documents/",
        "--query", "Contents[].Key",
        "--output", "json"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        s3_keys = json.loads(result.stdout) if result.stdout.strip() else []
        
        s3_doc_ids = set()
        for key in s3_keys:
            if key.startswith("documents/") and key.endswith(".pdf"):
                doc_id = key[10:-4]  # Remove "documents/" and ".pdf"
                s3_doc_ids.add(doc_id)
        
        return s3_doc_ids
    
    except subprocess.CalledProcessError as e:
        print(f"Error fetching S3 objects: {e}")
        return set()

def get_simple_document_ids():
    """Get document IDs from simple manifest"""
    simple_doc_ids = set()
    
    with open(SIMPLE_MANIFEST, "r") as f:
        for line in f:
            doc = json.loads(line.strip())
            simple_doc_ids.add(doc["doc_id"])
    
    return simple_doc_ids

def find_missing_documents():
    """Find documents that need to be uploaded"""
    s3_doc_ids = get_s3_document_ids()
    simple_doc_ids = get_simple_document_ids()
    
    missing_doc_ids = simple_doc_ids - s3_doc_ids
    
    print(f"Simple manifest: {len(simple_doc_ids)} documents")
    print(f"Already in S3: {len(s3_doc_ids)} documents")
    print(f"Missing from S3: {len(missing_doc_ids)} documents")
    
    return missing_doc_ids

def check_local_files(missing_doc_ids):
    """Check which missing documents exist locally"""
    local_pdf_dir = Path(LOCAL_PDF_DIR)
    
    available_locally = []
    not_found_locally = []
    
    for doc_id in missing_doc_ids:
        pdf_path = local_pdf_dir / f"{doc_id}.pdf"
        if pdf_path.exists():
            available_locally.append((doc_id, pdf_path))
        else:
            not_found_locally.append(doc_id)
    
    print(f"Available locally: {len(available_locally)} documents")
    print(f"Not found locally: {len(not_found_locally)} documents")
    
    if not_found_locally:
        print(f"First 10 missing locally: {list(not_found_locally)[:10]}")
    
    return available_locally, not_found_locally

def upload_documents(documents_to_upload, dry_run=True):
    """Upload documents to S3"""
    if dry_run:
        print(f"\n=== DRY RUN: Would upload {len(documents_to_upload)} documents ===")
        for i, (doc_id, pdf_path) in enumerate(documents_to_upload[:5]):
            print(f"  {i+1}. {doc_id}.pdf ({pdf_path.stat().st_size} bytes)")
        if len(documents_to_upload) > 5:
            print(f"  ... and {len(documents_to_upload) - 5} more")
        return
    
    print(f"\n=== UPLOADING {len(documents_to_upload)} documents ===")
    
    success_count = 0
    error_count = 0
    
    for i, (doc_id, pdf_path) in enumerate(documents_to_upload):
        s3_key = f"documents/{doc_id}.pdf"
        
        print(f"Uploading {i+1}/{len(documents_to_upload)}: {doc_id}.pdf")
        
        cmd = [
            "aws", "s3", "cp",
            str(pdf_path),
            f"s3://{S3_BUCKET}/{s3_key}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            success_count += 1
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i+1}/{len(documents_to_upload)} uploaded")
        
        except subprocess.CalledProcessError as e:
            print(f"  ERROR uploading {doc_id}: {e}")
            error_count += 1
    
    print(f"\n=== UPLOAD COMPLETE ===")
    print(f"Successfully uploaded: {success_count}")
    print(f"Errors: {error_count}")

def main():
    print("=== MISSING DOCUMENT UPLOAD TOOL ===")
    
    # Find missing documents
    missing_doc_ids = find_missing_documents()
    
    if not missing_doc_ids:
        print("✅ All documents from simple manifest are already in S3!")
        return
    
    # Check local availability
    available_locally, not_found_locally = check_local_files(missing_doc_ids)
    
    if not available_locally:
        print("❌ No missing documents found locally!")
        return
    
    # Ask for confirmation
    print(f"\nReady to upload {len(available_locally)} documents to S3.")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        upload_documents(available_locally, dry_run=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "--upload":
        response = input("Continue with upload? (yes/no): ")
        if response.lower() == 'yes':
            upload_documents(available_locally, dry_run=False)
        else:
            print("Upload cancelled.")
    else:
        print("Usage:")
        print("  python3 upload_missing_docs.py --dry-run   # Show what would be uploaded")
        print("  python3 upload_missing_docs.py --upload    # Actually upload files")

if __name__ == "__main__":
    main()
