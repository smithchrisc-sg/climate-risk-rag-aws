#!/usr/bin/env python3
"""
Layer Import Debug Test
Tests layer imports and PYTHONPATH configuration.
"""

import sys
import os
from pathlib import Path

print("Layer Import Debug Test")
print("=" * 30)

# Show current Python path
print("Current sys.path:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

# Check layer directories exist
layers_base = Path("./layers")
db_layer = layers_base / "database-core-layer" / "python"
kg_layer = layers_base / "knowledge-graph-layer" / "python"

print(f"\nLayer directories:")
print(f"  Base layers dir exists: {layers_base.exists()}")
print(f"  DB layer exists: {db_layer.exists()}")
print(f"  KG layer exists: {kg_layer.exists()}")

if db_layer.exists():
    utils_dir = db_layer / "utils"
    print(f"  DB utils dir exists: {utils_dir.exists()}")
    if utils_dir.exists():
        doc_manager = utils_dir / "DocumentIDManager.py"
        db_manager = utils_dir / "DatabaseManager.py"
        print(f"    DocumentIDManager.py exists: {doc_manager.exists()}")
        print(f"    DatabaseManager.py exists: {db_manager.exists()}")

# Test adding to path and importing
print(f"\nTesting imports:")

# Add layers to path
if db_layer.exists():
    sys.path.insert(0, str(db_layer))
    print(f"  Added to path: {db_layer}")

try:
    from utils.DocumentIDManager import DocumentIDManager
    print("  ✅ DocumentIDManager import successful")
    
    # Test initialization
    doc_manager = DocumentIDManager()
    print("  ✅ DocumentIDManager initialization successful")
    
except Exception as e:
    print(f"  ❌ DocumentIDManager import failed: {e}")

try:
    from utils.DatabaseManager import DatabaseManager
    print("  ✅ DatabaseManager import successful")
    
except Exception as e:
    print(f"  ❌ DatabaseManager import failed: {e}")

# Show environment variables
print(f"\nEnvironment variables:")
print(f"  PYTHONPATH: {os.getenv('PYTHONPATH', 'Not set')}")
print(f"  AWS_REGION: {os.getenv('AWS_REGION', 'Not set')}")