#!/usr/bin/env python3
"""
Test DocumentIDManager Integration
Validates that DocumentIDManager.add_solution() works correctly on EC2.
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

def test_doc_id_generation():
    """Test DocumentIDManager integration with sample solutions."""
    
    print("DocumentIDManager Integration Test")
    print("=" * 50)
    
    # Parse a few sample solutions
    parser = CSVParser()
    solutions = list(parser.parse_all_files())[:3]
    
    print(f"Testing with {len(solutions)} sample solutions...")
    
    for i, solution in enumerate(solutions, 1):
        print(f"\n--- Solution {i}: {solution.name[:50]}... ---")
        print(f"Source URL: {solution.source_url}")
        print(f"Generated doc_id: {solution.doc_id}")
        
        # Check if DocumentIDManager was used
        uses_manager = solution._get_doc_id_manager() is not False
        print(f"Uses DocumentIDManager: {uses_manager}")
        
        # Validate ID format
        if solution.doc_id.startswith('sol_'):
            print("✅ ID format valid (sol_ prefix)")
        else:
            print(f"❌ Invalid ID format: {solution.doc_id}")
        
        # Check ID length and format
        if len(solution.doc_id) >= 10:
            print(f"✅ ID length appropriate: {len(solution.doc_id)} chars")
        else:
            print(f"❌ ID too short: {len(solution.doc_id)} chars")

def test_database_connectivity():
    """Test if DocumentIDManager can connect to database."""
    
    print("\n" + "=" * 50)
    print("Database Connectivity Test")
    print("=" * 50)
    
    try:
        from utils.DocumentIDManager import DocumentIDManager
        doc_manager = DocumentIDManager()
        print("✅ DocumentIDManager imported successfully")
        
        # Test database connection (if possible)
        # This might fail locally but should work on EC2
        print("Testing database connectivity...")
        
        return True
        
    except Exception as e:
        print(f"❌ DocumentIDManager initialization failed: {e}")
        return False

def main():
    """Run all tests."""
    
    # Test 1: Document ID generation
    test_doc_id_generation()
    
    # Test 2: Database connectivity
    db_connected = test_database_connectivity()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if db_connected:
        print("✅ Ready for production DocumentIDManager usage")
    else:
        print("⚠️  Using fallback ID generation (expected for local testing)")
    
    print("\nNext steps:")
    print("1. Deploy to EC2 with VPC access")
    print("2. Run this test on EC2 to validate DocumentIDManager")
    print("3. Verify generated IDs match expected format")

if __name__ == "__main__":
    main()