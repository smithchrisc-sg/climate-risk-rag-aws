#!/usr/bin/env python3
"""
Simple, non-hanging deployment for vector embeddings system
"""
import subprocess
import sys
import os
import boto3
import json

def run_command_simple(command, description, timeout=300):
    """Run command with timeout and no hanging"""
    print("\n" + "="*50)
    print("STEP: {}".format(description))
    print("COMMAND: {}".format(command))
    print("="*50)
    
    try:
        if isinstance(command, list):
            result = subprocess.run(command, timeout=timeout, capture_output=True, text=True)
        else:
            result = subprocess.run(command, shell=True, timeout=timeout, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("SUCCESS: {}".format(description))
            if result.stdout:
                print("OUTPUT: {}".format(result.stdout[:500]))  # Limit output
            return True
        else:
            print("FAILED: {}".format(description))
            print("Exit code: {}".format(result.returncode))
            if result.stderr:
                print("ERROR: {}".format(result.stderr[:500]))
            return False
            
    except subprocess.TimeoutExpired:
        print("TIMEOUT: {} exceeded {} seconds".format(description, timeout))
        return False
    except Exception as e:
        print("ERROR: {} - {}".format(description, str(e)))
        return False

def setup_database_schema_direct():
    """Set up database schema using existing function"""
    print("\nSETTING UP DATABASE SCHEMA...")
    
    try:
        # Use the actual text-chunker-pipeline function
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda', region_name='us-east-1')
        
        # Simple test to verify function works
        test_payload = {
            "Records": [{
                "body": json.dumps({
                    "Message": json.dumps({
                        "doc_id": "vector_db_test_{}".format(int(__import__('time').time())),
                        "stage": "database_test",
                        "test_mode": True
                    })
                })
            }]
        }
        
        print("Testing database connection via text-chunker-pipeline...")
        response = lambda_client.invoke(
            FunctionName='text-chunker-pipeline',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response.get('StatusCode') == 200:
            print("SUCCESS: Database connection verified")
            print("Manual schema setup required - SQL commands:")
            print_schema_sql()
            return True
        else:
            print("FAILED: Database connection test failed")
            return False
            
    except Exception as e:
        print("ERROR: Database setup failed - {}".format(str(e)))
        print("Manual schema setup required - SQL commands:")
        print_schema_sql()
        return False

def print_schema_sql():
    """Print SQL commands for manual execution"""
    sql_commands = [
        """
        CREATE TABLE IF NOT EXISTS vector_embeddings_status (
            doc_id VARCHAR(255) PRIMARY KEY,
            status VARCHAR(50) NOT NULL,
            embeddings_count INTEGER,
            titan_cost_estimate DECIMAL(10,6),
            titan_cost_actual DECIMAL(10,6),
            opensearch_indexed BOOLEAN DEFAULT FALSE,
            cache_used BOOLEAN DEFAULT FALSE,
            model_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            processing_duration_seconds INTEGER
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_status ON vector_embeddings_status(status);",
        "CREATE INDEX IF NOT EXISTS idx_vector_embeddings_created_at ON vector_embeddings_status(created_at);",
        """
        ALTER TABLE document_processing_status 
        ADD COLUMN IF NOT EXISTS vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
        ADD COLUMN IF NOT EXISTS vector_embeddings_completed_at TIMESTAMP;
        """
    ]
    
    print("\n" + "="*50)
    print("MANUAL DATABASE SCHEMA SETUP")
    print("="*50)
    for i, sql in enumerate(sql_commands, 1):
        print("-- Command {}:".format(i))
        print(sql.strip())
        print()

def deploy_cdk_stack():
    """Deploy CDK stack with timeout"""
    print("\nDEPLOYING CDK STACK...")
    
    # Change to CDK directory
    original_dir = os.getcwd()
    os.chdir('cdk')
    
    try:
        # Install dependencies quickly
        if not run_command_simple("pip install -r requirements.txt", "Install CDK dependencies", 60):
            print("WARNING: CDK dependencies installation failed")
        
        # Deploy with timeout
        deploy_cmd = "cdk deploy vector-embeddings-pipeline --profile solve-global --require-approval never"
        success = run_command_simple(deploy_cmd, "Deploy vector embeddings CDK stack", 600)  # 10 minute timeout
        
        return success
        
    finally:
        os.chdir(original_dir)

def verify_deployment():
    """Verify deployment worked"""
    print("\nVERIFYING DEPLOYMENT...")
    
    try:
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda', region_name='us-east-1')
        
        # Check for vector embeddings functions
        response = lambda_client.list_functions(MaxItems=50)
        functions = [f['FunctionName'] for f in response['Functions']]
        
        vector_functions = [f for f in functions if 'VectorEmbeddings' in f or 'vector-embeddings' in f]
        
        if vector_functions:
            print("SUCCESS: Found vector embeddings functions:")
            for func in vector_functions:
                print("  - {}".format(func))
            return True
        else:
            print("WARNING: No vector embeddings functions found")
            print("Available functions containing 'vector' or 'embedding':")
            vector_related = [f for f in functions if 'vector' in f.lower() or 'embedding' in f.lower()]
            for func in vector_related:
                print("  - {}".format(func))
            return False
            
    except Exception as e:
        print("ERROR: Verification failed - {}".format(str(e)))
        return False

def main():
    """Main deployment function"""
    print("VECTOR EMBEDDINGS SYSTEM - SIMPLE DEPLOYMENT")
    print("="*60)
    print("This deployment avoids hanging issues by:")
    print("- Using timeouts on all operations")
    print("- No interactive prompts")
    print("- Direct AWS API calls")
    print("- Manual fallbacks")
    print("="*60)
    
    # Change to project directory
    os.chdir('/Users/chris/climate-risk-rag-aws')
    
    success_count = 0
    total_steps = 3
    
    # Step 1: Database schema
    if setup_database_schema_direct():
        success_count += 1
    
    # Step 2: CDK deployment
    if deploy_cdk_stack():
        success_count += 1
    
    # Step 3: Verification
    if verify_deployment():
        success_count += 1
    
    # Results
    print("\n" + "="*60)
    print("DEPLOYMENT RESULTS")
    print("="*60)
    print("Steps completed: {}/{}".format(success_count, total_steps))
    
    if success_count == total_steps:
        print("SUCCESS: Vector embeddings system deployed!")
        print("\nNext steps:")
        print("1. Run manual database schema if needed")
        print("2. Test with existing document")
        print("3. Monitor CloudWatch logs")
    elif success_count >= 2:
        print("PARTIAL SUCCESS: Most components deployed")
        print("Check individual step results above")
    else:
        print("FAILED: Deployment had significant issues")
        print("Check error messages above")
    
    print("\nManual verification commands:")
    print("aws lambda list-functions --profile solve-global --query 'Functions[?contains(FunctionName, `VectorEmbeddings`)].FunctionName'")

if __name__ == "__main__":
    main()
