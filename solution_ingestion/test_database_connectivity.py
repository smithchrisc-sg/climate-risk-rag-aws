#!/usr/bin/env python3
"""
Test database connectivity on EC2 within VPC.
Tests DatabaseManager and DocumentIDManager with real database.
"""

import sys
import os
from pathlib import Path

# Setup paths
sys.path.append(str(Path(__file__).parent))

def test_database_connection():
    """Test basic database connectivity."""
    print("Testing database connectivity...")
    
    try:
        # Import database utilities
        from database_core_layer.utils.DatabaseManager import DatabaseManager
        from database_core_layer.utils.DocumentIDManager import DocumentIDManager
        from config.environment import Environment
        
        # Initialize environment
        env = Environment()
        print(f"[OK] Environment loaded")
        print(f"Database URL: {env._mask_url(env.database_url)}")
        
        # Validate configuration
        if not env.validate_config():
            raise Exception("Environment validation failed")
        print(f"[OK] Environment validation passed")
        
        # Test DatabaseManager
        db_manager = DatabaseManager(env)
        print(f"[OK] DatabaseManager initialized")
        
        # Test connection
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"[OK] Database connected: {version}")
        
        # Test DocumentIDManager
        doc_id_manager = DocumentIDManager(env)
        print(f"[OK] DocumentIDManager initialized")
        
        # Test document ID generation
        test_doc_id = doc_id_manager.generate_document_id("test_solution", "test_country")
        print(f"[OK] Generated document ID: {test_doc_id}")
        
        # Test document ID lookup (should return None for new ID)
        existing_id = doc_id_manager.get_existing_document_id("test_solution", "test_country")
        print(f"[OK] Document ID lookup: {existing_id}")
        
        print("\n✓ ALL DATABASE TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n✗ DATABASE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_solution_model():
    """Test solution model creation."""
    print("\nTesting solution model...")
    
    try:
        from models.solution import Solution
        
        # Create test solution with correct constructor parameters
        solution = Solution(
            id="test_001",
            source_file="test.csv",
            row_number=1,
            number="001",
            name="Test Solution",
            country="Test Country",
            public_organisations="Test Org",
            international_organisations="",
            private_organisations="",
            type_of_risk="Climate Risk",
            type_of_solution="Adaptation",
            ppp="Public",
            theme="Water Management",
            year_of_implementation="2024",
            description="Test description",
            implementation_details="Test implementation",
            results="Test results",
            lessons_learned="Test lessons",
            contact_information="test@example.com",
            website="https://example.com",
            additional_information=""
        )
        
        print(f"[OK] Solution created: {solution.name}")
        print(f"[OK] Document ID: {solution.doc_id}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ SOLUTION MODEL TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== EC2 Database Connectivity Test ===\n")
    
    db_success = test_database_connection()
    model_success = test_solution_model()
    
    if db_success and model_success:
        print("\n🎉 All tests passed! Database connectivity is working.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check configuration.")
        sys.exit(1)
