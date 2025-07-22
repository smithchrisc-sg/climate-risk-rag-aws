#!/usr/bin/env python3
"""
Comprehend Job Monitor - Polls for job completion and sends notifications
"""
import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ComprehendJobMonitor:
    """Monitor Comprehend jobs and send completion notifications"""
    
    def __init__(self):
        """Initialize monitor with AWS clients"""
        self.comprehend_client = boto3.client('comprehend', region_name=os.environ.get('COMPREHEND_REGION', 'us-east-1'))
        self.sns_client = boto3.client('sns')
        
        # Configuration
        self.entity_completion_topic_arn = os.environ.get('ENTITY_COMPLETION_TOPIC_ARN',
                                                         'arn:aws:sns:us-east-1:861276078413:comprehend-entity-completion')
        self.keyphrase_completion_topic_arn = os.environ.get('KEYPHRASE_COMPLETION_TOPIC_ARN',
                                                            'arn:aws:sns:us-east-1:861276078413:comprehend-keyphrase-completion')
        
        logger.info("✅ Comprehend Job Monitor initialized")
    
    def process_event(self, event, context):
        """Process scheduled event to check job statuses"""
        try:
            logger.info("Checking Comprehend job statuses...")
            
            # Check entity detection jobs
            entity_jobs = self.list_jobs('entities-detection')
            entity_notifications = self.process_jobs(entity_jobs, 'entities-detection')
            
            # Check key phrases detection jobs
            keyphrase_jobs = self.list_jobs('key-phrases-detection')
            keyphrase_notifications = self.process_jobs(keyphrase_jobs, 'key-phrases-detection')
            
            total_notifications = len(entity_notifications) + len(keyphrase_notifications)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Processed {total_notifications} job completion notifications',
                    'entity_notifications': len(entity_notifications),
                    'keyphrase_notifications': len(keyphrase_notifications)
                })
            }
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            raise
    
    def list_jobs(self, job_type: str) -> List[Dict]:
        """List recent jobs of specified type"""
        try:
            if job_type == 'entities-detection':
                # Get all recent jobs (not just IN_PROGRESS)
                response = self.comprehend_client.list_entities_detection_jobs(
                    MaxResults=100
                )
                return response.get('EntitiesDetectionJobPropertiesList', [])
            else:  # key-phrases-detection
                response = self.comprehend_client.list_key_phrases_detection_jobs(
                    MaxResults=100
                )
                return response.get('KeyPhrasesDetectionJobPropertiesList', [])
                
        except Exception as e:
            logger.error(f"Error listing {job_type} jobs: {e}")
            return []
    
    def process_jobs(self, jobs: List[Dict], job_type: str) -> List[Dict]:
        """Process jobs and send notifications for completed ones"""
        notifications = []
        
        for job in jobs:
            try:
                job_id = job.get('JobId')
                job_name = job.get('JobName')
                
                if not job_id or not job_name:
                    continue
                
                # Get current job status
                if job_type == 'entities-detection':
                    response = self.comprehend_client.describe_entities_detection_job(JobId=job_id)
                    job_properties = response['EntitiesDetectionJobProperties']
                else:  # key-phrases-detection
                    response = self.comprehend_client.describe_key_phrases_detection_job(JobId=job_id)
                    job_properties = response['KeyPhrasesDetectionJobProperties']
                
                current_status = job_properties.get('JobStatus')
                
                # If job is completed, send notification
                if current_status in ['COMPLETED', 'FAILED', 'STOPPED']:
                    notification = self.send_completion_notification(job_properties, job_type)
                    if notification:
                        notifications.append(notification)
                        
            except Exception as e:
                logger.error(f"Error processing job {job.get('JobId', 'unknown')}: {e}")
                continue
        
        return notifications
    
    def send_completion_notification(self, job_properties: Dict, job_type: str) -> Dict:
        """Send completion notification for a job"""
        try:
            job_id = job_properties.get('JobId')
            job_name = job_properties.get('JobName')
            job_status = job_properties.get('JobStatus')
            
            # Create notification message
            message = {
                'JobId': job_id,
                'JobName': job_name,
                'JobStatus': job_status,
                'JobType': job_type,
                'Timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Add additional job details
            if job_status == 'COMPLETED':
                if job_type == 'entities-detection':
                    message['OutputDataConfig'] = job_properties.get('OutputDataConfig', {})
                else:  # key-phrases-detection
                    message['OutputDataConfig'] = job_properties.get('OutputDataConfig', {})
            elif job_status in ['FAILED', 'STOPPED']:
                message['Message'] = job_properties.get('Message', 'Job failed')
            
            # Determine target topic
            topic_arn = (self.entity_completion_topic_arn if job_type == 'entities-detection' 
                        else self.keyphrase_completion_topic_arn)
            
            # Send notification
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message, default=str),
                Subject=f"Comprehend {job_type} job {job_status.lower()}: {job_name}"
            )
            
            logger.info(f"Sent completion notification for {job_name} ({job_status}): {response['MessageId']}")
            
            return {
                'job_id': job_id,
                'job_name': job_name,
                'job_status': job_status,
                'message_id': response['MessageId']
            }
            
        except Exception as e:
            logger.error(f"Error sending notification for job {job_properties.get('JobId', 'unknown')}: {e}")
            return None
