#!/usr/bin/env python3
"""
Layer Import Diagnostic Test
Diagnoses layer import issues on EC2 instance.
"""

import sys
import os
from pathlib import Path

def diagnose_layer_structure():
    """Diagnose layer directory structure and files."""
    
    print("Layer Structure Diagnostic")
    print("=" * 30)
    
    base_path = Path(__file__).parent
    layers_path = base_path / "layers"
    
    print(f"Base path: {base_path}")
    print(f"Layers path: {layers_path}")
    print(f"Layers exists: {layers_path.exists()}")
    
    if layers_path.exists():
        print("\nLayers directory contents:")
        for item in layers_path.iterdir():
            print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
    
    # Check database layer
    db_layer_path = layers_path / "database-core-layer" / "python"
    print(f"\nDatabase layer path: {db_layer_path}")
    print(f"Database layer exists: {db_layer_path.exists()}")
    
    if db_layer_path.exists():
        print("Database layer contents:")
        for item in db_layer_path.rglob("*"):
            if item.is_file():
                print(f"  {item.relative_to(db_layer_path)}")
    
    # Check knowledge graph layer
    kg_layer_path = layers_path / "knowledge-graph-layer" / "python"
    print(f"\nKnowledge graph layer path: {kg_layer_path}")
    print(f"Knowledge graph layer exists: {kg_layer_path.exists()}")
    
    if kg_layer_path.exists():
        print("Knowledge graph layer contents:")
        for item in kg_layer_path.rglob("*"):
            if item.is_file():
                print(f"  {item.relative_to(kg_layer_path)}")

def test_sys_path_setup():
    """Test sys.path configuration for layer imports."""
    
    print("\nSys Path Configuration")
    print("=" * 25)
    
    base_path = Path(__file__).parent
    
    # Database layer path
    db_layer_path = base_path / "layers" / "database-core-layer" / "python"
    print(f"Database layer path: {db_layer_path}")
    print(f"Absolute path: {db_layer_path.absolute()}")
    
    if db_layer_path.exists():
        sys.path.insert(0, str(db_layer_path.absolute()))
        print(f"Added to sys.path: {db_layer_path.absolute()}")
    
    # Knowledge graph layer path
    kg_layer_path = base_path / "layers" / "knowledge-graph-layer" / "python"
    print(f"Knowledge graph layer path: {kg_layer_path}")
    print(f"Absolute path: {kg_layer_path.absolute()}")
    
    if kg_layer_path.exists():
        sys.path.insert(0, str(kg_layer_path.absolute()))
        print(f"Added to sys.path: {kg_layer_path.absolute()}")
    
    print(f"\nCurrent sys.path entries (first 10):")
    for i, path in enumerate(sys.path[:10]):
        print(f"  {i}: {path}")

def test_individual_imports():
    """Test individual module imports with detailed error reporting."""
    
    print("\nIndividual Import Tests")
    print("=" * 25)
    
    # Test DocumentIDManager
    print("Testing DocumentIDManager import...")
    try:
        from utils.DocumentIDManager import DocumentIDManager
        print("✅ DocumentIDManager imported successfully")
        
        # Test instantiation
        try:
            manager = DocumentIDManager()
            print("✅ DocumentIDManager instantiated successfully")
        except Exception as e:
            print(f"❌ DocumentIDManager instantiation failed: {e}")
            
    except ImportError as e:
        print(f"❌ DocumentIDManager import failed: {e}")
        
        # Check if utils module exists
        try:
            import utils
            print(f"✅ utils module found at: {utils.__file__}")
            print(f"utils module contents: {dir(utils)}")
        except ImportError:
            print("❌ utils module not found")
    
    # Test DatabaseManager
    print("\nTesting DatabaseManager import...")
    try:
        from utils.DatabaseManager import DatabaseManager
        print("✅ DatabaseManager imported successfully")
        
        # Test instantiation
        try:
            manager = DatabaseManager()
            print("✅ DatabaseManager instantiated successfully")
        except Exception as e:
            print(f"❌ DatabaseManager instantiation failed: {e}")
            
    except ImportError as e:
        print(f"❌ DatabaseManager import failed: {e}")
    
    # Test KnowledgeGraphManager
    print("\nTesting KnowledgeGraphManager import...")
    try:
        from utils.KnowledgeGraphManager import KnowledgeGraphManager
        print("✅ KnowledgeGraphManager imported successfully")
        
        # Test instantiation
        try:
            manager = KnowledgeGraphManager()
            print("✅ KnowledgeGraphManager instantiated successfully")
        except Exception as e:
            print(f"❌ KnowledgeGraphManager instantiation failed: {e}")
            
    except ImportError as e:
        print(f"❌ KnowledgeGraphManager import failed: {e}")

def test_alternative_import_paths():
    """Test alternative import paths and configurations."""
    
    print("\nAlternative Import Paths")
    print("=" * 28)
    
    base_path = Path(__file__).parent
    
    # Try different path configurations
    alternative_paths = [
        base_path / "layers" / "database-core-layer",
        base_path / "layers" / "database-core-layer" / "python" / "utils",
        base_path / ".." / "lambda" / "shared_layer" / "python",
        base_path / ".." / "layers" / "database-core-layer" / "python",
    ]
    
    for alt_path in alternative_paths:
        print(f"\nTrying path: {alt_path}")
        print(f"Exists: {alt_path.exists()}")
        
        if alt_path.exists():
            print("Contents:")
            for item in alt_path.iterdir():
                print(f"  {item.name}")

def main():
    """Run layer import diagnostics."""
    
    print("LAYER IMPORT DIAGNOSTICS")
    print("=" * 50)
    
    diagnose_layer_structure()
    test_sys_path_setup()
    test_individual_imports()
    test_alternative_import_paths()
    
    print("\n" + "=" * 50)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    main()