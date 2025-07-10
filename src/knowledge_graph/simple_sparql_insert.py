import json
import urllib3

def lambda_handler(event, context):
    """Simple SPARQL insert test for Neptune"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    sparql_endpoint = f"https://{neptune_endpoint}:8182/sparql"
    
    http = urllib3.PoolManager()
    results = {
        'tests': {}
    }
    
    # Test 1: Insert some sample data
    try:
        insert_query = """
INSERT DATA {
    <http://solve.global/knowledge-commons/Document_test> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://solve.global/knowledge-commons/schema#Document> .
    <http://solve.global/knowledge-commons/Document_test> <http://purl.org/dc/terms/title> "Test Document" .
    <http://solve.global/knowledge-commons/Document_test> <http://solve.global/knowledge-commons/schema#wordCount> "100"^^<http://www.w3.org/2001/XMLSchema#nonNegativeInteger> .
}
"""
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=insert_query,
            headers={'Content-Type': 'application/sparql-update'},
            timeout=60
        )
        
        if response.status == 200:
            results['tests']['insert'] = {
                'success': True,
                'status_code': response.status
            }
        else:
            results['tests']['insert'] = {
                'success': False,
                'status_code': response.status,
                'error': response.data.decode('utf-8')
            }
            
    except Exception as e:
        results['tests']['insert'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Query the inserted data
    try:
        query = """
SELECT ?doc ?title ?wordCount WHERE {
    ?doc <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://solve.global/knowledge-commons/schema#Document> .
    ?doc <http://purl.org/dc/terms/title> ?title .
    ?doc <http://solve.global/knowledge-commons/schema#wordCount> ?wordCount .
}
"""
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=60
        )
        
        if response.status == 200:
            query_result = json.loads(response.data.decode('utf-8'))
            bindings = query_result['results']['bindings']
            results['tests']['query'] = {
                'success': True,
                'status_code': response.status,
                'results_count': len(bindings),
                'results': bindings
            }
        else:
            results['tests']['query'] = {
                'success': False,
                'status_code': response.status,
                'error': response.data.decode('utf-8')
            }
            
    except Exception as e:
        results['tests']['query'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Count all triples
    try:
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=count_query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=60
        )
        
        if response.status == 200:
            count_result = json.loads(response.data.decode('utf-8'))
            count = count_result['results']['bindings'][0]['count']['value']
            results['tests']['count'] = {
                'success': True,
                'status_code': response.status,
                'triple_count': count
            }
        else:
            results['tests']['count'] = {
                'success': False,
                'status_code': response.status
            }
            
    except Exception as e:
        results['tests']['count'] = {
            'success': False,
            'error': str(e)
        }
    
    # Summary
    successful_tests = sum(1 for test in results['tests'].values() if test.get('success', False))
    total_tests = len(results['tests'])
    
    results['summary'] = {
        'successful_tests': successful_tests,
        'total_tests': total_tests,
        'overall_success': successful_tests > 0
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
