#!/usr/bin/env python3
"""
POC SQLite to PostgreSQL Migration Utility
Migrates document data from POC SQLite database to PostgreSQL DocumentIDManager system
"""

import sqlite3
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
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

class POCMigrationUtility:
    """Utility to migrate POC SQLite data to PostgreSQL DocumentIDManager"""
    
    def __init__(self, sqlite_path: str, postgres_url: str, dry_run: bool = False):
        """
        Initialize migration utility
        
        Args:
            sqlite_path: Path to POC SQLite database
            postgres_url: PostgreSQL connection string
            dry_run: If True, only analyze data without migrating
        """
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.dry_run = dry_run
        
        # Initialize connections
        self.sqlite_conn = None
        self.doc_id_manager = None
        
        # Migration statistics
        self.stats = {
            'total_documents': 0,
            'migrated_documents': 0,
            'skipped_documents': 0,
            'error_documents': 0,
            'url_patterns': {},
            'status_distribution': {},
            's3_mappings_created': 0
        }
        
        logger.info(f"Initialized POC Migration Utility")
        logger.info(f"SQLite source: {sqlite_path}")
        logger.info(f"PostgreSQL target: {postgres_url}")
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

    def analyze_poc_data(self) -> Dict[str, Any]:
        """Analyze POC SQLite data structure and content"""
        logger.info("🔍 Analyzing POC data structure...")
        
        cursor = self.sqlite_conn.cursor()
        
        # Get total document count
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        self.stats['total_documents'] = total_docs
        
        # Analyze status distribution
        cursor.execute("SELECT status, COUNT(*) FROM documents GROUP BY status")
        for row in cursor.fetchall():
            status, count = row
            self.stats['status_distribution'][status or 'null'] = count
        
        # Analyze URL patterns
        cursor.execute("SELECT url FROM documents WHERE url IS NOT NULL LIMIT 1000")
        url_patterns = {}
        for row in cursor.fetchall():
            url = row[0]
            if url:
                domain = urlparse(url).netloc
                url_patterns[domain] = url_patterns.get(domain, 0) + 1
        
        self.stats['url_patterns'] = url_patterns
        
        # Sample documents for analysis
        cursor.execute("""
            SELECT doc_id, url, original_filename, status, download_date, 
                   pdf_path, text_path, chunking_complete
            FROM documents 
            LIMIT 10
        """)
        
        sample_docs = []
        for row in cursor.fetchall():
            sample_docs.append(dict(row))
        
        analysis = {
            'total_documents': total_docs,
            'status_distribution': self.stats['status_distribution'],
            'url_patterns': url_patterns,
            'sample_documents': sample_docs,
            'doc_id_format': self._analyze_doc_id_format(sample_docs)
        }
        
        logger.info(f"📊 Analysis complete: {total_docs} documents found")
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

    def create_s3_mapping_strategy(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Create strategy for mapping URLs to S3 keys"""
        logger.info("🗺️  Creating S3 mapping strategy...")
        
        mapping_rules = {}
        
        # World Bank documents (most common pattern)
        if 'documents.worldbank.org' in analysis['url_patterns']:
            mapping_rules['worldbank'] = {
                'pattern': r'documents\.worldbank\.org',
                's3_prefix': 'worldbank/',
                'key_strategy': 'filename_based'
            }
        
        # Generic documents
        mapping_rules['generic'] = {
            'pattern': r'.*',
            's3_prefix': 'documents/',
            'key_strategy': 'doc_id_based'
        }
        
        logger.info(f"📋 Created {len(mapping_rules)} mapping rules")
        return mapping_rules

    def generate_s3_key(self, doc: Dict[str, Any], mapping_rules: Dict[str, str]) -> str:
        """Generate S3 key for a document based on mapping rules"""
        url = doc.get('url', '')
        doc_id = doc['doc_id']
        filename = doc.get('original_filename', '')
        
        # Try World Bank pattern first
        if 'documents.worldbank.org' in url and filename:
            # Use original filename for World Bank documents
            return f"worldbank/{filename}"
        
        # Fallback to doc_id based naming
        if filename:
            # Extract extension from filename
            _, ext = os.path.splitext(filename)
            return f"documents/{doc_id}{ext}"
        else:
            # Default to PDF extension
            return f"documents/{doc_id}.pdf"

    def migrate_documents(self, batch_size: int = 100) -> Dict[str, Any]:
        """Migrate documents from SQLite to PostgreSQL"""
        logger.info(f"🚀 Starting document migration (batch size: {batch_size})...")
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No actual migration will occur")
        
        cursor = self.sqlite_conn.cursor()
        
        # Get all documents
        cursor.execute("""
            SELECT doc_id, url, original_filename, pdf_path, text_path,
                   status, download_date, chunking_complete, error_message,
                   updated_at, qdrant_id, opensearch_id, kg_id
            FROM documents
            ORDER BY doc_id
        """)
        
        # Process in batches
        batch = []
        processed = 0
        
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            
            for row in rows:
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
        
        logger.info(f"✅ Migration complete: {processed} documents processed")
        return self.stats

    def _analyze_document(self, doc_data: Dict[str, Any]):
        """Analyze a single document (dry run mode)"""
        doc_id = doc_data['doc_id']
        url = doc_data.get('url', '')
        
        # Generate S3 key
        s3_key = self.generate_s3_key(doc_data, {})
        
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
                'source': 'poc_sqlite',
                'migrated_at': datetime.utcnow().isoformat(),
                'original_doc_id': doc_id
            },
            
            # S3 mapping for TextExtractor integration
            's3_mapping': {
                'expected_key': self.generate_s3_key(doc_data, {}),
                'bucket_hint': 'solve-global-kr-documents-861276078413-us-east-1'
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
        """Create a mapping file for TextExtractor to use"""
        logger.info("📝 Creating S3 mapping file for TextExtractor...")
        
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            SELECT doc_id, url, original_filename 
            FROM documents 
            WHERE url IS NOT NULL
        """)
        
        s3_mappings = {}
        
        for row in cursor.fetchall():
            doc_data = dict(row)
            s3_key = self.generate_s3_key(doc_data, {})
            
            s3_mappings[s3_key] = {
                'doc_id': doc_data['doc_id'],
                'url': doc_data['url'],
                'filename': doc_data.get('original_filename')
            }
        
        # Save mapping file
        with open(output_path, 'w') as f:
            json.dump(s3_mappings, f, indent=2)
        
        logger.info(f"✅ S3 mapping file created: {output_path}")
        logger.info(f"📊 {len(s3_mappings)} S3 key mappings created")
        
        self.stats['s3_mappings_created'] = len(s3_mappings)

    def generate_report(self) -> str:
        """Generate migration report"""
        report = f"""
# POC to PostgreSQL Migration Report
## Date: {datetime.utcnow().isoformat()}

## Migration Statistics
- **Total Documents**: {self.stats['total_documents']}
- **Successfully Migrated**: {self.stats['migrated_documents']}
- **Skipped**: {self.stats['skipped_documents']}
- **Errors**: {self.stats['error_documents']}
- **S3 Mappings Created**: {self.stats['s3_mappings_created']}

## Status Distribution
"""
        for status, count in self.stats['status_distribution'].items():
            report += f"- **{status}**: {count} documents\n"
        
        report += f"""
## URL Patterns
"""
        for domain, count in self.stats['url_patterns'].items():
            report += f"- **{domain}**: {count} documents\n"
        
        report += f"""
## Migration Mode
- **Dry Run**: {self.dry_run}
- **Database**: {'Analysis only' if self.dry_run else 'Full migration'}

## Next Steps
1. Review migration results
2. Test TextExtractor integration with migrated data
3. Validate S3 key mappings
4. Update downstream processors to use migrated doc_ids
"""
        
        return report

    def close_connections(self):
        """Close database connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            logger.info("🔌 Closed SQLite connection")

def main():
    """Main migration process"""
    parser = argparse.ArgumentParser(description='Migrate POC SQLite data to PostgreSQL')
    parser.add_argument('--sqlite-path', 
                       default='/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db',
                       help='Path to POC SQLite database')
    parser.add_argument('--postgres-url', 
                       default=os.environ.get('DATABASE_URL'),
                       help='PostgreSQL connection string')
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
    
    print("🚀 POC to PostgreSQL Migration Utility")
    print("=" * 50)
    
    # Initialize migration utility
    migrator = POCMigrationUtility(
        sqlite_path=args.sqlite_path,
        postgres_url=args.postgres_url,
        dry_run=args.dry_run
    )
    
    try:
        # Connect to databases
        migrator.connect_databases()
        
        # Analyze POC data
        analysis = migrator.analyze_poc_data()
        print(f"📊 Found {analysis['total_documents']} documents to migrate")
        
        # Create S3 mapping strategy
        mapping_rules = migrator.create_s3_mapping_strategy(analysis)
        
        # Migrate documents
        results = migrator.migrate_documents(batch_size=args.batch_size)
        
        # Create S3 mapping file
        mapping_file = os.path.join(args.output_dir, 'poc_s3_mappings.json')
        migrator.create_s3_mapping_file(mapping_file)
        
        # Generate report
        report = migrator.generate_report()
        report_file = os.path.join(args.output_dir, f'migration_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.md')
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\n✅ Migration completed successfully!")
        print(f"📋 Report saved: {report_file}")
        print(f"🗺️  S3 mappings saved: {mapping_file}")
        print(f"📊 Results: {results['migrated_documents']} migrated, {results['error_documents']} errors")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        sys.exit(1)
    
    finally:
        migrator.close_connections()

if __name__ == "__main__":
    main()
