#!/usr/bin/env python3
"""
Selective POC SQLite to PostgreSQL Migration Utility
Migrates only documents that exist in the S3 raw bucket (sample of ~1000 documents)
"""

import sqlite3
import os
import sys
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import argparse
from urllib.parse import urlparse
import re

# Add the layers path for DocumentIDManager
sys.path.append('/Users/chris/climate-risk-rag-aws/layers/app-source/utils')

try:
    from DocumentIDManager import DocumentIDManager
    from DatabaseManager import DatabaseManager
except ImportError as e:
    print(f"❌ Error importing DocumentIDManager: {e}")
    print("Make sure the layers/app-source/utils directory is accessible")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SelectivePOCMigrationUtility:
    """Utility to migrate only POC documents that exist in S3 raw bucket"""
    
    def __init__(self, sqlite_path: str, postgres_url: str, s3_bucket: str, 
                 aws_profile: str = 'solve-global', dry_run: bool = False):
        """
        Initialize selective migration utility
        
        Args:
            sqlite_path: Path to POC SQLite database
            postgres_url: PostgreSQL connection string
            s3_bucket: S3 bucket containing raw documents
            aws_profile: AWS profile to use
            dry_run: If True, only analyze data without migrating
        """
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.s3_bucket = s3_bucket
        self.aws_profile = aws_profile
        self.dry_run = dry_run
        
        # Initialize AWS session with profile
        self.session = boto3.Session(profile_name=aws_profile)
        self.s3_client = self.session.client('s3')
        
        # Initialize connections
        self.sqlite_conn = None
        self.doc_id_manager = None
        
        # Document sets
        self.s3_doc_ids: Set[str] = set()
        self.poc_doc_ids: Set[str] = set()
        self.migration_doc_ids: Set[str] = set()
        
        # Migration statistics
        self.stats = {
            'total_poc_documents': 0,
            'total_s3_documents': 0,
            'matching_documents': 0,
            'migrated_documents': 0,
            'skipped_documents': 0,
            'error_documents': 0,
            'url_patterns': {},
            'status_distribution': {},
            's3_mappings_created': 0
        }
        
        logger.info(f"Initialized Selective POC Migration Utility")
        logger.info(f"SQLite source: {sqlite_path}")
        logger.info(f"PostgreSQL target: {postgres_url}")
        logger.info(f"S3 bucket: {s3_bucket}")
        logger.info(f"AWS profile: {aws_profile}")
        logger.info(f"Dry run mode: {dry_run}")

    def connect_databases(self):
        """Establish database connections"""
        try:
            # Connect to SQLite
            if not os.path.exists(self.sqlite_path):
                raise FileNotFoundError(f"SQLite database not found: {self.sqlite_path}")
            
            self.sqlite_conn = sqlite3.connect(self.sqlite_path)
            self.sqlite_conn.row_factory = sqlite3.Row  # Enable column access by name
            logger.info("✅ Connected to SQLite database")
            
            # Connect to PostgreSQL via DocumentIDManager
            if not self.dry_run:
                self.doc_id_manager = DocumentIDManager(database_url=self.postgres_url)
                logger.info("✅ Connected to PostgreSQL via DocumentIDManager")
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            raise

    def get_s3_document_ids(self) -> Set[str]:
        """Get list of document IDs from S3 bucket"""
        logger.info(f"🔍 Scanning S3 bucket: {self.s3_bucket}")
        
        doc_ids = set()
        
        try:
            # List objects in the documents/ prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.s3_bucket, Prefix='documents/')
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        
                        # Extract doc_id from filename
                        # Format: documents/0004ad39_4285ab3d.pdf
                        if key.startswith('documents/') and key.endswith('.pdf'):
                            filename = os.path.basename(key)
                            doc_id = os.path.splitext(filename)[0]
                            
                            # Validate doc_id format (8chars_8chars)
                            if re.match(r'^[a-f0-9]{8}_[a-f0-9]{8}$', doc_id):
                                doc_ids.add(doc_id)
            
            logger.info(f"📊 Found {len(doc_ids)} documents in S3 bucket")
            self.stats['total_s3_documents'] = len(doc_ids)
            
            return doc_ids
            
        except Exception as e:
            logger.error(f"❌ Error scanning S3 bucket: {str(e)}")
            raise

    def get_poc_document_ids(self) -> Set[str]:
        """Get list of document IDs from POC SQLite database"""
        logger.info("🔍 Scanning POC SQLite database...")
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT doc_id FROM documents")
        
        doc_ids = set()
        for row in cursor.fetchall():
            doc_ids.add(row[0])
        
        logger.info(f"📊 Found {len(doc_ids)} documents in POC database")
        self.stats['total_poc_documents'] = len(doc_ids)
        
        return doc_ids

    def find_matching_documents(self) -> Set[str]:
        """Find documents that exist in both S3 and POC database"""
        logger.info("🔍 Finding documents that exist in both S3 and POC database...")
        
        # Get document IDs from both sources
        self.s3_doc_ids = self.get_s3_document_ids()
        self.poc_doc_ids = self.get_poc_document_ids()
        
        # Find intersection
        matching_docs = self.s3_doc_ids.intersection(self.poc_doc_ids)
        
        logger.info(f"📊 Found {len(matching_docs)} documents in both S3 and POC database")
        logger.info(f"   S3 only: {len(self.s3_doc_ids - self.poc_doc_ids)} documents")
        logger.info(f"   POC only: {len(self.poc_doc_ids - self.s3_doc_ids)} documents")
        
        self.stats['matching_documents'] = len(matching_docs)
        self.migration_doc_ids = matching_docs
        
        return matching_docs

    def analyze_migration_documents(self) -> Dict[str, Any]:
        """Analyze the documents that will be migrated"""
        logger.info("🔍 Analyzing documents for migration...")
        
        if not self.migration_doc_ids:
            self.find_matching_documents()
        
        cursor = self.sqlite_conn.cursor()
        
        # Get details for matching documents
        placeholders = ','.join('?' * len(self.migration_doc_ids))
        query = f"""
            SELECT doc_id, url, original_filename, status, download_date,
                   pdf_path, text_path, chunking_complete
            FROM documents 
            WHERE doc_id IN ({placeholders})
        """
        
        cursor.execute(query, list(self.migration_doc_ids))
        
        # Analyze status distribution
        status_counts = {}
        url_patterns = {}
        sample_docs = []
        
        for row in cursor.fetchall():
            doc = dict(row)
            sample_docs.append(doc)
            
            # Count status
            status = doc.get('status', 'null')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count URL patterns
            url = doc.get('url', '')
            if url:
                domain = urlparse(url).netloc
                url_patterns[domain] = url_patterns.get(domain, 0) + 1
        
        self.stats['status_distribution'] = status_counts
        self.stats['url_patterns'] = url_patterns
        
        analysis = {
            'migration_documents': len(self.migration_doc_ids),
            'status_distribution': status_counts,
            'url_patterns': url_patterns,
            'sample_documents': sample_docs[:10],  # First 10 for review
            'doc_id_format': self._analyze_doc_id_format(sample_docs)
        }
        
        logger.info(f"📊 Analysis complete: {len(self.migration_doc_ids)} documents to migrate")
        return analysis

    def _analyze_doc_id_format(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Analyze the doc_id format used in POC"""
        doc_ids = [doc['doc_id'] for doc in sample_docs if doc['doc_id']]
        
        if not doc_ids:
            return {'format': 'unknown', 'pattern': None}
        
        # Check if doc_ids follow the pattern: 8chars_8chars
        pattern = r'^[a-f0-9]{8}_[a-f0-9]{8}$'
        matches_pattern = all(re.match(pattern, doc_id) for doc_id in doc_ids)
        
        return {
            'format': 'hash_pair' if matches_pattern else 'custom',
            'pattern': pattern if matches_pattern else 'varied',
            'sample_ids': doc_ids[:5],
            'length_range': [len(min(doc_ids, key=len)), len(max(doc_ids, key=len))]
        }

    def generate_s3_key(self, doc: Dict[str, Any]) -> str:
        """Generate S3 key for a document"""
        doc_id = doc['doc_id']
        filename = doc.get('original_filename', '')
        url = doc.get('url', '')
        
        # For documents in our S3 bucket, they're stored as documents/{doc_id}.pdf
        return f"documents/{doc_id}.pdf"

    def migrate_selected_documents(self, batch_size: int = 100) -> Dict[str, Any]:
        """Migrate only the selected documents from SQLite to PostgreSQL"""
        logger.info(f"🚀 Starting selective document migration...")
        logger.info(f"   Documents to migrate: {len(self.migration_doc_ids)}")
        logger.info(f"   Batch size: {batch_size}")
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No actual migration will occur")
        
        cursor = self.sqlite_conn.cursor()
        
        # Get documents to migrate
        placeholders = ','.join('?' * len(self.migration_doc_ids))
        query = f"""
            SELECT doc_id, url, original_filename, pdf_path, text_path,
                   status, download_date, chunking_complete, error_message,
                   updated_at, qdrant_id, opensearch_id, kg_id
            FROM documents
            WHERE doc_id IN ({placeholders})
            ORDER BY doc_id
        """
        
        cursor.execute(query, list(self.migration_doc_ids))
        
        # Process documents
        processed = 0
        
        for row in cursor.fetchall():
            doc_data = dict(row)
            
            try:
                if self.dry_run:
                    # Just analyze the document
                    self._analyze_document(doc_data)
                    self.stats['migrated_documents'] += 1
                else:
                    # Actually migrate the document
                    self._migrate_single_document(doc_data)
                    self.stats['migrated_documents'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing document {doc_data['doc_id']}: {str(e)}")
                self.stats['error_documents'] += 1
            
            processed += 1
            if processed % 100 == 0:
                logger.info(f"📈 Processed {processed} documents...")
        
        logger.info(f"✅ Selective migration complete: {processed} documents processed")
        return self.stats

    def _analyze_document(self, doc_data: Dict[str, Any]):
        """Analyze a single document (dry run mode)"""
        doc_id = doc_data['doc_id']
        url = doc_data.get('url', '')
        
        # Generate S3 key
        s3_key = self.generate_s3_key(doc_data)
        
        # Log analysis
        logger.debug(f"📄 Document {doc_id}: URL={url[:50]}..., S3_key={s3_key}")

    def _migrate_single_document(self, doc_data: Dict[str, Any]):
        """Migrate a single document to PostgreSQL"""
        doc_id = doc_data['doc_id']
        
        # Prepare metadata for DocumentIDManager
        metadata = {
            'url': doc_data.get('url'),
            'original_filename': doc_data.get('original_filename'),
            'pdf_path': doc_data.get('pdf_path'),
            'text_path': doc_data.get('text_path'),
            'status': doc_data.get('status', 'pending'),
            'download_date': doc_data.get('download_date'),
            'chunking_complete': bool(doc_data.get('chunking_complete', False)),
            'error_message': doc_data.get('error_message'),
            'updated_at': doc_data.get('updated_at'),
            
            # System IDs from POC
            'system_ids': {
                'qdrant_id': doc_data.get('qdrant_id'),
                'opensearch_id': doc_data.get('opensearch_id'),
                'kg_id': doc_data.get('kg_id')
            },
            
            # Migration metadata
            'migration_info': {
                'source': 'poc_sqlite_selective',
                'migrated_at': datetime.utcnow().isoformat(),
                'original_doc_id': doc_id,
                'in_s3_bucket': True,
                's3_bucket': self.s3_bucket
            },
            
            # S3 mapping for TextExtractor integration
            's3_mapping': {
                'current_key': self.generate_s3_key(doc_data),
                'bucket': self.s3_bucket,
                'verified_in_s3': True
            }
        }
        
        # Add to DocumentIDManager
        self.doc_id_manager.add_or_update_document(doc_id, metadata)
        
        # Update system IDs if they exist
        for system_name, system_id in metadata['system_ids'].items():
            if system_id:
                self.doc_id_manager.update_system_id(
                    doc_id, 
                    system_name.replace('_id', ''), 
                    system_id, 
                    'migrated'
                )

    def create_s3_mapping_file(self, output_path: str):
        """Create a mapping file for TextExtractor to use (only for migrated documents)"""
        logger.info("📝 Creating S3 mapping file for migrated documents...")
        
        cursor = self.sqlite_conn.cursor()
        
        # Get only the documents we're migrating
        placeholders = ','.join('?' * len(self.migration_doc_ids))
        query = f"""
            SELECT doc_id, url, original_filename 
            FROM documents 
            WHERE doc_id IN ({placeholders})
            AND url IS NOT NULL
        """
        
        cursor.execute(query, list(self.migration_doc_ids))
        
        s3_mappings = {}
        
        for row in cursor.fetchall():
            doc_data = dict(row)
            s3_key = self.generate_s3_key(doc_data)
            
            s3_mappings[s3_key] = {
                'doc_id': doc_data['doc_id'],
                'url': doc_data['url'],
                'filename': doc_data.get('original_filename'),
                'migration_source': 'selective_poc_migration',
                'verified_in_s3': True
            }
        
        # Save mapping file
        with open(output_path, 'w') as f:
            json.dump(s3_mappings, f, indent=2)
        
        logger.info(f"✅ S3 mapping file created: {output_path}")
        logger.info(f"📊 {len(s3_mappings)} S3 key mappings created (selective migration)")
        
        self.stats['s3_mappings_created'] = len(s3_mappings)

    def generate_report(self) -> str:
        """Generate selective migration report"""
        report = f"""
# Selective POC to PostgreSQL Migration Report
## Date: {datetime.utcnow().isoformat()}

## Migration Strategy
- **Approach**: Selective migration of documents that exist in both POC database and S3 bucket
- **S3 Bucket**: {self.s3_bucket}
- **AWS Profile**: {self.aws_profile}

## Document Analysis
- **Total POC Documents**: {self.stats['total_poc_documents']}
- **Total S3 Documents**: {self.stats['total_s3_documents']}
- **Matching Documents**: {self.stats['matching_documents']}
- **Documents Migrated**: {self.stats['migrated_documents']}
- **Migration Errors**: {self.stats['error_documents']}

## Document Distribution
- **S3 Only**: {self.stats['total_s3_documents'] - self.stats['matching_documents']} documents
- **POC Only**: {self.stats['total_poc_documents'] - self.stats['matching_documents']} documents
- **Both S3 and POC**: {self.stats['matching_documents']} documents ✅

## Status Distribution (Migrated Documents)
"""
        for status, count in self.stats['status_distribution'].items():
            report += f"- **{status}**: {count} documents\n"
        
        report += f"""
## URL Patterns (Migrated Documents)
"""
        for domain, count in self.stats['url_patterns'].items():
            report += f"- **{domain}**: {count} documents\n"
        
        report += f"""
## S3 Integration
- **S3 Mappings Created**: {self.stats['s3_mappings_created']}
- **S3 Key Format**: `documents/{{doc_id}}.pdf`
- **Verified in S3**: All migrated documents confirmed to exist in S3

## Migration Mode
- **Dry Run**: {self.dry_run}
- **Database**: {'Analysis only' if self.dry_run else 'Full selective migration'}

## Benefits of Selective Migration
1. **Focused Dataset**: Only migrate documents we actually have in S3
2. **Reduced Complexity**: ~1000 documents vs 15,000+ full dataset
3. **Verified Availability**: All migrated documents confirmed to exist in S3
4. **Cost Efficiency**: No wasted processing on unavailable documents

## Next Steps
1. Review selective migration results
2. Test TextExtractor integration with migrated subset
3. Validate S3 key mappings work correctly
4. Update downstream processors to use migrated doc_ids
5. Consider expanding to full dataset later if needed
"""
        
        return report

    def close_connections(self):
        """Close database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            logger.info("🔌 Closed SQLite connection")

def main():
    """Main selective migration process"""
    parser = argparse.ArgumentParser(description='Selective POC SQLite to PostgreSQL migration')
    parser.add_argument('--sqlite-path', 
                       default='/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db',
                       help='Path to POC SQLite database')
    parser.add_argument('--postgres-url', 
                       default=os.environ.get('DATABASE_URL'),
                       help='PostgreSQL connection string')
    parser.add_argument('--s3-bucket',
                       default='solve-global-kr-documents-861276078413-us-east-1',
                       help='S3 bucket containing raw documents')
    parser.add_argument('--aws-profile',
                       default='solve-global',
                       help='AWS profile to use')
    parser.add_argument('--dry-run', action='store_true',
                       help='Analyze data without migrating')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for migration')
    parser.add_argument('--output-dir', 
                       default='/Users/chris/climate-risk-rag-aws',
                       help='Output directory for reports and mappings')
    
    args = parser.parse_args()
    
    if not args.postgres_url:
        print("❌ PostgreSQL URL required (set DATABASE_URL env var or use --postgres-url)")
        sys.exit(1)
    
    print("🚀 Selective POC to PostgreSQL Migration Utility")
    print("=" * 60)
    print(f"Strategy: Migrate only documents that exist in both POC database and S3 bucket")
    
    # Initialize migration utility
    migrator = SelectivePOCMigrationUtility(
        sqlite_path=args.sqlite_path,
        postgres_url=args.postgres_url,
        s3_bucket=args.s3_bucket,
        aws_profile=args.aws_profile,
        dry_run=args.dry_run
    )
    
    try:
        # Connect to databases
        migrator.connect_databases()
        
        # Find matching documents
        matching_docs = migrator.find_matching_documents()
        print(f"📊 Found {len(matching_docs)} documents in both S3 and POC database")
        
        if len(matching_docs) == 0:
            print("⚠️  No matching documents found. Check S3 bucket and POC database.")
            return
        
        # Analyze documents for migration
        analysis = migrator.analyze_migration_documents()
        print(f"📋 Analysis complete: {analysis['migration_documents']} documents to migrate")
        
        # Migrate documents
        results = migrator.migrate_selected_documents(batch_size=args.batch_size)
        
        # Create S3 mapping file
        mapping_file = os.path.join(args.output_dir, 'selective_poc_s3_mappings.json')
        migrator.create_s3_mapping_file(mapping_file)
        
        # Generate report
        report = migrator.generate_report()
        report_file = os.path.join(args.output_dir, f'selective_migration_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.md')
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n✅ Selective migration completed successfully!")
        print(f"📋 Report saved: {report_file}")
        print(f"🗺️  S3 mappings saved: {mapping_file}")
        print(f"📊 Results: {results['migrated_documents']} migrated, {results['error_documents']} errors")
        print(f"🎯 Strategy: Focused on {len(matching_docs)} documents that exist in both systems")
        
    except Exception as e:
        logger.error(f"❌ Selective migration failed: {str(e)}")
        sys.exit(1)
    
    finally:
        migrator.close_connections()

if __name__ == "__main__":
    main()
