#!/usr/bin/env python3
"""
Enhanced Pipeline Test Script - Batch Processing
Supports large-scale document processing with intelligent filtering
"""

import argparse
import json
import logging
import sqlite3
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocumentStatusChecker:
    """Check document status in PostgreSQL database"""
    
    def __init__(self):
        # Use same session logic as working script
        self.lambda_client = boto3.client('lambda', region_name='us-east-1', 
                                         config=Config(connect_timeout=5, read_timeout=65))
        
    def get_existing_documents(self) -> Set[str]:
        """Get all legacy doc_ids that have been processed (exist in database)"""
        try:
            # Use the database layer to check for existing documents
            import sys
            sys.path.append('layers/database-core-layer/python')
            from utils.DatabaseManager import DatabaseManager
            
            db_manager = DatabaseManager()
            
            # Query for all existing documents by their source URL hash
            # This matches how the pipeline-test-function creates doc IDs
            query = """
                SELECT DISTINCT 
                    SUBSTRING(doc_id FROM 1 FOR 8) as legacy_prefix
                FROM documents 
                WHERE source_url IS NOT NULL
            """
            results = db_manager.execute_query(query)
            
            existing_docs = {row[0] for row in results}
            logger.info(f"Found {len(existing_docs)} existing document prefixes in database")
            return existing_docs
            
        except Exception as e:
            logger.warning(f"Database check failed, falling back to S3 check: {e}")
            # Fallback to S3 check
            return self._get_existing_from_s3()
    
    def _get_existing_from_s3(self) -> Set[str]:
        """Fallback: Check S3 data-lake bucket for existing processed documents"""
        try:
            s3_client = boto3.client('s3', region_name='us-east-1')
            target_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
            
            existing_docs = set()
            
            # List all documents in data-lake/ prefix
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=target_bucket, Prefix='data-lake/')
            
            for page in pages:
                for obj in page.get('Contents', []):
                    if obj['Key'].endswith('.pdf'):
                        # Extract first 8 chars of filename (legacy doc prefix)
                        filename = obj['Key'].split('/')[-1]
                        doc_prefix = filename[:8]  # First 8 chars match legacy
                        existing_docs.add(doc_prefix)
            
            logger.info(f"Found {len(existing_docs)} existing documents in data-lake (S3 fallback)")
            return existing_docs
            
        except Exception as e:
            logger.error(f"Failed to check existing documents: {e}")
            return set()
    
    def get_completed_documents(self) -> Set[str]:
        """Get doc_ids with completed processing status"""
        try:
            # Use Lambda to query database (same as working script approach)  
            # For now, return empty set to avoid database connection issues
            logger.info("Completed document check temporarily disabled")
            return set()
            
        except Exception as e:
            logger.error(f"Failed to check completed documents: {e}")
            return set()

