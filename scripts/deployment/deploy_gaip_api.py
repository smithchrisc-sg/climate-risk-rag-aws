#!/usr/bin/env python3
import boto3
import json
import zipfile
import os
from pathlib import Path

def create_lambda_packages():
    """Create deployment packages for Lambda functions"""
    
    # Create JWT authorizer package
    auth_dir = Path("../lambda/jwt-authorizer")
    auth_zip = "jwt-authorizer.zip"
    
    with zipfile.ZipFile(auth_zip, 'w') as zf:
        zf.write(auth_dir / "handler.py", "handler.py")
    
    print(f"✅ Created {auth_zip}")
    
    # Create search Lambda package (minimal for now)
    search_dir = Path("../lambda/search")
    search_zip = "search-lambda.zip"
    
    with zipfile.ZipFile(search_zip, 'w') as zf:
        # Add main handler
        zf.write(search_dir / "handler.py", "handler.py")
        
        # Add minimal search coordinator
        zf.writestr("search/__init__.py", "")
        zf.writestr("search/coordinator.py", '''
import json
import time
from typing import Dict, Any

class SearchCoordinator:
    def __init__(self):
        pass
    
    async def search(self, query: str, filters: Dict[str, Any], 
                    parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal search implementation for testing"""
        
        # Mock results for testing
        results = [{
            'document_id': 'test-doc-1',
            'title': 'Climate Risk Assessment for North Macedonia',
            'summary': 'This document analyzes climate risks in North Macedonia...',
            'final_score': 0.95,
            'document_type': 'report',
            'categories': ['climate', 'risk-assessment'],
            'regions': ['North Macedonia', 'Europe'],
            'publication_date': '2024-01-15',
            'source_url': 'https://example.com/doc1.pdf',
            'highlights': {'content': ['North Macedonia faces significant climate risks...']},
            'search_types': ['keyword', 'graph'],
            'matched_concepts': ['North Macedonia', 'climate risk']
        }]
        
        return {
            'results': results,
            'pagination': {
                'cursor': None,
                'next_cursor': None,
                'total_results': 1,
                'returned_results': 1
            }
        }
''')
        
        # Add models
        zf.writestr("models/__init__.py", "")
        zf.writestr("models/request.py", open(search_dir / "models/request.py").read())
        
        # Add utils
        zf.writestr("utils/__init__.py", "")
        zf.writestr("utils/validation.py", open(search_dir / "utils/validation.py").read())
        zf.writestr("utils/formatting.py", open(search_dir / "utils/formatting.py").read())
    
    print(f"✅ Created {search_zip}")
    return auth_zip, search_zip

def deploy_lambda_functions():
    """Deploy Lambda functions using boto3"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create packages
    auth_zip, search_zip = create_lambda_packages()
    
    # Deploy JWT Authorizer
    try:
        with open(auth_zip, 'rb') as f:
            auth_response = lambda_client.create_function(
                FunctionName='gaip-jwt-authorizer',
                Runtime='python3.11',
                Role='arn:aws:iam::861276078413:role/lambda-execution-role',  # Will need to create this
                Handler='handler.lambda_handler',
                Code={'ZipFile': f.read()},
                Description='JWT Authorizer for GAIP API',
                Timeout=10,
                MemorySize=256,
                Environment={
                    'Variables': {
                        'JWT_SECRET': 'dev-test-secret-key-change-for-production'
                    }
                }
            )
        print(f"✅ Created JWT Authorizer: {auth_response['FunctionArn']}")
    except lambda_client.exceptions.ResourceConflictException:
        # Update existing function
        with open(auth_zip, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName='gaip-jwt-authorizer',
                ZipFile=f.read()
            )
        print("✅ Updated JWT Authorizer")
    
    # Deploy Search Lambda
    try:
        with open(search_zip, 'rb') as f:
            search_response = lambda_client.create_function(
                FunctionName='gaip-search-lambda',
                Runtime='python3.11',
                Role='arn:aws:iam::861276078413:role/lambda-execution-role',
                Handler='handler.lambda_handler',
                Code={'ZipFile': f.read()},
                Description='GAIP Search API Lambda',
                Timeout=30,
                MemorySize=1024,
                Layers=[
                    'arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer:61',
                    'arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16',
                    'arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2'
                ],
                Environment={
                    'Variables': {
                        'OPENSEARCH_ENDPOINT': 'https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com',
                        'NEPTUNE_ENDPOINT': 'solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com',
                        'POSTGRES_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
                        'POSTGRES_DATABASE': 'climate_risk_rag'
                    }
                }
            )
        print(f"✅ Created Search Lambda: {search_response['FunctionArn']}")
    except lambda_client.exceptions.ResourceConflictException:
        with open(search_zip, 'rb') as f:
            lambda_client.update_function_code(
                FunctionName='gaip-search-lambda',
                ZipFile=f.read()
            )
        print("✅ Updated Search Lambda")
    
    # Clean up zip files
    os.remove(auth_zip)
    os.remove(search_zip)
    
    return True

if __name__ == '__main__':
    print("🚀 Deploying GAIP API Lambda functions...")
    
    try:
        deploy_lambda_functions()
        print("\n✅ Lambda functions deployed successfully!")
        print("\nNext steps:")
        print("1. Create IAM execution role")
        print("2. Create API Gateway")
        print("3. Deploy test webapp")
        print("4. Generate API keys")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        print("Creating IAM role first...")
