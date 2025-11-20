#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys
import json

def load_ttl_to_neptune(ttl_file_path):
    # Neptune loader endpoint (not SPARQL)
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/loader"
    
    # Upload TTL to S3 first
    s3_client = boto3.client('s3')
    bucket = 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1'
    key = f"manual-upload/{ttl_file_path.split('/')[-1]}"
    
    print(f"Uploading {ttl_file_path} to s3://{bucket}/{key}")
    s3_client.upload_file(ttl_file_path, bucket, key)
    
    # Create loader request
    loader_payload = {
        "source": f"s3://{bucket}/{key}",
        "format": "turtle",
        "iamRoleArn": "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role",
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "MEDIUM",
        "updateSingleCardinalityProperties": "FALSE"
    }
    
    # Create AWS session and credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Create the request
    request = AWSRequest(
        method='POST',
        url=neptune_endpoint,
        data=json.dumps(loader_payload),
        headers={
            'Content-Type': 'application/json'
        }
    )
    
    # Sign the request
    SigV4Auth(credentials, 'neptune-db', 'us-east-1').add_auth(request)
    
    # Send the request
    response = requests.post(
        request.url,
        data=request.body,
        headers=dict(request.headers)
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    return response.status_code == 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_ttl_to_neptune.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_ttl_to_neptune(ttl_file)
    sys.exit(0 if success else 1)
