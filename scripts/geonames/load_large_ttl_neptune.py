#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
import time
import sys

def load_large_ttl_to_neptune(ttl_file_path):
    """Load large TTL file via Neptune bulk loader (most efficient for 35K+ lines)"""
    
    # Upload TTL to S3 first
    s3_client = boto3.client('s3')
    bucket = 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1'
    key = f"country-data/{ttl_file_path.split('/')[-1]}"
    
    print(f"Uploading {ttl_file_path} to s3://{bucket}/{key}")
    s3_client.upload_file(ttl_file_path, bucket, key)
    print("Upload complete")
    
    # Create Neptune loader job
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/loader"
    
    loader_payload = {
        "source": f"s3://{bucket}/{key}",
        "format": "turtle", 
        "iamRoleArn": "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role",
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "HIGH",  # Use HIGH for large files
        "updateSingleCardinalityProperties": "FALSE",
        "queueRequest": "TRUE"  # Queue for large loads
    }
    
    # Sign and send request
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method='POST',
        url=neptune_endpoint,
        data=json.dumps(loader_payload),
        headers={'Content-Type': 'application/json'}
    )
    
    SigV4Auth(credentials, 'neptune-db', 'us-east-1').add_auth(request)
    
    response = requests.post(
        request.url,
        data=request.body,
        headers=dict(request.headers)
    )
    
    if response.status_code == 200:
        result = response.json()
        load_id = result['payload']['loadId']
        print(f"Load job started: {load_id}")
        
        # Monitor progress
        monitor_load_progress(load_id)
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

def monitor_load_progress(load_id):
    """Monitor Neptune load job progress"""
    status_endpoint = f"https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/loader/{load_id}"
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    print("Monitoring load progress...")
    while True:
        request = AWSRequest(method='GET', url=status_endpoint)
        SigV4Auth(credentials, 'neptune-db', 'us-east-1').add_auth(request)
        
        response = requests.get(request.url, headers=dict(request.headers))
        
        if response.status_code == 200:
            status = response.json()
            overall_status = status['payload']['overallStatus']['status']
            
            print(f"Status: {overall_status}")
            
            if overall_status in ['LOAD_COMPLETED', 'LOAD_FAILED', 'LOAD_CANCELLED']:
                print(f"Final status: {overall_status}")
                if overall_status == 'LOAD_COMPLETED':
                    print("✅ Country data loaded successfully!")
                else:
                    print(f"❌ Load failed: {status}")
                break
        
        time.sleep(10)  # Check every 10 seconds

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_large_ttl_neptune.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_large_ttl_to_neptune(ttl_file)
    sys.exit(0 if success else 1)
