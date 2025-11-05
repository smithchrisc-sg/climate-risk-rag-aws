#!/usr/bin/env python3
import sys
from pathlib import Path

print("Testing direct import...")

# Add layer path directly
layer_path = Path(__file__).parent / "layers" / "database-core-layer" / "python"
print(f"Adding path: {layer_path}")
sys.path.insert(0, str(layer_path))

print("Current sys.path:")
for i, p in enumerate(sys.path[:5]):
    print(f"  {i}: {p}")

# Test psycopg2 first
try:
    import psycopg2
    print("[OK] psycopg2 imported successfully")
except Exception as e:
    print(f"[ERROR] psycopg2 import failed: {e}")

# Test utils module
try:
    import utils
    print(f"[OK] utils module found at: {utils.__file__}")
except Exception as e:
    print(f"[ERROR] utils module import failed: {e}")

# Test DatabaseManager
try:
    from utils.DatabaseManager import DatabaseManager
    print("[OK] DatabaseManager imported successfully")
except Exception as e:
    print(f"[ERROR] DatabaseManager import failed: {e}")
    import traceback
    traceback.print_exc()