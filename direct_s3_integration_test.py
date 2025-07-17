#!/usr/bin/env python3
"""
Direct S3 Integration Test
Bypasses database issues by uploading documents directly to S3 to trigger pipeline
"""

import boto3
import logging
import sys
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to run direct S3 integration test"""
    logger.info("🚀 Direct S3 Integration Test")
    logger.info("=============================")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Step 1: Upload a test document to trigger pipeline
        logger.info("Step 1: Uploading test document to S3")
        doc_id = upload_test_document()
        
        # Step 2: Wait for pipeline processing
        logger.info("Step 2: Waiting for pipeline processing")
        wait_for_processing()
        
        # Step 3: Check pipeline stages
        logger.info("Step 3: Checking pipeline stage results")
        check_pipeline_results(doc_id)
        
        logger.info("✅ Direct S3 integration test completed")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Direct S3 integration test failed: {str(e)}")
        return 1

def upload_test_document():
    """Upload a test document directly to S3 to trigger pipeline"""
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Use a small existing document from the corpus
    source_bucket = "solve-global-kr-documents-861276078413-us-east-1"
    target_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
    
    # Generate a unique document ID
    doc_id = f"integration_test_{int(time.time())}"
    
    try:
        # List available documents in source bucket
        logger.info("Finding available test documents...")
        response = s3_client.list_objects_v2(Bucket=source_bucket, MaxKeys=5)
        
        if 'Contents' not in response:
            logger.error("No documents found in source bucket")
            return None
        
        # Use the first available document
        source_key = response['Contents'][0]['Key']
        logger.info(f"Using source document: {source_key}")
        
        # Copy to target bucket with new doc_id
        target_key = f"data_lake/{doc_id}/source/{source_key}"
        
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        s3_client.copy_object(CopySource=copy_source, Bucket=target_bucket, Key=target_key)
        
        logger.info(f"✅ Uploaded test document: {target_key}")
        logger.info(f"Document ID: {doc_id}")
        
        return doc_id
        
    except Exception as e:
        logger.error(f"❌ Failed to upload test document: {str(e)}")
        return None

def wait_for_processing():
    """Wait for pipeline processing to occur"""
    logger.info("⏳ Waiting 3 minutes for pipeline processing...")
    time.sleep(180)  # Wait 3 minutes

def check_pipeline_results(doc_id):
    """Check results in S3 buckets to see pipeline progress"""
    if not doc_id:
        logger.error("No document ID to check")
        return
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Check different pipeline stages
    buckets_to_check = [
        ("solve-global-kr-dl-source-documents-861276078413-us-east-1", "Source Documents"),
        ("solve-global-kr-dl-text-861276078413-us-east-1", "Text Extraction"),
        ("solve-global-kr-dl-chunks-861276078413-us-east-1", "Text Chunking"),
        ("solve-global-kr-dl-nlp-861276078413-us-east-1", "NLP Processing")
    ]
    
    results = {}
    
    for bucket, stage_name in buckets_to_check:
        try:
            # Check for files related to our document
            prefix = f"data_lake/{doc_id}/"
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            if 'Contents' in response:
                file_count = len(response['Contents'])
                total_size = sum(obj['Size'] for obj in response['Contents'])
                results[stage_name] = {
                    'files': file_count,
                    'total_size': total_size,
                    'status': '✅ PROCESSED'
                }
                logger.info(f"✅ {stage_name}: {file_count} files ({total_size} bytes)")
            else:
                results[stage_name] = {
                    'files': 0,
                    'total_size': 0,
                    'status': '❌ NO DATA'
                }
                logger.info(f"❌ {stage_name}: No files found")
                
        except Exception as e:
            results[stage_name] = {
                'error': str(e),
                'status': '❌ ERROR'
            }
            logger.error(f"❌ {stage_name}: Error checking - {str(e)}")
    
    # Summary
    logger.info("\n📊 PIPELINE INTEGRATION TEST RESULTS")
    logger.info("====================================")
    for stage_name, result in results.items():
        logger.info(f"{stage_name}: {result['status']}")
    
    # Check if NLP stage was reached
    if results.get("NLP Processing", {}).get('files', 0) > 0:
        logger.info("\n🎉 SUCCESS: NLP stage was reached and processed data!")
        logger.info("Integration test successful - data flowed through to NLP stage")
    elif results.get("Text Chunking", {}).get('files', 0) > 0:
        logger.info("\n🔧 PARTIAL SUCCESS: Data reached chunking stage")
        logger.info("NLP stage may need more time or have processing issues")
    elif results.get("Text Extraction", {}).get('files', 0) > 0:
        logger.info("\n🔧 PARTIAL SUCCESS: Data reached text extraction stage")
        logger.info("Chunking or downstream stages may have issues")
    else:
        logger.info("\n❌ PIPELINE NOT TRIGGERED: No processing detected")
        logger.info("Document upload may not have triggered the pipeline")

if __name__ == "__main__":
    sys.exit(main())
