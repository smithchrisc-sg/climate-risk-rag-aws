#!/usr/bin/env python3
"""
Bulk Migration Script for Climate Risk RAG System
Migrates 15K+ documents from local data lake to AWS S3 with metadata preservation
"""

import os
import json
import sqlite3
import boto3
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import hashlib
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BulkMigrator:
    """Handles bulk migration of documents and metadata to AWS"""
    
    def __init__(self, local_data_path: str, aws_region: str = 'us-east-1'):
        self.local_data_path = Path(local_data_path)
        self.aws_region = aws_region
        
        # Initialize AWS clients
        self.s3 = boto3.client('s3', region_name=aws_region)
        self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        
        # Paths
        self.raw_docs_path = self.local_data_path / 'data' / 'raw'
        self.chunks_path = self.local_data_path / 'data' / 'chunks'
        self.embeddings_path = self.local_data_path / 'data' / 'embeddings'
        self.ner_results_path = self.local_data_path / 'data' / 'ner_results'
        self.db_path = self.local_data_path / 'db' / 'corpus_document_ids.db'
        self.provenance_path = self.local_data_path / 'data' / 'provenance.jsonl'
        
        # Migration statistics
        self.stats = {
            'documents_processed': 0,
            'documents_uploaded': 0,
            'metadata_records': 0,
            'chunks_processed': 0,
            'embeddings_processed': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def migrate_all(self, documents_bucket: str, artifacts_bucket: str, 
                   batch_size: int = 100, max_workers: int = 10) -> Dict[str, Any]:
        """Execute complete migration process"""
        logger.info("Starting bulk migration of Climate Risk RAG data")
        logger.info(f"Source: {self.local_data_path}")
        logger.info(f"Target: s3://{documents_bucket} and s3://{artifacts_bucket}")
        
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Load local metadata
            logger.info("Loading local metadata...")
            metadata_map = self._load_local_metadata()
            logger.info(f"Loaded metadata for {len(metadata_map)} documents")
            
            # Step 2: Get document list
            document_files = list(self.raw_docs_path.glob('*.pdf'))
            logger.info(f"Found {len(document_files)} PDF documents")
            
            # Step 3: Upload documents with metadata
            logger.info("Uploading documents to S3...")
            self._upload_documents_batch(
                document_files, documents_bucket, metadata_map, 
                batch_size, max_workers
            )
            
            # Step 4: Upload processed artifacts
            logger.info("Uploading processed artifacts...")
            self._upload_artifacts_batch(
                artifacts_bucket, metadata_map, batch_size, max_workers
            )
            
            # Step 5: Create migration summary
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            summary = {
                'migration_completed': end_time.isoformat(),
                'duration_seconds': duration,
                'statistics': self.stats,
                'source_path': str(self.local_data_path),
                'target_buckets': {
                    'documents': documents_bucket,
                    'artifacts': artifacts_bucket
                }
            }
            
            # Save summary to S3
            self.s3.put_object(
                Bucket=artifacts_bucket,
                Key='migration_summary.json',
                Body=json.dumps(summary, indent=2),
                ContentType='application/json'
            )
            
            logger.info("Migration completed successfully!")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Documents uploaded: {self.stats['documents_uploaded']}")
            logger.info(f"Errors: {self.stats['errors']}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
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
                               metadata_map: Dict, batch_size: int, max_workers: int):
        """Upload documents in parallel batches"""
        
        # Process in batches
        for i in tqdm(range(0, len(document_files), batch_size), desc="Uploading documents"):
            batch = document_files[i:i+batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for doc_path in batch:
                    future = executor.submit(
                        self._upload_single_document, 
                        doc_path, bucket, metadata_map
                    )
                    futures.append(future)
                
                # Wait for batch completion
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in batch upload: {str(e)}")
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
                'migration-source': 'local-poc'
            }
            
            # Add database metadata if available
            if doc_id in metadata_map:
                db_metadata = metadata_map[doc_id]
                for key, value in db_metadata.items():
                    if isinstance(value, (str, int, float)) and key != 'provenance':
                        # S3 metadata keys must be lowercase and alphanumeric
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
                    StorageClass='STANDARD_IA'  # Cost optimization for infrequent access
                )
            
            # Upload detailed metadata as separate JSON file
            if doc_id in metadata_map:
                detailed_metadata = {
                    'doc_id': doc_id,
                    'filename': doc_path.name,
                    'file_size': doc_path.stat().st_size,
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'database_metadata': metadata_map[doc_id],
                    'file_hash': self._calculate_file_hash(doc_path)
                }
                
                self.s3.put_object(
                    Bucket=bucket.replace('documents', 'artifacts'),  # Use artifacts bucket
                    Key=f"metadata/{doc_id}.json",
                    Body=json.dumps(detailed_metadata, indent=2),
                    ContentType='application/json'
                )
            
            self.stats['documents_uploaded'] += 1
            logger.debug(f"Uploaded: {doc_path.name}")
            
        except Exception as e:
            logger.error(f"Error uploading {doc_path.name}: {str(e)}")
            self.stats['errors'] += 1
            raise
    
    def _upload_artifacts_batch(self, bucket: str, metadata_map: Dict, 
                               batch_size: int, max_workers: int):
        """Upload processed artifacts (chunks, embeddings, NER results) preserving folder structure"""
        
        # Upload chunks with folder structure
        if self.chunks_path.exists():
            chunk_folders = list(self.chunks_path.glob('*/'))  # Get document folders
            logger.info(f"Uploading chunks from {len(chunk_folders)} document folders...")
            self._upload_folder_structure_artifacts(chunk_folders, bucket, 'chunks', max_workers)
        
        # Upload embeddings with folder structure
        if self.embeddings_path.exists():
            embedding_folders = list(self.embeddings_path.glob('*/'))  # Get document folders
            logger.info(f"Uploading embeddings from {len(embedding_folders)} document folders...")
            self._upload_folder_structure_artifacts(embedding_folders, bucket, 'embeddings', max_workers)
        
        # Upload NER results with folder structure
        if self.ner_results_path.exists():
            ner_folders = list(self.ner_results_path.glob('*/'))  # Get document folders
            logger.info(f"Uploading NER results from {len(ner_folders)} document folders...")
            self._upload_folder_structure_artifacts(ner_folders, bucket, 'ner_results', max_workers)
    
    def _upload_folder_structure_artifacts(self, folders: List[Path], bucket: str, 
                                          prefix: str, max_workers: int):
        """Upload artifacts preserving document folder structure"""
        
        # Count total files for progress tracking
        total_files = 0
        folder_file_map = {}
        
        for folder in folders:
            if folder.is_dir():
                files = list(folder.glob('*.json'))
                folder_file_map[folder] = files
                total_files += len(files)
        
        logger.info(f"Found {total_files} {prefix} files across {len(folders)} document folders")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for folder, files in folder_file_map.items():
                doc_id = folder.name  # Document ID from folder name
                
                for file_path in files:
                    future = executor.submit(
                        self._upload_structured_artifact_file, 
                        file_path, bucket, prefix, doc_id
                    )
                    futures.append(future)
            
            # Process results with progress bar
            for future in tqdm(concurrent.futures.as_completed(futures), 
                             total=len(futures), desc=f"Uploading {prefix}"):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error uploading {prefix} artifact: {str(e)}")
                    self.stats['errors'] += 1
    
    def _upload_structured_artifact_file(self, file_path: Path, bucket: str, 
                                        prefix: str, doc_id: str):
        """Upload a single artifact file preserving folder structure"""
        try:
            # Preserve folder structure: prefix/doc_id/filename
            key = f"{prefix}/{doc_id}/{file_path.name}"
            
            # Check if already exists
            try:
                self.s3.head_object(Bucket=bucket, Key=key)
                return  # Already exists
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
            
            # Upload file
            with open(file_path, 'rb') as f:
                self.s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=f,
                    ContentType='application/json',
                    StorageClass='STANDARD_IA'
                )
            
            # Update stats
            if prefix == 'chunks':
                self.stats['chunks_processed'] += 1
            elif prefix == 'embeddings':
                self.stats['embeddings_processed'] += 1
            
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
    
    def create_migration_manifest(self, bucket: str) -> Dict[str, Any]:
        """Create a manifest of all migrated files"""
        manifest = {
            'created_at': datetime.utcnow().isoformat(),
            'migration_stats': self.stats,
            'documents': [],
            'artifacts': []
        }
        
        try:
            # List documents
            paginator = self.s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix='documents/'):
                for obj in page.get('Contents', []):
                    manifest['documents'].append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
            
            # List artifacts
            for page in paginator.paginate(Bucket=bucket.replace('documents', 'artifacts')):
                for obj in page.get('Contents', []):
                    manifest['artifacts'].append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
            
            # Save manifest
            self.s3.put_object(
                Bucket=bucket.replace('documents', 'artifacts'),
                Key='migration_manifest.json',
                Body=json.dumps(manifest, indent=2, default=str),
                ContentType='application/json'
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Error creating manifest: {str(e)}")
            return manifest


def main():
    parser = argparse.ArgumentParser(description='Bulk migrate Climate Risk RAG data to AWS')
    parser.add_argument('--local-path', required=True, 
                       help='Path to local climate_risk_rag directory')
    parser.add_argument('--documents-bucket', required=True,
                       help='S3 bucket for documents')
    parser.add_argument('--artifacts-bucket', required=True,
                       help='S3 bucket for artifacts')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for parallel processing')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Maximum number of worker threads')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run without uploading')
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = BulkMigrator(args.local_path, args.region)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be uploaded")
        # Load metadata to validate
        metadata_map = migrator._load_local_metadata()
        document_files = list(migrator.raw_docs_path.glob('*.pdf'))
        
        print(f"\nMigration Plan:")
        print(f"Documents to upload: {len(document_files)}")
        print(f"Metadata records: {len(metadata_map)}")
        print(f"Target buckets: {args.documents_bucket}, {args.artifacts_bucket}")
        print(f"Batch size: {args.batch_size}")
        print(f"Max workers: {args.max_workers}")
        
    else:
        # Execute migration
        summary = migrator.migrate_all(
            args.documents_bucket,
            args.artifacts_bucket,
            args.batch_size,
            args.max_workers
        )
        
        # Create manifest
        manifest = migrator.create_migration_manifest(args.documents_bucket)
        
        print(f"\n🎉 Migration completed successfully!")
        print(f"Documents uploaded: {summary['statistics']['documents_uploaded']}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds")
        print(f"Errors: {summary['statistics']['errors']}")


if __name__ == "__main__":
    main()
