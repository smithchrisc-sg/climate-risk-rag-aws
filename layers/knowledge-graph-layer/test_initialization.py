#!/usr/bin/env python3
"""
Test script to validate KnowledgeGraphManager initialization after dependency injection fix
"""
import sys
import os

# Add the layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def test_kg_manager_initialization():
    """Test that KnowledgeGraphManager initializes without circular dependency issues"""
    print("Testing KnowledgeGraphManager initialization...")
    
    try:
        # Set required environment variables
        os.environ['NEPTUNE_ENDPOINT'] = 'test-endpoint.cluster-test.neptune.amazonaws.com'
        os.environ['NEPTUNE_PORT'] = '8182'
        
        # Import and initialize
        from utils.KnowledgeGraphManager import KnowledgeGraphManager
        
        print("✅ Import successful")
        
        # This should not fail with circular dependency
        kg_manager = KnowledgeGraphManager()
        
        print("✅ KnowledgeGraphManager initialization successful")
        
        # Test that all components are properly initialized
        assert hasattr(kg_manager, 'ontology_manager'), "OntologyManager not initialized"
        assert hasattr(kg_manager, 'query_builder'), "SPARQLQueryBuilder not initialized"
        assert hasattr(kg_manager, 'uri_manager'), "URIManager not initialized"
        assert hasattr(kg_manager, 'triple_manager'), "TripleManager not initialized"
        assert hasattr(kg_manager, 'bulk_load_manager'), "BulkLoadManager not initialized"
        
        print("✅ All managers properly initialized")
        
        # Test that OntologyManager has the required namespaces
        ontology_mgr = kg_manager.ontology_manager
        assert hasattr(ontology_mgr, 'kr_ns'), "kr_ns namespace not set"
        assert hasattr(ontology_mgr, 'dcterms_ns'), "dcterms_ns namespace not set"
        assert hasattr(ontology_mgr, 'foaf_ns'), "foaf_ns namespace not set"
        assert hasattr(ontology_mgr, 'skos_ns'), "skos_ns namespace not set"
        
        print("✅ OntologyManager namespaces properly injected")
        
        # Test that namespaces are the same objects (proper dependency injection)
        assert ontology_mgr.kr_ns is kg_manager.kr_ns, "kr_ns not properly injected"
        assert ontology_mgr.dcterms_ns is kg_manager.dcterms_ns, "dcterms_ns not properly injected"
        
        print("✅ Dependency injection working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ontology_manager_direct():
    """Test OntologyManager direct initialization with dependency injection"""
    print("\nTesting OntologyManager direct initialization...")
    
    try:
        from utils.OntologyManager import OntologyManager
        from rdflib import Namespace
        
        # Create test namespaces
        kr_ns = Namespace("https://solve.global/ontologies/kr/")
        dcterms_ns = Namespace("http://purl.org/dc/terms/")
        foaf_ns = Namespace("http://xmlns.com/foaf/0.1/")
        skos_ns = Namespace("http://www.w3.org/2004/02/skos/core#")
        
        # This should work with dependency injection
        ontology_mgr = OntologyManager(kr_ns, dcterms_ns, foaf_ns, skos_ns)
        
        print("✅ OntologyManager direct initialization successful")
        
        # Verify namespaces are set correctly
        assert ontology_mgr.kr_ns == kr_ns, "kr_ns not set correctly"
        assert ontology_mgr.dcterms_ns == dcterms_ns, "dcterms_ns not set correctly"
        
        print("✅ Namespaces properly set via dependency injection")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Knowledge Graph Layer Initialization Test")
    print("=" * 60)
    
    success1 = test_kg_manager_initialization()
    success2 = test_ontology_manager_direct()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED!")
        print("Dependency injection implementation successful.")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED!")
        print("Dependency injection implementation needs fixes.")
        sys.exit(1)
