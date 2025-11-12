import sys
import os
import logging

# Add layer paths
sys.path.insert(0, '/opt/python')
sys.path.insert(0, '/opt')

print("Python path:")
for path in sys.path:
    print(f"  {path}")

print("\nChecking /opt directory:")
try:
    if os.path.exists('/opt'):
        for item in os.listdir('/opt'):
            print(f"  {item}")
    else:
        print("  /opt does not exist")
except Exception as e:
    print(f"  Error listing /opt: {e}")

print("\nChecking /opt/python directory:")
try:
    if os.path.exists('/opt/python'):
        for item in os.listdir('/opt/python'):
            print(f"  {item}")
    else:
        print("  /opt/python does not exist")
except Exception as e:
    print(f"  Error listing /opt/python: {e}")

print("\nTrying imports:")
try:
    import knowledge_graph_layer
    print("  SUCCESS: import knowledge_graph_layer")
    print(f"  Module path: {knowledge_graph_layer.__file__}")
    print(f"  Module contents: {dir(knowledge_graph_layer)}")
except ImportError as e:
    print(f"  FAILED: import knowledge_graph_layer - {e}")

try:
    from knowledge_graph_layer import KnowledgeGraphManager
    print("  SUCCESS: from knowledge_graph_layer import KnowledgeGraphManager")
except ImportError as e:
    print(f"  FAILED: from knowledge_graph_layer import KnowledgeGraphManager - {e}")
