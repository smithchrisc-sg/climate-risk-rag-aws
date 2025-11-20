#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys

def load_ttl_via_sparql(ttl_file_path):
    # Neptune SPARQL endpoint
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    # Read TTL file
    with open(ttl_file_path, 'r', encoding='utf-8') as f:
        ttl_data = f.read()
    
    # Create SPARQL INSERT DATA query
    sparql_query = f"""
    INSERT DATA {{
        {ttl_data}
    }}
    """
    
    # Create AWS session and credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Create the request
    request = AWSRequest(
        method='POST',
        url=neptune_endpoint,
        data=sparql_query,
        headers={
            'Content-Type': 'application/sparql-update'
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
        print("Usage: python load_ttl_via_sparql.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_ttl_via_sparql(ttl_file)
    sys.exit(0 if success else 1)
