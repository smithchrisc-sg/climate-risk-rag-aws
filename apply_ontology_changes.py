#!/usr/bin/env python3
"""
Apply ontology changes to Neptune in correct order.
Usage: python3 apply_ontology_changes.py
"""

import sys
import time
import requests
import boto3
from boto3 import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

NEPTUNE_ENDPOINT = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
NEPTUNE_LOADER = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/loader"
S3_BUCKET = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
IAM_ROLE = "arn:aws:iam::861276078413:role/NeptuneLoadFromS3"
REGION = "us-east-1"

def run_sparql_update(query):
    """Execute SPARQL UPDATE query against Neptune."""
    session = Session()
    creds = session.get_credentials().get_frozen_credentials()
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = AWSRequest(method="POST", url=NEPTUNE_ENDPOINT, data={"update": query}, headers=headers)
    SigV4Auth(creds, "neptune-db", REGION).add_auth(r)
    
    resp = requests.post(NEPTUNE_ENDPOINT, headers=dict(r.headers.items()), data={"update": query})
    
    if resp.status_code != 200:
        raise Exception(f"SPARQL update failed: {resp.text}")
    
    return resp

def load_ttl_to_neptune(local_file, s3_key):
    """Parse TTL file and execute as SPARQL INSERT."""
    print(f"📥 Loading {local_file} into Neptune via SPARQL INSERT...")
    
    with open(local_file, 'r') as f:
        content = f.read()
    
    # Extract prefixes
    prefixes = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('@prefix'):
            # Convert @prefix to PREFIX for SPARQL
            # @prefix sg: <http://...> . -> PREFIX sg: <http://...>
            sparql_prefix = line.replace('@prefix', 'PREFIX').rstrip(' .')
            prefixes.append(sparql_prefix)
    
    # Get everything after prefixes as triples
    # Find where prefixes end (after last @prefix line)
    prefix_end = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('@prefix'):
            prefix_end = i + 1
    
    # Get triple content (skip comments and empty lines)
    triple_lines = []
    for line in lines[prefix_end:]:
        line = line.strip()
        if line and not line.startswith('#'):
            triple_lines.append(line)
    
    triple_block = '\n'.join(triple_lines)
    
    # Build INSERT query
    prefix_block = '\n'.join(prefixes)
    
    query = f"{prefix_block}\n\nINSERT DATA {{\n{triple_block}\n}}"
    
    print(f"   Executing INSERT...")
    print("DEBUG: Generated query (first 60 lines):")
    for i, line in enumerate(query.split('\n')[:60], 1):
        print(f"{i:3}: {line}")
    run_sparql_update(query)
    print(f"   ✅ Triples inserted successfully")

def parse_ttl_for_moves(filepath):
    """Extract taxonomy move queries from commented sections in TTL file."""
    moves = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    i = 0

def parse_sparql_file(filepath):
    """Parse SPARQL file and return list of queries."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract PREFIX declarations
    prefixes = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('PREFIX'):
            prefixes.append(line)
    
    prefix_block = '\n'.join(prefixes)
    
    # Split queries by semicolon
    queries = []
    current_query = []
    in_query = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments outside queries
        if not line or (line.startswith('#') and not in_query):
            continue
        
        # Skip PREFIX lines (already extracted)
        if line.startswith('PREFIX'):
            continue
        
        # Start of a query (DELETE, INSERT, or comment before query)
        if line.startswith(('DELETE', 'INSERT', '#')):
            in_query = True
        
        if in_query:
            current_query.append(line)
            
            # Query ends with semicolon
            if line.endswith(';'):
                query_text = '\n'.join(current_query)
                # Remove trailing semicolon and add prefixes
                query_text = query_text.rstrip(';').strip()
                queries.append(f"{prefix_block}\n\n{query_text}")
                current_query = []
                in_query = False
    
    return queries

def parse_ttl_for_moves(filepath):
    """Extract taxonomy move queries from commented sections in TTL file."""
    moves = []
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for move comments
        if line.startswith('# Move '):
            # Next two lines should be DELETE and INSERT
            if i + 2 < len(lines):
                delete_line = lines[i + 1].strip()
                insert_line = lines[i + 2].strip()
                
                if delete_line.startswith('# DELETE') and insert_line.startswith('# INSERT'):
                    # Uncomment and combine into SPARQL UPDATE
                    delete_stmt = delete_line[2:].strip()  # Remove "# "
                    insert_stmt = insert_line[2:].strip()  # Remove "# "
                    
                    query = f"PREFIX sg: <http://solve.global/knowledge-commons/>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\n{delete_stmt}\n{insert_stmt}\nWHERE {{ {delete_stmt.replace('DELETE { ', '').replace(' }', '')} }}"
                    moves.append(query)
        
        i += 1
    
    return moves
    """Parse SPARQL file into individual queries."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split on semicolons (each query ends with ;)
    queries = []
    current = []
    
    for line in content.split('\n'):
        if line.strip().startswith('#'):
            continue  # Skip comments
        if line.strip().startswith('PREFIX'):
            if current:
                queries.append('\n'.join(current))
                current = []
            current.append(line)
        elif line.strip():
            current.append(line)
            if line.strip().endswith(';'):
                queries.append('\n'.join(current))
                current = []
    
    if current:
        queries.append('\n'.join(current))
    
    return [q.strip() for q in queries if q.strip() and not q.strip().startswith('#')]

