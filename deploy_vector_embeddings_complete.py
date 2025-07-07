#!/usr/bin/env python3
"""
Complete deployment script for vector embeddings system
"""
import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print("\n" + "="*60)
    print("STEP: {}".format(description))
    print("COMMAND: {}".format(command))
    print("="*60)
    
    try:
        if isinstance(command, list):
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        
        if result.stdout:
            print("OUTPUT:")
            print(result.stdout)
        
        print("SUCCESS: {}".format(description))
        return True
        
    except subprocess.CalledProcessError as e:
        print("ERROR: {} failed".format(description))
        print("Exit code: {}".format(e.returncode))
        if e.stdout:
            print("STDOUT: {}".format(e.stdout))
        if e.stderr:
            print("STDERR: {}".format(e.stderr))
        return False

def deploy_vector_embeddings():
    """Deploy complete vector embeddings system"""
    
    print("DEPLOYING VECTOR EMBEDDINGS SYSTEM")
    print("="*60)
    print("This will deploy a complete, integrated vector embeddings system")
    print("Estimated time: 5-10 minutes")
    print("="*60)
    
    # Change to project directory
    os.chdir('/Users/chris/climate-risk-rag-aws')
    
    # Step 1: Database schema migration
    print("\n1. MIGRATING DATABASE SCHEMA...")
    if not run_command("python migrate_vector_embeddings_schema.py", "Database schema migration"):
        print("WARNING: Database schema migration failed - you may need to run SQL manually")
        response = input("Continue with deployment? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Step 2: Create embeddings layer (optional - can use existing dependencies)
    print("\n2. CHECKING LAMBDA LAYERS...")
    print("Using existing layers: climate-risk-core-utilities-pipeline, opensearch-dependencies")
    print("Note: SentenceTransformers will be installed as part of function deployment")
    
    # Step 3: Deploy CDK stack
    print("\n3. DEPLOYING CDK INFRASTRUCTURE...")
    os.chdir('cdk')
    
    # Install CDK dependencies
    if not run_command("pip install -r requirements.txt", "Install CDK dependencies"):
        return False
    
    # CDK bootstrap (if needed)
    run_command("cdk bootstrap --profile solve-global", "CDK bootstrap (may already be done)")
    
    # CDK deploy
    if not run_command("cdk deploy vector-embeddings-pipeline --profile solve-global --require-approval never", 
                      "Deploy vector embeddings infrastructure"):
        return False
    
    # Step 4: Verify deployment
    print("\n4. VERIFYING DEPLOYMENT...")
    os.chdir('..')
    
    # Check if functions were created
    check_functions_cmd = [
        "aws", "lambda", "list-functions", 
        "--profile", "solve-global",
        "--region", "us-east-1",
        "--query", "Functions[?contains(FunctionName, 'VectorEmbeddings')].FunctionName"
    ]
    
    if run_command(check_functions_cmd, "Verify Lambda functions created"):
        print("SUCCESS: Vector embeddings functions deployed!")
    
    # Step 5: Test with sample document (optional)
    print("\n5. READY FOR TESTING")
    print("="*60)
    print("Vector embeddings system is deployed and ready!")
    print("\nTo test:")
    print("1. Trigger text chunker for an existing document")
    print("2. Check CloudWatch logs for vector embeddings processor")
    print("3. Verify database status updates")
    print("4. Check OpenSearch for vector index creation")
    
    print("\nEnvironment variables set:")
    print("- EMBEDDINGS_MODEL_TYPE=sentence_transformers (free)")
    print("- COST_THRESHOLD_PER_DOC=0.50")
    print("\nTo switch to Titan:")
    print("aws lambda update-function-configuration --function-name vector-embeddings-pipeline-VectorEmbeddingsWorker --environment Variables='{\"EMBEDDINGS_MODEL_TYPE\":\"titan\"}' --profile solve-global")
    
    return True

def main():
    """Main deployment function"""
    
    print("Vector Embeddings System - Complete Deployment")
    print("This will deploy a fully integrated vector embeddings system")
    print("\nComponents to be deployed:")
    print("- Database schema updates")
    print("- Vector Embeddings Processor Lambda")
    print("- Vector Embeddings Worker Lambda") 
    print("- SNS/SQS integration")
    print("- IAM roles and permissions")
    print("- OpenSearch vector index support")
    
    response = input("\nProceed with deployment? (y/n): ")
    if response.lower() != 'y':
        print("Deployment cancelled.")
        return
    
    success = deploy_vector_embeddings()
    
    if success:
        print("\n" + "="*60)
        print("DEPLOYMENT COMPLETE!")
        print("="*60)
        print("Vector embeddings system is ready for use.")
        print("Check the logs and test with a sample document.")
    else:
        print("\n" + "="*60)
        print("DEPLOYMENT FAILED!")
        print("="*60)
        print("Check the error messages above and resolve issues.")
        print("You may need to run parts of the deployment manually.")

if __name__ == "__main__":
    main()
