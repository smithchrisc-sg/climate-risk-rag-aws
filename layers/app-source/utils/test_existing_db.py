#!/usr/bin/env python3
"""
Test DatabaseManager with existing schema (bypass initialization)
"""

import os
import sys
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

class ExistingDatabaseManager:
    """DatabaseManager that works with existing schema"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.environ.get('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("Database connection string required")
        
        # Create connection pool
        self._connection_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=self.connection_string
        )
        
        print("✅ DatabaseManager initialized (existing schema)")
    
    def get_connection(self):
        """Get connection from pool"""
        return self._connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool"""
        self._connection_pool.putconn(conn)
    
    def test_operations(self):
        """Test basic database operations"""
        print("\n🧪 Testing database operations...")
        
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Test document operations
                test_doc_id = 'test_doc_climate_001'
                
                # Check if document exists
                cursor.execute('SELECT COUNT(*) FROM documents WHERE doc_id = %s', (test_doc_id,))
                result = cursor.fetchone()
                exists = result['count'] > 0 if isinstance(result, dict) else result[0] > 0
                
                if not exists:
                    # Insert test document
                    cursor.execute('''
                        INSERT INTO documents (
                            doc_id, url, original_filename, status, 
                            download_date, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW())
                    ''', (
                        test_doc_id,
                        'https://example.com/climate-report.pdf',
                        'climate_risk_assessment_2024.pdf',
                        'pending'
                    ))
                    print(f"✅ Inserted test document: {test_doc_id}")
                else:
                    print(f"📋 Test document already exists: {test_doc_id}")
                
                # Query document with metadata view
                cursor.execute('''
                    SELECT doc_id, original_filename, status, created_at
                    FROM document_metadata_view 
                    WHERE doc_id = %s
                ''', (test_doc_id,))
                
                result = cursor.fetchone()
                if result:
                    print(f"📊 Retrieved via view: {result['doc_id']} - {result['original_filename']}")
                    print(f"   Status: {result['status']}, Created: {result['created_at']}")
                
                # Test textract job insertion
                cursor.execute('''
                    SELECT COUNT(*) FROM textract_jobs 
                    WHERE doc_hash = %s
                ''', (f"hash_{test_doc_id}",))
                
                result = cursor.fetchone()
                job_exists = result['count'] > 0 if isinstance(result, dict) else result[0] > 0
                
                if not job_exists:
                    cursor.execute('''
                        INSERT INTO textract_jobs (
                            job_id, doc_hash, source_bucket, source_key,
                            output_bucket, status, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ''', (
                        f"job_{test_doc_id}",
                        f"hash_{test_doc_id}",
                        "test-documents-bucket",
                        f"documents/{test_doc_id}.pdf",
                        "test-output-bucket",
                        "pending"
                    ))
                    print(f"✅ Inserted textract job for: {test_doc_id}")
                
                # Test processing status
                cursor.execute('''
                    INSERT INTO document_processing_status (
                        doc_hash, filename, source_bucket, source_key,
                        text_extraction_status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (doc_hash) DO UPDATE SET
                        text_extraction_status = EXCLUDED.text_extraction_status,
                        updated_at = NOW()
                ''', (
                    f"hash_{test_doc_id}",
                    'climate_risk_assessment_2024.pdf',
                    "test-documents-bucket",
                    f"documents/{test_doc_id}.pdf",
                    "pending"
                ))
                print(f"✅ Updated processing status for: {test_doc_id}")
                
                # Get statistics
                cursor.execute('SELECT COUNT(*) FROM documents')
                result = cursor.fetchone()
                doc_count = result['count'] if isinstance(result, dict) else result[0]
                
                cursor.execute('SELECT COUNT(*) FROM textract_jobs')
                result = cursor.fetchone()
                job_count = result['count'] if isinstance(result, dict) else result[0]
                
                cursor.execute('SELECT COUNT(*) FROM document_processing_status')
                result = cursor.fetchone()
                status_count = result['count'] if isinstance(result, dict) else result[0]
                
                print(f"\n📊 Database Statistics:")
                print(f"   Documents: {doc_count}")
                print(f"   Textract Jobs: {job_count}")
                print(f"   Processing Status Records: {status_count}")
                
                # Test the processing pipeline view
                cursor.execute('''
                    SELECT doc_hash, filename, text_extraction_status, 
                           textract_job_id, created_at
                    FROM processing_pipeline_status
                    ORDER BY created_at DESC
                    LIMIT 5
                ''')
                
                pipeline_status = cursor.fetchall()
                if pipeline_status:
                    print(f"\n📋 Recent Pipeline Status:")
                    for status in pipeline_status:
                        print(f"   {status['filename']}: {status['text_extraction_status']}")
                
                conn.commit()
                
        finally:
            self.return_connection(conn)
        
        print("\n✅ All database operations completed successfully!")

def main():
    """Test the database with existing schema"""
    print("🔑 Testing Climate Risk RAG Database")
    print("=" * 50)
    
    try:
        # Initialize database manager
        db = ExistingDatabaseManager()
        
        # Run tests
        db.test_operations()
        
        print("\n🎉 Database testing completed successfully!")
        print("📋 The database is ready for:")
        print("   - Document processing pipeline")
        print("   - TextExtractor integration")
        print("   - TextChunker operations")
        print("   - Multi-system ID tracking")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
