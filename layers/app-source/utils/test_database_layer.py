#!/usr/bin/env python3
"""
Test script for PostgreSQL database layer conversion
Tests DatabaseManager and DocumentIDManager functionality
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connection"""
    logger.info("Testing database connection...")
    
    try:
        from DatabaseManager import DatabaseManager
        
        # Test with environment variable
        db_manager = DatabaseManager()
        
        # Test schema validation
        is_valid = db_manager.validate_schema()
        logger.info(f"Schema validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

def test_document_operations():
    """Test document CRUD operations"""
    logger.info("Testing document operations...")
    
    try:
        from DocumentIDManager import DocumentIDManager
        
        # Initialize manager
        doc_manager = DocumentIDManager()
        
        # Test document creation
        test_url = "https://example.com/test-document.pdf"
        doc_id = doc_manager.get_or_create_id(test_url)
        logger.info(f"Created document ID: {doc_id}")
        
        # Test metadata update
        test_metadata = {
            'title': {
                'value': 'Test Document',
                'confidence': 0.9,
                'source': 'test'
            },
            'author': {
                'value': 'Test Author',
                'confidence': 0.8,
                'source': 'test'
            },
            'status': 'processing',
            'processing_info': {
                'test_run': True,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        doc_manager.add_or_update_document(doc_id, test_metadata)
        logger.info("✅ Document metadata updated")
        
        # Test metadata retrieval
        retrieved_metadata = doc_manager.get_document_metadata(doc_id)
        if retrieved_metadata:
            logger.info("✅ Document metadata retrieved")
            logger.info(f"   Title: {retrieved_metadata.get('title')}")
            logger.info(f"   Status: {retrieved_metadata.get('status')}")
        else:
            logger.error("❌ Failed to retrieve document metadata")
            return False
        
        # Test status update
        success = doc_manager.update_document_status(doc_id, 'completed')
        logger.info(f"Status update: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        # Test system ID update
        success = doc_manager.update_system_id(doc_id, 'test_system', 'test_id_123')
        logger.info(f"System ID update: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Document operations test failed: {str(e)}")
        return False

def test_s3_integration():
    """Test S3-based document ID generation"""
    logger.info("Testing S3 integration...")
    
    try:
        from DocumentIDManager import DocumentIDManager
        
        # Initialize manager
        doc_manager = DocumentIDManager()
        
        # Test S3-based ID generation (without actual S3 access)
        test_bucket = "test-bucket"
        test_key = "documents/test-document.pdf"
        
        doc_id = doc_manager.generate_id_from_s3(test_bucket, test_key)
        logger.info(f"Generated S3-based document ID: {doc_id}")
        
        # Test get_or_create with S3
        doc_id2 = doc_manager.get_or_create_id_from_s3(test_bucket, test_key)
        logger.info(f"Get/create S3 document ID: {doc_id2}")
        
        if doc_id == doc_id2:
            logger.info("✅ S3 ID generation is consistent")
        else:
            logger.warning("⚠️ S3 ID generation inconsistency")
        
        return True
        
    except Exception as e:
        logger.error(f"S3 integration test failed: {str(e)}")
        return False

def test_bulk_operations():
    """Test bulk operations and performance"""
    logger.info("Testing bulk operations...")
    
    try:
        from DocumentIDManager import DocumentIDManager
        
        doc_manager = DocumentIDManager()
        
        # Create multiple documents
        doc_ids = []
        for i in range(5):
            url = f"https://example.com/document-{i}.pdf"
            doc_id = doc_manager.get_or_create_id(url)
            doc_ids.append(doc_id)
            
            # Add metadata
            metadata = {
                'title': f'Test Document {i}',
                'status': 'pending',
                'processing_info': {
                    'batch_test': True,
                    'index': i
                }
            }
            doc_manager.add_or_update_document(doc_id, metadata)
        
        logger.info(f"✅ Created {len(doc_ids)} test documents")
        
        # Test listing documents
        documents = doc_manager.list_documents(limit=10)
        logger.info(f"✅ Listed {len(documents)} documents")
        
        # Test statistics
        stats = doc_manager.get_processing_statistics()
        logger.info(f"✅ Processing statistics: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"Bulk operations test failed: {str(e)}")
        return False

def test_connection_pooling():
    """Test connection pooling behavior"""
    logger.info("Testing connection pooling...")
    
    try:
        from DatabaseManager import DatabaseManager
        
        # Create multiple managers to test pool sharing
        managers = [DatabaseManager() for _ in range(3)]
        
        # Test concurrent operations
        for i, manager in enumerate(managers):
            test_doc = {
                'doc_id': f'pool_test_{i}',
                'url': f'https://example.com/pool-test-{i}.pdf',
                'status': 'testing'
            }
            manager.add_or_update_document(f'pool_test_{i}', test_doc)
        
        logger.info("✅ Connection pooling test completed")
        return True
        
    except Exception as e:
        logger.error(f"Connection pooling test failed: {str(e)}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    logger.info("Cleaning up test data...")
    
    try:
        from DatabaseManager import DatabaseManager
        
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Delete test documents
                cursor.execute("""
                    DELETE FROM documents 
                    WHERE url LIKE 'https://example.com/%' 
                    OR url LIKE 's3://test-bucket/%'
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"✅ Cleaned up {deleted_count} test documents")
                
        finally:
            db_manager.return_connection(conn)
            
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")

def main():
    """Run all tests"""
    logger.info("🧪 Starting PostgreSQL Database Layer Tests")
    logger.info("=" * 60)
    
    # Check environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not set")
        logger.info("Please set DATABASE_URL to your PostgreSQL connection string")
        return False
    
    logger.info(f"Database URL configured: {database_url.split('@')[0]}@***")
    
    # Run tests
    tests = [
        ("Database Connection", test_database_connection),
        ("Document Operations", test_document_operations),
        ("S3 Integration", test_s3_integration),
        ("Bulk Operations", test_bulk_operations),
        ("Connection Pooling", test_connection_pooling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        logger.info("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Clean up
    logger.info(f"\n🧹 Cleanup")
    logger.info("-" * 40)
    cleanup_test_data()
    
    # Summary
    logger.info(f"\n📊 Test Results Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name:.<30} {status}")
    
    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Database layer is ready.")
        return True
    else:
        logger.error(f"💥 {total - passed} tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
