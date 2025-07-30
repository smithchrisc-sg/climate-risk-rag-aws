#!/usr/bin/env python3
"""
Complete Pipeline Configuration Audit
Checks database configuration for all discovered Lambda functions in the Climate Risk RAG pipeline
"""

import boto3
import json

# Correct database URL from previous fixes
CORRECT_DATABASE_URL = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"

# All discovered Lambda functions that should have database configuration
PIPELINE_FUNCTIONS = [
    # Core pipeline functions (previously validated)
    "solve-global-kr-pipeline-test-function",
    "solve-global-kr-textextractor-initiator", 
    "solve-global-kr-textextractor-processor",
    "text-chunker-pipeline",
    "nlp-processor",
    "nlp-worker",
    "document-structure-kg-processor",
    "kg-integration-worker",
    
    # Vector embeddings functions (newly discovered)
    "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA",
    "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi",
    
    # Keyword indexing functions (newly discovered)
    "keyword-indexer",
    "async-keyword-indexer-initiator", 
    "async-keyword-indexer-worker",
    
    # Entity resolution function (newly discovered)
    "entity-resolution-service",
    
    # Additional functions that may need database access
    "solve-global-kr-text-chunker-db",
    "solve-global-kr-text-chunker-phase1",
]

def audit_lambda_functions():
    """
    Audit all pipeline Lambda functions for correct database configuration
    Returns: (correct_functions, incorrect_functions, missing_functions)
    """
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    correct_functions = []
    incorrect_functions = []
    missing_functions = []
    
    print("COMPLETE PIPELINE CONFIGURATION AUDIT")
    print("=" * 60)
    
    for function_name in PIPELINE_FUNCTIONS:
        try:
            response = lambda_client.get_function_configuration(FunctionName=function_name)
            
            # Check if function has environment variables
            env_vars = response.get('Environment', {}).get('Variables', {})
            
            if 'DATABASE_URL' in env_vars:
                current_db_url = env_vars['DATABASE_URL']
                
                if current_db_url == CORRECT_DATABASE_URL:
                    print("[OK] {}: Database URL correct".format(function_name))
                    correct_functions.append(function_name)
                else:
                    print("[ERROR] {}: Database URL incorrect".format(function_name))
                    print("   Current: {}...".format(current_db_url[:50]))
                    incorrect_functions.append(function_name)
            else:
                print("[WARN] {}: No DATABASE_URL environment variable".format(function_name))
                # Some functions might not need database access
                
        except lambda_client.exceptions.ResourceNotFoundException:
            print("[MISSING] {}: Function not found".format(function_name))
            missing_functions.append(function_name)
        except Exception as e:
            print("[ERROR] {}: Error checking function - {}".format(function_name, str(e)))
    
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("Functions with correct database config: {}".format(len(correct_functions)))
    print("Functions with incorrect database config: {}".format(len(incorrect_functions)))
    print("Functions not found: {}".format(len(missing_functions)))
    
    if incorrect_functions:
        print("\nFunctions needing database URL updates:")
        for func in incorrect_functions:
            print("   - {}".format(func))
    
    if missing_functions:
        print("\nFunctions not found (may have different names):")
        for func in missing_functions:
            print("   - {}".format(func))
    
    return correct_functions, incorrect_functions, missing_functions

def check_function_details(function_name):
    """Get detailed information about a specific function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        print("\nFUNCTION DETAILS: {}".format(function_name))
        print("Runtime: {}".format(response.get('Runtime', 'N/A')))
        print("Handler: {}".format(response.get('Handler', 'N/A')))
        print("Memory: {} MB".format(response.get('MemorySize', 'N/A')))
        print("Timeout: {} seconds".format(response.get('Timeout', 'N/A')))
        print("Last Modified: {}".format(response.get('LastModified', 'N/A')))
        
        # Environment variables
        env_vars = response.get('Environment', {}).get('Variables', {})
        if env_vars:
            print("Environment Variables:")
            for key, value in env_vars.items():
                if 'DATABASE_URL' in key or 'PASSWORD' in key:
                    print("  {}: {}...".format(key, value[:30]))
                else:
                    print("  {}: {}".format(key, value))
        
        # VPC Configuration
        vpc_config = response.get('VpcConfig', {})
        if vpc_config.get('VpcId'):
            print("VPC ID: {}".format(vpc_config['VpcId']))
            print("Subnets: {}".format(vpc_config.get('SubnetIds', [])))
            print("Security Groups: {}".format(vpc_config.get('SecurityGroupIds', [])))
        
    except Exception as e:
        print("Error getting function details: {}".format(str(e)))

if __name__ == "__main__":
    # Run the complete audit
    correct, incorrect, missing = audit_lambda_functions()
    
    # Show details for newly discovered vector embeddings functions
    print("\n" + "=" * 60)
    print("DETAILED ANALYSIS OF KEY FUNCTIONS")
    
    key_functions = [
        "vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA",
        "vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi", 
        "entity-resolution-service",
        "keyword-indexer"
    ]
    
    for func in key_functions:
        check_function_details(func)
