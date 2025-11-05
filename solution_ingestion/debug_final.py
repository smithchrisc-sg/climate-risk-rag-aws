#!/usr/bin/env python3
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

print("Before setup:")
for i, path in enumerate(sys.path[:3]):
    print(f"  {i}: {path}")

from solution_utils.layer_imports import setup_layer_imports
setup_layer_imports()

print("\nAfter setup:")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i}: {path}")

print("\nTesting imports:")
try:
    from utils.DatabaseManager import DatabaseManager
    print("[OK] DatabaseManager imported")
except Exception as e:
    print(f"[ERROR] DatabaseManager failed: {e}")

try:
    from utils.DocumentIDManager import DocumentIDManager
    print("[OK] DocumentIDManager imported")
except Exception as e:
    print(f"[ERROR] DocumentIDManager failed: {e}")