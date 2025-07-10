#!/usr/bin/env python3
"""
Neptune Test Lambda Function
Test Neptune connectivity from within the VPC using a Lambda function
"""

import json
import urllib3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda function to test Neptune connectivity from within VPC"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    status_url = f"https://{neptune_endpoint}:8182/status"
    sparql_url = f"https://{neptune_endpoint}:8182/sparql"
    
    http = urllib3.PoolManager()
    
    results = {
        'neptune_endpoint': neptune_endpoint,
        'tests': {}
    }
    
    # Test 1: Status endpoint
    try:
        logger.info(f"Testing Neptune status endpoint: {status_url}")
        response = http.request('GET', status_url, timeout=10)
        
        if response.status == 200:
            status_data = json.loads(response.data.decode('utf-8'))
            results['tests']['status'] = {
                'success': True,
                'status_code': response.status,
                'data': status_data
            }
            logger.info(f"✅ Status test passed: {status_data}")
        else:
            results['tests']['status'] = {
                'success': False,
                'status_code': response.status,
                'error': f"HTTP {response.status}"
            }
            logger.error(f"❌ Status test failed: HTTP {response.status}")
            
    except Exception as e:
        results['tests']['status'] = {
            'success': False,
            'error': str(e)
        }
        logger.error(f"❌ Status test error: {e}")
    
    # Test 2: SPARQL query
    try:
        logger.info(f"Testing SPARQL endpoint: {sparql_url}")
        
        # Simple count query
        query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        response = http.request(
            'POST',
            sparql_url,
            body=query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=30
        )
        
        if response.status == 200:
            query_result = json.loads(response.data.decode('utf-8'))
            count = query_result['results']['bindings'][0]['count']['value']
            results['tests']['sparql'] = {
                'success': True,
                'status_code': response.status,
                'triple_count': count
            }
            logger.info(f"✅ SPARQL test passed: {count} triples")
        else:
            results['tests']['sparql'] = {
                'success': False,
                'status_code': response.status,
                'error': f"HTTP {response.status}"
            }
            logger.error(f"❌ SPARQL test failed: HTTP {response.status}")
            
    except Exception as e:
        results['tests']['sparql'] = {
            'success': False,
            'error': str(e)
        }
        logger.error(f"❌ SPARQL test error: {e}")
    
    # Test 3: Insert test data
    try:
        logger.info("Testing data insertion...")
        
        insert_query = """
INSERT DATA {
    <http://test.example/doc1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://test.example/Document> .
    <http://test.example/doc1> <http://www.w3.org/2000/01/rdf-schema#label> "Test Document from Lambda" .
}
"""
        
        response = http.request(
            'POST',
            sparql_url,
            body=insert_query,
            headers={'Content-Type': 'application/sparql-update'},
            timeout=30
        )
        
        if response.status == 200:
            results['tests']['insert'] = {
                'success': True,
                'status_code': response.status
            }
            logger.info("✅ Insert test passed")
        else:
            results['tests']['insert'] = {
                'success': False,
                'status_code': response.status,
                'error': f"HTTP {response.status}"
            }
            logger.error(f"❌ Insert test failed: HTTP {response.status}")
            
    except Exception as e:
        results['tests']['insert'] = {
            'success': False,
            'error': str(e)
        }
        logger.error(f"❌ Insert test error: {e}")
    
    # Test 4: Query inserted data
    try:
        logger.info("Testing query of inserted data...")
        
        query = """
SELECT ?s ?p ?o WHERE {
    ?s ?p ?o .
    FILTER(CONTAINS(str(?s), "test.example"))
}
"""
        
        response = http.request(
            'POST',
            sparql_url,
            body=query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=30
        )
        
        if response.status == 200:
            query_result = json.loads(response.data.decode('utf-8'))
            bindings = query_result['results']['bindings']
            results['tests']['query_inserted'] = {
                'success': True,
                'status_code': response.status,
                'results_count': len(bindings),
                'results': bindings
            }
            logger.info(f"✅ Query test passed: {len(bindings)} results")
        else:
            results['tests']['query_inserted'] = {
                'success': False,
                'status_code': response.status,
                'error': f"HTTP {response.status}"
            }
            logger.error(f"❌ Query test failed: HTTP {response.status}")
            
    except Exception as e:
        results['tests']['query_inserted'] = {
            'success': False,
            'error': str(e)
        }
        logger.error(f"❌ Query test error: {e}")
    
    # Calculate success rate
    successful_tests = sum(1 for test in results['tests'].values() if test.get('success', False))
    total_tests = len(results['tests'])
    
    results['summary'] = {
        'successful_tests': successful_tests,
        'total_tests': total_tests,
        'success_rate': f"{successful_tests}/{total_tests}",
        'overall_success': successful_tests == total_tests
    }
    
    logger.info(f"🏁 Test Results: {successful_tests}/{total_tests} tests passed")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }

# For local testing
if __name__ == "__main__":
    # Simulate Lambda event and context
    class MockContext:
        def __init__(self):
            self.function_name = "neptune-test"
            self.memory_limit_in_mb = 128
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:neptune-test"
    
    result = lambda_handler({}, MockContext())
    print(json.dumps(result, indent=2))
