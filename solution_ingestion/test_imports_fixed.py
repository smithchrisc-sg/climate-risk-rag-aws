#!/usr/bin/env python3
"""
Test script to verify layer imports work correctly.
"""

import sys
from pathlib import Path

def test_layer_imports():
    """Test that layer imports work correctly."""
    
    print("Testing layer import setup...")
    
    try:
        # Add current directory to path
        sys.path.append(str(Path(__file__).parent))
        
        # Setup layer imports
        from solution_utils.layer_imports import setup_layer_imports
        setup_layer_imports()
        print("[OK] Layer imports setup successful")
        
        # Test database layer imports
        import utils.DatabaseManager
        DatabaseManager = utils.DatabaseManager.DatabaseManager
        print("[OK] DatabaseManager import successful")
        
        import utils.DocumentIDManager
        DocumentIDManager = utils.DocumentIDManager.DocumentIDManager
        print("[OK] DocumentIDManager import successful")
        
        # Test knowledge graph layer imports
        import utils.KnowledgeGraphManager
        KnowledgeGraphManager = utils.KnowledgeGraphManager.KnowledgeGraphManager
        print("[OK] KnowledgeGraphManager import successful")
        
        from rdflib import Graph
        print("[OK] rdflib import successful")
        
        # Test solution model (which uses DocumentIDManager)
        print("\nTesting solution model...")
        from models.solution import Solution
        print("[OK] Solution model import successful")
        
        print("\nAll imports working correctly!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_layer_imports()
    sys.exit(0 if success else 1)