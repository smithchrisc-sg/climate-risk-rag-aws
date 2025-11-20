#!/usr/bin/env python3
"""
Test script for Admin Ontology Manager Lambda
Demonstrates how to invoke the admin utility for ontology operations
"""

import json
import boto3
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminOntologyManagerTester:
    """Test client for Admin Ontology Manager Lambda"""
    
    def __init__(self, function_name: str = "solve-global-kr-admin-ontology-manager"):
        self.lambda_client = boto3.client('lambda')
        self.function_name = function_name
        
    def invoke_operation(self, operation: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Invoke an ontology management operation"""
        
        if parameters is None:
            parameters = {}
            
        payload = {
            'operation': operation,
            'parameters': parameters
        }
        
        logger.info(f"Invoking operation: {operation}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('StatusCode') == 200:
                logger.info(f"Operation {operation} completed successfully")
                return response_payload
            else:
                logger.error(f"Operation {operation} failed with status: {response.get('StatusCode')}")
                return response_payload
                
        except Exception as e:
            logger.error(f"Failed to invoke operation {operation}: {e}")
            raise

def test_ontology_operations():
    """Test various ontology management operations"""
    
    tester = AdminOntologyManagerTester()
    
    print("=== Testing Admin Ontology Manager ===\n")
    
    # Test 1: Get ontology statistics
    print("1. Getting ontology statistics...")
    try:
        result = tester.invoke_operation('get_ontology_stats')
        print(f"✓ Ontology stats: {json.dumps(result.get('body', {}), indent=2)}")
    except Exception as e:
        print(f"✗ Failed to get ontology stats: {e}")
    
    print()
    
    # Test 2: Load ontology from S3 (default)
    print("2. Loading default ontology from S3...")
    try:
        result = tester.invoke_operation('load_ontology_from_s3', {
            's3_key': 'climate-risk-ontology.ttl',
            'format': 'turtle',
            'force_reload': True
        })
        print(f"✓ Ontology loaded: {json.dumps(result.get('body', {}), indent=2)}")
    except Exception as e:
        print(f"✗ Failed to load ontology: {e}")
    
    print()
    
    # Test 3: Get concepts
    print("3. Getting ontology concepts...")
    try:
        result = tester.invoke_operation('get_concepts')
        body = json.loads(result.get('body', '{}'))
        if body.get('success'):
            concept_count = body.get('result', {}).get('concept_count', 0)
            print(f"✓ Found {concept_count} concepts")
            
            # Show first few concepts
            concepts = body.get('result', {}).get('concepts', [])
            if concepts:
                print("First few concepts:")
                for i, concept in enumerate(concepts[:3]):
                    print(f"  - {concept.get('uri', 'N/A')}: {concept.get('label', 'N/A')}")
        else:
            print(f"✗ Failed to get concepts: {body.get('error')}")
    except Exception as e:
        print(f"✗ Failed to get concepts: {e}")
    
    print()
    
    # Test 4: Search concepts by label
    print("4. Searching concepts by label...")
    try:
        result = tester.invoke_operation('find_concepts_by_label', {
            'label': 'climate',
            'fuzzy': True
        })
        body = json.loads(result.get('body', '{}'))
        if body.get('success'):
            concept_count = body.get('result', {}).get('concept_count', 0)
            print(f"✓ Found {concept_count} concepts matching 'climate'")
            
            # Show matching concepts
            concepts = body.get('result', {}).get('concepts', [])
            for concept in concepts[:3]:
                print(f"  - {concept.get('uri', 'N/A')}: {concept.get('label', 'N/A')}")
        else:
            print(f"✗ Failed to search concepts: {body.get('error')}")
    except Exception as e:
        print(f"✗ Failed to search concepts: {e}")
    
    print()
    
    # Test 5: Load sample ontology content
    print("5. Loading sample ontology content...")
    sample_ttl = """
    @prefix kr: <https://solve.global/ontology/climate-risk/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    
    kr:TestConcept a owl:Class ;
        rdfs:label "Test Concept" ;
        rdfs:comment "A test concept for demonstration" .
    """
    
    try:
        result = tester.invoke_operation('load_ontology_from_content', {
            'ttl_content': sample_ttl,
            'force_reload': True
        })
        print(f"✓ Sample ontology loaded: {json.dumps(result.get('body', {}), indent=2)}")
    except Exception as e:
        print(f"✗ Failed to load sample ontology: {e}")
    
    print()
    
    # Test 6: Clear cache
    print("6. Clearing ontology cache...")
    try:
        result = tester.invoke_operation('clear_cache')
        print(f"✓ Cache cleared: {json.dumps(result.get('body', {}), indent=2)}")
    except Exception as e:
        print(f"✗ Failed to clear cache: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_ontology_operations()
