#!/usr/bin/env python3
"""
Update Vector Embeddings Functions with Keyword Indexer's Security Group
"""

import boto3
import json
from datetime import datetime

def update_function_vpc_config(function_name, security_group_ids):
    """Update Lambda function VPC config with new security group"""
    
    print(f"🔄 Updating VPC config for {function_name}")
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    try:
        # Get current function configuration
        response = lambda_client.get_function(
            FunctionName=function_name
        )
        
        current_config = response['Configuration']
        current_vpc_config = current_config.get('VpcConfig', {})
        current_subnet_ids = current_vpc_config.get('SubnetIds', [])
        current_sg_ids = current_vpc_config.get('SecurityGroupIds', [])
        
        print(f"  Current VPC config:")
        print(f"    - Subnets: {current_subnet_ids}")
        print(f"    - Security Groups: {current_sg_ids}")
        
        # Update function configuration with new security group
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            VpcConfig={
                'SubnetIds': current_subnet_ids,
                'SecurityGroupIds': security_group_ids
            }
        )
        
        print(f"✅ Updated VPC config for {function_name}")
        print(f"  New VPC config:")
        print(f"    - Subnets: {current_subnet_ids}")
        print(f"    - Security Groups: {security_group_ids}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating VPC config for {function_name}: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Vector Embeddings VPC Config Update")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    # Keyword indexer security group
    keyword_indexer_sg = ["sg-0709acdc3f0cccd7f"]
    
    # Functions to update
    functions = [
        "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA",
        "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi"
    ]
    
    success_count = 0
    
    # Update each function
    for function_name in functions:
        if update_function_vpc_config(function_name, keyword_indexer_sg):
            success_count += 1
    
    print(f"\n📊 Update Summary: {success_count}/{len(functions)} functions updated")
    
    if success_count == len(functions):
        print("🎉 Vector embeddings VPC config update complete!")
        print("   The vector embeddings pipeline should now be able to connect to the database.")
    else:
        print("⚠️  Some updates failed - check logs and retry failed updates.")
