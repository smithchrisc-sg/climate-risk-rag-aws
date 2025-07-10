import json
import urllib3

def lambda_handler(event, context):
    """Simple Neptune connectivity test"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    
    results = {
        'neptune_endpoint': neptune_endpoint,
        'tests': {}
    }
    
    http = urllib3.PoolManager()
    
    # Test 1: Status endpoint
    try:
        status_url = f"https://{neptune_endpoint}:8182/status"
        response = http.request('GET', status_url, timeout=10)
        
        if response.status == 200:
            status_data = json.loads(response.data.decode('utf-8'))
            results['tests']['status'] = {
                'success': True,
                'status_code': response.status,
                'data': status_data
            }
        else:
            results['tests']['status'] = {
                'success': False,
                'status_code': response.status
            }
    except Exception as e:
        results['tests']['status'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Simple SPARQL query
    try:
        sparql_url = f"https://{neptune_endpoint}:8182/sparql"
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
        else:
            results['tests']['sparql'] = {
                'success': False,
                'status_code': response.status
            }
    except Exception as e:
        results['tests']['sparql'] = {
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
