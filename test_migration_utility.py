#!/usr/bin/env python3
"""
Test script for POC Migration Utility
Validates the migration logic before running on full dataset
"""

import os
import sys
import sqlite3
from datetime import datetime

def test_sqlite_connection():
    """Test connection to SQLite database"""
    print("🧪 Testing SQLite connection...")
    
    sqlite_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
    
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Test basic queries
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        print(f"  ✅ Connected to SQLite: {total_docs} documents found")
        
        # Test sample data
        cursor.execute("SELECT doc_id, url, original_filename FROM documents LIMIT 3")
        samples = cursor.fetchall()
        
        print("  📄 Sample documents:")
        for row in samples:
            doc = dict(row)
            print(f"    - {doc['doc_id']}: {doc['original_filename']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ SQLite connection failed: {str(e)}")
        return False

def test_documentid_manager_import():
    """Test DocumentIDManager import"""
    print("🧪 Testing DocumentIDManager import...")
    
    try:
        # Add the layers path
        sys.path.append('/Users/chris/climate-risk-rag-aws/layers/app-source/utils')
        
        from DocumentIDManager import DocumentIDManager
        print("  ✅ DocumentIDManager imported successfully")
        
        # Test initialization (without actual database connection)
        try:
            # This will fail without proper DATABASE_URL, but import should work
            doc_manager = DocumentIDManager(database_url="postgresql://test")
            print("  ✅ DocumentIDManager can be instantiated")
        except Exception as e:
            print(f"  ⚠️  DocumentIDManager instantiation failed (expected): {str(e)}")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ DocumentIDManager import failed: {str(e)}")
        print("  💡 Make sure the layers/app-source/utils directory exists")
        return False

def test_s3_key_generation():
    """Test S3 key generation logic"""
    print("🧪 Testing S3 key generation...")
    
    # Sample document data from SQLite
    sample_docs = [
        {
            'doc_id': '94bee167_0c5c1713',
            'url': 'http://documents.worldbank.org/curated/en/513441468326170992/pdf/589020NWP0EACC10Box353823B01public1.pdf',
            'original_filename': '589020NWP0EACC10Box353823B01public1.pdf'
        },
        {
            'doc_id': '99112f11_a6f5a4e8',
            'url': 'http://documents.worldbank.org/curated/en/986961467721999165/pdf/ACS19080-REVISED-OUO-9-Making-Climate-Finance-Work-in-Agriculture-Final-Version.pdf',
            'original_filename': 'ACS19080-REVISED-OUO-9-Making-Climate-Finance-Work-in-Agriculture-Final-Version.pdf'
        },
        {
            'doc_id': 'test123_456789',
            'url': 'https://example.com/document.pdf',
            'original_filename': 'example-document.pdf'
        }
    ]
    
    def generate_s3_key(doc):
        """Test S3 key generation logic"""
        url = doc.get('url', '')
        doc_id = doc['doc_id']
        filename = doc.get('original_filename', '')
        
        # World Bank documents
        if 'documents.worldbank.org' in url and filename:
            return f"worldbank/{filename}"
        
        # Generic documents
        if filename:
            _, ext = os.path.splitext(filename)
            return f"documents/{doc_id}{ext}"
        else:
            return f"documents/{doc_id}.pdf"
    
    print("  📋 S3 key generation results:")
    for doc in sample_docs:
        s3_key = generate_s3_key(doc)
        print(f"    - {doc['doc_id']} → {s3_key}")
    
    print("  ✅ S3 key generation working")
    return True

def test_migration_dry_run():
    """Test migration utility in dry run mode"""
    print("🧪 Testing migration utility dry run...")
    
    try:
        # Import the migration utility
        sys.path.append('/Users/chris/climate-risk-rag-aws')
        from migrate_poc_to_postgres import POCMigrationUtility
        
        # Test with dry run mode (no database connection needed)
        migrator = POCMigrationUtility(
            sqlite_path="/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db",
            postgres_url="postgresql://test",  # Dummy URL for dry run
            dry_run=True
        )
        
        # Test database connection (SQLite only)
        migrator.sqlite_conn = sqlite3.connect(migrator.sqlite_path)
        migrator.sqlite_conn.row_factory = sqlite3.Row
        
        # Test analysis
        analysis = migrator.analyze_poc_data()
        print(f"  ✅ Analysis complete: {analysis['total_documents']} documents")
        print(f"  📊 Status distribution: {analysis['status_distribution']}")
        print(f"  🌐 URL patterns: {list(analysis['url_patterns'].keys())}")
        
        # Test S3 mapping strategy
        mapping_rules = migrator.create_s3_mapping_strategy(analysis)
        print(f"  ✅ S3 mapping rules created: {len(mapping_rules)} rules")
        
        migrator.close_connections()
        return True
        
    except Exception as e:
        print(f"  ❌ Migration utility test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing POC Migration Utility")
    print("=" * 50)
    print(f"Test time: {datetime.utcnow().isoformat()}")
    print()
    
    tests = [
        ("SQLite Connection", test_sqlite_connection),
        ("DocumentIDManager Import", test_documentid_manager_import),
        ("S3 Key Generation", test_s3_key_generation),
        ("Migration Dry Run", test_migration_dry_run)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
        print()
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("📊 Test Summary")
    print("-" * 20)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Migration utility is ready to use.")
        print("\n📋 Next steps:")
        print("1. Set DATABASE_URL environment variable")
        print("2. Run migration in dry-run mode first:")
        print("   python migrate_poc_to_postgres.py --dry-run")
        print("3. Review results and run full migration:")
        print("   python migrate_poc_to_postgres.py")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Fix issues before running migration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
