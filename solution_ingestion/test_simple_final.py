#!/usr/bin/env python3
import sys
import os
from pathlib import Path

os.chdir(Path(__file__).parent)
sys.path.append(str(Path.cwd()))

print("Testing simplified layer imports...")

try:
    from solution_utils.layer_imports import setup_layer_imports
    setup_layer_imports()
    print("[OK] Layer setup complete")
    
    # Test database imports (should work since DB layer is first)
    import utils.DatabaseManager
    DatabaseManager = utils.DatabaseManager.DatabaseManager
    print("[OK] DatabaseManager imported")
    
    import utils.DocumentIDManager
    DocumentIDManager = utils.DocumentIDManager.DocumentIDManager
    print("[OK] DocumentIDManager imported")
    
    # Test KG imports using helper
    from solution_utils.layer_imports import import_kg_utils
    kg_utils = import_kg_utils()
    KnowledgeGraphManager = kg_utils['KnowledgeGraphManager']
    print("[OK] KnowledgeGraphManager imported via helper")
    
    # Test rdflib
    from rdflib import Graph
    print("[OK] rdflib imported")
    
    print("\n✓ SUCCESS: All critical imports working!")
    
except Exception as e:
    print(f"\n✗ FAILED: {e}")
    import traceback
    traceback.print_exc()