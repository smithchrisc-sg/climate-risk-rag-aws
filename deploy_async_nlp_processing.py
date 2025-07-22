#!/usr/bin/env python3
"""
Deploy Asynchronous NLP Processing Infrastructure
"""
import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Deploy the async NLP processing infrastructure"""
    print("🚀 Deploying Asynchronous NLP Processing Infrastructure")
    print("=" * 60)
    
    # Change to CDK directory
    cdk_dir = os.path.join(os.path.dirname(__file__), 'cdk')
    os.chdir(cdk_dir)
    
    # Install CDK dependencies
    if not run_command("pip install -r requirements.txt", "Installing CDK dependencies"):
        sys.exit(1)
    
    # Bootstrap CDK (if needed)
    print("\n🔄 Checking CDK bootstrap status...")
    bootstrap_result = subprocess.run("cdk bootstrap", shell=True, capture_output=True, text=True)
    if bootstrap_result.returncode != 0:
        print("CDK already bootstrapped or bootstrap not needed")
    else:
        print("✅ CDK bootstrap completed")
    
    # Synthesize the stack
    if not run_command("cdk synth -a 'python app_async_nlp_processing.py'", 
                      "Synthesizing async NLP processing stack"):
        sys.exit(1)
    
    # Deploy the stack
    if not run_command("cdk deploy -a 'python app_async_nlp_processing.py' --require-approval never", 
                      "Deploying async NLP processing stack"):
        sys.exit(1)
    
    print("\n🎉 Async NLP Processing Infrastructure Deployment Complete!")
    print("=" * 60)
    print("\n📋 Deployed Components:")
    print("• SNS Topics: comprehend-entity-completion, comprehend-keyphrase-completion")
    print("• SQS Queues: nlp-worker-entity-queue, nlp-worker-keyphrase-queue")
    print("• Lambda Functions: nlp-worker-entity, nlp-worker-keyphrase, comprehend-job-monitor")
    print("• CloudWatch Events: comprehend-job-monitor-schedule (every 2 minutes)")
    print("• Updated NLP Processor with async configuration")
    
    print("\n🔧 Next Steps:")
    print("1. Verify all Lambda functions are deployed correctly")
    print("2. Test the pipeline with a sample document")
    print("3. Monitor CloudWatch logs for proper operation")
    print("4. Ensure database stage constraints include: nlp_entity_processing, nlp_keyphrase_processing")

if __name__ == "__main__":
    main()
