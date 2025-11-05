#!/usr/bin/env python3
"""
Final test of layer imports with both direct imports and helper functions.
"""

import sys
import os
from pathlib import Path

# Setup
os.chdir(Path(__file__).parent)
sys.path.append(str(Path.cwd()))

print("Testing layer imports...")

try:
    # Test setup
    from solution_utils.layer_imports import setup_layer_imports
    setup_layer_imports()
    print("[OK] Layer imports setup successful")
    
    # Test direct imports (database layer should be found first)
    import utils.DatabaseManager
    DatabaseManager = utils.DatabaseManager.DatabaseManager
    print("[OK] DatabaseManager imported via direct import")
    
    import utils.DocumentIDManager
    DocumentIDManager = utils.DocumentIDManager.DocumentIDManager
    print("[OK] DocumentIDManager imported via direct import")
    
    # Test helper functions for specific imports
    from solution_utils.layer_imports import get_knowledge_graph_manager
    KnowledgeGraphManager = get_knowledge_graph_manager()
    print("[OK] KnowledgeGraphManager imported via helper function")
    
    # Test rdflib from KG layer
    from rdflib import Graph
    print("[OK] rdflib imported successfully")
    
    # Test solution model
    from models.solution import Solution
    print("[OK] Solution model imported successfully")
    
    print("\n✓ ALL IMPORTS SUCCESSFUL!")
    print("The layer import system is working correctly.")
    
except Exception as e:
    print(f"\n✗ IMPORT FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)