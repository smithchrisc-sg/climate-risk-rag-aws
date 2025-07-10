#!/usr/bin/env python3
"""
Async Neptune Bulk Loader - Job Initiator
Kicks off Neptune bulk loading jobs and publishes completion events
"""

import json
import urllib3
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Lambda function to initiate Neptune bulk loading jobs asynchronously"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    loader_endpoint = f"https://{neptune_endpoint}:8182/loader"
    
    ttl_bucket = "solve-global-kr-neptune-ttl-861276078413-us-east-1"
    neptune_load_role = "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role"
    
    # SNS topic for job completion notifications
    completion_topic_arn = "arn:aws:sns:us-east-1:861276078413:neptune-bulk-load-jobs"
    
    doc_id = event.get('doc_id', '0032f6cb_f0caef34')
    load_type = event.get('load_type', 'document')  # 'schema' or 'document'
    
    http = urllib3.PoolManager()
    sns = boto3.client('sns', region_name='us-east-1')
    
    result = {
        'doc_id': doc_id,
        'load_type': load_type,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Determine S3 source path based on load type
        if load_type == 'schema':
            s3_source = f"s3://{ttl_bucket}/ontology/"
            job_name = f"schema-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        else:
            s3_source = f"s3://{ttl_bucket}/documents/{doc_id}/"
            job_name = f"document-{doc_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Create bulk load request
        load_request = {
            "source": s3_source,
            "format": "turtle",
            "iamRoleArn": neptune_load_role,
            "region": "us-east-1",
            "failOnError": "FALSE",
            "parallelism": "MEDIUM",
            "updateSingleCardinalityProperties": "FALSE",
            "queueRequest": "TRUE"
        }
        
        # Submit bulk load job
        response = http.request(
            'POST',
            loader_endpoint,
            body=json.dumps(load_request),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status == 200:
            load_result = json.loads(response.data.decode('utf-8'))
            load_id = load_result['payload']['loadId']
            
            result.update({
                'success': True,
                'load_id': load_id,
                'job_name': job_name,
                's3_source': s3_source,
                'status': 'SUBMITTED'
            })
            
            # Publish job submission notification
            job_message = {
                'action': 'JOB_SUBMITTED',
                'load_id': load_id,
                'doc_id': doc_id,
                'load_type': load_type,
                'job_name': job_name,
                's3_source': s3_source,
                'submitted_at': datetime.now().isoformat()
            }
            
            try:
                sns.publish(
                    TopicArn=completion_topic_arn,
                    Message=json.dumps(job_message),
                    Subject=f"Neptune Bulk Load Job Submitted: {job_name}"
                )
                result['notification_sent'] = True
            except Exception as e:
                result['notification_error'] = str(e)
            
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
        'doc_id': '0032f6cb_f0caef34',
        'load_type': 'document'
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "neptune-bulk-loader-async"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
