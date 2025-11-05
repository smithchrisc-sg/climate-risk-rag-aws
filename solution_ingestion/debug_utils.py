#!/usr/bin/env python3
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from utils.layer_imports import setup_layer_imports
setup_layer_imports()

print("Python paths after setup:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print("\nTrying to find utils module:")
try:
    import utils
    print(f"utils found at: {utils.__file__}")
    print(f"utils.__path__: {getattr(utils, '__path__', 'No __path__')}")
except Exception as e:
    print(f"utils import failed: {e}")

print("\nTrying to find DatabaseManager directly:")
try:
    # Try importing from specific path
    layer_path = Path(__file__).parent / "layers" / "database-core-layer" / "python"
    if str(layer_path) not in sys.path:
        sys.path.insert(0, str(layer_path))
    
    # Import with full module path
    import importlib.util
    db_manager_path = layer_path / "utils" / "DatabaseManager.py"
    spec = importlib.util.spec_from_file_location("DatabaseManager", db_manager_path)
    db_manager_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(db_manager_module)
    print(f"DatabaseManager loaded successfully from: {db_manager_path}")
    
except Exception as e:
    print(f"Direct DatabaseManager import failed: {e}")
    import traceback
    traceback.print_exc()