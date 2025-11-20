#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys
import time
import os
import re

def split_and_load_countries(ttl_file_path):
    """Split TTL by country and load each individually"""
    
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    # Read TTL file
    with open(ttl_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract prefixes
    lines = content.split('\n')
    prefixes = []
    
    for line in lines:
        if line.strip().startswith('@prefix') or line.strip().startswith('PREFIX'):
            prefixes.append(line.strip())
    
    prefix_block = '\n'.join(prefixes)
    
    # Split by country (each starts with <https://sws.geonames.org/...)
    countries = re.split(r'\n(?=<https://sws\.geonames\.org/)', content)
    
    # Filter out prefix section
    country_data = [c for c in countries if c.strip().startswith('<https://sws.geonames.org/')]
    
    print(f"Found {len(country_data)} countries to load")
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    success_count = 0
    
    for i, country in enumerate(country_data, 1):
        # Extract country name for logging
        name_match = re.search(r'gn:name\s+"([^"]+)"', country)
        country_name = name_match.group(1) if name_match else f"Country {i}"
        
        print(f"Loading {i}/{len(country_data)}: {country_name}")
        
        # Build complete TTL for this country
        ttl_data = prefix_block + '\n\n' + country.strip()
        
        # Create SPARQL INSERT query
        sparql_query = f"""
        {prefix_block}
        
        INSERT DATA {{
            GRAPH <http://www.geonames.org/ontology/data> {{
                {country.strip()}
            }}
        }}
        """
        
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
            print(f"✅ {country_name} loaded successfully")
            success_count += 1
        else:
            print(f"❌ {country_name} failed: {response.status_code} - {response.text}")
        
        # Small delay between loads
        time.sleep(0.2)
    
    print(f"✅ Completed: {success_count}/{len(country_data)} countries loaded successfully")
    return success_count > 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python split_and_load_countries.py <ttl_file>")
        sys.exit(1)
    
    ttl_file = sys.argv[1]
    success = split_and_load_countries(ttl_file)
    sys.exit(0 if success else 1)
