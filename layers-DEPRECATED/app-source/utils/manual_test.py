#!/usr/bin/env python3
"""
Manual testing script for database layer components
Use this for interactive testing and debugging
"""

import os
import sys
from datetime import datetime

def test_basic_connection():
    """Test basic database connection"""
    print("🔌 Testing database connection...")
    
    from DatabaseManager import DatabaseManager
    
    try:
        db_manager = DatabaseManager()
        print("✅ DatabaseManager initialized successfully")
        
        # Test schema validation
        is_valid = db_manager.validate_schema()
        print(f"📋 Schema validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
        
        return db_manager
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return None

def test_document_creation():
    """Test document creation and retrieval"""
    print("\n📄 Testing document operations...")
    
    from DocumentIDManager import DocumentIDManager
    
    try:
        doc_manager = DocumentIDManager()
        
        # Create a test document
        test_url = "https://example.com/test-doc.pdf"
        doc_id = doc_manager.get_or_create_id(test_url)
        print(f"📝 Created document ID: {doc_id}")
        
        # Add metadata
        metadata = {
            'title': {
                'value': 'Manual Test Document',
                'confidence': 0.95,
                'source': 'manual_test'
            },
            'status': 'testing'
        }
        
        doc_manager.add_or_update_document(doc_id, metadata)
        print("✅ Metadata added successfully")
        
        # Retrieve and display
        retrieved = doc_manager.get_document_metadata(doc_id)
        if retrieved:
            print(f"📖 Retrieved document:")
            print(f"   Title: {retrieved.get('title')}")
            print(f"   Status: {retrieved.get('status')}")
            print(f"   Created: {retrieved.get('created_at')}")
        
        return doc_id
        
    except Exception as e:
        print(f"❌ Document operations failed: {str(e)}")
        return None

def test_s3_integration():
    """Test S3-based document ID generation"""
    print("\n🪣 Testing S3 integration...")
    
    from DocumentIDManager import DocumentIDManager
    
    try:
        doc_manager = DocumentIDManager()
        
        # Test S3 ID generation
        bucket = "test-bucket"
        key = "documents/sample.pdf"
        
        doc_id = doc_manager.generate_id_from_s3(bucket, key)
        print(f"🆔 S3-based document ID: {doc_id}")
        
        # Test get_or_create
        doc_id2 = doc_manager.get_or_create_id_from_s3(bucket, key)
        print(f"🔄 Get/create result: {doc_id2}")
        
        if doc_id == doc_id2:
            print("✅ S3 ID generation is consistent")
        else:
            print("⚠️ S3 ID generation inconsistency detected")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 integration test failed: {str(e)}")
        return False

def test_metadata_structures():
    """Test DocumentMetadata classes"""
    print("\n📊 Testing metadata structures...")
    
    try:
        from document_processing.DocumentMetadata import DocumentMetadata, MetadataField
        
        # Create metadata with confidence scoring
        metadata = DocumentMetadata(
            doc_id="test_123",
            title=MetadataField("Test Document", 0.9, "manual"),
            author=MetadataField("Test Author", 0.8, "manual"),
            status="testing"
        )
        
        print(f"📋 Created metadata: {metadata}")
        print(f"🎯 Quality score: {metadata.metadata_quality}")
        print(f"✅ Validation: {'PASSED' if metadata.is_valid() else 'FAILED'}")
        
        # Test serialization
        metadata_dict = metadata.to_dict()
        print(f"📤 Serialization: {len(metadata_dict)} fields")
        
        # Test deserialization
        restored = DocumentMetadata.from_dict(metadata_dict)
        print(f"📥 Deserialization: {restored.title.value if restored.title else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata structures test failed: {str(e)}")
        return False

def interactive_mode():
    """Interactive testing mode"""
    print("\n🎮 Interactive Mode")
    print("Available commands:")
    print("  1 - Test connection")
    print("  2 - Create document")
    print("  3 - List documents")
    print("  4 - Get statistics")
    print("  5 - Test S3 integration")
    print("  q - Quit")
    
    from DocumentIDManager import DocumentIDManager
    doc_manager = DocumentIDManager()
    
    while True:
        try:
            choice = input("\nEnter command: ").strip()
            
            if choice == 'q':
                break
            elif choice == '1':
                test_basic_connection()
            elif choice == '2':
                url = input("Enter document URL: ").strip()
                if url:
                    doc_id = doc_manager.get_or_create_id(url)
                    print(f"Created document ID: {doc_id}")
            elif choice == '3':
                docs = doc_manager.list_documents(limit=5)
                print(f"Found {len(docs)} documents:")
                for doc in docs:
                    print(f"  {doc['doc_id']}: {doc.get('title', 'No title')} ({doc['status']})")
            elif choice == '4':
                stats = doc_manager.get_processing_statistics()
                print(f"Statistics: {stats}")
            elif choice == '5':
                test_s3_integration()
            else:
                print("Invalid command")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {str(e)}")

def main():
    """Main testing function"""
    print("🧪 Manual Database Layer Testing")
    print("=" * 50)
    
    # Check environment
    if not os.environ.get('DATABASE_URL'):
        print("❌ DATABASE_URL environment variable not set")
        print("Please set it with: export DATABASE_URL='postgresql://user:pass@host:port/db'")
        return
    
    print(f"🔗 Database URL: {os.environ['DATABASE_URL'].split('@')[0]}@***")
    
    # Run basic tests
    print("\n🚀 Running basic tests...")
    
    # Test 1: Connection
    db_manager = test_basic_connection()
    if not db_manager:
        print("❌ Cannot proceed without database connection")
        return
    
    # Test 2: Document operations
    doc_id = test_document_creation()
    
    # Test 3: S3 integration
    test_s3_integration()
    
    # Test 4: Metadata structures
    test_metadata_structures()
    
    # Interactive mode
    print("\n" + "=" * 50)
    interactive_mode()
    
    print("\n👋 Manual testing completed!")

if __name__ == "__main__":
    main()
