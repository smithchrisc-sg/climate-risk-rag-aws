#!/usr/bin/env python3
"""
Minimal test to verify basic imports and functionality work on EC2.
"""

import sys
import os
from pathlib import Path

# Setup paths
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        # Test basic imports
        from config.environment import Environment
        print("[OK] Environment imported")
        
        from models.solution import Solution
        print("[OK] Solution imported")
        
        from parsers.csv_parser import CSVParser
        print("[OK] CSVParser imported")
        
        from generators.pseudo_document_generator import PseudoDocumentGenerator
        print("[OK] PseudoDocumentGenerator imported")
        
        from generators.chunk_generator import ChunkGenerator
        print("[OK] ChunkGenerator imported")
        
        from generators.rdf_generator import RDFGenerator
        print("[OK] RDFGenerator imported")
        
        from utils.data_lake_writer import DataLakeWriter
        print("[OK] DataLakeWriter imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """Test environment configuration."""
    print("\nTesting environment...")
    
    try:
        from config.environment import Environment
        
        env = Environment()
        print(f"[OK] Environment loaded")
        print(f"Database URL configured: {bool(env.database_url)}")
        print(f"OpenSearch endpoint: {bool(env.opensearch_endpoint)}")
        print(f"Neptune endpoint: {bool(env.neptune_endpoint)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

def test_csv_parser():
    """Test CSV parser with sample data."""
    print("\nTesting CSV parser...")
    
    try:
        from parsers.csv_parser import CSVParser
        
        parser = CSVParser()
        print("[OK] CSVParser created")
        
        # Check if input files exist
        input_dir = Path("input_data")
        if input_dir.exists():
            csv_files = list(input_dir.glob("*.csv"))
            print(f"[OK] Found {len(csv_files)} CSV files")
            
            if csv_files:
                # Try parsing first file - limit to 5 solutions to avoid connection issues
                solutions_iter = parser.parse_csv_file(csv_files[0])
                solutions = []
                for i, solution in enumerate(solutions_iter):
                    if i >= 5:  # Limit to 5 solutions
                        break
                    solutions.append(solution)
                
                print(f"[OK] Parsed {len(solutions)} solutions from {csv_files[0].name}")
                
                if solutions:
                    solution = solutions[0]
                    print(f"[OK] Sample solution: {solution.name} ({solution.country})")
        else:
            print("[WARN] No input_data directory found")
        
        return True
        
    except Exception as e:
        print(f"❌ CSV parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_generators():
    """Test document and chunk generators."""
    print("\nTesting generators...")
    
    try:
        from generators.pseudo_document_generator import PseudoDocumentGenerator
        from generators.chunk_generator import ChunkGenerator
        
        doc_gen = PseudoDocumentGenerator()
        chunk_gen = ChunkGenerator()
        
        print("[OK] Generators created")
        return True
        
    except Exception as e:
        print(f"❌ Generator test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Minimal EC2 Functionality Test ===\n")
    
    tests = [
        test_imports,
        test_environment, 
        test_csv_parser,
        test_generators
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    if all(results):
        print("\n🎉 All basic tests passed! Core functionality working.")
        sys.exit(0)
    else:
        print(f"\n❌ {len([r for r in results if not r])} tests failed.")
        sys.exit(1)
