#!/usr/bin/env python3
import boto3
import json
import zipfile
import os
import time

def create_jwt_authorizer():
    """Create minimal JWT authorizer Lambda"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create inline code
    code = '''
import json
import jwt
import os

def lambda_handler(event, context):
    try:
        token = event['authorizationToken']
        if not token.startswith('Bearer '):
            raise Exception('Unauthorized')
        
        token = token[7:]
        secret = 'dev-test-secret-key-change-for-production'
        
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        user_id = payload.get('sub')
        if not user_id:
            raise Exception('Unauthorized')
        
        return {
            'principalId': user_id,
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': event['methodArn']
                }]
            },
            'context': {
                'userId': user_id,
                'organization': payload.get('org', ''),
                'roles': json.dumps(payload.get('roles', []))
            }
        }
    except:
        raise Exception('Unauthorized')
'''
    
    # Create zip file
    with zipfile.ZipFile('auth.zip', 'w') as zf:
        zf.writestr('lambda_function.py', code)
    
    try:
        with open('auth.zip', 'rb') as f:
            response = lambda_client.create_function(
                FunctionName='gaip-jwt-authorizer',
                Runtime='python3.11',
                Role='arn:aws:iam::861276078413:role/gaip-lambda-execution-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': f.read()},
                Description='GAIP JWT Authorizer',
                Timeout=10,
                MemorySize=256
            )
        print(f"✅ Created JWT Authorizer: {response['FunctionArn']}")
        return response['FunctionArn']
    except lambda_client.exceptions.ResourceConflictException:
        print("✅ JWT Authorizer already exists")
        return f"arn:aws:lambda:us-east-1:861276078413:function:gaip-jwt-authorizer"
    finally:
        os.remove('auth.zip')

def create_search_lambda():
    """Create minimal search Lambda"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create inline code
    code = '''
import json
import time

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        query = body.get('query', '')
        
        # Mock response for testing
        response = {
            "results": [{
                "document_id": "test-doc-1",
                "title": "Climate Risk Assessment for North Macedonia",
                "summary": "This document analyzes climate risks in North Macedonia including temperature changes, precipitation patterns, and extreme weather events.",
                "score": 0.95,
                "document_type": "report",
                "categories": ["climate", "risk-assessment"],
                "regions": ["North Macedonia", "Europe"],
                "publication_date": "2024-01-15",
                "source_url": "https://example.com/doc1.pdf",
                "highlights": {
                    "content": ["North Macedonia faces significant climate risks including increased temperatures and changing precipitation patterns."]
                },
                "metadata": {
                    "search_types": ["keyword", "graph"],
                    "matched_concepts": ["North Macedonia", "climate risk"],
                    "file_size": 2048000,
                    "processing_status": "completed"
                }
            }],
            "pagination": {
                "cursor": None,
                "next_cursor": None,
                "total_results": 1,
                "returned_results": 1,
                "limit": 20
            },
            "execution_time": 0.123,
            "query": query
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            })
        }
'''
    
    # Create zip file
    with zipfile.ZipFile('search.zip', 'w') as zf:
        zf.writestr('lambda_function.py', code)
    
    try:
        with open('search.zip', 'rb') as f:
            response = lambda_client.create_function(
                FunctionName='gaip-search-lambda',
                Runtime='python3.11',
                Role='arn:aws:iam::861276078413:role/gaip-lambda-execution-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': f.read()},
                Description='GAIP Search Lambda',
                Timeout=30,
                MemorySize=512
            )
        print(f"✅ Created Search Lambda: {response['FunctionArn']}")
        return response['FunctionArn']
    except lambda_client.exceptions.ResourceConflictException:
        print("✅ Search Lambda already exists")
        return f"arn:aws:lambda:us-east-1:861276078413:function:gaip-search-lambda"
    finally:
        os.remove('search.zip')