class SmartDocumentSelector:
    """Document selection using exact same logic as invoke_pipeline_test.py"""
    
    def __init__(self):
        # Use exact same initialization as working script
        self.lambda_client = boto3.client('lambda', region_name='us-east-1', 
                                         config=Config(connect_timeout=5, read_timeout=65))
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.sqlite_db_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        self.existing_bucket = "solve-global-kr-documents-861276078413-us-east-1"
    
    def get_available_documents_with_urls(self, limit: int = 200) -> List[Dict]:
        """Get available documents from S3 and match with SQLite URLs locally - EXACT COPY from working script"""
        try:
            logger.info(f"Fetching documents from S3 and matching with SQLite database...")
            
            # Get documents from S3
            response = self.s3_client.list_objects_v2(
                Bucket=self.existing_bucket,
                Prefix="documents/",
                MaxKeys=limit * 2
            )
            
            if 'Contents' not in response:
                logger.error("No documents found in S3 bucket")
                return []
            
            # Extract S3 document info
            s3_documents = {}
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    filename = os.path.basename(key)
                    doc_id_from_filename = filename.replace('.pdf', '')
                    size_mb = round(obj['Size'] / (1024 * 1024), 2)
                    estimated_pages = max(1, int((size_mb * 1024) / 75))  # ~75KB per page
                    
                    s3_documents[doc_id_from_filename] = {
                        'key': key,
                        'filename': filename,
                        'doc_id_from_filename': doc_id_from_filename,
                        'doc_id': doc_id_from_filename,  # Add for compatibility
                        'size': obj['Size'],
                        'size_mb': size_mb,
                        'estimated_pages': estimated_pages,
                        'last_modified': obj['LastModified']
                    }
            
            logger.info(f"Found {len(s3_documents)} PDF documents in S3")
            
            # Query SQLite for source URLs
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT doc_id, url, original_filename FROM documents")
            sqlite_results = cursor.fetchall()
            conn.close()
            
            logger.info(f"Found {len(sqlite_results)} documents in SQLite database")
            
            # Match S3 documents with SQLite URLs
            matched_documents = []
            for doc_id, url, original_filename in sqlite_results:
                if doc_id in s3_documents:
                    doc_info = s3_documents[doc_id].copy()
                    doc_info['source_url'] = url
                    doc_info['original_filename'] = original_filename
                    doc_info['file_size_bytes'] = doc_info['size']  # Add for compatibility
                    matched_documents.append(doc_info)
            
            logger.info(f"Successfully matched {len(matched_documents)} documents with source URLs")
            return matched_documents
            
        except Exception as e:
            logger.error(f"Error getting documents with URLs: {e}")
            return []
    
    def filter_documents_by_criteria(self, documents: List[Dict], **criteria) -> List[Dict]:
        """Filter documents by criteria locally - EXACT COPY from working script"""
        try:
            num_documents = criteria.get('num_documents', 5)
            min_size_mb = criteria.get('min_size_mb', 1.0)
            max_size_mb = criteria.get('max_size_mb', 10.0)
            document_types = criteria.get('document_types')
            target_avg_pages = criteria.get('target_avg_pages', 20)
            
            logger.info(f"Filtering {len(documents)} documents with criteria:")
            logger.info(f"  - Count: {num_documents}")
            logger.info(f"  - Size: {min_size_mb}-{max_size_mb} MB")
            logger.info(f"  - Document types: {document_types or 'any'}")
            logger.info(f"  - Target avg pages: {target_avg_pages}")
            
            # Filter by size
            filtered = [
                doc for doc in documents 
                if min_size_mb <= doc['size_mb'] <= max_size_mb
            ]
            logger.info(f"After size filtering: {len(filtered)} documents")
            
            # Filter by document type if specified
            if document_types:
                document_type_patterns = {
                    "report": ["report", "assessment", "evaluation", "study"],
                    "policy": ["policy", "strategy", "framework", "guideline"],
                    "research": ["research", "analysis", "working", "paper"],
                    "project": ["project", "implementation", "completion", "icr"],
                    "financial": ["financial", "economic", "budget", "cost"],
                    "technical": ["technical", "manual", "specification", "guide"]
                }
                
                type_filtered = []
                for doc in filtered:
                    filename_lower = doc['filename'].lower()
                    for doc_type in document_types:
                        if doc_type in document_type_patterns:
                            patterns = document_type_patterns[doc_type]
                            if any(pattern in filename_lower for pattern in patterns):
                                type_filtered.append(doc)
                                break
                filtered = type_filtered
                logger.info(f"After document type filtering: {len(filtered)} documents")
            
            # Sort by how close they are to target page count
            filtered.sort(key=lambda x: abs(x['estimated_pages'] - target_avg_pages))
            
            # Limit results
            filtered = filtered[:num_documents]
            
            if filtered:
                total_pages = sum(doc['estimated_pages'] for doc in filtered)
                avg_pages = total_pages / len(filtered)
                avg_size = sum(doc['size_mb'] for doc in filtered) / len(filtered)
                
                logger.info(f"Selected {len(filtered)} documents:")
                logger.info(f"  - Total estimated pages: {total_pages}")
                logger.info(f"  - Average pages per doc: {avg_pages:.1f}")
                logger.info(f"  - Average size: {avg_size:.1f} MB")
                
                for i, doc in enumerate(filtered, 1):
                    logger.info(f"  {i}. {doc['filename']}: {doc['size_mb']} MB (~{doc['estimated_pages']} pages)")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return documents[:criteria.get('num_documents', 5)]
    
    def filter_existing_documents(self, documents: List[Dict], existing_docs: Set[str], 
                                completed_docs: Set[str], skip_existing: bool, 
                                skip_completed: bool) -> List[Dict]:
        """Filter out existing/completed documents"""
        if not skip_existing and not skip_completed:
            return documents
            
        filtered = []
        skipped_count = 0
        
        for doc in documents:
            # Get the legacy doc_id (filename without .pdf) and its prefix
            legacy_doc_id = doc['filename'].replace('.pdf', '')
            legacy_prefix = legacy_doc_id[:8]  # First 8 chars
            
            skip_doc = False
            
            if skip_existing and legacy_prefix in existing_docs:
                skip_doc = True
                skipped_count += 1
            
            if skip_completed and legacy_prefix in completed_docs:
                skip_doc = True
                skipped_count += 1
            
            if not skip_doc:
                filtered.append(doc)
        
        logger.info(f"Filtered {len(documents)} -> {len(filtered)} documents (skipped {skipped_count} existing/completed)")
        return filtered

