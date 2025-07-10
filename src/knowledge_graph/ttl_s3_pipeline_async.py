#!/usr/bin/env python3
"""
TTL S3 Pipeline with Async Neptune Loading
Generate TTL files and trigger async Neptune bulk loading
"""

import boto3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Add the knowledge graph module to path
sys.path.append(os.path.dirname(__file__))
from ttl_s3_pipeline import TTLPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncTTLPipeline(TTLPipeline):
    """Extended TTL pipeline with async Neptune bulk loading"""
    
    def __init__(self, aws_profile: str = 'solve-global'):
        super().__init__(aws_profile)
        
        # Lambda function for async bulk loading
        self.bulk_loader_function = 'neptune-bulk-loader-async'
        self.lambda_client = self.session.client('lambda', region_name='us-east-1')
    
    def process_document_with_loading(self, doc_id: str, load_to_neptune: bool = True) -> Dict[str, Any]:
        """Complete pipeline: generate TTL, upload to S3, and optionally load to Neptune"""
        logger.info(f"Processing document {doc_id} with Neptune loading: {load_to_neptune}")
        
        try:
            # Step 1: Generate and upload TTL files
            result = self.process_document(doc_id)
            
            if result['status'] != 'success':
                return result
            
            # Step 2: Trigger Neptune bulk loading if requested
            if load_to_neptune:
                loading_result = self.trigger_neptune_loading(doc_id)
                result['neptune_loading'] = loading_result
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            return {
                'doc_id': doc_id,
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    def trigger_neptune_loading(self, doc_id: str) -> Dict[str, Any]:
        """Trigger async Neptune bulk loading for a document"""
        logger.info(f"Triggering Neptune bulk loading for document {doc_id}")
        
        loading_results = {
            'doc_id': doc_id,
            'jobs': []
        }
        
        try:
            # Step 1: Load schema first (if not already loaded)
            schema_result = self.trigger_bulk_load_job(doc_id, 'schema')
            loading_results['jobs'].append(schema_result)
            
            # Step 2: Load document data
            document_result = self.trigger_bulk_load_job(doc_id, 'document')
            loading_results['jobs'].append(document_result)
            
            # Summary
            successful_jobs = sum(1 for job in loading_results['jobs'] if job.get('success', False))
            loading_results['summary'] = {
                'successful_jobs': successful_jobs,
                'total_jobs': len(loading_results['jobs']),
                'all_jobs_submitted': successful_jobs == len(loading_results['jobs'])
            }
            
            return loading_results
            
        except Exception as e:
            logger.error(f"Error triggering Neptune loading: {e}")
            loading_results['error'] = str(e)
            return loading_results
    
    def trigger_bulk_load_job(self, doc_id: str, load_type: str) -> Dict[str, Any]:
        """Trigger a single bulk load job via Lambda"""
        
        payload = {
            'doc_id': doc_id,
            'load_type': load_type
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.bulk_loader_function,
                InvocationType='RequestResponse',  # Synchronous for job submission
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 200:
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload['statusCode'] == 200:
                    job_result = json.loads(response_payload['body'])
                    logger.info(f"Successfully submitted {load_type} load job: {job_result.get('load_id')}")
                    return job_result
                else:
                    error_body = json.loads(response_payload['body'])
                    logger.error(f"Bulk load job submission failed: {error_body}")
                    return {
                        'success': False,
                        'load_type': load_type,
                        'error': error_body
                    }
            else:
                logger.error(f"Lambda invocation failed: {response['StatusCode']}")
                return {
                    'success': False,
                    'load_type': load_type,
                    'error': f"Lambda invocation failed with status {response['StatusCode']}"
                }
                
        except Exception as e:
            logger.error(f"Error invoking bulk loader Lambda: {e}")
            return {
                'success': False,
                'load_type': load_type,
                'error': str(e)
            }
    
    def check_loading_status(self, load_id: str) -> Dict[str, Any]:
        """Check the status of a Neptune bulk loading job"""
        
        payload = {
            'load_id': load_id
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='neptune-bulk-loader-monitor',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 200:
                response_payload = json.loads(response['Payload'].read())
                
                if response_payload['statusCode'] == 200:
                    status_result = json.loads(response_payload['body'])
                    return status_result
                else:
                    error_body = json.loads(response_payload['body'])
                    return {
                        'success': False,
                        'error': error_body
                    }
            else:
                return {
                    'success': False,
                    'error': f"Lambda invocation failed with status {response['StatusCode']}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def wait_for_completion(self, load_ids: List[str], timeout_minutes: int = 30) -> Dict[str, Any]:
        """Wait for multiple load jobs to complete (for testing/debugging)"""
        
        import time
        
        logger.info(f"Waiting for {len(load_ids)} load jobs to complete...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        completed_jobs = {}
        
        while time.time() - start_time < timeout_seconds:
            all_complete = True
            
            for load_id in load_ids:
                if load_id not in completed_jobs:
                    status = self.check_loading_status(load_id)
                    
                    if status.get('success', False):
                        if status.get('job_complete', False):
                            completed_jobs[load_id] = status
                            logger.info(f"Job {load_id} completed with status: {status.get('status')}")
                        else:
                            all_complete = False
                    else:
                        logger.error(f"Error checking status for job {load_id}: {status.get('error')}")
                        completed_jobs[load_id] = status
            
            if all_complete:
                logger.info("All jobs completed!")
                break
            
            time.sleep(30)  # Check every 30 seconds
        
        return {
            'completed_jobs': completed_jobs,
            'all_complete': len(completed_jobs) == len(load_ids),
            'timeout_reached': time.time() - start_time >= timeout_seconds
        }

def main():
    """Main function to test async TTL pipeline"""
    
    doc_id = "0032f6cb_f0caef34"
    
    print(f"🚀 ASYNC TTL PIPELINE - Processing Document: {doc_id}")
    print("=" * 60)
    
    pipeline = AsyncTTLPipeline()
    
    try:
        # Process document with Neptune loading
        result = pipeline.process_document_with_loading(doc_id, load_to_neptune=True)
        
        if result['status'] == 'success':
            print("✅ Document processing completed successfully!")
            print(f"📁 Files generated: {', '.join(result['files_generated'])}")
            
            # Check Neptune loading results
            if 'neptune_loading' in result:
                loading = result['neptune_loading']
                print(f"🔄 Neptune loading jobs:")
                
                for job in loading['jobs']:
                    if job.get('success', False):
                        print(f"   ✅ {job['load_type']}: Job {job['load_id']} submitted")
                    else:
                        print(f"   ❌ {job['load_type']}: {job.get('error', 'Unknown error')}")
                
                # Extract load IDs for monitoring
                load_ids = [job['load_id'] for job in loading['jobs'] if job.get('success', False)]
                
                if load_ids:
                    print(f"📊 Monitor job status with load IDs: {', '.join(load_ids)}")
                    print(f"🔗 Jobs will complete asynchronously and send notifications")
            
            return True
        else:
            print(f"❌ Document processing failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