def create_api_gateway(auth_arn, search_arn):
    """Create API Gateway"""
    
    apigw = boto3.client('apigateway', region_name='us-east-1')
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create REST API
    try:
        api_response = apigw.create_rest_api(
            name='gaip-api',
            description='GAIP Knowledge Repository API',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")
    except Exception as e:
        print(f"API Gateway might exist: {e}")
        # Get existing API
        apis = apigw.get_rest_apis()
        for api in apis['items']:
            if api['name'] == 'gaip-api':
                api_id = api['id']
                print(f"✅ Using existing API Gateway: {api_id}")
                break
        else:
            raise Exception("Could not create or find API Gateway")
    
    # Get root resource
    resources = apigw.get_resources(restApiId=api_id)
    root_id = None
    for resource in resources['items']:
        if resource['path'] == '/':
            root_id = resource['id']
            break
    
    # Create authorizer
    try:
        auth_response = apigw.create_authorizer(
            restApiId=api_id,
            name='jwt-authorizer',
            type='TOKEN',
            authorizerUri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{auth_arn}/invocations',
            authorizerCredentials='arn:aws:iam::861276078413:role/gaip-lambda-execution-role',
            tokenHeader='Authorization'
        )
        authorizer_id = auth_response['id']
        print(f"✅ Created Authorizer: {authorizer_id}")
    except Exception as e:
        print(f"Authorizer might exist: {e}")
        authorizers = apigw.get_authorizers(restApiId=api_id)
        for auth in authorizers['items']:
            if auth['name'] == 'jwt-authorizer':
                authorizer_id = auth['id']
                break
        else:
            authorizer_id = None
    
    # Create search resource
    try:
        search_resource = apigw.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='search'
        )
        search_resource_id = search_resource['id']
        print(f"✅ Created /search resource: {search_resource_id}")
    except Exception as e:
        print(f"Search resource might exist: {e}")
        resources = apigw.get_resources(restApiId=api_id)
        for resource in resources['items']:
            if resource.get('pathPart') == 'search':
                search_resource_id = resource['id']
                break
        else:
            raise Exception("Could not create search resource")
    
    # Create POST method
    try:
        method_response = apigw.put_method(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='POST',
            authorizationType='CUSTOM',
            authorizerId=authorizer_id if authorizer_id else None
        )
        print("✅ Created POST method")
    except Exception as e:
        print(f"POST method might exist: {e}")
    
    # Create integration
    try:
        integration_response = apigw.put_integration(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{search_arn}/invocations'
        )
        print("✅ Created Lambda integration")
    except Exception as e:
        print(f"Integration might exist: {e}")
    
    # Add Lambda permissions
    try:
        lambda_client.add_permission(
            FunctionName='gaip-jwt-authorizer',
            StatementId='api-gateway-invoke-auth',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:us-east-1:861276078413:{api_id}/*/*'
        )
    except Exception as e:
        print(f"Auth permission might exist: {e}")
    
    try:
        lambda_client.add_permission(
            FunctionName='gaip-search-lambda',
            StatementId='api-gateway-invoke-search',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:us-east-1:861276078413:{api_id}/*/*'
        )
    except Exception as e:
        print(f"Search permission might exist: {e}")
    
    # Deploy API
    try:
        deploy_response = apigw.create_deployment(
            restApiId=api_id,
            stageName='v1'
        )
        print("✅ Deployed API to v1 stage")
    except Exception as e:
        print(f"Deployment issue: {e}")
    
    api_url = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/v1"
    print(f"🌐 API URL: {api_url}")
    
    return api_url

if __name__ == '__main__':
    print("🚀 Deploying GAIP API...")
    
    # Create Lambda functions
    auth_arn = create_jwt_authorizer()
    search_arn = create_search_lambda()
    
    # Wait for functions to be ready
    time.sleep(5)
    
    # Create API Gateway
    api_url = create_api_gateway(auth_arn, search_arn)
    
    print(f"\n✅ GAIP API deployed successfully!")
    print(f"🌐 API Endpoint: {api_url}")
    print(f"\nNext steps:")
    print(f"1. Generate API keys: python3 generate_api_keys.py")
    print(f"2. Deploy test webapp: ./deploy_test_webapp.sh")
    print(f"3. Test with: curl -X POST {api_url}/search -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' -d '{{\"query\":\"climate risk North Macedonia\"}}'")