def main():
    print("=" * 80)
    print("APPLYING ONTOLOGY CHANGES TO NEPTUNE")
    print("=" * 80)
    print()
    
    # Step 1: Load new taxonomy concepts
    print("STEP 1: Loading new taxonomy concepts (Additions)")
    print("-" * 80)
    try:
        # First, extract and execute taxonomy moves
        moves = parse_ttl_for_moves('risk_additions_FINAL.ttl')
        if moves:
            print(f"Found {len(moves)} taxonomy reparenting operations")
            for i, query in enumerate(moves, 1):
                print(f"   Executing move {i}/{len(moves)}...")
                run_sparql_update(query)
            print(f"✅ Taxonomy moves executed\n")
        
        # Then load new concepts
        load_ttl_to_neptune('risk_additions_FINAL.ttl', 'ontology/risk_additions_FINAL.ttl')
        print("✅ Additions loaded successfully\n")
    except FileNotFoundError:
        print("⚠️  risk_additions_FINAL.ttl not found - skipping\n")
    except Exception as e:
        print(f"❌ Error loading additions: {e}\n")
        sys.exit(1)
    
    # Step 2: Execute equivalents (remaps)
    print("STEP 2: Executing equivalents/remaps")
    print("-" * 80)
    try:
        queries = parse_sparql_file('risk_equivalents_remap_FINAL.sparql')
        print(f"Found {len(queries)} remap queries")
        
        for i, query in enumerate(queries, 1):
            if not query or not query.strip():
                continue
            print(f"   Executing query {i}/{len(queries)}...")
            run_sparql_update(query)
        
        print("✅ Equivalents executed successfully\n")
    except FileNotFoundError:
        print("⚠️  risk_equivalents_remap_FINAL.sparql not found - skipping\n")
    except Exception as e:
        print(f"❌ Error executing equivalents: {e}\n")
        sys.exit(1)
    
    # Step 3: Execute deletions
    print("STEP 3: Executing deletions")
    print("-" * 80)
    try:
        queries = parse_sparql_file('risk_irrelevant_remove_FINAL.sparql')
        print(f"Found {len(queries)} deletion queries")
        
        for i, query in enumerate(queries, 1):
            if not query or not query.strip():
                continue
            print(f"   Executing query {i}/{len(queries)}...")
            run_sparql_update(query)
        
        print("✅ Deletions executed successfully\n")
    except FileNotFoundError:
        print("⚠️  risk_irrelevant_remove_FINAL.sparql not found - skipping\n")
    except Exception as e:
        print(f"❌ Error executing deletions: {e}\n")
        sys.exit(1)
    
    # Step 4: Validation
    print("STEP 4: Validation")
    print("-" * 80)
    print("Checking for riskless solutions...")
    
    validation_query = """
    PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
    PREFIX sg: <http://solve.global/knowledge-commons/>
    
    SELECT (COUNT(DISTINCT ?solution) AS ?count)
    WHERE {
      ?solution a sgd:Solution .
      FILTER NOT EXISTS { ?solution sg:addressesRisk ?risk }
    }
    """
    
    try:
        session = Session()
        creds = session.get_credentials().get_frozen_credentials()
        
        r = AWSRequest(method="POST", url=NEPTUNE_ENDPOINT, data={"query": validation_query})
        SigV4Auth(creds, "neptune-db", REGION).add_auth(r)
        
        resp = requests.post(NEPTUNE_ENDPOINT, headers=dict(r.headers.items()), data={"query": validation_query})
        result = resp.json()
        
        count = int(result['results']['bindings'][0]['count']['value'])
        
        if count == 0:
            print(f"✅ Validation passed: No riskless solutions")
        else:
            print(f"⚠️  WARNING: {count} solutions have no risks!")
        
    except Exception as e:
        print(f"⚠️  Validation query failed: {e}")
    
    print()
    print("=" * 80)
    print("ONTOLOGY CHANGES APPLIED SUCCESSFULLY")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Regenerate CSV: python3 generate_risk_classification_csv.py")
    print("2. Test search with updated taxonomy")
    print("3. Continue with next category")

if __name__ == '__main__':
    main()