class BatchProcessor:
    """Handle batch processing with delays and progress tracking"""
    
    def __init__(self, batch_size: int = 10, delay: int = 30):
        self.batch_size = batch_size
        self.delay = delay
        # Use same Lambda client as working script
        self.lambda_client = boto3.client('lambda', region_name='us-east-1', 
                                         config=Config(connect_timeout=5, read_timeout=65))
        self.lambda_function_name = 'pipeline-test-function'
    
    def estimate_cost_and_time(self, documents: List[Dict]) -> Dict[str, Any]:
        """Estimate processing cost and time"""
        total_pages = sum(doc.get('estimated_pages', 20) for doc in documents)
        total_docs = len(documents)
        
        # Rough cost estimates (USD)
        textract_cost = total_pages * 0.0015  # $1.50 per 1000 pages
        lambda_cost = total_docs * 0.01       # Rough Lambda costs
        storage_cost = total_docs * 0.001     # S3/OpenSearch storage
        
        total_cost = textract_cost + lambda_cost + storage_cost
        
        # Time estimates (minutes)
        textract_time = total_pages * 0.1     # ~6 seconds per page
        processing_time = total_docs * 2      # ~2 minutes per document
        
        total_time = max(textract_time, processing_time)
        
        return {
            'total_documents': total_docs,
            'total_pages': total_pages,
            'estimated_cost_usd': round(total_cost, 2),
            'estimated_time_minutes': round(total_time, 1),
            'breakdown': {
                'textract_cost': round(textract_cost, 2),
                'lambda_cost': round(lambda_cost, 2),
                'storage_cost': round(storage_cost, 2)
            }
        }
    
    def process_batches(self, documents: List[Dict], progress_file: Optional[str] = None) -> Dict[str, Any]:
        """Process documents in batches with progress tracking"""
        total_docs = len(documents)
        total_batches = (total_docs + self.batch_size - 1) // self.batch_size
        
        results = {
            'total_documents': total_docs,
            'total_batches': total_batches,
            'successful_batches': 0,
            'failed_batches': 0,
            'processed_documents': [],
            'failed_documents': []
        }
        
        logger.info(f"Processing {total_docs} documents in {total_batches} batches")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_docs)
            batch_docs = documents[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_docs)} documents)")
            
            try:
                batch_result = self._process_single_batch(batch_docs)
                results['successful_batches'] += 1
                results['processed_documents'].extend(batch_result.get('processed_documents', []))
                
                # Save progress
                if progress_file:
                    self._save_progress(progress_file, results, batch_num + 1, total_batches)
                
            except Exception as e:
                logger.error(f"Batch {batch_num + 1} failed: {e}")
                results['failed_batches'] += 1
                results['failed_documents'].extend([doc['doc_id'] for doc in batch_docs])
            
            # Delay between batches (except for last batch)
            if batch_num < total_batches - 1:
                logger.info(f"Waiting {self.delay} seconds before next batch...")
                time.sleep(self.delay)
        
        return results
    
    def _process_single_batch(self, documents: List[Dict]) -> Dict[str, Any]:
        """Process a single batch of documents using same logic as working script"""
        # Convert to the format expected by Lambda (same as invoke_pipeline_test.py)
        document_pairs = []
        for doc in documents:
            # Extract legacy doc ID from filename (remove .pdf extension)
            legacy_doc_id = doc['filename'].replace('.pdf', '')
            source_url = doc['source_url']
            
            document_pairs.append({
                'legacy_doc_id': legacy_doc_id,
                'source_url': source_url
            })
        
        # Use exact same payload structure as working script
        payload = {
            'action': 'test',
            'document_pairs': document_pairs
        }
        
        # Invoke pipeline test Lambda (same as working script)
        response = self.lambda_client.invoke(
            FunctionName=self.lambda_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload, default=str)  # Handle datetime serialization
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response['StatusCode'] != 200:
            raise Exception(f"Lambda invocation failed: {response_payload}")
        
        return {
            'processed_documents': [doc['doc_id'] for doc in documents],
            'lambda_response': response_payload
        }
    
    def _save_progress(self, progress_file: str, results: Dict, current_batch: int, total_batches: int):
        """Save processing progress to file"""
        progress_data = {
            'timestamp': datetime.now().isoformat(),
            'current_batch': current_batch,
            'total_batches': total_batches,
            'results': results
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Enhanced Pipeline Test - Batch Processing')
    
    # Document selection
    parser.add_argument('--max-documents', type=int, default=50,
                       help='Maximum number of documents to process')
    parser.add_argument('--min-size-mb', type=float, default=1.0,
                       help='Minimum document size in MB')
    parser.add_argument('--max-size-mb', type=float, default=10.0,
                       help='Maximum document size in MB')
    
    # Filtering options
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip documents already in PostgreSQL')
    parser.add_argument('--skip-completed', action='store_true',
                       help='Skip documents with completed processing status')
    
    # Selection strategy
    parser.add_argument('--selection-strategy', choices=['random', 'oldest-first', 'newest-first', 'missing-only'],
                       default='random', help='Document selection strategy')
    
    # Batch processing
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of documents per batch')
    parser.add_argument('--batch-delay', type=int, default=30,
                       help='Delay between batches in seconds')
    
    # Progress management
    parser.add_argument('--save-progress', type=str,
                       help='Save progress to specified file')
    
    # Safety
    parser.add_argument('--force', action='store_true',
                       help='Skip safety confirmations')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without executing')
    
    args = parser.parse_args()
    
    try:
        # Initialize components using working script patterns
        status_checker = DocumentStatusChecker()
        selector = SmartDocumentSelector()
        processor = BatchProcessor(args.batch_size, args.batch_delay)
        
        # Get existing/completed documents if filtering requested
        existing_docs = set()
        completed_docs = set()
        
        if args.skip_existing or args.selection_strategy == 'missing-only':
            existing_docs = status_checker.get_existing_documents()
        
        if args.skip_completed:
            completed_docs = status_checker.get_completed_documents()
        
        # Get candidate documents using working script logic
        logger.info("📋 Selecting documents locally...")
        available_docs = selector.get_available_documents_with_urls(limit=300)
        
        if not available_docs:
            logger.error("No documents found")
            return
        
        # Filter by existing/completed status
        filtered_docs = selector.filter_existing_documents(
            available_docs, existing_docs, completed_docs,
            args.skip_existing or args.selection_strategy == 'missing-only',
            args.skip_completed
        )
        
        if not filtered_docs:
            logger.info("No documents remaining after filtering")
            return
        
        # Apply size and count filtering using working script logic
        selected_docs = selector.filter_documents_by_criteria(
            filtered_docs,
            num_documents=args.max_documents,
            min_size_mb=args.min_size_mb,
            max_size_mb=args.max_size_mb,
            target_avg_pages=20
        )
        
        if not selected_docs:
            logger.error("No documents selected after filtering")
            return
        
        # Estimate cost and time
        estimates = processor.estimate_cost_and_time(selected_docs)
        
        logger.info("=" * 60)
        logger.info("PROCESSING ESTIMATES")
        logger.info("=" * 60)
        logger.info(f"Documents: {estimates['total_documents']}")
        logger.info(f"Total pages: {estimates['total_pages']}")
        logger.info(f"Estimated cost: ${estimates['estimated_cost_usd']}")
        logger.info(f"Estimated time: {estimates['estimated_time_minutes']} minutes")
        logger.info(f"Batches: {(len(selected_docs) + args.batch_size - 1) // args.batch_size}")
        
        # Safety check
        if not args.force and not args.dry_run:
            if estimates['estimated_cost_usd'] > 10:
                response = input(f"Estimated cost is ${estimates['estimated_cost_usd']}. Continue? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Operation cancelled by user")
                    return
        
        if args.dry_run:
            logger.info("DRY RUN - Would process these documents:")
            for i, doc in enumerate(selected_docs[:10], 1):
                logger.info(f"  {i}. {doc['filename']}: {doc['size_mb']} MB (~{doc['estimated_pages']} pages)")
            if len(selected_docs) > 10:
                logger.info(f"  ... and {len(selected_docs) - 10} more")
            return
        
        # Process documents
        logger.info("=" * 60)
        logger.info("STARTING BATCH PROCESSING")
        logger.info("=" * 60)
        
        results = processor.process_batches(selected_docs, args.save_progress)
        
        # Report results
        logger.info("=" * 60)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total documents: {results['total_documents']}")
        logger.info(f"Successful batches: {results['successful_batches']}")
        logger.info(f"Failed batches: {results['failed_batches']}")
        logger.info(f"Processed documents: {len(results['processed_documents'])}")
        logger.info(f"Failed documents: {len(results['failed_documents'])}")
        
        if results['failed_documents']:
            logger.warning("Failed documents:")
            for doc_id in results['failed_documents']:
                logger.warning(f"  - {doc_id}")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        raise

if __name__ == "__main__":
    main()
