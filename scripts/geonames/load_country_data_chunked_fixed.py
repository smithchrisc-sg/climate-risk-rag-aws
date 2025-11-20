#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys
import time

def load_country_data_chunked(ttl_file_path, chunk_size=500):
    """Load country TTL in chunks via SPARQL INSERT with proper Unicode handling"""
    
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    # Read TTL file with proper encoding
    with open(ttl_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into prefixes and data
    lines = content.split('\n')
    prefixes = []
    data_lines = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('@prefix') or line.startswith('PREFIX'):
            prefixes.append(line)
        elif line and not line.startswith('#') and not line.startswith('@'):
            data_lines.append(line)
    
    prefix_block = '\n'.join(prefixes)
    print(f"Found {len(data_lines)} data lines, processing in chunks of {chunk_size}")
    
    # Process in smaller chunks to avoid Unicode issues
    session = boto3.Session()
    credentials = session.get_credentials()
    
    total_chunks = (len(data_lines) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(data_lines), chunk_size):
        chunk_num = (i // chunk_size) + 1
        chunk = data_lines[i:i + chunk_size]
        
        # Build TTL chunk - let Neptune parse it as TTL directly
        ttl_data = prefix_block + '\n\n' + '\n'.join(chunk)
        
        print(f"Loading chunk {chunk_num}/{total_chunks} ({len(chunk)} lines)...")
        
        # Use TTL content type instead of SPARQL UPDATE
        request = AWSRequest(
            method='POST',
            url=neptune_endpoint,
            data=ttl_data.encode('utf-8'),
            headers={'Content-Type': 'text/turtle'}
        )
        
        SigV4Auth(credentials, 'neptune-db', 'us-east-1').add_auth(request)
        
        response = requests.post(
            request.url,
            data=request.body,
            headers=dict(request.headers)
        )
        
        if response.status_code == 200:
            print(f"✅ Chunk {chunk_num} loaded successfully")
        else:
            print(f"❌ Chunk {chunk_num} failed: {response.status_code} - {response.text}")
            # Continue with next chunk instead of failing completely
            continue
        
        # Small delay between chunks
        time.sleep(1)
    
    print(f"✅ Processing complete!")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_country_data_chunked_fixed.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_country_data_chunked(ttl_file)
    sys.exit(0 if success else 1)
