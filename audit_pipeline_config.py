#!/usr/bin/env python3
"""
Comprehensive Pipeline Configuration Audit
Verify all Lambda functions have correct database passwords and configurations
"""

import boto3
import json
from datetime import datetime

def audit_pipeline_configuration():
    """Audit all pipeline Lambda functions for correct configuration"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Expected database URL with current password
    expected_db_url = "postgresql://postgres:c0xfd_t#PBUqV(pLM-9IqM59G:>c@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
    
    # All Lambda functions that should have database access
    pipeline_functions = [
        'solve-global-kr-pipeline-test-function',
        'solve-global-kr-textextractor-initiator', 
        'solve-global-kr-textextractor-processor',
        'text-chunker-pipeline',
        'nlp-processor',
        'nlp-worker',
        'vector-embeddings-processor',
        'vector-embeddings-worker',
        'keyword-indexer',
        'keyword-indexer-worker',
        'document-structure-kg-processor',
        'kg-integration-worker',
        'entity-resolver'
    ]
    
    print("CLIMATE RISK RAG PIPELINE CONFIGURATION AUDIT")
    print("=" * 60)
    print(f"Audit Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Expected DB Password: c0xfd_t#PBUqV(pLM-9IqM59G:>c")
    print()
    
    results = {
        'correct_db_config': [],
        'incorrect_db_config': [],
        'missing_db_config': [],
        'function_not_found': [],
        'other_issues': []
    }
    
    for function_name in pipeline_functions:
        print(f"🔍 Checking: {function_name}")
        
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']
            
            # Check environment variables
            env_vars = config.get('Environment', {}).get('Variables', {})
            db_url = env_vars.get('DATABASE_URL', '')
            
            if not db_url:
                print(f"   ❌ No DATABASE_URL found")
                results['missing_db_config'].append(function_name)
            elif db_url == expected_db_url:
                print(f"   ✅ Database configuration correct")
                results['correct_db_config'].append(function_name)
            else:
                print(f"   ❌ Database configuration incorrect")
                # Check if it's just the password that's wrong
                if "c0xfd_t#PBUqV(pLM-9IqM59G:>c" in db_url:
                    print(f"      ℹ️  Password is correct, other URL differences")
                else:
                    print(f"      ⚠️  Password appears to be wrong")
                results['incorrect_db_config'].append({
                    'function': function_name,
                    'current_url': db_url[:50] + "..." if len(db_url) > 50 else db_url
                })
            
            # Check other important configurations
            issues = []
            
            # Check VPC configuration for database functions
            vpc_config = config.get('VpcConfig', {})
            if vpc_config.get('VpcId') != 'vpc-051c21d88c7dc3819':
                issues.append("Wrong VPC")
            
            # Check if using database subnets for DB-connected functions
            subnets = vpc_config.get('SubnetIds', [])
            db_subnets = ['subnet-0e9efc5fdf29e9da0', 'subnet-00efdcc220a613ae3']
            if function_name in ['solve-global-kr-textextractor-initiator', 
                                'solve-global-kr-textextractor-processor',
                                'solve-global-kr-pipeline-test-function']:
                if not any(subnet in db_subnets for subnet in subnets):
                    issues.append("Not using database subnets")
            
            # Check timeout settings
            timeout = config.get('Timeout', 0)
            if timeout < 300:  # Less than 5 minutes
                issues.append(f"Short timeout: {timeout}s")
            
            # Check memory settings
            memory = config.get('MemorySize', 0)
            if memory < 512:
                issues.append(f"Low memory: {memory}MB")
            
            # Check layers
            layers = config.get('Layers', [])
            if not layers:
                issues.append("No Lambda layers")
            
            if issues:
                print(f"   ⚠️  Other issues: {', '.join(issues)}")
                results['other_issues'].append({
                    'function': function_name,
                    'issues': issues
                })
            else:
                print(f"   ✅ Other configurations look good")
                
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"   ❌ Function not found")
            results['function_not_found'].append(function_name)
        except Exception as e:
            print(f"   ❌ Error checking function: {e}")
            results['other_issues'].append({
                'function': function_name,
                'issues': [f"Error: {e}"]
            })
        
        print()
    
    # Summary
    print("AUDIT SUMMARY")
    print("=" * 40)
    print(f"✅ Correct DB Config: {len(results['correct_db_config'])}")
    print(f"❌ Incorrect DB Config: {len(results['incorrect_db_config'])}")
    print(f"⚠️  Missing DB Config: {len(results['missing_db_config'])}")
    print(f"❓ Functions Not Found: {len(results['function_not_found'])}")
    print(f"⚠️  Other Issues: {len(results['other_issues'])}")
    print()
    
    if results['incorrect_db_config']:
        print("FUNCTIONS NEEDING DATABASE URL UPDATES:")
        for item in results['incorrect_db_config']:
            print(f"  - {item['function']}")
    
    if results['missing_db_config']:
        print("FUNCTIONS MISSING DATABASE URL:")
        for func in results['missing_db_config']:
            print(f"  - {func}")
    
    if results['function_not_found']:
        print("FUNCTIONS NOT FOUND (may use different names):")
        for func in results['function_not_found']:
            print(f"  - {func}")
    
    return results

if __name__ == "__main__":
    audit_pipeline_configuration()
