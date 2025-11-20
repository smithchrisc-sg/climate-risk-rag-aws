#!/usr/bin/env python3
"""
Test Neptune-FTS Integration
This script can be run from within a Lambda function to test Neptune FTS functionality
"""

import json
import boto3
import requests
from requests.auth import HTTPBasicAuth
import os

def test_neptune_fts_query():
    """Test Neptune FTS query functionality"""
    
    # Neptune configuration
    neptune_endpoint = "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    sparql_endpoint = f"https://{neptune_endpoint}:8182/sparql"
    
    # Test FTS query
    test_query = """
    PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
    
    SELECT ?s ?p ?o ?score
    WHERE {
      ?s ?p ?o .
      FILTER(neptune-fts:query(neptune-fts:field('object'), 'climate'))
      BIND(neptune-fts:score() AS ?score)
    }
    ORDER BY DESC(?score)
    LIMIT 5
    """
    
    try:
        # Use AWS4Auth for Neptune authentication
        from requests_aws4auth import AWS4Auth
        
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Create AWS4Auth object
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            'us-east-1',
            'neptune-db',
            session_token=credentials.token
        )
        
        # Execute SPARQL query
        response = requests.post(
            sparql_endpoint,
            data={'query': test_query},
            headers={
                'Accept': 'application/sparql-results+json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            bindings = results.get('results', {}).get('bindings', [])
            
            print(f"✅ Neptune FTS query successful!")
            print(f"📊 Found {len(bindings)} results")
            
            for i, binding in enumerate(bindings):
                subject = binding.get('s', {}).get('value', 'N/A')
                predicate = binding.get('p', {}).get('value', 'N/A')
                obj = binding.get('o', {}).get('value', 'N/A')
                score = binding.get('score', {}).get('value', 'N/A')
                
                print(f"  {i+1}. Score: {score}")
                print(f"     Subject: {subject}")
                print(f"     Object: {obj[:100]}...")
                print()
            
            return True
        else:
            print(f"❌ Neptune FTS query failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Neptune FTS query error: {e}")
        return False

def test_opensearch_index():
    """Test OpenSearch index accessibility"""
    
    # OpenSearch configuration
    opensearch_endpoint = "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
    username = "admin"
    password = "veqpat-kegba2-zapbyZ"
    
    try:
        # Test index existence
        response = requests.get(
            f"{opensearch_endpoint}/neptune-fts/_stats",
            auth=HTTPBasicAuth(username, password),
            verify=True,
            timeout=10
        )
        
        if response.status_code == 200:
            stats = response.json()
            indices = stats.get('indices', {})
            neptune_fts = indices.get('neptune-fts', {})
            
            print(f"✅ OpenSearch neptune-fts index accessible!")
            print(f"📊 Index stats:")
            print(f"   Documents: {neptune_fts.get('total', {}).get('docs', {}).get('count', 'N/A')}")
            print(f"   Size: {neptune_fts.get('total', {}).get('store', {}).get('size_in_bytes', 'N/A')} bytes")
            
            return True
        else:
            print(f"❌ OpenSearch index check failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ OpenSearch index check error: {e}")
        return False

def test_ontology_manager_fts():
    """Test OntologyManager FTS methods"""
    
    try:
        # This would be run from within a Lambda with the layer
        import sys
        sys.path.append('/opt/python')  # Lambda layer path
        
        from utils.KnowledgeGraphManager import KnowledgeGraphManager
        from utils.OntologyManager import OntologyManager
        from rdflib import Namespace
        
        # Initialize managers
        kg_manager = KnowledgeGraphManager()
        ontology_manager = kg_manager.ontology_manager
        
        # Test list_ontologies
        ontologies = ontology_manager.list_ontologies()
        print(f"✅ OntologyManager.list_ontologies() returned {len(ontologies)} ontologies")
        
        # Test search_ontology_specific
        if ontologies:
            first_ontology = ontologies[0]['id']
            search_results = ontology_manager.search_ontology_specific(
                ontology_id=first_ontology,
                search_term='climate',
                limit=3
            )
            print(f"✅ OntologyManager.search_ontology_specific() returned {len(search_results)} results")
            
            for result in search_results:
                print(f"   - {result.get('label', 'N/A')} (score: {result.get('score', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ OntologyManager FTS test error: {e}")
        return False

def lambda_handler(event, context):
    """Lambda handler for testing Neptune FTS integration"""
    
    print("🧪 Testing Neptune-FTS Integration")
    print("=" * 50)
    
    results = {
        'opensearch_index': False,
        'neptune_fts_query': False,
        'ontology_manager': False
    }
    
    # Test OpenSearch index
    print("\n1. Testing OpenSearch Index...")
    results['opensearch_index'] = test_opensearch_index()
    
    # Test Neptune FTS query
    print("\n2. Testing Neptune FTS Query...")
    results['neptune_fts_query'] = test_neptune_fts_query()
    
    # Test OntologyManager FTS methods
    print("\n3. Testing OntologyManager FTS Methods...")
    results['ontology_manager'] = test_ontology_manager_fts()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    all_passed = all(results.values())
    overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    print(f"\n🎯 Overall Status: {overall_status}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Neptune FTS integration test completed',
            'results': results,
            'all_passed': all_passed
        })
    }

if __name__ == "__main__":
    # For local testing (won't work due to VPC restrictions)
    print("This script is designed to run from within a Lambda function in the VPC")
    print("Use the admin_ontology_manager Lambda to execute this test")
