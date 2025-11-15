#!/usr/bin/env python3
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
import sys

def execute_sparql_query(query, query_type="query"):
    """Execute SPARQL query with AWS signing"""
    neptune_endpoint = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182/sparql"
    
    session = boto3.Session()
    credentials = session.get_credentials()
    
    content_type = "application/sparql-query" if query_type == "query" else "application/sparql-update"
    
    request = AWSRequest(
        method='POST',
        url=neptune_endpoint,
        data=query,
        headers={'Content-Type': content_type}
    )
    
    SigV4Auth(credentials, 'neptune-db', 'us-east-1').add_auth(request)
    
    response = requests.post(
        request.url,
        data=request.body,
        headers=dict(request.headers)
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
    if query_type == "query":
        return response.json()
    return response.text

def step1_count_current_triples():
    """Count current dcterms:spatial triples with wrong namespace"""
    query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT (COUNT(*) AS ?count) WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "http://www.geonames.org/ontology#"))
    }
    """
    
    print("Step 1: Counting current triples with wrong namespace...")
    result = execute_sparql_query(query)
    if result:
        count = result['results']['bindings'][0]['count']['value']
        print(f"Found {count} triples to fix")
        return int(count)
    return 0

def step2_preview_changes():
    """Preview what changes will be made"""
    query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?s ?old_geo ?new_geo WHERE {
        ?s dcterms:spatial ?old_geo .
        FILTER(STRSTARTS(STR(?old_geo), "http://www.geonames.org/ontology#"))
        BIND(IRI(REPLACE(STR(?old_geo), "http://www.geonames.org/ontology#", "https://sws.geonames.org/")) AS ?new_geo)
    }
    LIMIT 10
    """
    
    print("\nStep 2: Preview of changes (first 10)...")
    result = execute_sparql_query(query)
    if result:
        for binding in result['results']['bindings']:
            old_uri = binding['old_geo']['value']
            new_uri = binding['new_geo']['value']
            print(f"  {old_uri} -> {new_uri}")
    
    return input("\nDo these changes look correct? (yes/no): ").lower() == 'yes'

def step3_backup_data():
    """Create backup of current spatial triples"""
    query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?s ?geo WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "http://www.geonames.org/ontology#"))
    }
    """
    
    print("\nStep 3: Creating backup...")
    result = execute_sparql_query(query)
    if result:
        with open('geonames_backup.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Backup saved to geonames_backup.json ({len(result['results']['bindings'])} triples)")
        return True
    return False

def step4_apply_fix():
    """Apply the namespace fix"""
    update_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    
    DELETE { ?s dcterms:spatial ?old_geo }
    INSERT { ?s dcterms:spatial ?new_geo }
    WHERE {
        ?s dcterms:spatial ?old_geo .
        FILTER(STRSTARTS(STR(?old_geo), "http://www.geonames.org/ontology#"))
        BIND(IRI(REPLACE(STR(?old_geo), "http://www.geonames.org/ontology#", "https://sws.geonames.org/")) AS ?new_geo)
    }
    """
    
    print("\nStep 4: Applying fix...")
    result = execute_sparql_query(update_query, "update")
    if result is not None:
        print("Update completed successfully")
        return True
    return False

def step5_verify_fix():
    """Verify the fix worked"""
    # Check old namespace count
    old_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT (COUNT(*) AS ?count) WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "http://www.geonames.org/ontology#"))
    }
    """
    
    # Check new namespace count
    new_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT (COUNT(*) AS ?count) WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/"))
    }
    """
    
    print("\nStep 5: Verifying fix...")
    
    old_result = execute_sparql_query(old_query)
    new_result = execute_sparql_query(new_query)
    
    if old_result and new_result:
        old_count = int(old_result['results']['bindings'][0]['count']['value'])
        new_count = int(new_result['results']['bindings'][0]['count']['value'])
        
        print(f"Old namespace triples remaining: {old_count}")
        print(f"New namespace triples created: {new_count}")
        
        return old_count == 0 and new_count > 0
    
    return False

def main():
    print("GeoNames Namespace Fix - Safe Migration")
    print("=" * 50)
    
    # Step 1: Count current triples
    original_count = step1_count_current_triples()
    if original_count == 0:
        print("No triples found to fix!")
        return
    
    # Step 2: Preview changes
    if not step2_preview_changes():
        print("Operation cancelled by user")
        return
    
    # Step 3: Create backup
    if not step3_backup_data():
        print("Failed to create backup - aborting")
        return
    
    # Step 4: Apply fix
    if not step4_apply_fix():
        print("Failed to apply fix - check backup file")
        return
    
    # Step 5: Verify
    if step5_verify_fix():
        print("\n✅ Fix completed successfully!")
        print("Backup file: geonames_backup.json")
    else:
        print("\n❌ Verification failed - check data manually")

if __name__ == "__main__":
    main()
