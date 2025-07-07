#!/usr/bin/env python3
"""
Selective Migration Script (Corrected)
Migrates ONLY the selected sample documents and their associated artifacts
"""

import os
import json
import boto3
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SelectiveMigrator:
    """Handles selective migration of sample documents and artifacts"""
    
    def __init__(self, local_path: str, documents_bucket: str, chunks_bucket: str,
                 embeddings_bucket: str, ner_results_bucket: str, extracted_text_bucket: str,
                 region: str, profile: str = None, max_workers: int = 4):
        self.local_path = Path(local_path)
        self.documents_bucket = documents_bucket
        self.chunks_bucket = chunks_bucket
        self.embeddings_bucket = embeddings_bucket
        self.ner_results_bucket = ner_results_bucket
        self.extracted_text_bucket = extracted_text_bucket
        self.region = region
        self.profile = profile
        self.max_workers = max_workers
        
        # Initialize AWS clients with profile if provided
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.s3_client = session.client('s3', region_name=region)
        
        # Migration statistics
        self.stats = {
            'documents': {'attempted': 0, 'succeeded': 0, 'failed': 0, 'skipped': 0},
            'chunks': {'attempted': 0, 'succeeded': 0, 'failed': 0, 'skipped': 0},
            'embeddings': {'attempted': 0, 'succeeded': 0, 'failed': 0, 'skipped': 0},
            'ner_results': {'attempted': 0, 'succeeded': 0, 'failed': 0, 'skipped': 0},
            'text_files': {'attempted': 0, 'succeeded': 0, 'failed': 0, 'skipped': 0}
        }
        
        self.errors = []
    
    def load_sample_selection(self, sample_file: str) -> List[Dict]:
        """Load sample document selection from JSON file"""
        logger.info(f"Loading sample selection from: {sample_file}")
        
        with open(sample_file, 'r') as f:
            sample_data = json.load(f)
        
        sample_docs = sample_data.get('sample_documents', [])
        logger.info(f"Loaded {len(sample_docs)} documents for migration")
        
        return sample_docs
    
    def migrate_sample_documents(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate sample documents to S3"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating {len(sample_docs)} sample documents...")
        
        raw_docs_path = self.local_path / "data" / "raw"
        if not raw_docs_path.exists():
            logger.error(f"Raw documents path not found: {raw_docs_path}")
            return False
        
        # Prepare migration tasks
        migration_tasks = []
        for doc in sample_docs:
            doc_id = doc['doc_id']
            
            # Find PDF file (try different extensions and naming patterns)
            pdf_candidates = [
                raw_docs_path / f"{doc_id}.pdf",
                raw_docs_path / f"{doc_id}.PDF",
            ]
            
            pdf_file = None
            for candidate in pdf_candidates:
                if candidate.exists():
                    pdf_file = candidate
                    break
            
            if pdf_file:
                migration_tasks.append({
                    'local_path': pdf_file,
                    's3_key': f"documents/{doc_id}.pdf",
                    'doc_id': doc_id,
                    'type': 'document'
                })
            else:
                logger.warning(f"PDF file not found for document: {doc_id}")
                self.stats['documents']['skipped'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} documents")
            return True
        
        # Execute migrations
        return self._execute_migration_tasks(migration_tasks, 'documents')
    
    def migrate_sample_chunks(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate chunks for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating chunks for {len(sample_docs)} sample documents...")
        
        chunks_path = self.local_path / "data" / "chunks"
        if not chunks_path.exists():
            logger.error(f"Chunks path not found: {chunks_path}")
            return False
        
        migration_tasks = []
        for doc in sample_docs:
            doc_id = doc['doc_id']
            doc_chunks_path = chunks_path / doc_id
            
            if doc_chunks_path.exists() and doc_chunks_path.is_dir():
                # Find all chunk files for this document
                chunk_files = list(doc_chunks_path.glob("*.json"))
                
                for chunk_file in chunk_files:
                    migration_tasks.append({
                        'local_path': chunk_file,
                        's3_key': f"chunks/{doc_id}/{chunk_file.name}",
                        'doc_id': doc_id,
                        'type': 'chunk',
                        'bucket': self.chunks_bucket
                    })
            else:
                logger.warning(f"Chunks directory not found for document: {doc_id}")
                self.stats['chunks']['skipped'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} chunk files")
            return True
        
        return self._execute_migration_tasks(migration_tasks, 'chunks')
    
    def migrate_sample_embeddings(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate embeddings for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating embeddings for {len(sample_docs)} sample documents...")
        
        # Try different possible embedding paths
        embedding_paths = [
            self.local_path / "data" / "embeddings",
            self.local_path / "data" / "processed" / "embeddings"
        ]
        
        embeddings_path = None
        for path in embedding_paths:
            if path.exists():
                embeddings_path = path
                break
        
        if not embeddings_path:
            logger.error("Embeddings path not found in any expected location")
            return False
        
        migration_tasks = []
        for doc in sample_docs:
            doc_id = doc['doc_id']
            doc_embeddings_path = embeddings_path / doc_id
            
            if doc_embeddings_path.exists() and doc_embeddings_path.is_dir():
                # Find all embedding files for this document
                embedding_files = list(doc_embeddings_path.glob("*.json"))
                
                for embedding_file in embedding_files:
                    migration_tasks.append({
                        'local_path': embedding_file,
                        's3_key': f"embeddings/{doc_id}/{embedding_file.name}",
                        'doc_id': doc_id,
                        'type': 'embedding'
                    })
            else:
                logger.warning(f"Embeddings directory not found for document: {doc_id}")
                self.stats['embeddings']['skipped'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} embedding files")
            return True
        
        return self._execute_migration_tasks(migration_tasks, 'embeddings')
    
    def migrate_sample_ner(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate NER results for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating NER results for {len(sample_docs)} sample documents...")
        
        # Try different possible NER paths
        ner_paths = [
            self.local_path / "data" / "ner_results",
            self.local_path / "data" / "processed" / "ner_Flair",
            self.local_path / "data" / "processed" / "ner_results"
        ]
        
        ner_path = None
        for path in ner_paths:
            if path.exists():
                ner_path = path
                break
        
        if not ner_path:
            logger.warning("NER results path not found - skipping NER migration")
            return True  # Not critical, continue
        
        migration_tasks = []
        for doc in sample_docs:
            doc_id = doc['doc_id']
            
            # Try different NER file patterns
            ner_candidates = [
                ner_path / f"{doc_id}.json",
                ner_path / f"{doc_id}_ner.json",
                ner_path / doc_id / "ner_results.json"
            ]
            
            ner_file = None
            for candidate in ner_candidates:
                if candidate.exists():
                    ner_file = candidate
                    break
            
            if ner_file:
                migration_tasks.append({
                    'local_path': ner_file,
                    's3_key': f"ner_results/{doc_id}.json",
                    'doc_id': doc_id,
                    'type': 'ner_result'
                })
            else:
                logger.debug(f"NER file not found for document: {doc_id}")
                self.stats['ner_results']['skipped'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} NER files")
            return True
        
        return self._execute_migration_tasks(migration_tasks, 'ner_results')
    
    def migrate_sample_text(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate extracted text for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating extracted text for {len(sample_docs)} sample documents...")
        
        # Try different possible text paths
        text_paths = [
            self.local_path / "data" / "text",
            self.local_path / "data" / "processed" / "text",
            self.local_path / "data" / "extracted_text"
        ]
        
        text_path = None
        for path in text_paths:
            if path.exists():
                text_path = path
                break
        
        if not text_path:
            logger.warning("Extracted text path not found - skipping text migration")
            return True  # Not critical, continue
        
        migration_tasks = []
        for doc in sample_docs:
            doc_id = doc['doc_id']
            
            # Try different text file patterns
            text_candidates = [
                text_path / f"{doc_id}.txt",
                text_path / f"{doc_id}_text.txt",
                text_path / doc_id / "extracted_text.txt"
            ]
            
            text_file = None
            for candidate in text_candidates:
                if candidate.exists():
                    text_file = candidate
                    break
            
            if text_file:
                migration_tasks.append({
                    'local_path': text_file,
                    's3_key': f"extracted_text/{doc_id}.txt",
                    'doc_id': doc_id,
                    'type': 'text_file'
                })
            else:
                logger.debug(f"Text file not found for document: {doc_id}")
                self.stats['text_files']['skipped'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} text files")
            return True
        
        return self._execute_migration_tasks(migration_tasks, 'text_files')
    
    def _execute_migration_tasks(self, tasks: List[Dict], task_type: str) -> bool:
        """Execute migration tasks with parallel processing"""
        if not tasks:
            logger.info(f"No {task_type} to migrate")
            return True
        
        logger.info(f"Migrating {len(tasks)} {task_type} files...")
        
        success_count = 0
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._upload_file, task): task 
                for task in tasks
            }
            
            # Process results with progress bar
            with tqdm(total=len(tasks), desc=f"Uploading {task_type}") as pbar:
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    
                    try:
                        success = future.result()
                        if success:
                            success_count += 1
                            self.stats[task_type]['succeeded'] += 1
                        else:
                            failed_count += 1
                            self.stats[task_type]['failed'] += 1
                    except Exception as e:
                        logger.error(f"Task failed for {task['doc_id']}: {e}")
                        failed_count += 1
                        self.stats[task_type]['failed'] += 1
                        self.errors.append({
                            'task': task,
                            'error': str(e),
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    
                    pbar.update(1)
        
        self.stats[task_type]['attempted'] = len(tasks)
        
        logger.info(f"{task_type.title()} migration completed: {success_count} succeeded, {failed_count} failed")
        
        return failed_count == 0
    
    def _upload_file(self, task: Dict) -> bool:
        """Upload a single file to S3"""
        try:
            local_path = task['local_path']
            s3_key = task['s3_key']
            
            # Determine target bucket based on task type
            bucket_mapping = {
                'document': self.documents_bucket,
                'chunk': self.chunks_bucket,
                'embedding': self.embeddings_bucket,
                'ner_result': self.ner_results_bucket,
                'text_file': self.extracted_text_bucket
            }
            
            bucket = bucket_mapping.get(task['type'], self.documents_bucket)
            
            # Check if file already exists
            try:
                self.s3_client.head_object(Bucket=bucket, Key=s3_key)
                logger.debug(f"File already exists, skipping: {s3_key}")
                return True
            except self.s3_client.exceptions.NoSuchKey:
                pass  # File doesn't exist, proceed with upload
            
            # Upload file
            extra_args = {
                'Metadata': {
                    'doc_id': task['doc_id'],
                    'migration_type': 'selective',
                    'migration_timestamp': datetime.utcnow().isoformat(),
                    'file_type': task['type']
                }
            }
            
            self.s3_client.upload_file(
                str(local_path), 
                bucket, 
                s3_key,
                ExtraArgs=extra_args
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {task['local_path']}: {e}")
            return False
    
    def migrate_metadata(self, sample_docs: List[Dict], sample_file: str, dry_run: bool = False) -> bool:
        """Migrate sample metadata to S3"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating sample metadata...")
        
        if dry_run:
            logger.info("[DRY RUN] Would migrate sample metadata")
            return True
        
        try:
            # Create comprehensive metadata
            metadata = {
                'migration_info': {
                    'type': 'selective_migration',
                    'timestamp': datetime.utcnow().isoformat(),
                    'sample_size': len(sample_docs),
                    'sample_file': sample_file,
                    'migration_stats': self.stats
                },
                'sample_documents': sample_docs,
                'migration_errors': self.errors
            }
            
            # Upload metadata
            metadata_json = json.dumps(metadata, indent=2, default=str)
            
            self.s3_client.put_object(
                Bucket=self.chunks_bucket,  # Use chunks bucket for metadata
                Key='metadata/selective_migration_metadata.json',
                Body=metadata_json,
                ContentType='application/json',
                Metadata={
                    'migration_type': 'selective',
                    'sample_size': str(len(sample_docs)),
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            logger.info("Sample metadata uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload metadata: {e}")
            return False
    
    def run_selective_migration(self, sample_file: str, dry_run: bool = False) -> bool:
        """Run complete selective migration process"""
        logger.info(f"Starting selective migration {'(DRY RUN)' if dry_run else ''}...")
        
        try:
            # Load sample selection
            sample_docs = self.load_sample_selection(sample_file)
            
            if not sample_docs:
                logger.error("No sample documents loaded")
                return False
            
            # Migration steps
            steps = [
                ("documents", self.migrate_sample_documents),
                ("chunks", self.migrate_sample_chunks),
                ("embeddings", self.migrate_sample_embeddings),
                ("ner_results", self.migrate_sample_ner),
                ("text_files", self.migrate_sample_text)
            ]
            
            success = True
            for step_name, step_func in steps:
                logger.info(f"\n--- Starting {step_name} migration ---")
                step_success = step_func(sample_docs, dry_run)
                if not step_success:
                    logger.error(f"{step_name.title()} migration failed")
                    success = False
                    # Continue with other steps even if one fails
            
            # Upload metadata (even if some steps failed)
            if not dry_run:
                self.migrate_metadata(sample_docs, sample_file, dry_run)
            
            # Print final statistics
            self._print_migration_summary()
            
            return success
            
        except Exception as e:
            logger.error(f"Selective migration failed: {e}")
            return False
    
    def _print_migration_summary(self):
        """Print migration summary statistics"""
        print("\n" + "="*60)
        print("SELECTIVE MIGRATION SUMMARY")
        print("="*60)
        
        total_attempted = sum(stats['attempted'] for stats in self.stats.values())
        total_succeeded = sum(stats['succeeded'] for stats in self.stats.values())
        total_failed = sum(stats['failed'] for stats in self.stats.values())
        total_skipped = sum(stats['skipped'] for stats in self.stats.values())
        
        print(f"Overall Statistics:")
        print(f"  Total files attempted: {total_attempted}")
        print(f"  Successfully migrated: {total_succeeded}")
        print(f"  Failed: {total_failed}")
        print(f"  Skipped: {total_skipped}")
        print(f"  Success rate: {(total_succeeded/total_attempted*100):.1f}%" if total_attempted > 0 else "  Success rate: N/A")
        
        print(f"\nDetailed Statistics:")
        for category, stats in self.stats.items():
            if stats['attempted'] > 0:
                success_rate = (stats['succeeded'] / stats['attempted'] * 100) if stats['attempted'] > 0 else 0
                print(f"  {category.title()}:")
                print(f"    Attempted: {stats['attempted']}")
                print(f"    Succeeded: {stats['succeeded']}")
                print(f"    Failed: {stats['failed']}")
                print(f"    Skipped: {stats['skipped']}")
                print(f"    Success rate: {success_rate:.1f}%")
        
        if self.errors:
            print(f"\nErrors encountered: {len(self.errors)}")
            print("Check migration logs for detailed error information")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Selective migration of sample documents')
    parser.add_argument('--local-path', required=True, help='Path to local data lake')
    parser.add_argument('--documents-bucket', required=True, help='S3 bucket for documents')
    parser.add_argument('--chunks-bucket', required=True, help='S3 bucket for chunks')
    parser.add_argument('--embeddings-bucket', required=True, help='S3 bucket for embeddings')
    parser.add_argument('--ner-results-bucket', required=True, help='S3 bucket for NER results')
    parser.add_argument('--extracted-text-bucket', required=True, help='S3 bucket for extracted text')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--sample-file', required=True, help='Sample selection JSON file')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum parallel workers')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without actual migration')
    
    args = parser.parse_args()
    
    try:
        migrator = SelectiveMigrator(
            local_path=args.local_path,
            documents_bucket=args.documents_bucket,
            chunks_bucket=args.chunks_bucket,
            embeddings_bucket=args.embeddings_bucket,
            ner_results_bucket=args.ner_results_bucket,
            extracted_text_bucket=args.extracted_text_bucket,
            region=args.region,
            profile=args.profile,
            max_workers=args.max_workers
        )
        
        success = migrator.run_selective_migration(args.sample_file, args.dry_run)
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
