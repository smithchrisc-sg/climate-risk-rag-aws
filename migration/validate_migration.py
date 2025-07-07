#!/usr/bin/env python3
"""
Migration Validation Script
Validates that all documents and metadata were successfully migrated
"""

import boto3
import json
import logging
from pathlib import Path
from typing import Dict, List, Set
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationValidator:
    """Validates migration completeness and integrity"""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        self.s3 = boto3.client('s3', region_name=aws_region)
    
    def validate_migration(self, local_path: str, documents_bucket: str, 
                          artifacts_bucket: str) -> Dict[str, any]:
        """Validate complete migration"""
        logger.info("Starting migration validation...")
        
        results = {
            'validation_timestamp': boto3.Session().region_name,
            'local_analysis': {},
            'aws_analysis': {},
            'comparison': {},
            'issues': []
        }
        
        # Analyze local files
        local_path = Path(local_path)
        results['local_analysis'] = self._analyze_local_files(local_path)
        
        # Analyze AWS files
        results['aws_analysis'] = self._analyze_aws_files(documents_bucket, artifacts_bucket)
        
        # Compare
        results['comparison'] = self._compare_local_vs_aws(
            results['local_analysis'], 
            results['aws_analysis']
        )
        
        # Generate report
        self._generate_validation_report(results)
        
        return results
    
    def _analyze_local_files(self, local_path: Path) -> Dict:
        """Analyze local file structure with correct folder-per-document counting"""
        analysis = {
            'raw_documents': 0,
            'chunk_folders': 0,
            'total_chunk_files': 0,
            'embedding_folders': 0,
            'total_embedding_files': 0,
            'ner_result_folders': 0,
            'total_ner_files': 0,
            'document_ids': set()
        }
        
        # Count raw documents
        raw_path = local_path / 'data' / 'raw'
        if raw_path.exists():
            pdf_files = list(raw_path.glob('*.pdf'))
            analysis['raw_documents'] = len(pdf_files)
            analysis['document_ids'] = {f.stem for f in pdf_files}
        
        # Count chunks (folder per document, files per chunk)
        chunks_path = local_path / 'data' / 'chunks'
        if chunks_path.exists():
            chunk_folders = list(chunks_path.glob('*/'))
            analysis['chunk_folders'] = len(chunk_folders)
            
            total_chunk_files = 0
            for folder in chunk_folders:
                if folder.is_dir():
                    chunk_files = list(folder.glob('*.json'))
                    total_chunk_files += len(chunk_files)
            
            analysis['total_chunk_files'] = total_chunk_files
        
        # Count embeddings (folder per document, files per embedding)
        embeddings_path = local_path / 'data' / 'embeddings'
        if embeddings_path.exists():
            embedding_folders = list(embeddings_path.glob('*/'))
            analysis['embedding_folders'] = len(embedding_folders)
            
            total_embedding_files = 0
            for folder in embedding_folders:
                if folder.is_dir():
                    embedding_files = list(folder.glob('*.json'))
                    total_embedding_files += len(embedding_files)
            
            analysis['total_embedding_files'] = total_embedding_files
        
        # Count NER results (folder per document, files per result)
        ner_path = local_path / 'data' / 'ner_results'
        if ner_path.exists():
            ner_folders = list(ner_path.glob('*/'))
            analysis['ner_result_folders'] = len(ner_folders)
            
            total_ner_files = 0
            for folder in ner_folders:
                if folder.is_dir():
                    ner_files = list(folder.glob('*.json'))
                    total_ner_files += len(ner_files)
            
            analysis['total_ner_files'] = total_ner_files
        
        logger.info(f"Local analysis: {analysis['raw_documents']} documents, "
                   f"{analysis['total_chunk_files']} chunk files in {analysis['chunk_folders']} folders, "
                   f"{analysis['total_embedding_files']} embedding files in {analysis['embedding_folders']} folders")
        
        return analysis
    
    def _analyze_aws_files(self, documents_bucket: str, artifacts_bucket: str) -> Dict:
        """Analyze AWS S3 files with correct folder structure counting"""
        analysis = {
            'documents': 0,
            'metadata_files': 0,
            'chunk_folders': 0,
            'total_chunk_files': 0,
            'embedding_folders': 0,
            'total_embedding_files': 0,
            'ner_result_folders': 0,
            'total_ner_files': 0,
            'document_ids': set(),
            'total_size_bytes': 0
        }
        
        try:
            # Analyze documents bucket
            paginator = self.s3.get_paginator('list_objects_v2')
            
            # Documents
            for page in paginator.paginate(Bucket=documents_bucket, Prefix='documents/'):
                for obj in page.get('Contents', []):
                    if obj['Key'].endswith('.pdf'):
                        analysis['documents'] += 1
                        analysis['total_size_bytes'] += obj['Size']
                        # Extract doc ID from filename
                        filename = obj['Key'].split('/')[-1]
                        doc_id = filename.replace('.pdf', '')
                        analysis['document_ids'].add(doc_id)
            
            # Artifacts - count folder structure
            chunk_folders = set()
            embedding_folders = set()
            ner_folders = set()
            
            for page in paginator.paginate(Bucket=artifacts_bucket):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    analysis['total_size_bytes'] += obj['Size']
                    
                    if key.startswith('metadata/'):
                        analysis['metadata_files'] += 1
                    elif key.startswith('chunks/'):
                        # Extract folder structure: chunks/doc_id/chunk_file.json
                        parts = key.split('/')
                        if len(parts) >= 3:  # chunks/doc_id/file.json
                            doc_id = parts[1]
                            chunk_folders.add(doc_id)
                            analysis['total_chunk_files'] += 1
                    elif key.startswith('embeddings/'):
                        # Extract folder structure: embeddings/doc_id/embedding_file.json
                        parts = key.split('/')
                        if len(parts) >= 3:  # embeddings/doc_id/file.json
                            doc_id = parts[1]
                            embedding_folders.add(doc_id)
                            analysis['total_embedding_files'] += 1
                    elif key.startswith('ner_results/'):
                        # Extract folder structure: ner_results/doc_id/ner_file.json
                        parts = key.split('/')
                        if len(parts) >= 3:  # ner_results/doc_id/file.json
                            doc_id = parts[1]
                            ner_folders.add(doc_id)
                            analysis['total_ner_files'] += 1
            
            analysis['chunk_folders'] = len(chunk_folders)
            analysis['embedding_folders'] = len(embedding_folders)
            analysis['ner_result_folders'] = len(ner_folders)
            
            logger.info(f"AWS analysis: {analysis['documents']} documents, "
                       f"{analysis['total_chunk_files']} chunk files in {analysis['chunk_folders']} folders, "
                       f"{analysis['total_embedding_files']} embedding files in {analysis['embedding_folders']} folders")
            
        except Exception as e:
            logger.error(f"Error analyzing AWS files: {str(e)}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _compare_local_vs_aws(self, local: Dict, aws: Dict) -> Dict:
        """Compare local vs AWS file counts with correct folder structure"""
        comparison = {
            'documents_match': local['raw_documents'] == aws['documents'],
            'chunk_folders_match': local['chunk_folders'] == aws['chunk_folders'],
            'total_chunk_files_match': local['total_chunk_files'] == aws['total_chunk_files'],
            'embedding_folders_match': local['embedding_folders'] == aws['embedding_folders'],
            'total_embedding_files_match': local['total_embedding_files'] == aws['total_embedding_files'],
            'ner_folders_match': local['ner_result_folders'] == aws['ner_result_folders'],
            'total_ner_files_match': local['total_ner_files'] == aws['total_ner_files'],
            'missing_documents': [],
            'extra_documents': [],
            'summary': {}
        }
        
        # Find missing/extra documents
        local_ids = local.get('document_ids', set())
        aws_ids = aws.get('document_ids', set())
        
        comparison['missing_documents'] = list(local_ids - aws_ids)
        comparison['extra_documents'] = list(aws_ids - local_ids)
        
        # Summary
        comparison['summary'] = {
            'local_documents': local['raw_documents'],
            'aws_documents': aws['documents'],
            'local_chunk_files': local['total_chunk_files'],
            'aws_chunk_files': aws['total_chunk_files'],
            'local_embedding_files': local['total_embedding_files'],
            'aws_embedding_files': aws['total_embedding_files'],
            'missing_count': len(comparison['missing_documents']),
            'extra_count': len(comparison['extra_documents']),
            'migration_success_rate': (
                (aws['documents'] / local['raw_documents'] * 100) 
                if local['raw_documents'] > 0 else 0
            ),
            'chunk_migration_rate': (
                (aws['total_chunk_files'] / local['total_chunk_files'] * 100)
                if local['total_chunk_files'] > 0 else 0
            ),
            'embedding_migration_rate': (
                (aws['total_embedding_files'] / local['total_embedding_files'] * 100)
                if local['total_embedding_files'] > 0 else 0
            )
        }
        
        return comparison
    
    def _generate_validation_report(self, results: Dict):
        """Generate human-readable validation report with correct structure"""
        print("\n" + "="*60)
        print("🔍 MIGRATION VALIDATION REPORT")
        print("="*60)
        
        local = results['local_analysis']
        aws = results['aws_analysis']
        comp = results['comparison']
        
        print(f"\n📊 FILE COUNTS:")
        print(f"  Documents:        {local['raw_documents']:>6} local → {aws['documents']:>6} AWS")
        print(f"  Chunk Folders:    {local['chunk_folders']:>6} local → {aws['chunk_folders']:>6} AWS")
        print(f"  Total Chunks:     {local['total_chunk_files']:>6} local → {aws['total_chunk_files']:>6} AWS")
        print(f"  Embed Folders:    {local['embedding_folders']:>6} local → {aws['embedding_folders']:>6} AWS")
        print(f"  Total Embeddings: {local['total_embedding_files']:>6} local → {aws['total_embedding_files']:>6} AWS")
        print(f"  NER Folders:      {local['ner_result_folders']:>6} local → {aws['ner_result_folders']:>6} AWS")
        print(f"  Total NER Files:  {local['total_ner_files']:>6} local → {aws['total_ner_files']:>6} AWS")
        
        print(f"\n✅ VALIDATION STATUS:")
        print(f"  Documents:        {'✅ PASS' if comp['documents_match'] else '❌ FAIL'}")
        print(f"  Chunk Folders:    {'✅ PASS' if comp['chunk_folders_match'] else '❌ FAIL'}")
        print(f"  Total Chunks:     {'✅ PASS' if comp['total_chunk_files_match'] else '❌ FAIL'}")
        print(f"  Embed Folders:    {'✅ PASS' if comp['embedding_folders_match'] else '❌ FAIL'}")
        print(f"  Total Embeddings: {'✅ PASS' if comp['total_embedding_files_match'] else '❌ FAIL'}")
        print(f"  NER Folders:      {'✅ PASS' if comp['ner_folders_match'] else '❌ FAIL'}")
        print(f"  Total NER Files:  {'✅ PASS' if comp['total_ner_files_match'] else '❌ FAIL'}")
        
        print(f"\n📈 MIGRATION SUMMARY:")
        print(f"  Document Success Rate:  {comp['summary']['migration_success_rate']:.1f}%")
        print(f"  Chunk Success Rate:     {comp['summary']['chunk_migration_rate']:.1f}%")
        print(f"  Embedding Success Rate: {comp['summary']['embedding_migration_rate']:.1f}%")
        print(f"  Missing Docs:           {comp['summary']['missing_count']}")
        print(f"  Extra Docs:             {comp['summary']['extra_count']}")
        print(f"  Total Size:             {aws['total_size_bytes'] / (1024**3):.2f} GB")
        
        if comp['missing_documents']:
            print(f"\n⚠️  MISSING DOCUMENTS (first 10):")
            for doc_id in comp['missing_documents'][:10]:
                print(f"    {doc_id}")
        
        if comp['extra_documents']:
            print(f"\n❓ EXTRA DOCUMENTS (first 10):")
            for doc_id in comp['extra_documents'][:10]:
                print(f"    {doc_id}")
        
        # Overall status
        all_match = all([
            comp['documents_match'],
            comp['chunk_folders_match'],
            comp['total_chunk_files_match'],
            comp['embedding_folders_match'],
            comp['total_embedding_files_match'],
            comp['ner_folders_match'],
            comp['total_ner_files_match']
        ])
        
        print(f"\n🎯 OVERALL STATUS: {'✅ MIGRATION SUCCESSFUL' if all_match else '⚠️  MIGRATION INCOMPLETE'}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Validate Climate Risk RAG migration')
    parser.add_argument('--local-path', required=True,
                       help='Path to local climate_risk_rag directory')
    parser.add_argument('--documents-bucket', required=True,
                       help='S3 bucket for documents')
    parser.add_argument('--artifacts-bucket', required=True,
                       help='S3 bucket for artifacts')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--output-file', 
                       help='Save detailed results to JSON file')
    
    args = parser.parse_args()
    
    validator = MigrationValidator(args.region)
    results = validator.validate_migration(
        args.local_path,
        args.documents_bucket,
        args.artifacts_bucket
    )
    
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {args.output_file}")


if __name__ == "__main__":
    main()
