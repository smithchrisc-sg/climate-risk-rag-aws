#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Change to the script directory
os.chdir(Path(__file__).parent)
sys.path.append(str(Path.cwd()))

from solution_utils.layer_imports import setup_layer_imports
setup_layer_imports()

print("Testing specific imports...")

# Import from specific paths
db_layer_path = Path.cwd() / "layers" / "database-core-layer" / "python"
kg_layer_path = Path.cwd() / "layers" / "knowledge-graph-layer" / "python"

print(f"DB layer path: {db_layer_path}")
print(f"KG layer path: {kg_layer_path}")

try:
    # Add DB layer path temporarily to front
    sys.path.insert(0, str(db_layer_path))
    import utils.DatabaseManager as db_utils
    DatabaseManager = db_utils.DatabaseManager
    print("[OK] DatabaseManager imported from DB layer")
    
    import utils.DocumentIDManager as doc_utils
    DocumentIDManager = doc_utils.DocumentIDManager
    print("[OK] DocumentIDManager imported from DB layer")
    
    # Remove DB layer and add KG layer for KG imports
    sys.path.remove(str(db_layer_path))
    if str(kg_layer_path) not in sys.path:
        sys.path.insert(0, str(kg_layer_path))
    
    import utils.KnowledgeGraphManager as kg_utils
    KnowledgeGraphManager = kg_utils.KnowledgeGraphManager
    print("[OK] KnowledgeGraphManager imported from KG layer")
    
    print("SUCCESS: All specific imports working!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()