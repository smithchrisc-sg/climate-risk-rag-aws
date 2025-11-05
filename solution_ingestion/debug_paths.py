#!/usr/bin/env python3
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from utils.layer_imports import setup_layer_imports
setup_layer_imports()

print("Python paths:")
for i, path in enumerate(sys.path):
    print(f"  {i}: {path}")

print("\nChecking database layer path:")
db_path = Path(__file__).parent / "layers" / "database-core-layer" / "python"
print(f"Database layer path: {db_path}")
print(f"Path exists: {db_path.exists()}")

utils_path = db_path / "utils"
print(f"Utils path: {utils_path}")
print(f"Utils exists: {utils_path.exists()}")

db_manager_path = utils_path / "DatabaseManager.py"
print(f"DatabaseManager.py exists: {db_manager_path.exists()}")

if db_manager_path.exists():
    print(f"DatabaseManager.py size: {db_manager_path.stat().st_size} bytes")