#!/usr/bin/env python3
import boto3
import json
import sys

def load_country_data_via_lambda(ttl_file_path):
    """Load country TTL via existing kg-triple-loader Lambda (no production changes)"""
    
    # Upload TTL to S3 first
    s3_client = boto3.client('s3')
    bucket = 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1'
    key = f"country-data/{ttl_file_path.split('/')[-1]}"
    
    print(f"Uploading {ttl_file_path} to s3://{bucket}/{key}")
    s3_client.upload_file(ttl_file_path, bucket, key)
    print("Upload complete")
    
    # Invoke existing kg-triple-loader Lambda (has proper permissions)
    lambda_client = boto3.client('lambda')
    
    payload = {
        "s3_bucket": bucket,
        "s3_key": key,
        "format": "turtle"
    }
    
    print(f"Invoking existing kg-triple-loader Lambda...")
    
    response = lambda_client.invoke(
        FunctionName='kg-triple-loader',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    print(f"Lambda response: {json.dumps(result, indent=2)}")
    
    if response['StatusCode'] == 200:
        print("✅ Country data load job submitted successfully!")
        return True
    else:
        print("❌ Load job submission failed")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_country_data_via_lambda.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_country_data_via_lambda(ttl_file)
    sys.exit(0 if success else 1)
