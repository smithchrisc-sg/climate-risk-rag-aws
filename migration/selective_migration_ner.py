#!/usr/bin/env python3
"""
Selective Migration Script (NER-Based)
Migrates ONLY the selected sample documents and their associated artifacts
based on documents that have completed NER processing.

Updated folder structure:
- PDFs: data/raw/
- Extracted text: data/processed/text/
- Chunks: data/chunks/
- Embeddings: data/embeddings/
- NER results: data/ner_results/
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
        
        # Updated folder paths based on correct structure
        self.raw_docs_path = self.local_path / "data" / "raw"
        self.text_path = self.local_path / "data" / "processed" / "text"
        self.chunks_path = self.local_path / "data" / "chunks"
        self.embeddings_path = self.local_path / "data" / "embeddings"
        self.ner_results_path = self.local_path / "data" / "ner_results"
        
        # Initialize AWS clients with profile if provided
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.s3_client = session.client('s3', region_name=region)
        
        self.stats = {
            'documents_uploaded': 0,
            'chunks_uploaded': 0,
            'embeddings_uploaded': 0,
            'ner_results_uploaded': 0,
            'text_files_uploaded': 0,
            'errors': 0,
            'skipped': 0
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
        
        if not self.raw_docs_path.exists():
            logger.error(f"Raw documents path not found: {self.raw_docs_path}")
            return False
        
        # Prepare migration tasks
        migration_tasks = []
        for doc in sample_docs:
            doc_id = doc['doc_id']
            
            # Find PDF file (try different extensions and naming patterns)
            pdf_file = None
            for pattern in [f"{doc_id}.pdf", f"{doc_id}"]:
                potential_path = self.raw_docs_path / pattern
                if potential_path.exists():
                    pdf_file = potential_path
                    break
            
            if pdf_file:
                migration_tasks.append({
                    'doc_id': doc_id,
                    'local_path': pdf_file,
                    'bucket': self.documents_bucket,
                    's3_key': f"documents/{doc_id}.pdf",
                    'type': 'document'
                })
            else:
                logger.warning(f"PDF file not found for document: {doc_id}")
                self.stats['skipped'] += 1
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} documents")
            return True
        
        # Execute migration tasks
        if migration_tasks:
            self._execute_upload_tasks(migration_tasks, "documents")
        
        return True
    
    def migrate_sample_chunks(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate chunks for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating chunks for {len(sample_docs)} sample documents...")
        
        if not self.chunks_path.exists():
            logger.error(f"Chunks path not found: {self.chunks_path}")
            return False
        
        migration_tasks = []
        total_chunks = 0
        
        for doc in sample_docs:
            doc_id = doc['doc_id']
            chunks_dir = self.chunks_path / doc_id
            
            if chunks_dir.exists() and chunks_dir.is_dir():
                chunk_files = list(chunks_dir.glob("*.json"))
                total_chunks += len(chunk_files)
                
                for chunk_file in chunk_files:
                    migration_tasks.append({
                        'doc_id': doc_id,
                        'local_path': chunk_file,
                        'bucket': self.chunks_bucket,
                        's3_key': f"chunks/{doc_id}/{chunk_file.name}",
                        'type': 'chunk'
                    })
            else:
                logger.warning(f"Chunks directory not found for document: {doc_id}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {total_chunks} chunk files")
            return True
        
        logger.info(f"\n--- Starting chunks migration ---")
        if migration_tasks:
            self._execute_upload_tasks(migration_tasks, "chunks")
        
        return True
    
    def migrate_sample_embeddings(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate embeddings for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating embeddings for {len(sample_docs)} sample documents...")
        
        if not self.embeddings_path.exists():
            logger.error(f"Embeddings path not found: {self.embeddings_path}")
            return False
        
        migration_tasks = []
        total_embeddings = 0
        
        for doc in sample_docs:
            doc_id = doc['doc_id']
            embeddings_dir = self.embeddings_path / doc_id
            
            if embeddings_dir.exists() and embeddings_dir.is_dir():
                embedding_files = list(embeddings_dir.glob("*.npy"))
                total_embeddings += len(embedding_files)
                
                for embedding_file in embedding_files:
                    migration_tasks.append({
                        'doc_id': doc_id,
                        'local_path': embedding_file,
                        'bucket': self.embeddings_bucket,
                        's3_key': f"embeddings/{doc_id}/{embedding_file.name}",
                        'type': 'embedding'
                    })
            else:
                logger.warning(f"Embeddings directory not found for document: {doc_id}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {total_embeddings} embedding files")
            return True
        
        logger.info(f"\n--- Starting embeddings migration ---")
        if migration_tasks:
            self._execute_upload_tasks(migration_tasks, "embeddings")
        
        return True
    
    def migrate_sample_ner_results(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate NER results for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating NER results for {len(sample_docs)} sample documents...")
        
        if not self.ner_results_path.exists():
            logger.error(f"NER results path not found: {self.ner_results_path}")
            return False
        
        migration_tasks = []
        
        for doc in sample_docs:
            doc_id = doc['doc_id']
            ner_file = doc.get('ner_file')
            
            if ner_file:
                ner_path = self.ner_results_path / ner_file
                if ner_path.exists():
                    migration_tasks.append({
                        'doc_id': doc_id,
                        'local_path': ner_path,
                        'bucket': self.ner_results_bucket,
                        's3_key': f"ner_results/{ner_file}",
                        'type': 'ner_result'
                    })
                else:
                    logger.warning(f"NER file not found: {ner_path}")
            else:
                logger.warning(f"No NER file specified for document: {doc_id}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} NER files")
            return True
        
        logger.info(f"\n--- Starting ner_results migration ---")
        if migration_tasks:
            self._execute_upload_tasks(migration_tasks, "ner_results")
        
        return True
    
    def migrate_sample_text_files(self, sample_docs: List[Dict], dry_run: bool = False) -> bool:
        """Migrate extracted text files for sample documents"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating extracted text for {len(sample_docs)} sample documents...")
        
        if not self.text_path.exists():
            logger.error(f"Text files path not found: {self.text_path}")
            return False
        
        migration_tasks = []
        
        for doc in sample_docs:
            doc_id = doc['doc_id']
            
            # Try different text file patterns
            text_file = None
            for pattern in [f"{doc_id}.txt", f"{doc_id}"]:
                potential_path = self.text_path / pattern
                if potential_path.exists():
                    text_file = potential_path
                    break
            
            if text_file:
                migration_tasks.append({
                    'doc_id': doc_id,
                    'local_path': text_file,
                    'bucket': self.extracted_text_bucket,
                    's3_key': f"extracted_text/{doc_id}.txt",
                    'type': 'text_file'
                })
            else:
                logger.warning(f"Text file not found for document: {doc_id}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate {len(migration_tasks)} text files")
            return True
        
        logger.info(f"\n--- Starting text_files migration ---")
        if migration_tasks:
            self._execute_upload_tasks(migration_tasks, "text_files")
        
        return True
    
    def _execute_upload_tasks(self, tasks: List[Dict], task_type: str):
        """Execute upload tasks with progress tracking"""
        logger.info(f"Uploading {len(tasks)} {task_type}...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._upload_file, task): task 
                for task in tasks
            }
            
            # Process completed tasks with progress bar
            with tqdm(total=len(tasks), desc=f"Uploading {task_type}") as pbar:
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        success = future.result()
                        if success:
                            self.stats[f"{task['type']}s_uploaded"] += 1
                        else:
                            self.stats['errors'] += 1
                    except Exception as e:
                        logger.error(f"Error uploading {task['local_path']}: {str(e)}")
                        self.stats['errors'] += 1
                        self.errors.append({
                            'file': str(task['local_path']),
                            'error': str(e),
                            'type': task['type']
                        })
                    finally:
                        pbar.update(1)
    
    def _upload_file(self, task: Dict) -> bool:
        """Upload a single file to S3"""
        try:
            local_path = task['local_path']
            bucket = task['bucket']
            s3_key = task['s3_key']
            
            # Skip existence check for now to avoid 404 errors
            # Just upload the file directly
            
            # Upload file
            self.s3_client.upload_file(
                str(local_path),
                bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'source': 'climate_risk_rag_migration',
                        'doc_id': task['doc_id'],
                        'migration_date': datetime.utcnow().isoformat()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {str(e)}")
            return False
    
    def run_migration(self, sample_file: str, dry_run: bool = False) -> Dict:
        """Run the complete selective migration process"""
        start_time = datetime.utcnow()
        
        try:
            # Load sample selection
            sample_docs = self.load_sample_selection(sample_file)
            
            if not sample_docs:
                logger.error("No sample documents loaded")
                return {'success': False, 'error': 'No sample documents'}
            
            logger.info(f"Starting {'dry run' if dry_run else 'migration'} for {len(sample_docs)} documents")
            
            # Migrate each type of data
            success = True
            success &= self.migrate_sample_documents(sample_docs, dry_run)
            success &= self.migrate_sample_chunks(sample_docs, dry_run)
            success &= self.migrate_sample_embeddings(sample_docs, dry_run)
            success &= self.migrate_sample_ner_results(sample_docs, dry_run)
            success &= self.migrate_sample_text_files(sample_docs, dry_run)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Generate summary
            summary = {
                'success': success,
                'dry_run': dry_run,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'sample_size': len(sample_docs),
                'statistics': self.stats.copy(),
                'errors': self.errors.copy() if self.errors else []
            }
            
            self._print_migration_summary(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'statistics': self.stats.copy(),
                'errors': self.errors.copy()
            }
    
    def _print_migration_summary(self, summary: Dict):
        """Print migration summary"""
        print("\n" + "="*60)
        print("SELECTIVE MIGRATION SUMMARY")
        print("="*60)
        
        if summary['dry_run']:
            print("🧪 DRY RUN MODE - No files were actually uploaded")
        
        print("Overall Statistics:")
        print(f"  Total files attempted: {sum(summary['statistics'].values()) - summary['statistics']['errors'] - summary['statistics']['skipped']}")
        print(f"  Successfully migrated: {sum(v for k, v in summary['statistics'].items() if k.endswith('_uploaded'))}")
        print(f"  Failed: {summary['statistics']['errors']}")
        print(f"  Skipped: {summary['statistics']['skipped']}")
        
        total_attempted = sum(summary['statistics'].values()) - summary['statistics']['errors'] - summary['statistics']['skipped']
        if total_attempted > 0:
            success_rate = (sum(v for k, v in summary['statistics'].items() if k.endswith('_uploaded')) / total_attempted) * 100
            print(f"  Success rate: {success_rate:.1f}%")
        else:
            print("  Success rate: N/A")
        
        print("\nDetailed Statistics:")
        for key, value in summary['statistics'].items():
            if key.endswith('_uploaded'):
                print(f"  {key.replace('_uploaded', '').title()}: {value}")
        
        print("="*60)
        
        if summary['errors']:
            print(f"\n⚠️  {len(summary['errors'])} errors occurred during migration")

def main():
    parser = argparse.ArgumentParser(description='Selective migration of climate risk documents')
    parser.add_argument('--local-path', required=True, help='Path to local climate risk data')
    parser.add_argument('--documents-bucket', required=True, help='S3 bucket for documents')
    parser.add_argument('--chunks-bucket', required=True, help='S3 bucket for chunks')
    parser.add_argument('--embeddings-bucket', required=True, help='S3 bucket for embeddings')
    parser.add_argument('--ner-results-bucket', required=True, help='S3 bucket for NER results')
    parser.add_argument('--extracted-text-bucket', required=True, help='S3 bucket for extracted text')
    parser.add_argument('--region', required=True, help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--sample-file', required=True, help='Sample selection JSON file')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximum concurrent uploads')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without uploading')
    
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
        
        result = migrator.run_migration(args.sample_file, args.dry_run)
        
        return 0 if result['success'] else 1
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
