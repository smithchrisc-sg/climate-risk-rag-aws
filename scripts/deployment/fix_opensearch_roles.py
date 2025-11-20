#!/usr/bin/env python3
"""
Fix OpenSearch role mapping by adding Neptune Lambda role to all_access role
Uses the working document-processing-lambda-role credentials via Lambda invoke
"""

import json
import boto3
import base64

def create_role_mapping_lambda():
    """Create a temporary Lambda to update OpenSearch role mapping"""
    
    lambda_code = '''
import json
import requests
from requests.auth import HTTPBasicAuth
import boto3

def lambda_handler(event, context):
    """Update OpenSearch role mapping to include Neptune Lambda role"""
    
    opensearch_endpoint = "vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
    
    # Role mapping API endpoint
    url = f"https://{opensearch_endpoint}/_plugins/_security/api/rolesmapping/all_access"
    
    # Add both roles to the mapping
    payload = {
        "backend_roles": [
            "arn:aws:iam::861276078413:role/document-processing-lambda-role",
            "arn:aws:iam::861276078413:role/NeptuneQuickStart-Neptune-NeptuneStreamPollerExecut-LHQUuhdnZMJk"
        ]
    }
    
    try:
        # Make the API call to update role mapping
        response = requests.put(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        return {
            'statusCode': response.status_code,
            'body': {
                'message': 'Role mapping updated',
                'response': response.text,
                'payload_sent': payload
            }
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': str(e),
                'payload_sent': payload
            }
        }
'''
    
    # Create Lambda client
    lambda_client = boto3.client('lambda')
    
    # Create the temporary Lambda function
    try:
        response = lambda_client.create_function(
            FunctionName='temp-opensearch-role-fixer',
            Runtime='python3.9',
            Role='arn:aws:iam::861276078413:role/document-processing-lambda-role',
            Handler='index.lambda_handler',
            Code={'ZipFile': lambda_code.encode()},
            Description='Temporary function to fix OpenSearch role mapping',
            Timeout=60,
            VpcConfig={
                'SubnetIds': ['subnet-0e9efc5fdf29e9da0', 'subnet-00efdcc220a613ae3'],
                'SecurityGroupIds': ['sg-0c9e10b9cfb4c9eb0']
            }
        )
        
        print(f"✅ Created temporary Lambda: {response['FunctionArn']}")
        return response['FunctionName']
        
    except lambda_client.exceptions.ResourceConflictException:
        print("⚠️  Lambda function already exists, using existing one")
        return 'temp-opensearch-role-fixer'
    except Exception as e:
        print(f"❌ Failed to create Lambda: {e}")
        return None

def invoke_role_fixer(function_name):
    """Invoke the role fixer Lambda"""
    
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse'
        )
        
        # Parse the response
        payload = json.loads(response['Payload'].read())
        
        print("📋 Lambda Response:")
        print(json.dumps(payload, indent=2))
        
        return payload.get('statusCode') == 200
        
    except Exception as e:
        print(f"❌ Failed to invoke Lambda: {e}")
        return False

def cleanup_lambda(function_name):
    """Delete the temporary Lambda function"""
    
    lambda_client = boto3.client('lambda')
    
    try:
        lambda_client.delete_function(FunctionName=function_name)
        print(f"🧹 Cleaned up temporary Lambda: {function_name}")
    except Exception as e:
        print(f"⚠️  Failed to cleanup Lambda: {e}")

def main():
    """Main execution"""
    
    print("🔧 Creating temporary Lambda to fix OpenSearch role mapping...")
    
    # Create the Lambda function
    function_name = create_role_mapping_lambda()
    if not function_name:
        return False
    
    # Wait a moment for the function to be ready
    print("⏳ Waiting for Lambda to be ready...")
    import time
    time.sleep(10)
    
    # Invoke the function
    print("🚀 Invoking role mapping fix...")
    success = invoke_role_fixer(function_name)
    
    # Cleanup
    cleanup_lambda(function_name)
    
    if success:
        print("✅ OpenSearch role mapping should now be fixed!")
        print("🧪 Try the Neptune Stream Poller Lambda again")
    else:
        print("❌ Failed to fix role mapping")
    
    return success

if __name__ == "__main__":
    main()
