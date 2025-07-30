#!/usr/bin/env python3
"""
Test SNS Notifications for Comprehend Jobs
"""
import boto3
import json
import time
from datetime import datetime

def test_sns_notifications():
    """Test that the next Comprehend job will use SNS notifications"""
    
    print("🧪 TESTING SNS NOTIFICATIONS FOR COMPREHEND JOBS")
    print("=" * 55)
    
    # Check current queue depths
    sqs_client = boto3.client('sqs')
    queues = [
        'nlp-worker-entity-queue',
        'nlp-worker-keyphrase-queue'
    ]
    
    print("📊 Current SQS Queue Depths:")
    initial_counts = {}
    for queue_name in queues:
        queue_url = f"https://sqs.us-east-1.amazonaws.com/861276078413/{queue_name}"
        try:
            response = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            count = int(response['Attributes']['ApproximateNumberOfMessages'])
            initial_counts[queue_name] = count
            print(f"   - {queue_name}: {count} messages")
        except Exception as e:
            print(f"   ❌ Error checking {queue_name}: {e}")
            initial_counts[queue_name] = 0
    
    # Check recent Comprehend jobs to see if any are running
    comprehend_client = boto3.client('comprehend')
    
    print(f"\n🔍 Recent Comprehend Jobs:")
    try:
        # Check entity detection jobs
        entity_response = comprehend_client.list_entities_detection_jobs(MaxResults=3)
        entity_jobs = entity_response.get('EntitiesDetectionJobPropertiesList', [])
        
        print("   Entity Detection Jobs:")
        for job in entity_jobs[:3]:
            status = job.get('JobStatus', 'UNKNOWN')
            job_name = job.get('JobName', 'Unknown')
            submit_time = job.get('SubmitTime', 'Unknown')
            print(f"     - {job_name}: {status} (submitted: {submit_time})")
        
        # Check key phrases jobs
        phrases_response = comprehend_client.list_key_phrases_detection_jobs(MaxResults=3)
        phrases_jobs = phrases_response.get('KeyPhrasesDetectionJobPropertiesList', [])
        
        print("   Key Phrases Detection Jobs:")
        for job in phrases_jobs[:3]:
            status = job.get('JobStatus', 'UNKNOWN')
            job_name = job.get('JobName', 'Unknown')
            submit_time = job.get('SubmitTime', 'Unknown')
            print(f"     - {job_name}: {status} (submitted: {submit_time})")
            
    except Exception as e:
        print(f"   ❌ Error checking Comprehend jobs: {e}")
    
    print(f"\n🎯 TESTING INSTRUCTIONS:")
    print("1. Run a document through the pipeline:")
    print("   - Upload a document to trigger text extraction")
    print("   - Wait for text chunking to complete")
    print("   - nlp-initiator will start Comprehend jobs with SNS config")
    print()
    print("2. Monitor for SNS notifications:")
    print("   - Watch SQS queue depths increase when jobs complete")
    print("   - Check CloudWatch logs for nlp-worker functions")
    print("   - Verify immediate processing (no 2-minute delay)")
    print()
    print("3. Verify job configuration:")
    print("   - Check that new Comprehend jobs include NotificationConfig")
    print("   - Confirm SNS topics receive completion messages")
    print()
    print("📋 Expected Behavior:")
    print("   - Comprehend job completes → SNS notification → SQS message → Lambda trigger")
    print("   - Processing should be IMMEDIATE (not delayed by polling)")
    print()
    print("🚨 If SNS doesn't work:")
    print("   - Check CloudWatch logs for nlp-initiator errors")
    print("   - Verify Comprehend job includes NotificationConfig")
    print("   - Check SNS topic permissions")
    print("   - Restore from lambda-DEPRECATED/comprehend-monitor if needed")

if __name__ == "__main__":
    test_sns_notifications()
