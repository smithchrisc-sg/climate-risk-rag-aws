#!/usr/bin/env python3
"""
Test the new simplified structure
"""

print("Testing new simplified import structure...")

try:
    # Test database imports
    from database_core_layer.utils.DatabaseManager import DatabaseManager
    print("[OK] DatabaseManager imported")
    
    from database_core_layer.utils.DocumentIDManager import DocumentIDManager
    print("[OK] DocumentIDManager imported")
    
    # Test knowledge graph imports
    from knowledge_graph_layer.utils.KnowledgeGraphManager import KnowledgeGraphManager
    print("[OK] KnowledgeGraphManager imported")
    
    # Test solution model
    from models.solution import Solution
    print("[OK] Solution model imported")
    
    print("\n✓ SUCCESS: All imports working with new structure!")
    
except Exception as e:
    print(f"\n✗ FAILED: {e}")
    import traceback
    traceback.print_exc()