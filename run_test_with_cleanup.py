#!/usr/bin/env python3
"""
Run Pipeline Test with Cleanup
Runs the cleanup lambda before running the pipeline test
"""

import boto3
import logging
import sys
import json
import subprocess
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to run cleanup and pipeline test"""
    logger.info("🧹 Running Cleanup and Pipeline Test")
    logger.info("==================================================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Step 1: Run cleanup lambda
        logger.info("Step 1: Running cleanup lambda")
        run_cleanup_lambda()
        
        # Step 2: Wait for cleanup to complete
        logger.info("Step 2: Waiting for cleanup to complete")
        time.sleep(10)  # Wait 10 seconds for cleanup to complete
        
        # Step 3: Run pipeline test
        logger.info("Step 3: Running pipeline test")
        run_pipeline_test()
        
        logger.info("✅ Successfully ran cleanup and pipeline test")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error running cleanup and pipeline test: {str(e)}")
        return 1

def run_cleanup_lambda():
    """Run the cleanup lambda function"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Invoke cleanup lambda
    logger.info("Invoking solve-global-kr-cleanup-service lambda")
    
    # Prepare payload
    payload = {
        "action": "cleanup_all",
        "doc_id": "all",  # Clean up all documents
        "force": True,    # Force cleanup even if documents are in use
        "cleanup_scope": {
            "databases": {
                "postgresql": {
                    "enabled": True,
                    "tables": [
                        "document_processing_status",
                        "nlp_processing_status",
                        "vector_processing_status",
                        "keyword_processing_status",
                        "kg_processing_status",
                        "text_chunking_status",
                        "textract_jobs"
                    ],
                    "document_ids": []  # Empty list means all documents
                },
                "opensearch": {
                    "enabled": True,
                    "collections": ["chunks", "documents", "vectors"],
                    "document_ids": []  # Empty list means all documents
                },
                "neptune": {
                    "enabled": True,
                    "clear_all_triples": True,
                    "document_ids": []  # Empty list means all documents
                }
            },
            "s3_data_lake": {
                "enabled": True,
                "buckets": [
                    "solve-global-kr-dl-source-documents-861276078413-us-east-1",
                    "solve-global-kr-dl-text-861276078413-us-east-1",
                    "solve-global-kr-dl-chunks-861276078413-us-east-1",
                    "solve-global-kr-dl-vectors-861276078413-us-east-1",
                    "solve-global-kr-dl-nlp-861276078413-us-east-1"
                ],
                "document_ids": [],  # Empty list means all documents
                "preserve_structure": True
            }
        },
        "safety_checks": {
            "dry_run": False,
            "max_documents_to_delete": 1000,
            "require_confirmation": False,
            "confirmation_provided": True
        }
    }
    
    # Invoke lambda
    response = lambda_client.invoke(
        FunctionName='solve-global-kr-cleanup-service',
        InvocationType='RequestResponse',  # Wait for response
        Payload=json.dumps(payload)
    )
    
    # Parse response
    response_payload = json.loads(response['Payload'].read().decode('utf-8'))
    
    if response['StatusCode'] == 200:
        logger.info(f"Cleanup lambda executed successfully: {response_payload}")
    else:
        logger.error(f"Cleanup lambda failed: {response_payload}")
        raise Exception(f"Cleanup lambda failed: {response_payload}")

def run_pipeline_test():
    """Run the pipeline test"""
    logger.info("Running pipeline test")
    
    # Build command
    cmd = [
        "python3",
        "invoke_pipeline_test.py",
        "--action", "setup_and_test",
        "--num-documents", "1",
        "--min-size-mb", "0.5",
        "--max-size-mb", "1.5",
        "--target-avg-pages", "3",
        "--skip-lambda-invocation"
    ]
    
    # Run command
    logger.info(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Log output
    logger.info(f"Pipeline test stdout: {result.stdout}")
    
    if result.stderr:
        logger.warning(f"Pipeline test stderr: {result.stderr}")
    
    # Check result
    if result.returncode == 0:
        logger.info("Pipeline test completed successfully")
    else:
        logger.error(f"Pipeline test failed with return code {result.returncode}")
        raise Exception(f"Pipeline test failed with return code {result.returncode}")

if __name__ == "__main__":
    sys.exit(main())
