import json
import urllib3
import time

def lambda_handler(event, context):
    """Lambda function to perform Neptune bulk loading from within VPC"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    loader_endpoint = f"https://{neptune_endpoint}:8182/loader"
    sparql_endpoint = f"https://{neptune_endpoint}:8182/sparql"
    
    ttl_bucket = "solve-global-kr-neptune-ttl-861276078413-us-east-1"
    neptune_load_role = "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role"
    
    doc_id = event.get('doc_id', '0032f6cb_f0caef34')
    
    http = urllib3.PoolManager()
    results = {
        'doc_id': doc_id,
        'steps': {}
    }
    
    # Step 1: Load schema
    try:
        schema_load_request = {
            "source": f"s3://{ttl_bucket}/ontology/",
            "format": "turtle",
            "iamRoleArn": neptune_load_role,
            "region": "us-east-1",
            "failOnError": "FALSE",
            "parallelism": "MEDIUM",
            "updateSingleCardinalityProperties": "FALSE",
            "queueRequest": "TRUE"
        }
        
        response = http.request(
            'POST',
            loader_endpoint,
            body=json.dumps(schema_load_request),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status == 200:
            schema_result = json.loads(response.data.decode('utf-8'))
            schema_load_id = schema_result['payload']['loadId']
            results['steps']['schema_load'] = {
                'success': True,
                'load_id': schema_load_id
            }
        else:
            results['steps']['schema_load'] = {
                'success': False,
                'status_code': response.status,
                'error': response.data.decode('utf-8')
            }
            return {
                'statusCode': 500,
                'body': json.dumps(results)
            }
            
    except Exception as e:
        results['steps']['schema_load'] = {
            'success': False,
            'error': str(e)
        }
        return {
            'statusCode': 500,
            'body': json.dumps(results)
        }
    
    # Step 2: Wait for schema load to complete
    try:
        for i in range(30):  # Wait up to 5 minutes
            status_response = http.request(
                'GET',
                f"{loader_endpoint}/{schema_load_id}",
                timeout=30
            )
            
            if status_response.status == 200:
                status_data = json.loads(status_response.data.decode('utf-8'))
                overall_status = status_data['payload']['overallStatus']['status']
                
                if overall_status == "LOAD_COMPLETED":
                    results['steps']['schema_wait'] = {
                        'success': True,
                        'status': overall_status
                    }
                    break
                elif overall_status in ["LOAD_FAILED", "LOAD_CANCELLED"]:
                    results['steps']['schema_wait'] = {
                        'success': False,
                        'status': overall_status
                    }
                    return {
                        'statusCode': 500,
                        'body': json.dumps(results)
                    }
                
                time.sleep(10)
            else:
                results['steps']['schema_wait'] = {
                    'success': False,
                    'error': f'Status check failed: {status_response.status}'
                }
                return {
                    'statusCode': 500,
                    'body': json.dumps(results)
                }
        else:
            results['steps']['schema_wait'] = {
                'success': False,
                'error': 'Timeout waiting for schema load'
            }
            return {
                'statusCode': 500,
                'body': json.dumps(results)
            }
            
    except Exception as e:
        results['steps']['schema_wait'] = {
            'success': False,
            'error': str(e)
        }
        return {
            'statusCode': 500,
            'body': json.dumps(results)
        }
    
    # Step 3: Load document data
    try:
        doc_load_request = {
            "source": f"s3://{ttl_bucket}/documents/{doc_id}/",
            "format": "turtle",
            "iamRoleArn": neptune_load_role,
            "region": "us-east-1",
            "failOnError": "FALSE",
            "parallelism": "MEDIUM",
            "updateSingleCardinalityProperties": "FALSE",
            "queueRequest": "TRUE"
        }
        
        response = http.request(
            'POST',
            loader_endpoint,
            body=json.dumps(doc_load_request),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status == 200:
            doc_result = json.loads(response.data.decode('utf-8'))
            doc_load_id = doc_result['payload']['loadId']
            results['steps']['document_load'] = {
                'success': True,
                'load_id': doc_load_id
            }
        else:
            results['steps']['document_load'] = {
                'success': False,
                'status_code': response.status,
                'error': response.data.decode('utf-8')
            }
            return {
                'statusCode': 500,
                'body': json.dumps(results)
            }
            
    except Exception as e:
        results['steps']['document_load'] = {
            'success': False,
            'error': str(e)
        }
        return {
            'statusCode': 500,
            'body': json.dumps(results)
        }
    
    # Step 4: Wait for document load to complete
    try:
        for i in range(60):  # Wait up to 10 minutes
            status_response = http.request(
                'GET',
                f"{loader_endpoint}/{doc_load_id}",
                timeout=30
            )
            
            if status_response.status == 200:
                status_data = json.loads(status_response.data.decode('utf-8'))
                overall_status = status_data['payload']['overallStatus']['status']
                
                if overall_status == "LOAD_COMPLETED":
                    results['steps']['document_wait'] = {
                        'success': True,
                        'status': overall_status
                    }
                    break
                elif overall_status in ["LOAD_FAILED", "LOAD_CANCELLED"]:
                    results['steps']['document_wait'] = {
                        'success': False,
                        'status': overall_status
                    }
                    return {
                        'statusCode': 500,
                        'body': json.dumps(results)
                    }
                
                time.sleep(10)
            else:
                results['steps']['document_wait'] = {
                    'success': False,
                    'error': f'Status check failed: {status_response.status}'
                }
                return {
                    'statusCode': 500,
                    'body': json.dumps(results)
                }
        else:
            results['steps']['document_wait'] = {
                'success': False,
                'error': 'Timeout waiting for document load'
            }
            return {
                'statusCode': 500,
                'body': json.dumps(results)
            }
            
    except Exception as e:
        results['steps']['document_wait'] = {
            'success': False,
            'error': str(e)
        }
        return {
            'statusCode': 500,
            'body': json.dumps(results)
        }
    
    # Step 5: Test loaded data
    try:
        # Count total triples
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=count_query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=30
        )
        
        if response.status == 200:
            count_result = json.loads(response.data.decode('utf-8'))
            count = count_result['results']['bindings'][0]['count']['value']
            results['steps']['test_data'] = {
                'success': True,
                'triple_count': count
            }
        else:
            results['steps']['test_data'] = {
                'success': False,
                'status_code': response.status
            }
            
    except Exception as e:
        results['steps']['test_data'] = {
            'success': False,
            'error': str(e)
        }
    
    # Calculate overall success
    successful_steps = sum(1 for step in results['steps'].values() if step.get('success', False))
    total_steps = len(results['steps'])
    
    results['summary'] = {
        'successful_steps': successful_steps,
        'total_steps': total_steps,
        'overall_success': successful_steps == total_steps
    }
    
    return {
        'statusCode': 200 if results['summary']['overall_success'] else 500,
        'body': json.dumps(results, indent=2)
    }
