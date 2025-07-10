#!/usr/bin/env python3
"""
Test Neptune Connection
Verify connectivity to Neptune cluster and basic SPARQL operations
"""

import requests
import json
import time
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeptuneConnectionTester:
    """Test Neptune connectivity and basic operations"""
    
    def __init__(self, neptune_endpoint: str):
        self.neptune_endpoint = neptune_endpoint
        self.sparql_endpoint = f"https://{neptune_endpoint}:8182/sparql"
        self.status_endpoint = f"https://{neptune_endpoint}:8182/status"
        
        # Headers for SPARQL requests
        self.headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
    
    def test_connection(self) -> bool:
        """Test basic connectivity to Neptune"""
        logger.info("Testing Neptune connection...")
        
        try:
            response = requests.get(self.status_endpoint, timeout=10)
            if response.status_code == 200:
                status_data = response.json()
                logger.info(f"✅ Neptune connection successful!")
                logger.info(f"   Status: {status_data.get('status', 'unknown')}")
                logger.info(f"   Version: {status_data.get('version', 'unknown')}")
                return True
            else:
                logger.error(f"❌ Neptune connection failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Neptune connection error: {e}")
            return False
    
    def test_sparql_query(self) -> bool:
        """Test basic SPARQL query functionality"""
        logger.info("Testing SPARQL query functionality...")
        
        # Simple query to count triples
        query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        try:
            response = requests.post(
                self.sparql_endpoint,
                data=query,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                count = result['results']['bindings'][0]['count']['value']
                logger.info(f"✅ SPARQL query successful!")
                logger.info(f"   Triple count: {count}")
                return True
            else:
                logger.error(f"❌ SPARQL query failed: HTTP {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ SPARQL query error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ SPARQL query processing error: {e}")
            return False
    
    def load_sample_data(self) -> bool:
        """Load sample RDF data to test write operations"""
        logger.info("Testing data loading with sample RDF...")
        
        # Sample RDF data in Turtle format
        sample_ttl = """
@prefix ex: <http://example.org/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:test_document rdf:type ex:Document ;
    rdfs:label "Test Document" ;
    ex:hasProperty "test_value" .
"""
        
        try:
            # Use Neptune's bulk loader endpoint for Turtle data
            load_endpoint = f"https://{self.neptune_endpoint}:8182/loader"
            
            # For now, let's try a simple INSERT query instead
            insert_query = """
INSERT DATA {
    <http://example.org/test_document> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Document> .
    <http://example.org/test_document> <http://www.w3.org/2000/01/rdf-schema#label> "Test Document" .
    <http://example.org/test_document> <http://example.org/hasProperty> "test_value" .
}
"""
            
            response = requests.post(
                self.sparql_endpoint,
                data=insert_query,
                headers={'Content-Type': 'application/sparql-update'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("✅ Sample data loaded successfully!")
                return True
            else:
                logger.error(f"❌ Data loading failed: HTTP {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Data loading error: {e}")
            return False
    
    def test_sample_query(self) -> bool:
        """Test querying the sample data we loaded"""
        logger.info("Testing query of loaded sample data...")
        
        query = """
SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
    FILTER(CONTAINS(str(?s), "test_document"))
}
"""
        
        try:
            response = requests.post(
                self.sparql_endpoint,
                data=query,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                bindings = result['results']['bindings']
                logger.info(f"✅ Sample data query successful!")
                logger.info(f"   Found {len(bindings)} triples")
                
                for binding in bindings:
                    s = binding['s']['value']
                    p = binding['p']['value']
                    o = binding['o']['value']
                    logger.info(f"   {s} -> {p} -> {o}")
                
                return True
            else:
                logger.error(f"❌ Sample query failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Sample query error: {e}")
            return False
    
    def cleanup_test_data(self) -> bool:
        """Clean up test data"""
        logger.info("Cleaning up test data...")
        
        delete_query = """
DELETE WHERE {
    <http://example.org/test_document> ?p ?o .
}
"""
        
        try:
            response = requests.post(
                self.sparql_endpoint,
                data=delete_query,
                headers={'Content-Type': 'application/sparql-update'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("✅ Test data cleaned up successfully!")
                return True
            else:
                logger.warning(f"⚠️ Cleanup may have failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Cleanup error: {e}")
            return False
    
    def run_full_test(self) -> bool:
        """Run complete Neptune connectivity test"""
        logger.info("🚀 Starting Neptune connectivity test suite")
        logger.info("=" * 60)
        
        tests_passed = 0
        total_tests = 5
        
        # Test 1: Basic connection
        if self.test_connection():
            tests_passed += 1
        
        # Test 2: SPARQL query
        if self.test_sparql_query():
            tests_passed += 1
        
        # Test 3: Data loading
        if self.load_sample_data():
            tests_passed += 1
        
        # Test 4: Query loaded data
        if self.test_sample_query():
            tests_passed += 1
        
        # Test 5: Cleanup
        if self.cleanup_test_data():
            tests_passed += 1
        
        logger.info("=" * 60)
        logger.info(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            logger.info("🎉 All Neptune connectivity tests PASSED!")
            logger.info("   Neptune is ready for knowledge graph operations")
            return True
        else:
            logger.error("❌ Some Neptune connectivity tests FAILED!")
            logger.error("   Check Neptune configuration and network connectivity")
            return False

def main():
    """Main function to test Neptune connectivity"""
    
    # Neptune cluster endpoint
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    
    print("🔗 NEPTUNE CONNECTIVITY TEST")
    print("=" * 60)
    print(f"Neptune Endpoint: {neptune_endpoint}")
    print(f"SPARQL Endpoint: https://{neptune_endpoint}:8182/sparql")
    print("=" * 60)
    
    tester = NeptuneConnectionTester(neptune_endpoint)
    
    try:
        success = tester.run_full_test()
        
        if success:
            print("\n🎯 NEXT STEPS:")
            print("   1. Neptune is ready for knowledge graph data loading")
            print("   2. You can proceed with TTL data import")
            print("   3. Implement SPARQL query interfaces")
            
        else:
            print("\n🔧 TROUBLESHOOTING:")
            print("   1. Check VPC connectivity (are you on VPN?)")
            print("   2. Verify security group rules allow access")
            print("   3. Confirm Neptune cluster is in 'available' status")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
