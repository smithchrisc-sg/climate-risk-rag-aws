#!/usr/bin/env python3
"""
Backfill Document Hashes for Textract-Processed Documents

Retroactively adds document hashes to the metadata of documents that have
completed text extraction but don't have hashes stored yet.

This prevents reprocessing during development and future repository rescans.
"""

import boto3
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append('/Users/chris/climate-risk-rag-aws/layers/database-core-layer/python')
from utils.DatabaseManager import DatabaseManager

class DocumentHashBackfiller:
    """Backfill document hashes for already-processed documents"""
    
    def __init__(self):
        self.s3 = boto3.client('s3', region_name='us-east-1')
        self.db_manager = DatabaseManager()
        self.source_bucket = 'solve-global-kr-dl-source-documents-861276078413-us-east-1'
        
    def calculate_document_hash(self, bucket: str, key: str) -> str:
        """
        Calculate document hash using ETag for single-part uploads
        
        Returns:
            Hash string in format "md5:hash" or "sha256:hash"
        """
        try:
            # Get object metadata
            response = self.s3.head_object(Bucket=bucket, Key=key)
            etag = response['ETag'].strip('"')
            file_size = response['ContentLength']
            
            # Check if multipart upload (has hyphen in ETag)
            if '-' in etag:
                print(f"  ⚠️  Multipart upload detected, calculating full hash...")
                # Download and hash full content
                obj = self.s3.get_object(Bucket=bucket, Key=key)
                content = obj['Body'].read()
                
                import hashlib
                hash_value = hashlib.sha256(content).hexdigest()
                return f"sha256:{hash_value}"
            else:
                # Single-part upload - ETag is MD5
                return f"md5:{etag}"
                
        except Exception as e:
            print(f"  ❌ Error calculating hash: {e}")
            raise
    
    def get_documents_needing_hashes(self) -> List[Dict]:
        """
        Get documents that have completed text extraction but don't have hashes
        
        Returns:
            List of dicts with doc_id and metadata
        """
        query = """
            SELECT DISTINCT doc_id, metadata, timestamp
            FROM document_processing_status
            WHERE stage = 'textract_complete'
            AND status = 'completed'
            AND (metadata IS NULL OR NOT metadata ? 'document_hash')
            ORDER BY timestamp DESC
        """
        
        results = self.db_manager.execute_query(query)
        
        documents = []
        for row in results:
            documents.append({
                'doc_id': row[0],
                'metadata': row[1] or {},
                'timestamp': row[2]
            })
        
        return documents
    
    def get_document_s3_key(self, doc_id: str) -> Optional[str]:
        """
        Find S3 key for document by doc_id
        Checks both data-lake/ and documents/ prefixes
        """
        # Try data-lake prefix first (most common)
        for prefix in ['data-lake/', 'documents/', '']:
            key = f"{prefix}{doc_id}.pdf"
            try:
                self.s3.head_object(Bucket=self.source_bucket, Key=key)
                return key
            except:
                continue
        
        return None
    
    def backfill_hash(self, doc_id: str, metadata: Dict) -> bool:
        """
        Calculate and store hash for a single document
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\n📄 Processing: {doc_id}")
            
            # Find document in S3
            s3_key = self.get_document_s3_key(doc_id)
            if not s3_key:
                print(f"  ❌ Document not found in S3")
                return False
            
            print(f"  📍 Found at: s3://{self.source_bucket}/{s3_key}")
            
            # Calculate hash
            doc_hash = self.calculate_document_hash(self.source_bucket, s3_key)
            print(f"  🔐 Hash: {doc_hash}")
            
            # Update metadata with hash
            updated_metadata = metadata.copy()
            updated_metadata['document_hash'] = doc_hash
            updated_metadata['hash_backfilled_at'] = datetime.utcnow().isoformat() + 'Z'
            
            # Store updated metadata
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='textract_complete',
                status='completed',
                metadata=updated_metadata
            )
            
            print(f"  ✅ Hash stored in metadata")
            return True
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    def run(self, dry_run: bool = False, limit: int = None):
        """
        Run the backfill process
        
        Args:
            dry_run: If True, only show what would be done
            limit: Optional limit on number of documents to process
        """
        print("=" * 60)
        print("Document Hash Backfill Script")
        print("=" * 60)
        
        # Get documents needing hashes
        print("\n🔍 Finding documents without hashes...")
        documents = self.get_documents_needing_hashes()
        
        if not documents:
            print("✅ No documents need hash backfill!")
            return
        
        print(f"📊 Found {len(documents)} documents without hashes")
        
        if limit:
            documents = documents[:limit]
            print(f"📌 Limited to first {limit} documents")
        
        if dry_run:
            print("\n🔍 DRY RUN - No changes will be made")
            print("\nDocuments that would be processed:")
            for doc in documents[:10]:
                print(f"  - {doc['doc_id']} (processed: {doc['timestamp']})")
            if len(documents) > 10:
                print(f"  ... and {len(documents) - 10} more")
            return
        
        # Process documents
        print("\n🚀 Starting backfill process...")
        successful = 0
        failed = 0
        
        for i, doc in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}]", end=" ")
            if self.backfill_hash(doc['doc_id'], doc['metadata']):
                successful += 1
            else:
                failed += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("BACKFILL COMPLETE")
        print("=" * 60)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {len(documents)}")
        print(f"💾 Success rate: {successful/len(documents)*100:.1f}%")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill document hashes for processed documents')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of documents to process')
    
    args = parser.parse_args()
    
    backfiller = DocumentHashBackfiller()
    backfiller.run(dry_run=args.dry_run, limit=args.limit)

if __name__ == '__main__':
    main()
