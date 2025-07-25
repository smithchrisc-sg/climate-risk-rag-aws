#!/usr/bin/env python3
"""
Simple test to validate dependency injection syntax without full dependencies
"""
import ast
import sys
import os

def test_ontology_manager_constructor():
    """Test that OntologyManager constructor has correct signature"""
    print("Testing OntologyManager constructor signature...")
    
    file_path = os.path.join(os.path.dirname(__file__), 'python', 'utils', 'OntologyManager.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Parse the AST
    tree = ast.parse(content)
    
    # Find the OntologyManager class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'OntologyManager':
            # Find the __init__ method
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                    # Check the arguments
                    args = [arg.arg for arg in item.args.args]
                    expected_args = ['self', 'kr_ns', 'dcterms_ns', 'foaf_ns', 'skos_ns']
                    
                    if args == expected_args:
                        print("✅ OntologyManager constructor has correct dependency injection signature")
                        return True
                    else:
                        print(f"❌ Expected args: {expected_args}, got: {args}")
                        return False
    
    print("❌ Could not find OntologyManager.__init__ method")
    return False

def test_knowledge_graph_manager_call():
    """Test that KnowledgeGraphManager calls OntologyManager with correct arguments"""
    print("Testing KnowledgeGraphManager OntologyManager instantiation...")
    
    file_path = os.path.join(os.path.dirname(__file__), 'python', 'utils', 'KnowledgeGraphManager.py')
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Look for the OntologyManager instantiation
    if 'OntologyManager(' in content and 'self.kr_ns' in content:
        # Check that it's called with the right arguments
        if ('self.kr_ns, ' in content and 
            'self.dcterms_ns, ' in content and 
            'self.foaf_ns, ' in content and 
            'self.skos_ns' in content):
            print("✅ KnowledgeGraphManager calls OntologyManager with dependency injection")
            return True
        else:
            print("❌ OntologyManager not called with all required namespace arguments")
            return False
    else:
        print("❌ Could not find OntologyManager instantiation in KnowledgeGraphManager")
        return False

def test_no_circular_dependency():
    """Test that there's no circular dependency pattern"""
    print("Testing for absence of circular dependency...")
    
    ontology_file = os.path.join(os.path.dirname(__file__), 'python', 'utils', 'OntologyManager.py')
    
    with open(ontology_file, 'r') as f:
        content = f.read()
    
    # Check that OntologyManager doesn't store kg_manager reference
    if 'self.kg_manager = kg_manager' in content:
        print("❌ OntologyManager still stores kg_manager reference (circular dependency)")
        return False
    
    # Check that it doesn't store unused components
    if 'self.uri_manager = ' in content or 'self.query_builder = ' in content:
        print("❌ OntologyManager still stores unused components")
        return False
    
    print("✅ No circular dependency pattern found")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Dependency Injection Validation Test")
    print("=" * 60)
    
    test1 = test_ontology_manager_constructor()
    test2 = test_knowledge_graph_manager_call()
    test3 = test_no_circular_dependency()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3:
        print("🎉 ALL DEPENDENCY INJECTION TESTS PASSED!")
        print("Clean architecture implementation successful.")
        sys.exit(0)
    else:
        print("❌ DEPENDENCY INJECTION TESTS FAILED!")
        sys.exit(1)
