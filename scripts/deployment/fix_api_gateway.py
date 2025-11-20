#!/usr/bin/env python3
import boto3

def fix_api_gateway():
    """Fix API Gateway configuration"""
    
    apigw = boto3.client('apigateway', region_name='us-east-1')
    api_id = '43l6kohmrf'  # From previous deployment
    
    # Get resources
    resources = apigw.get_resources(restApiId=api_id)
    search_resource_id = None
    
    for resource in resources['items']:
        if resource.get('pathPart') == 'search':
            search_resource_id = resource['id']
            break
    
    if not search_resource_id:
        print("❌ Search resource not found")
        return
    
    # Create POST method without authorizer for now
    try:
        apigw.put_method(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='POST',
            authorizationType='NONE'
        )
        print("✅ Created POST method")
    except Exception as e:
        print(f"Method exists: {e}")
    
    # Create integration
    try:
        apigw.put_integration(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri='arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:861276078413:function:gaip-search-lambda/invocations'
        )
        print("✅ Created integration")
    except Exception as e:
        print(f"Integration exists: {e}")
    
    # Add CORS
    try:
        apigw.put_method(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        
        apigw.put_integration(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={'application/json': '{"statusCode": 200}'}
        )
        
        apigw.put_method_response(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )
        
        apigw.put_integration_response(
            restApiId=api_id,
            resourceId=search_resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
        )
        print("✅ Added CORS support")
    except Exception as e:
        print(f"CORS might exist: {e}")
    
    # Deploy
    try:
        apigw.create_deployment(
            restApiId=api_id,
            stageName='v1'
        )
        print("✅ Deployed API")
    except Exception as e:
        print(f"Deployment: {e}")
    
    print(f"🌐 API URL: https://{api_id}.execute-api.us-east-1.amazonaws.com/v1")

if __name__ == '__main__':
    fix_api_gateway()
