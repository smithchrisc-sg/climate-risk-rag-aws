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

def step1_count_uris_without_slashes():
    """Count GeoNames URIs without trailing slashes"""
    query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT (COUNT(*) AS ?count) WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/") && !STRENDS(STR(?geo), "/"))
    }
    """
    
    print("Step 1: Counting GeoNames URIs without trailing slashes...")
    result = execute_sparql_query(query)
    if result:
        count = result['results']['bindings'][0]['count']['value']
        print(f"Found {count} URIs to fix")
        return int(count)
    return 0

def step2_preview_changes():
    """Preview what changes will be made"""
    query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?s ?old_geo ?new_geo WHERE {
        ?s dcterms:spatial ?old_geo .
        FILTER(STRSTARTS(STR(?old_geo), "https://sws.geonames.org/") && !STRENDS(STR(?old_geo), "/"))
        BIND(IRI(CONCAT(STR(?old_geo), "/")) AS ?new_geo)
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
        FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/") && !STRENDS(STR(?geo), "/"))
    }
    """
    
    print("\nStep 3: Creating backup...")
    result = execute_sparql_query(query)
    if result:
        with open('geonames_slash_backup.json', 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Backup saved to geonames_slash_backup.json ({len(result['results']['bindings'])} triples)")
        return True
    return False

def step4_apply_fix():
    """Apply the trailing slash fix"""
    update_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    
    DELETE { ?s dcterms:spatial ?old_geo }
    INSERT { ?s dcterms:spatial ?new_geo }
    WHERE {
        ?s dcterms:spatial ?old_geo .
        FILTER(STRSTARTS(STR(?old_geo), "https://sws.geonames.org/") && !STRENDS(STR(?old_geo), "/"))
        BIND(IRI(CONCAT(STR(?old_geo), "/")) AS ?new_geo)
    }
    """
    
    print("\nStep 4: Applying trailing slash fix...")
    result = execute_sparql_query(update_query, "update")
    if result is not None:
        print("Update completed successfully")
        return True
    return False

def step5_verify_fix():
    """Verify the fix worked"""
    # Check URIs without slashes
    without_slash_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT (COUNT(*) AS ?count) WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/") && !STRENDS(STR(?geo), "/"))
    }
    """
    
    # Check URIs with slashes
    with_slash_query = """
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT (COUNT(*) AS ?count) WHERE {
        ?s dcterms:spatial ?geo .
        FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/") && STRENDS(STR(?geo), "/"))
    }
    """
    
    print("\nStep 5: Verifying fix...")
    
    without_result = execute_sparql_query(without_slash_query)
    with_result = execute_sparql_query(with_slash_query)
    
    if without_result and with_result:
        without_count = int(without_result['results']['bindings'][0]['count']['value'])
        with_count = int(with_result['results']['bindings'][0]['count']['value'])
        
        print(f"URIs without trailing slash remaining: {without_count}")
        print(f"URIs with trailing slash: {with_count}")
        
        return without_count == 0 and with_count > 0
    
    return False

def main():
    print("GeoNames Trailing Slash Fix - Safe Migration")
    print("=" * 50)
    print("(Thanks to Ora Lassila and the old RDF/XML days! 😅)")
    print()
    
    # Step 1: Count current URIs
    original_count = step1_count_uris_without_slashes()
    if original_count == 0:
        print("No URIs found to fix!")
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
        print("\n✅ Trailing slash fix completed successfully!")
        print("Backup file: geonames_slash_backup.json")
        print("Now you just need to load the country-level GeoNames data...")
    else:
        print("\n❌ Verification failed - check data manually")

if __name__ == "__main__":
    main()
