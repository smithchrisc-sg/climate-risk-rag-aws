#!/usr/bin/env python3
"""
⚠️⚠️⚠️ WARNING: THIS SCRIPT IS BROKEN - DO NOT USE ⚠️⚠️⚠️

This script claims to do "selective" migration but actually migrates ALL data:
- All documents (15,176 PDFs) - NOT selective
- All embeddings (1.02M files) - NOT selective  
- All text files (15,155 files) - NOT selective
- Only chunks are selective (1,000 documents)

This would cost ~$88/month instead of the intended ~$20/month.

USE selective_migration.py INSTEAD (the corrected version)

⚠️⚠️⚠️ DO NOT USE THIS SCRIPT ⚠️⚠️⚠️

Original broken description:
Selective Migration Script for Climate Risk RAG System
Migrates selected data for testing and comparison:
- All documents (15,176 PDFs)
- All embeddings (1.02M files from /data/processed/embeddings/)
- Flair NER results (91 files from /data/processed/ner_Flair/)
- Extracted text (15,155 files from /data/processed/text/)
- Sample chunks (1,000 documents from /data/chunks/)
"""

import os
import json
import sqlite3
import boto3
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import hashlib
import random
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('selective_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SelectiveMigrator:
    """Handles selective migration for testing and comparison"""
    
    def __init__(self, local_data_path: str, aws_region: str = 'us-east-1'):
        self.local_data_path = Path(local_data_path)
        self.aws_region = aws_region
        
        # Initialize AWS clients
        self.s3 = boto3.client('s3', region_name=aws_region)
        
        # Paths
        self.raw_docs_path = self.local_data_path / 'data' / 'raw'
        self.chunks_path = self.local_data_path / 'data' / 'chunks'
        self.processed_path = self.local_data_path / 'data' / 'processed'
        self.embeddings_path = self.processed_path / 'embeddings'
        self.ner_flair_path = self.processed_path / 'ner_Flair'
        self.text_path = self.processed_path / 'text'
        self.db_path = self.local_data_path / 'db' / 'corpus_document_ids.db'
        self.provenance_path = self.local_data_path / 'data' / 'provenance.jsonl'
        
        # Migration statistics
        self.stats = {
            'documents_processed': 0,
            'documents_uploaded': 0,
            'embeddings_processed': 0,
            'ner_results_processed': 0,
            'text_files_processed': 0,
            'sample_chunks_processed': 0,
            'metadata_records': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def migrate_selective(self, documents_bucket: str, artifacts_bucket: str,
                         sample_chunk_count: int = 1000, max_workers: int = 10) -> Dict[str, Any]:
        """Execute selective migration for testing"""
        logger.info("Starting selective migration for testing and comparison")
        logger.info(f"Source: {self.local_data_path}")
        logger.info(f"Target: s3://{documents_bucket} and s3://{artifacts_bucket}")
        logger.info(f"Sample chunks: {sample_chunk_count} documents")
        
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Load local metadata
            logger.info("Loading local metadata...")
            metadata_map = self._load_local_metadata()
            logger.info(f"Loaded metadata for {len(metadata_map)} documents")
            
            # Step 2: Upload all documents
            logger.info("Uploading all documents...")
            document_files = list(self.raw_docs_path.glob('*.pdf'))
            logger.info(f"Found {len(document_files)} PDF documents")
            self._upload_documents_batch(document_files, documents_bucket, metadata_map, max_workers)
            
            # Step 3: Upload all embeddings (processed)
            logger.info("Uploading processed embeddings...")
            self._upload_processed_embeddings(artifacts_bucket, max_workers)
            
            # Step 4: Upload Flair NER results
            logger.info("Uploading Flair NER results...")
            self._upload_flair_ner_results(artifacts_bucket, max_workers)
            
            # Step 5: Upload extracted text
            logger.info("Uploading extracted text files...")
            self._upload_extracted_text(artifacts_bucket, max_workers)
            
            # Step 6: Upload sample chunks for comparison
            logger.info(f"Uploading sample chunks ({sample_chunk_count} documents)...")
            self._upload_sample_chunks(artifacts_bucket, sample_chunk_count, max_workers)
            
            # Step 7: Create migration summary
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            summary = {
                'migration_type': 'selective_for_testing',
                'migration_completed': end_time.isoformat(),
                'duration_seconds': duration,
                'statistics': self.stats,
                'source_path': str(self.local_data_path),
                'target_buckets': {
                    'documents': documents_bucket,
                    'artifacts': artifacts_bucket
                },
                'selective_criteria': {
                    'all_documents': True,
                    'all_embeddings': True,
                    'flair_ner_only': True,
                    'all_text_files': True,
                    'sample_chunks': sample_chunk_count
                }
            }
            
            # Save summary to S3
            self.s3.put_object(
                Bucket=artifacts_bucket,
                Key='selective_migration_summary.json',
                Body=json.dumps(summary, indent=2),
                ContentType='application/json'
            )
            
            logger.info("Selective migration completed successfully!")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Documents uploaded: {self.stats['documents_uploaded']}")
            logger.info(f"Embeddings processed: {self.stats['embeddings_processed']}")
            logger.info(f"Errors: {self.stats['errors']}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Selective migration failed: {str(e)}")
            raise
    
    def _load_local_metadata(self) -> Dict[str, Dict]:
        """Load metadata from local database and provenance files"""
        metadata_map = {}
        
        # Load from SQLite database
        if self.db_path.exists():
            try:
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get table schema first
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"Database tables: {tables}")
                
                # Try common table names
                for table_name in ['documents', 'document_metadata', 'corpus_documents']:
                    try:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                        rows = cursor.fetchall()
                        if rows:
                            logger.info(f"Found data in table: {table_name}")
                            cursor.execute(f"SELECT * FROM {table_name}")
                            for row in cursor.fetchall():
                                doc_id = None
                                # Try different column names for document ID
                                for col in ['doc_id', 'document_id', 'id', 'hash_id']:
                                    if col in row.keys():
                                        doc_id = row[col]
                                        break
                                
                                if doc_id:
                                    metadata_map[doc_id] = dict(row)
                            break
                    except sqlite3.OperationalError:
                        continue
                
                conn.close()
                logger.info(f"Loaded {len(metadata_map)} records from database")
                
            except Exception as e:
                logger.warning(f"Could not load database metadata: {str(e)}")
        
        # Load from provenance file
        if self.provenance_path.exists():
            try:
                with open(self.provenance_path, 'r') as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            doc_id = record.get('doc_id')
                            if doc_id:
                                if doc_id not in metadata_map:
                                    metadata_map[doc_id] = {}
                                metadata_map[doc_id]['provenance'] = record
                        except json.JSONDecodeError:
                            continue
                
                logger.info(f"Enhanced metadata with provenance for {len(metadata_map)} documents")
                
            except Exception as e:
                logger.warning(f"Could not load provenance data: {str(e)}")
        
        return metadata_map
    
    def _upload_documents_batch(self, document_files: List[Path], bucket: str, 
                               metadata_map: Dict, max_workers: int):
        """Upload all documents"""
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for doc_path in document_files:
                future = executor.submit(
                    self._upload_single_document, 
                    doc_path, bucket, metadata_map
                )
                futures.append(future)
            
            # Process with progress bar
            for future in tqdm(concurrent.futures.as_completed(futures), 
                             total=len(futures), desc="Uploading documents"):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error in document upload: {str(e)}")
                    self.stats['errors'] += 1
    
    def _upload_single_document(self, doc_path: Path, bucket: str, metadata_map: Dict):
        """Upload a single document with metadata"""
        try:
            doc_id = doc_path.stem  # Remove .pdf extension
            
            # Check if already uploaded
            try:
                self.s3.head_object(Bucket=bucket, Key=f"documents/{doc_path.name}")
                logger.debug(f"Document {doc_path.name} already exists, skipping")
                self.stats['skipped'] += 1
                return
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
            
            # Prepare metadata
            s3_metadata = {
                'doc-id': doc_id,
                'original-filename': doc_path.name,
                'upload-timestamp': datetime.utcnow().isoformat(),
                'migration-source': 'selective-migration',
                'migration-type': 'testing-comparison'
            }
            
            # Add database metadata if available
            if doc_id in metadata_map:
                db_metadata = metadata_map[doc_id]
                for key, value in db_metadata.items():
                    if isinstance(value, (str, int, float)) and key != 'provenance':
                        clean_key = ''.join(c.lower() if c.isalnum() else '-' for c in str(key))
                        s3_metadata[clean_key] = str(value)
            
            # Upload document
            with open(doc_path, 'rb') as f:
                self.s3.put_object(
                    Bucket=bucket,
                    Key=f"documents/{doc_path.name}",
                    Body=f,
                    ContentType='application/pdf',
                    Metadata=s3_metadata,
                    StorageClass='STANDARD_IA'
                )
            
            # Upload detailed metadata
            if doc_id in metadata_map:
                detailed_metadata = {
                    'doc_id': doc_id,
                    'filename': doc_path.name,
                    'file_size': doc_path.stat().st_size,
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'migration_type': 'selective_testing',
                    'database_metadata': metadata_map[doc_id],
                    'file_hash': self._calculate_file_hash(doc_path)
                }
                
                self.s3.put_object(
                    Bucket=bucket.replace('documents', 'artifacts'),
                    Key=f"metadata/{doc_id}.json",
                    Body=json.dumps(detailed_metadata, indent=2),
                    ContentType='application/json'
                )
            
            self.stats['documents_uploaded'] += 1
            
        except Exception as e:
            logger.error(f"Error uploading {doc_path.name}: {str(e)}")
            self.stats['errors'] += 1
            raise
    
    def _upload_processed_embeddings(self, bucket: str, max_workers: int):
        """Upload processed embeddings preserving folder structure"""
        
        if not self.embeddings_path.exists():
            logger.warning("Processed embeddings path not found")
            return
        
        # Get all embedding folders
        embedding_folders = list(self.embeddings_path.glob('*/'))
        logger.info(f"Found {len(embedding_folders)} embedding document folders")
        
        # Count total files for progress tracking
        total_files = 0
        folder_file_map = {}
        
        for folder in embedding_folders:
            if folder.is_dir():
                files = list(folder.glob('*.json'))
                if files:  # Only include folders with files
                    folder_file_map[folder] = files
                    total_files += len(files)
        
        logger.info(f"Found {total_files} embedding files across {len(folder_file_map)} folders")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for folder, files in folder_file_map.items():
                doc_id = folder.name
                
                for file_path in files:
                    future = executor.submit(
                        self._upload_processed_file,
                        file_path, bucket, f"processed_embeddings/{doc_id}", 'embedding'
                    )
                    futures.append(future)
            
            # Process with progress bar
            for future in tqdm(concurrent.futures.as_completed(futures),
                             total=len(futures), desc="Uploading embeddings"):
                try:
                    future.result()
                    self.stats['embeddings_processed'] += 1
                except Exception as e:
                    logger.error(f"Error uploading embedding: {str(e)}")
                    self.stats['errors'] += 1
    
    def _upload_flair_ner_results(self, bucket: str, max_workers: int):
        """Upload Flair NER results"""
        
        if not self.ner_flair_path.exists():
            logger.warning("Flair NER results path not found")
            return
        
        ner_files = list(self.ner_flair_path.glob('*.json'))
        logger.info(f"Found {len(ner_files)} Flair NER result files")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for file_path in ner_files:
                future = executor.submit(
                    self._upload_processed_file,
                    file_path, bucket, "processed_ner_flair", 'ner_result'
                )
                futures.append(future)
            
            # Process with progress bar
            for future in tqdm(concurrent.futures.as_completed(futures),
                             total=len(futures), desc="Uploading Flair NER"):
                try:
                    future.result()
                    self.stats['ner_results_processed'] += 1
                except Exception as e:
                    logger.error(f"Error uploading NER result: {str(e)}")
                    self.stats['errors'] += 1
    
    def _upload_extracted_text(self, bucket: str, max_workers: int):
        """Upload extracted text files"""
        
        if not self.text_path.exists():
            logger.warning("Extracted text path not found")
            return
        
        text_files = list(self.text_path.glob('*.txt'))
        logger.info(f"Found {len(text_files)} extracted text files")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for file_path in text_files:
                future = executor.submit(
                    self._upload_processed_file,
                    file_path, bucket, "processed_text", 'text_file'
                )
                futures.append(future)
            
            # Process with progress bar
            for future in tqdm(concurrent.futures.as_completed(futures),
                             total=len(futures), desc="Uploading text files"):
                try:
                    future.result()
                    self.stats['text_files_processed'] += 1
                except Exception as e:
                    logger.error(f"Error uploading text file: {str(e)}")
                    self.stats['errors'] += 1
    
    def _upload_sample_chunks(self, bucket: str, sample_count: int, max_workers: int):
        """Upload sample chunks for comparison testing"""
        
        if not self.chunks_path.exists():
            logger.warning("Chunks path not found")
            return
        
        # Get all chunk folders and sample them
        all_chunk_folders = list(self.chunks_path.glob('*/'))
        if len(all_chunk_folders) < sample_count:
            sample_folders = all_chunk_folders
            logger.warning(f"Only {len(all_chunk_folders)} chunk folders available, using all")
        else:
            sample_folders = random.sample(all_chunk_folders, sample_count)
        
        logger.info(f"Selected {len(sample_folders)} document folders for chunk sampling")
        
        # Count total files in sample
        total_files = 0
        folder_file_map = {}
        
        for folder in sample_folders:
            if folder.is_dir():
                files = list(folder.glob('*.json'))
                if files:
                    folder_file_map[folder] = files
                    total_files += len(files)
        
        logger.info(f"Found {total_files} chunk files in sample")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for folder, files in folder_file_map.items():
                doc_id = folder.name
                
                for file_path in files:
                    future = executor.submit(
                        self._upload_processed_file,
                        file_path, bucket, f"sample_chunks/{doc_id}", 'chunk_sample'
                    )
                    futures.append(future)
            
            # Process with progress bar
            for future in tqdm(concurrent.futures.as_completed(futures),
                             total=len(futures), desc="Uploading sample chunks"):
                try:
                    future.result()
                    self.stats['sample_chunks_processed'] += 1
                except Exception as e:
                    logger.error(f"Error uploading sample chunk: {str(e)}")
                    self.stats['errors'] += 1
        
        # Save sample document list for reference
        sample_doc_ids = [folder.name for folder in sample_folders]
        sample_manifest = {
            'sample_type': 'chunk_comparison',
            'sample_size': len(sample_doc_ids),
            'total_chunk_files': total_files,
            'document_ids': sample_doc_ids,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.s3.put_object(
            Bucket=bucket,
            Key='sample_chunks_manifest.json',
            Body=json.dumps(sample_manifest, indent=2),
            ContentType='application/json'
        )
    
    def _upload_processed_file(self, file_path: Path, bucket: str, prefix: str, file_type: str):
        """Upload a single processed file"""
        try:
            key = f"{prefix}/{file_path.name}"
            
            # Check if already exists
            try:
                self.s3.head_object(Bucket=bucket, Key=key)
                return  # Already exists
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
            
            # Determine content type
            content_type = 'application/json' if file_path.suffix == '.json' else 'text/plain'
            
            # Upload file
            with open(file_path, 'rb') as f:
                self.s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=f,
                    ContentType=content_type,
                    StorageClass='STANDARD_IA',
                    Metadata={
                        'file-type': file_type,
                        'migration-type': 'selective-testing',
                        'upload-timestamp': datetime.utcnow().isoformat()
                    }
                )
            
        except Exception as e:
            logger.error(f"Error uploading {file_path}: {str(e)}")
            raise
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


def main():
    parser = argparse.ArgumentParser(description='Selective migration for testing and comparison')
    parser.add_argument('--local-path', required=True,
                       help='Path to local climate_risk_rag directory')
    parser.add_argument('--documents-bucket', required=True,
                       help='S3 bucket for documents')
    parser.add_argument('--artifacts-bucket', required=True,
                       help='S3 bucket for artifacts')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--sample-chunks', type=int, default=1000,
                       help='Number of documents to sample for chunk comparison')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Maximum number of worker threads')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run without uploading')
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = SelectiveMigrator(args.local_path, args.region)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be uploaded")
        
        # Analyze what would be migrated
        print(f"\nSelective Migration Plan:")
        print(f"Documents: All PDFs from {migrator.raw_docs_path}")
        print(f"Embeddings: All from {migrator.embeddings_path}")
        print(f"NER Results: Flair only from {migrator.ner_flair_path}")
        print(f"Text Files: All from {migrator.text_path}")
        print(f"Sample Chunks: {args.sample_chunks} documents from {migrator.chunks_path}")
        print(f"Target buckets: {args.documents_bucket}, {args.artifacts_bucket}")
        
        # Count files
        if migrator.raw_docs_path.exists():
            doc_count = len(list(migrator.raw_docs_path.glob('*.pdf')))
            print(f"Documents to upload: {doc_count}")
        
        if migrator.embeddings_path.exists():
            emb_folders = len(list(migrator.embeddings_path.glob('*/')))
            print(f"Embedding folders: {emb_folders}")
        
        if migrator.ner_flair_path.exists():
            ner_count = len(list(migrator.ner_flair_path.glob('*.json')))
            print(f"Flair NER files: {ner_count}")
        
        if migrator.text_path.exists():
            text_count = len(list(migrator.text_path.glob('*.txt')))
            print(f"Text files: {text_count}")
        
    else:
        # Execute selective migration
        summary = migrator.migrate_selective(
            args.documents_bucket,
            args.artifacts_bucket,
            args.sample_chunks,
            args.max_workers
        )
        
        print(f"\n🎉 Selective migration completed successfully!")
        print(f"Documents uploaded: {summary['statistics']['documents_uploaded']}")
        print(f"Embeddings processed: {summary['statistics']['embeddings_processed']}")
        print(f"NER results processed: {summary['statistics']['ner_results_processed']}")
        print(f"Text files processed: {summary['statistics']['text_files_processed']}")
        print(f"Sample chunks processed: {summary['statistics']['sample_chunks_processed']}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Errors: {summary['statistics']['errors']}")


if __name__ == "__main__":
    main()
