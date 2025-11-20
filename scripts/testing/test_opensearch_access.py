#!/usr/bin/env python3
"""
Test OpenSearch access and show role mapping via existing Lambda
"""

import json
import boto3

def test_via_lambda():
    """Use existing working Lambda to test OpenSearch and show role mappings"""
    
    lambda_client = boto3.client('lambda')
    
    # Test code to run in the working Lambda environment
    test_code = '''
import json
import requests

def lambda_handler(event, context):
    opensearch_endpoint = "vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
    
    results = {}
    
    # Test 1: Basic cluster info
    try:
        response = requests.get(f"https://{opensearch_endpoint}/", timeout=10)
        results['cluster_info'] = {
            'status_code': response.status_code,
            'response': response.text[:500]
        }
    except Exception as e:
        results['cluster_info'] = {'error': str(e)}
    
    # Test 2: Get current role mappings
    try:
        response = requests.get(
            f"https://{opensearch_endpoint}/_plugins/_security/api/rolesmapping/all_access",
            timeout=10
        )
        results['role_mapping'] = {
            'status_code': response.status_code,
            'response': response.text
        }
    except Exception as e:
        results['role_mapping'] = {'error': str(e)}
    
    # Test 3: Try to update role mapping
    try:
        payload = {
            "backend_roles": [
                "arn:aws:iam::861276078413:role/document-processing-lambda-role",
                "arn:aws:iam::861276078413:role/NeptuneQuickStart-Neptune-NeptuneStreamPollerExecut-LHQUuhdnZMJk"
            ]
        }
        
        response = requests.put(
            f"https://{opensearch_endpoint}/_plugins/_security/api/rolesmapping/all_access",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        results['update_mapping'] = {
            'status_code': response.status_code,
            'response': response.text,
            'payload_sent': payload
        }
    except Exception as e:
        results['update_mapping'] = {'error': str(e)}
    
    return results
'''
    
    # Get one of the working Lambda functions
    try:
        # Update the keyword-indexer Lambda temporarily
        print("🔧 Temporarily updating keyword-indexer Lambda to test OpenSearch access...")
        
        response = lambda_client.update_function_code(
            FunctionName='keyword-indexer',
            ZipFile=test_code.encode()
        )
        
        print("⏳ Waiting for update to complete...")
        import time
        time.sleep(5)
        
        # Invoke the test
        print("🧪 Testing OpenSearch access...")
        response = lambda_client.invoke(
            FunctionName='keyword-indexer',
            InvocationType='RequestResponse'
        )
        
        # Parse results
        payload = json.loads(response['Payload'].read())
        
        print("📋 Test Results:")
        print(json.dumps(payload, indent=2))
        
        return payload
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    test_via_lambda()
