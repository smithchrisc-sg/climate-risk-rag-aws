#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Change to the script directory
os.chdir(Path(__file__).parent)

# Add current directory to path
sys.path.append(str(Path.cwd()))

print("Working directory:", Path.cwd())

# Import and setup layers
from solution_utils.layer_imports import setup_layer_imports
setup_layer_imports()

print("Testing imports...")
try:
    import utils.DatabaseManager
    print("[OK] DatabaseManager imported")
    
    import utils.DocumentIDManager  
    print("[OK] DocumentIDManager imported")
    
    print("SUCCESS: All imports working!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()