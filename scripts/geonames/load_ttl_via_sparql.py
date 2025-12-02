#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import sys
import argparse

def load_ttl_via_sparql(ttl_file_path, named_graph=None):
    # Neptune SPARQL endpoint
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    # Read TTL file
    with open(ttl_file_path, 'r', encoding='utf-8') as f:
        ttl_data = f.read()
    
    # Common prefixes that might be missing
    common_prefixes = {
        'sgm': 'PREFIX sgm: <http://solve.global/knowledge-commons/process-metadata#>',
        'sg': 'PREFIX sg: <https://solve.global/ontology/>',
        'sgd': 'PREFIX sgd: <https://solve.global/data/>',
        'rdf': 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>',
        'rdfs': 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>',
        'owl': 'PREFIX owl: <http://www.w3.org/2002/07/owl#>',
        'xsd': 'PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>',
        'dcterms': 'PREFIX dcterms: <http://purl.org/dc/terms/>'
    }
    
    # Extract @prefix declarations and convert to SPARQL PREFIX
    prefixes = []
    declared_prefixes = set()
    ttl_lines = []
    
    for line in ttl_data.split('\n'):
        if line.strip().startswith('@prefix'):
            # Convert @prefix to SPARQL PREFIX
            # @prefix sg: <http://...> . -> PREFIX sg: <http://...>
            sparql_prefix = line.strip().replace('@prefix', 'PREFIX').rstrip(' .')
            prefixes.append(sparql_prefix)
            # Track which prefix was declared
            prefix_name = line.split()[1].rstrip(':')
            declared_prefixes.add(prefix_name)
        else:
            ttl_lines.append(line)
    
    # Add common prefixes that weren't declared but might be used
    for prefix_name, prefix_decl in common_prefixes.items():
        if prefix_name not in declared_prefixes:
            prefixes.insert(0, prefix_decl)
    
    # Rebuild TTL without @prefix lines
    clean_ttl = '\n'.join(ttl_lines)
    
    # Build SPARQL query with prefixes
    prefix_block = '\n'.join(prefixes)
    
    # Create SPARQL INSERT DATA query with optional named graph
    if named_graph:
        sparql_query = f"""
        {prefix_block}
        
        INSERT DATA {{
            GRAPH <{named_graph}> {{
                {clean_ttl}
            }}
        }}
        """
    else:
        sparql_query = f"""
        {prefix_block}
        
        INSERT DATA {{
            {clean_ttl}
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
    parser = argparse.ArgumentParser(description='Load TTL file to Neptune via SPARQL')
    parser.add_argument('ttl_file', help='Path to TTL file')
    parser.add_argument('--graph', '--named-graph', dest='named_graph', 
                        help='Named graph URI (e.g., http://solve.global/knowledge-commons/graph/ontology-alignment)')
    
    args = parser.parse_args()
    
    if args.named_graph:
        print(f"Loading {args.ttl_file} into named graph: {args.named_graph}")
    else:
        print(f"Loading {args.ttl_file} into default graph")
    
    success = load_ttl_via_sparql(args.ttl_file, args.named_graph)
    sys.exit(0 if success else 1)
