#!/usr/bin/env python3
"""
Standalone deployment script for Admin Ontology Manager
Uses existing infrastructure patterns without creating conflicts
"""

import boto3
import json
import zipfile
import os
from pathlib import Path

def create_deployment_package():
    """Create deployment package for admin ontology manager"""
    
    # Create zip file
    zip_path = "/tmp/admin-ontology-manager.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add lambda function code at root level
        lambda_dir = Path("lambda/admin_ontology_manager")
        for file_path in lambda_dir.rglob("*.py"):
            arcname = file_path.name  # Just the filename, not the path
            zipf.write(file_path, arcname)
    
    return zip_path

def deploy_function():
    """Deploy the admin ontology manager function"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    zip_path = create_deployment_package()
    
    function_name = "solve-global-kr-admin-ontology-manager"
    
    # Read zip file
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Function configuration
    function_config = {
        'FunctionName': function_name,
        'Runtime': 'python3.11',
        'Role': 'arn:aws:iam::861276078413:role/document-processing-lambda-role',  # Use existing role
        'Handler': 'lambda_function.lambda_handler',
        'Code': {'ZipFile': zip_content},
        'Description': 'Administrative utility for ontology management operations',
        'Timeout': 900,  # 15 minutes
        'MemorySize': 1024,
        'VpcConfig': {
            'SubnetIds': [
                'subnet-03d8bd6cf3491f38c',  # From existing functions
                'subnet-0c0be1dd59f70f70e'
            ],
            'SecurityGroupIds': ['sg-0c9e10b9cfb4c9eb0']  # From existing functions
        },
        'Environment': {
            'Variables': {
                'DATABASE_SECRET_NAME': 'rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863',
                'DB_PORT': '5432',
                'DB_NAME': 'climate_risk_rag',
                'DB_HOST': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
                'NEPTUNE_ENDPOINT': 'solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com',
                'NEPTUNE_PORT': '8182',
                'TTL_BUCKET': 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1',
                'LOG_LEVEL': 'INFO'
            }
        },
        'Layers': [
            'arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16',
            'arn:aws:lambda:us-east-1:861276078413:layer:knowledge-graph-layer:7'  # Now exists
        ]
    }
    
    try:
        # Try to create function
        response = lambda_client.create_function(**function_config)
        print(f"✅ Created function: {function_name}")
        print(f"   ARN: {response['FunctionArn']}")
        
    except lambda_client.exceptions.ResourceConflictException:
        # Function exists, update it
        print(f"Function {function_name} exists, updating...")
        
        # Update function code
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # Update function configuration
        config_update = {k: v for k, v in function_config.items() 
                        if k not in ['Code']}  # Keep FunctionName
        lambda_client.update_function_configuration(**config_update)
        
        print(f"✅ Updated function: {function_name}")
    
    # Clean up
    os.remove(zip_path)
    
    return function_name

if __name__ == "__main__":
    print("🚀 Deploying Admin Ontology Manager...")
    function_name = deploy_function()
    print(f"✅ Deployment complete: {function_name}")
    print("\n📋 Next steps:")
    print("1. Upload ontology to S3")
    print("2. Test with: aws lambda invoke --function-name solve-global-kr-admin-ontology-manager")
