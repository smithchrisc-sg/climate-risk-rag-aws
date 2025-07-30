#!/usr/bin/env python3
"""
Update Database URLs for Remaining Lambda Functions
Updates the DATABASE_URL environment variable for functions with incorrect configurations
"""

import boto3
import json

# Correct database URL
CORRECT_DATABASE_URL = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"

# Functions that need database URL updates (based on our audit)
FUNCTIONS_TO_UPDATE = [
    "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA",
    "async-keyword-indexer-initiator",
    "async-keyword-indexer-worker"
]

def update_function_database_url(function_name):
    """Update the DATABASE_URL for a specific Lambda function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Get current configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env_vars = response.get('Environment', {}).get('Variables', {})
        
        # Update the DATABASE_URL
        current_env_vars['DATABASE_URL'] = CORRECT_DATABASE_URL
        
        # Update the function configuration
        update_response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': current_env_vars}
        )
        
        print("SUCCESS: Updated {} - DATABASE_URL corrected".format(function_name))
        return True
        
    except Exception as e:
        print("ERROR: Failed to update {} - {}".format(function_name, str(e)))
        return False

def main():
    print("UPDATING DATABASE URLs FOR REMAINING FUNCTIONS")
    print("=" * 60)
    
    success_count = 0
    total_count = len(FUNCTIONS_TO_UPDATE)
    
    for function_name in FUNCTIONS_TO_UPDATE:
        if update_function_database_url(function_name):
            success_count += 1
    
    print("\n" + "=" * 60)
    print("UPDATE SUMMARY")
    print("Successfully updated: {}/{}".format(success_count, total_count))
    
    if success_count == total_count:
        print("All functions updated successfully!")
    else:
        print("Some functions failed to update. Check errors above.")

if __name__ == "__main__":
    main()
