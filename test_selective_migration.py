#!/usr/bin/env python3
"""
Test script for Selective POC Migration Utility
Validates the selective migration logic before running on actual data
"""

import os
import sys
import sqlite3
import boto3
from datetime import datetime

def test_s3_bucket_access():
    """Test access to S3 bucket with solve-global profile"""
    print("🧪 Testing S3 bucket access...")
    
    try:
        session = boto3.Session(profile_name='solve-global')
        s3_client = session.client('s3')
        
        bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        
        # Test bucket access
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix='documents/',
            MaxKeys=10
        )
        
        if 'Contents' in response:
            doc_count = len(response['Contents'])
            print(f"  ✅ S3 bucket accessible: {doc_count} sample documents found")
            
            # Show sample document names
            print("  📄 Sample S3 documents:")
            for obj in response['Contents'][:5]:
                key = obj['Key']
                filename = os.path.basename(key)
                doc_id = os.path.splitext(filename)[0] if filename.endswith('.pdf') else 'unknown'
                print(f"    - {doc_id}: {key}")
            
            return True
        else:
            print("  ⚠️  S3 bucket accessible but no documents found")
            return False
        
    except Exception as e:
        print(f"  ❌ S3 bucket access failed: {str(e)}")
        return False

def test_sqlite_sample_docs():
    """Test SQLite database and get sample doc_ids"""
    print("🧪 Testing SQLite database sample...")
    
    sqlite_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
    
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get sample documents that might match S3 format
        cursor.execute("""
            SELECT doc_id, url, original_filename 
            FROM documents 
            WHERE doc_id LIKE '%_%' 
            AND LENGTH(doc_id) = 17
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        
        print(f"  ✅ SQLite accessible: {len(samples)} sample documents")
        print("  📄 Sample POC documents:")
        
        sample_doc_ids = []
        for row in samples:
            doc = dict(row)
            doc_id = doc['doc_id']
            filename = doc.get('original_filename', 'unknown')
            sample_doc_ids.append(doc_id)
            print(f"    - {doc_id}: {filename}")
        
        conn.close()
        return sample_doc_ids
        
    except Exception as e:
        print(f"  ❌ SQLite access failed: {str(e)}")
        return []

def test_doc_id_matching():
    """Test if any POC doc_ids match S3 document names"""
    print("🧪 Testing doc_id matching between S3 and POC...")
    
    try:
        # Get S3 document IDs
        session = boto3.Session(profile_name='solve-global')
        s3_client = session.client('s3')
        bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix='documents/',
            MaxKeys=100  # Sample first 100
        )
        
        s3_doc_ids = set()
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.pdf'):
                    filename = os.path.basename(key)
                    doc_id = os.path.splitext(filename)[0]
                    s3_doc_ids.add(doc_id)
        
        print(f"  📊 Found {len(s3_doc_ids)} S3 document IDs (sample)")
        
        # Get POC document IDs (sample)
        sqlite_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db"
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT doc_id FROM documents LIMIT 1000")  # Sample first 1000
        poc_doc_ids = set(row[0] for row in cursor.fetchall())
        
        print(f"  📊 Found {len(poc_doc_ids)} POC document IDs (sample)")
        
        # Find matches
        matches = s3_doc_ids.intersection(poc_doc_ids)
        
        print(f"  🎯 Found {len(matches)} matching documents!")
        
        if matches:
            print("  ✅ Sample matches:")
            for doc_id in list(matches)[:5]:
                print(f"    - {doc_id}")
        
        conn.close()
        return len(matches) > 0
        
    except Exception as e:
        print(f"  ❌ Doc ID matching test failed: {str(e)}")
        return False

def test_selective_migration_dry_run():
    """Test selective migration utility in dry run mode"""
    print("🧪 Testing selective migration utility...")
    
    try:
        # Import the selective migration utility
        sys.path.append('/Users/chris/climate-risk-rag-aws')
        from migrate_poc_selective import SelectivePOCMigrationUtility
        
        # Test with dry run mode
        migrator = SelectivePOCMigrationUtility(
            sqlite_path="/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db",
            postgres_url="postgresql://test",  # Dummy URL for dry run
            s3_bucket="solve-global-kr-documents-861276078413-us-east-1",
            aws_profile="solve-global",
            dry_run=True
        )
        
        # Test database connection (SQLite only for dry run)
        migrator.sqlite_conn = sqlite3.connect(migrator.sqlite_path)
        migrator.sqlite_conn.row_factory = sqlite3.Row
        
        # Test finding matching documents
        matching_docs = migrator.find_matching_documents()
        print(f"  ✅ Found {len(matching_docs)} documents in both S3 and POC")
        
        if len(matching_docs) > 0:
            # Test analysis
            analysis = migrator.analyze_migration_documents()
            print(f"  ✅ Analysis complete: {analysis['migration_documents']} documents to migrate")
            print(f"  📊 Status distribution: {analysis['status_distribution']}")
            print(f"  🌐 URL patterns: {list(analysis['url_patterns'].keys())}")
        
        migrator.close_connections()
        return len(matching_docs) > 0
        
    except Exception as e:
        print(f"  ❌ Selective migration test failed: {str(e)}")
        return False

def main():
    """Run all selective migration tests"""
    print("🚀 Testing Selective POC Migration Utility")
    print("=" * 60)
    print(f"Test time: {datetime.utcnow().isoformat()}")
    print()
    
    tests = [
        ("S3 Bucket Access", test_s3_bucket_access),
        ("SQLite Sample Documents", lambda: len(test_sqlite_sample_docs()) > 0),
        ("Doc ID Matching", test_doc_id_matching),
        ("Selective Migration Dry Run", test_selective_migration_dry_run)
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
        print("\n🎉 All tests passed! Selective migration utility is ready to use.")
        print("\n📋 Next steps:")
        print("1. Set DATABASE_URL environment variable")
        print("2. Run selective migration in dry-run mode first:")
        print("   python migrate_poc_selective.py --dry-run")
        print("3. Review results and run selective migration:")
        print("   python migrate_poc_selective.py")
        print("\n🎯 Benefits of selective migration:")
        print("   • Only migrates ~1000 documents that exist in S3")
        print("   • Avoids migrating 14,000+ documents we don't have")
        print("   • Focused test set for TextExtractor integration")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Fix issues before running migration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
