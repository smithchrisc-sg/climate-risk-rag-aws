#!/usr/bin/env python3
import boto3
import json
import sys

def load_ttl_via_lambda(ttl_file_path):
    # Upload TTL to S3 first
    s3_client = boto3.client('s3')
    bucket = 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1'
    key = f"manual-upload/{ttl_file_path.split('/')[-1]}"
    
    print(f"Uploading {ttl_file_path} to s3://{bucket}/{key}")
    s3_client.upload_file(ttl_file_path, bucket, key)
    
    # Invoke the kg-triple-loader Lambda
    lambda_client = boto3.client('lambda')
    
    payload = {
        "s3_bucket": bucket,
        "s3_key": key,
        "format": "turtle"
    }
    
    print(f"Invoking kg-triple-loader Lambda...")
    response = lambda_client.invoke(
        FunctionName='kg-triple-loader',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Lambda response: {result}")
    
    return response['StatusCode'] == 200

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_ttl_via_lambda.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_ttl_via_lambda(ttl_file)
    sys.exit(0 if success else 1)
