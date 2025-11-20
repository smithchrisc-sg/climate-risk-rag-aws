#!/usr/bin/env python3
"""
Test Solution Ingestion Utility
Validates solution processing without database connections
"""

import csv
import json
from solution_ingestion_utility import SolutionIngestionUtility

class MockDatabaseManager:
    """Mock database manager for testing"""
    def add_or_update_document(self, **kwargs):
        print(f"Mock DB: Adding document {kwargs.get('document_id')} with content_type {kwargs.get('content_type')}")

class MockDocumentIDManager:
    """Mock document ID manager for testing"""
    def generate_solution_id(self, name):
        return f"sol_{name.lower().replace(' ', '_')}"

class MockUtility:
    """Mock utility classes for testing"""
    def normalize(self, text):
        return text.strip()

def test_solution_processing():
    """Test solution processing with sample data"""
    
    # Create test utility with mocks
    utility = SolutionIngestionUtility()
    utility.db_manager = MockDatabaseManager()
    utility.doc_id_manager = MockDocumentIDManager()
    utility.text_normalizer = MockUtility()
    
    # Test with sample CSV
    csv_path = "data/input/solutions/sample_solutions.csv"
    
    print("Testing solution ingestion utility...")
    print(f"Processing CSV: {csv_path}")
    
    try:
        stats = utility.process_solutions_csv(csv_path)
        print(f"\nTest Results:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Chunks created: {stats['chunks_created']}")
        
        if stats['processed'] > 0:
            print("\n✅ Solution ingestion utility test PASSED")
        else:
            print("\n❌ Solution ingestion utility test FAILED")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_solution_processing()
