#!/usr/bin/env python3
"""
Database Integration Test
Tests DocumentIDManager and DatabaseManager functionality on EC2.
"""

import logging
import sys
import os
from pathlib import Path

# Add layers to path
layers_path = Path(__file__).parent / "layers" / "database-core-layer" / "python"
sys.path.insert(0, str(layers_path))

from models.solution import Solution
from parsers.csv_parser import CSVParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_document_id_manager():
    """Test DocumentIDManager integration."""
    
    print("DocumentIDManager Test")
    print("=" * 30)
    
    # Parse one sample solution
    parser = CSVParser()
    solutions = list(parser.parse_all_files())[:1]
    
    if not solutions:
        print("❌ No solutions found to test")
        return False
    
    solution = solutions[0]
    
    print(f"Testing solution: {solution.name[:50]}...")
    print(f"Source URL: {solution.source_url}")
    print(f"Generated doc_id: {solution.doc_id}")
    
    # Check DocumentIDManager usage
    uses_manager = solution._get_doc_id_manager() is not False
    print(f"Uses DocumentIDManager: {uses_manager}")
    
    # Validate ID format
    if solution.doc_id.startswith('sol_'):
        print("✅ ID format valid (sol_ prefix)")
        return True
    else:
        print(f"❌ Invalid ID format: {solution.doc_id}")
        return False

def test_database_manager():
    """Test DatabaseManager functionality."""
    
    print("\nDatabaseManager Test")
    print("=" * 30)
    
    try:
        from utils.DatabaseManager import DatabaseManager
        db_manager = DatabaseManager()
        print("✅ DatabaseManager imported and initialized")
        
        # Test basic database operations
        print("Testing database connectivity...")
        
        # Try to get document count (should work if DB is accessible)
        try:
            count = db_manager.get_document_count()
            print(f"✅ Database accessible - document count: {count}")
            return True
        except Exception as e:
            print(f"❌ Database query failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ DatabaseManager initialization failed: {e}")
        return False

def test_solution_storage():
    """Test storing a solution in the database."""
    
    print("\nSolution Storage Test")
    print("=" * 30)
    
    try:
        from utils.DatabaseManager import DatabaseManager
        db_manager = DatabaseManager()
        
        # Parse one solution
        parser = CSVParser()
        solutions = list(parser.parse_all_files())[:1]
        
        if not solutions:
            print("❌ No solutions to test")
            return False
        
        solution = solutions[0]
        
        print(f"Testing storage of: {solution.name[:50]}...")
        print(f"Doc ID: {solution.doc_id}")
        
        # Test storing document metadata
        try:
            db_manager.store_document_metadata(
                doc_id=solution.doc_id,
                title=solution.name,
                source_url=solution.source_url,
                metadata=solution.get_metadata()
            )
            print("✅ Document metadata stored successfully")
            
            # Test storing document text
            text_content = solution.get_full_text()
            db_manager.store_document_text(
                doc_id=solution.doc_id,
                text_content=text_content
            )
            print("✅ Document text stored successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Storage failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def test_environment_setup():
    """Test environment and layer setup."""
    
    print("Environment Setup Test")
    print("=" * 30)
    
    # Check Python path
    print(f"Python path includes layers: {str(layers_path) in sys.path}")
    
    # Check layer files exist
    doc_manager_path = layers_path / "utils" / "DocumentIDManager.py"
    db_manager_path = layers_path / "utils" / "DatabaseManager.py"
    
    print(f"DocumentIDManager exists: {doc_manager_path.exists()}")
    print(f"DatabaseManager exists: {db_manager_path.exists()}")
    
    # Check environment variables
    db_url = os.getenv('DATABASE_URL')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    print(f"DATABASE_URL set: {bool(db_url)}")
    print(f"AWS_REGION: {aws_region}")
    
    return doc_manager_path.exists() and db_manager_path.exists()

def main():
    """Run all database integration tests."""
    
    print("Database Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Environment setup
    env_ok = test_environment_setup()
    
    # Test 2: DocumentIDManager
    doc_id_ok = test_document_id_manager()
    
    # Test 3: DatabaseManager
    db_manager_ok = test_database_manager()
    
    # Test 4: Solution storage (only if previous tests pass)
    storage_ok = False
    if env_ok and doc_id_ok and db_manager_ok:
        storage_ok = test_solution_storage()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    print(f"Environment Setup: {'✅' if env_ok else '❌'}")
    print(f"DocumentIDManager: {'✅' if doc_id_ok else '❌'}")
    print(f"DatabaseManager: {'✅' if db_manager_ok else '❌'}")
    print(f"Solution Storage: {'✅' if storage_ok else '❌'}")
    
    all_passed = env_ok and doc_id_ok and db_manager_ok and storage_ok
    
    print(f"\nOverall Status: {'✅ READY FOR DEVELOPMENT' if all_passed else '❌ NEEDS FIXES'}")
    
    if not all_passed:
        print("\nTroubleshooting:")
        if not env_ok:
            print("- Check layer files are copied correctly")
            print("- Verify PYTHONPATH includes layer directories")
        if not doc_id_ok or not db_manager_ok:
            print("- Check DATABASE_URL environment variable")
            print("- Verify EC2 has VPC access to RDS")
            print("- Check security group allows PostgreSQL (5432)")
        if not storage_ok:
            print("- Check database schema supports solutions")
            print("- Verify IAM permissions for RDS access")

if __name__ == "__main__":
    main()