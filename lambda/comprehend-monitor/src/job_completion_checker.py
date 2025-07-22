#!/usr/bin/env python3
"""
Simple Job Completion Checker - Checks specific jobs and triggers workers
"""
import json
import boto3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class JobCompletionChecker:
    """Check specific Comprehend jobs and trigger workers when complete"""
    
    def __init__(self):
        """Initialize checker with AWS clients"""
        self.comprehend_client = boto3.client('comprehend', region_name=os.environ.get('COMPREHEND_REGION', 'us-east-1'))
        self.lambda_client = boto3.client('lambda')
        
        # Configuration
        self.entity_worker_function = os.environ.get('ENTITY_WORKER_FUNCTION', 'nlp-worker-entity')
        self.keyphrase_worker_function = os.environ.get('KEYPHRASE_WORKER_FUNCTION', 'nlp-worker-keyphrase')
        
        logger.info("✅ Job Completion Checker initialized")
    
    def process_event(self, event, context):
        """Process scheduled event to check recent job completions"""
        try:
            logger.info("Checking for recently completed Comprehend jobs...")
            
            # Get jobs from the last 10 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=10)
            
            # Check entity detection jobs
            entity_jobs = self.get_recent_completed_jobs('entities-detection', cutoff_time)
            entity_triggered = self.trigger_workers_for_jobs(entity_jobs, 'entities-detection')
            
            # Check key phrases detection jobs
            keyphrase_jobs = self.get_recent_completed_jobs('key-phrases-detection', cutoff_time)
            keyphrase_triggered = self.trigger_workers_for_jobs(keyphrase_jobs, 'key-phrases-detection')
            
            total_triggered = len(entity_triggered) + len(keyphrase_triggered)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Triggered {total_triggered} worker invocations',
                    'entity_workers_triggered': len(entity_triggered),
                    'keyphrase_workers_triggered': len(keyphrase_triggered),
                    'entity_jobs': entity_triggered,
                    'keyphrase_jobs': keyphrase_triggered
                })
            }
            
        except Exception as e:
            logger.error(f"Checker error: {e}")
            raise
    
    def get_recent_completed_jobs(self, job_type: str, cutoff_time: datetime) -> List[Dict]:
        """Get recently completed jobs of specified type"""
        try:
            if job_type == 'entities-detection':
                response = self.comprehend_client.list_entities_detection_jobs(
                    Filter={'JobStatus': 'COMPLETED'},
                    MaxResults=50
                )
                jobs = response.get('EntitiesDetectionJobPropertiesList', [])
            else:  # key-phrases-detection
                response = self.comprehend_client.list_key_phrases_detection_jobs(
                    Filter={'JobStatus': 'COMPLETED'},
                    MaxResults=50
                )
                jobs = response.get('KeyPhrasesDetectionJobPropertiesList', [])
            
            # Filter for recent jobs
            recent_jobs = []
            for job in jobs:
                end_time = job.get('EndTime')
                if end_time:
                    # Convert to UTC if timezone-aware
                    if end_time.tzinfo is not None:
                        end_time = end_time.replace(tzinfo=None)
                    
                    if end_time > cutoff_time:
                        recent_jobs.append(job)
            
            logger.info(f"Found {len(recent_jobs)} recent {job_type} jobs")
            return recent_jobs
                
        except Exception as e:
            logger.error(f"Error getting recent {job_type} jobs: {e}")
            return []
    
    def trigger_workers_for_jobs(self, jobs: List[Dict], job_type: str) -> List[Dict]:
        """Trigger worker functions for completed jobs"""
        triggered = []
        
        for job in jobs:
            try:
                job_id = job.get('JobId')
                job_name = job.get('JobName')
                
                if not job_id or not job_name:
                    continue
                
                # Create notification message similar to what SNS would send
                message = {
                    'JobId': job_id,
                    'JobName': job_name,
                    'JobStatus': 'COMPLETED',
                    'JobType': job_type,
                    'Timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                
                # Create event payload for the worker
                event_payload = {
                    'Records': [{
                        'body': json.dumps({
                            'Type': 'Notification',
                            'Message': json.dumps(message)
                        })
                    }]
                }
                
                # Determine which worker to invoke
                function_name = (self.entity_worker_function if job_type == 'entities-detection' 
                               else self.keyphrase_worker_function)
                
                # Invoke the worker
                response = self.lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps(event_payload)
                )
                
                logger.info(f"Triggered {function_name} for job {job_name}")
                
                triggered.append({
                    'job_id': job_id,
                    'job_name': job_name,
                    'function_name': function_name,
                    'status_code': response['StatusCode']
                })
                
            except Exception as e:
                logger.error(f"Error triggering worker for job {job.get('JobId', 'unknown')}: {e}")
                continue
        
        return triggered
