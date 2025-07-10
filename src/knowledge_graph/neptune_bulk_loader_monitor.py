#!/usr/bin/env python3
"""
Neptune Bulk Load Job Monitor
Checks status of Neptune bulk loading jobs and publishes completion events
"""

import json
import urllib3
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Lambda function to monitor Neptune bulk loading job status"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    loader_endpoint = f"https://{neptune_endpoint}:8182/loader"
    
    # SNS topic for job completion notifications
    completion_topic_arn = "arn:aws:sns:us-east-1:861276078413:neptune-bulk-load-jobs"
    
    # Can be triggered by EventBridge schedule or SNS message
    load_id = None
    
    # Check if triggered by SNS (from job submission)
    if 'Records' in event:
        for record in event['Records']:
            if record.get('EventSource') == 'aws:sns':
                sns_message = json.loads(record['Sns']['Message'])
                if sns_message.get('action') == 'JOB_SUBMITTED':
                    load_id = sns_message.get('load_id')
                    break
    
    # Check if load_id provided directly
    if not load_id:
        load_id = event.get('load_id')
    
    if not load_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No load_id provided'})
        }
    
    http = urllib3.PoolManager()
    sns = boto3.client('sns', region_name='us-east-1')
    
    result = {
        'load_id': load_id,
        'checked_at': datetime.now().isoformat()
    }
    
    try:
        # Check job status
        response = http.request(
            'GET',
            f"{loader_endpoint}/{load_id}",
            timeout=30
        )
        
        if response.status == 200:
            status_data = json.loads(response.data.decode('utf-8'))
            payload = status_data['payload']
            
            overall_status = payload['overallStatus']['status']
            
            result.update({
                'success': True,
                'status': overall_status,
                'details': payload
            })
            
            # Check if job is complete (success or failure)
            if overall_status in ['LOAD_COMPLETED', 'LOAD_FAILED', 'LOAD_CANCELLED']:
                
                # Extract job details
                job_details = {
                    'load_id': load_id,
                    'status': overall_status,
                    'completed_at': datetime.now().isoformat(),
                    'total_time_spent': payload.get('totalTimeSpent', 0),
                    'total_records': payload.get('totalRecords', 0),
                    'total_duplicates': payload.get('totalDuplicates', 0)
                }
                
                # Add error details if failed
                if overall_status in ['LOAD_FAILED', 'LOAD_CANCELLED']:
                    job_details['error_details'] = payload.get('errorDetails', [])
                
                # Publish completion notification
                completion_message = {
                    'action': 'JOB_COMPLETED',
                    'load_id': load_id,
                    'status': overall_status,
                    'success': overall_status == 'LOAD_COMPLETED',
                    'job_details': job_details
                }
                
                try:
                    sns.publish(
                        TopicArn=completion_topic_arn,
                        Message=json.dumps(completion_message, indent=2),
                        Subject=f"Neptune Bulk Load Job {overall_status}: {load_id}"
                    )
                    result['completion_notification_sent'] = True
                except Exception as e:
                    result['notification_error'] = str(e)
                
                result['job_complete'] = True
                
            else:
                # Job still in progress
                result['job_complete'] = False
                result['progress'] = {
                    'records_loaded': payload.get('totalRecords', 0),
                    'time_elapsed': payload.get('totalTimeSpent', 0)
                }
        else:
            result.update({
                'success': False,
                'status_code': response.status,
                'error': response.data.decode('utf-8')
            })
            
    except Exception as e:
        result.update({
            'success': False,
            'error': str(e)
        })
    
    return {
        'statusCode': 200 if result.get('success', False) else 500,
        'body': json.dumps(result, indent=2)
    }

# For testing locally
if __name__ == "__main__":
    # Test event
    test_event = {
        'load_id': 'test-load-id-123'
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "neptune-bulk-loader-monitor"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
