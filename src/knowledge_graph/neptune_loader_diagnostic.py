import json
import urllib3
import time

def lambda_handler(event, context):
    """Diagnostic test for Neptune loader endpoint"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    
    http = urllib3.PoolManager()
    results = {
        'tests': {},
        'neptune_endpoint': neptune_endpoint
    }
    
    # Test 1: Basic connectivity to loader endpoint
    try:
        loader_status_url = f"https://{neptune_endpoint}:8182/loader"
        
        # Try a simple GET request to see if endpoint responds
        response = http.request('GET', loader_status_url, timeout=10)
        
        results['tests']['loader_endpoint_get'] = {
            'success': True,
            'status_code': response.status,
            'response_size': len(response.data),
            'response_preview': response.data.decode('utf-8')[:200]
        }
        
    except Exception as e:
        results['tests']['loader_endpoint_get'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Compare with working SPARQL endpoint
    try:
        sparql_url = f"https://{neptune_endpoint}:8182/sparql"
        
        # Simple query we know works
        query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        response = http.request(
            'POST',
            sparql_url,
            body=query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=10
        )
        
        if response.status == 200:
            result = json.loads(response.data.decode('utf-8'))
            count = result['results']['bindings'][0]['count']['value']
            results['tests']['sparql_endpoint'] = {
                'success': True,
                'status_code': response.status,
                'triple_count': count
            }
        else:
            results['tests']['sparql_endpoint'] = {
                'success': False,
                'status_code': response.status
            }
            
    except Exception as e:
        results['tests']['sparql_endpoint'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Try minimal bulk load request
    try:
        loader_url = f"https://{neptune_endpoint}:8182/loader"
        
        # Minimal test request
        minimal_request = {
            "source": "s3://solve-global-kr-neptune-ttl-861276078413-us-east-1/ontology/document_structure_schema.ttl",
            "format": "turtle",
            "iamRoleArn": "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role",
            "region": "us-east-1",
            "failOnError": "FALSE"
        }
        
        # Try with shorter timeout first
        response = http.request(
            'POST',
            loader_url,
            body=json.dumps(minimal_request),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status == 200:
            load_result = json.loads(response.data.decode('utf-8'))
            results['tests']['minimal_bulk_load'] = {
                'success': True,
                'status_code': response.status,
                'load_id': load_result.get('payload', {}).get('loadId'),
                'response': load_result
            }
        else:
            results['tests']['minimal_bulk_load'] = {
                'success': False,
                'status_code': response.status,
                'response': response.data.decode('utf-8')[:500]
            }
            
    except Exception as e:
        results['tests']['minimal_bulk_load'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 4: Check if it's a timeout vs connection issue
    try:
        loader_url = f"https://{neptune_endpoint}:8182/loader"
        
        # Try with very long timeout to see if it's just slow
        start_time = time.time()
        
        response = http.request(
            'POST',
            loader_url,
            body=json.dumps(minimal_request),
            headers={'Content-Type': 'application/json'},
            timeout=120  # 2 minutes
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status == 200:
            load_result = json.loads(response.data.decode('utf-8'))
            results['tests']['long_timeout_test'] = {
                'success': True,
                'status_code': response.status,
                'elapsed_time': elapsed_time,
                'load_id': load_result.get('payload', {}).get('loadId')
            }
        else:
            results['tests']['long_timeout_test'] = {
                'success': False,
                'status_code': response.status,
                'elapsed_time': elapsed_time,
                'response': response.data.decode('utf-8')[:500]
            }
            
    except Exception as e:
        results['tests']['long_timeout_test'] = {
            'success': False,
            'error': str(e),
            'elapsed_time': time.time() - start_time if 'start_time' in locals() else 0
        }
    
    # Summary
    successful_tests = sum(1 for test in results['tests'].values() if test.get('success', False))
    total_tests = len(results['tests'])
    
    results['summary'] = {
        'successful_tests': successful_tests,
        'total_tests': total_tests,
        'diagnosis': 'pending_analysis'
    }
    
    # Diagnosis logic
    if results['tests'].get('sparql_endpoint', {}).get('success', False):
        if results['tests'].get('loader_endpoint_get', {}).get('success', False):
            if results['tests'].get('minimal_bulk_load', {}).get('success', False):
                results['summary']['diagnosis'] = 'bulk_loading_working'
            else:
                results['summary']['diagnosis'] = 'bulk_load_request_issue'
        else:
            results['summary']['diagnosis'] = 'loader_endpoint_not_accessible'
    else:
        results['summary']['diagnosis'] = 'general_neptune_connectivity_issue'
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
