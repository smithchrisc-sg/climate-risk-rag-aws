#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys
import time

def load_country_data_chunked(ttl_file_path, chunk_size=1000):
    """Load country TTL in chunks via SPARQL INSERT"""
    
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    # Read and parse TTL file
    with open(ttl_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Extract prefixes and data
    prefixes = []
    data_lines = []
    
    for line in lines:
        if line.strip().startswith('@prefix') or line.strip().startswith('PREFIX'):
            prefixes.append(line.strip())
        elif line.strip() and not line.strip().startswith('#'):
            data_lines.append(line.strip())
    
    prefix_block = '\n'.join(prefixes)
    print(f"Found {len(data_lines)} data lines, processing in chunks of {chunk_size}")
    
    # Process in chunks
    session = boto3.Session()
    credentials = session.get_credentials()
    
    total_chunks = (len(data_lines) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(data_lines), chunk_size):
        chunk_num = (i // chunk_size) + 1
        chunk = data_lines[i:i + chunk_size]
        
        # Build SPARQL INSERT query
        ttl_chunk = '\n'.join(chunk)
        sparql_query = f"""
        {prefix_block}
        
        INSERT DATA {{
            GRAPH <http://www.geonames.org/ontology/data> {{
                {ttl_chunk}
            }}
        }}
        """
        
        print(f"Loading chunk {chunk_num}/{total_chunks} ({len(chunk)} lines)...")
        
        # Execute query
        request = AWSRequest(
            method='POST',
            url=neptune_endpoint,
            data=sparql_query,
            headers={'Content-Type': 'application/sparql-update'}
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
            return False
        
        # Small delay between chunks
        time.sleep(0.5)
    
    print(f"✅ All {total_chunks} chunks loaded successfully!")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python load_country_data_chunked.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = load_country_data_chunked(ttl_file)
    sys.exit(0 if success else 1)
