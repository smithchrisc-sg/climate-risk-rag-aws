#!/usr/bin/env python3
"""
Estimate page counts for documents in manifest using local PDF files
"""
import json
import os
import subprocess
from pathlib import Path

def get_page_count(pdf_path):
    """Get page count from PDF file using pdfinfo or similar"""
    try:
        # Try using pdfinfo (part of poppler-utils)
        result = subprocess.run(
            ['pdfinfo', str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
    except:
        pass
    
    # Fallback: try pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except:
        pass
    
    # Fallback: try PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except:
        pass
    
    return None

def estimate_manifest_pages(manifest_path, pdf_directory):
    """Estimate total pages for all documents in manifest"""
    
    pdf_dir = Path(pdf_directory)
    total_pages = 0
    total_docs = 0
    found_docs = 0
    missing_docs = []
    page_counts = []
    
    print(f"Reading manifest: {manifest_path}")
    print(f"Looking for PDFs in: {pdf_directory}\n")
    
    with open(manifest_path, 'r') as f:
        for line in f:
            doc = json.loads(line.strip())
            
            # Skip documents marked with skip flag
            if doc.get('skip', False):
                continue
            
            total_docs += 1
            doc_id = doc['doc_id']
            title = doc['title']
            
            # Find PDF by doc_id
            pdf_path = pdf_dir / f"{doc_id}.pdf"
            
            if pdf_path.exists():
                pages = get_page_count(pdf_path)
                if pages:
                    total_pages += pages
                    found_docs += 1
                    page_counts.append(pages)
                    print(f"✓ {doc_id}.pdf: {pages} pages")
                else:
                    print(f"✗ {doc_id}.pdf: Error reading PDF")
                    missing_docs.append(doc_id)
            else:
                print(f"✗ {doc_id}.pdf: File not found")
                missing_docs.append(doc_id)
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total documents in manifest (excluding skip): {total_docs}")
    print(f"PDFs found and readable: {found_docs}")
    print(f"PDFs missing or unreadable: {len(missing_docs)}")
    print(f"\nTotal pages (found documents): {total_pages:,}")
    
    if page_counts:
        avg_pages = total_pages / len(page_counts)
        print(f"Average pages per document: {avg_pages:.1f}")
        print(f"Min pages: {min(page_counts)}")
        print(f"Max pages: {max(page_counts)}")
        print(f"Median pages: {sorted(page_counts)[len(page_counts)//2]}")
        
        # Estimate for missing documents
        if missing_docs:
            estimated_missing_pages = len(missing_docs) * avg_pages
            estimated_total = total_pages + estimated_missing_pages
            print(f"\nEstimated pages for missing docs: {estimated_missing_pages:.0f}")
            print(f"Estimated total pages: {estimated_total:.0f}")
            
            # Cost estimate
            textract_cost = estimated_total * 0.065
            print(f"\nEstimated Textract cost (if all new): ${textract_cost:,.2f}")
            print(f"Estimated Textract cost (if 50% duplicates): ${textract_cost/2:,.2f}")
    
    if missing_docs and len(missing_docs) <= 20:
        print(f"\nMissing files:")
        for doc_id in missing_docs[:20]:
            print(f"  - {doc_id}.pdf")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Estimate page counts for manifest documents')
    parser.add_argument('--manifest', required=True, help='Path to manifest JSONL file')
    parser.add_argument('--pdf-dir', required=True, help='Directory containing PDF files')
    
    args = parser.parse_args()
    
    estimate_manifest_pages(args.manifest, args.pdf_dir)
