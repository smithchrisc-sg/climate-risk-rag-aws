"""
Commands to run in a Jupyter notebook with VPC access to Neptune
Copy and paste these into your Neptune notebook to load the geonames data
"""

import requests
import json
import time

# Neptune configuration
NEPTUNE_ENDPOINT = "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
NEPTUNE_PORT = 8182

def load_to_neptune(s3_uri, named_graph=None, format_type='turtle'):
    """Load data into Neptune using the bulk loader API"""
    
    loader_endpoint = f"https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/loader"
    
    payload = {
        "source": s3_uri,
        "format": format_type,
        "iamRoleArn": "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role",
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "MEDIUM",
        "updateSingleCardinalityProperties": "FALSE",
        "queueRequest": "TRUE"
    }
    
    # Add named graph configuration if specified
    if named_graph:
        payload["parserConfiguration"] = {
            "namedGraphUri": named_graph
        }
    
    print(f"Loading {s3_uri}...")
    if named_graph:
        print(f"Into named graph: {named_graph}")
    
    response = requests.post(
        loader_endpoint,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        load_id = result.get('payload', {}).get('loadId')
        print(f"✅ Load job started! Load ID: {load_id}")
        return load_id
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return None

def check_load_status(load_id):
    """Check the status of a load job"""
    
    status_endpoint = f"https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/loader/{load_id}"
    
    response = requests.get(status_endpoint, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        status = result.get('payload', {}).get('overallStatus', {}).get('status', 'UNKNOWN')
        print(f"Status: {status}")
        
        if status == 'LOAD_COMPLETED':
            stats = result.get('payload', {}).get('overallStatus', {})
            print(f"✅ Completed! Records: {stats.get('totalRecords', 'N/A')}")
        elif status in ['LOAD_FAILED', 'LOAD_CANCELLED']:
            print(f"❌ Failed with status: {status}")
            errors = result.get('payload', {}).get('overallStatus', {}).get('errors', [])
            for error in errors[:3]:
                print(f"Error: {error}")
        
        return status
    else:
        print(f"Failed to get status: {response.status_code}")
        return None

# =============================================================================
# STEP 1: Load Geonames Ontology Schema
# =============================================================================

print("=== Loading Geonames Ontology Schema ===")
schema_load_id = load_to_neptune(
    s3_uri="s3://solve-global-kr-dl-neptune-ttl-861276078413-us-east-1/geonames_ontology_v3.3.ttl",
    named_graph="http://www.geonames.org/ontology",
    format_type="turtle"
)

# Wait and check status
if schema_load_id:
    print("Waiting for schema load to complete...")
    while True:
        status = check_load_status(schema_load_id)
        if status in ['LOAD_COMPLETED', 'LOAD_FAILED', 'LOAD_CANCELLED']:
            break
        time.sleep(10)

# =============================================================================
# STEP 2: Load Geonames Administrative Data  
# =============================================================================

print("\n=== Loading Geonames Administrative Data ===")
data_load_id = load_to_neptune(
    s3_uri="s3://solve-global-kr-dl-neptune-ttl-861276078413-us-east-1/geonames-adm-features-from_2020-02-14.ttl",
    named_graph="http://www.geonames.org/ontology/data",
    format_type="turtle"
)

# Wait and check status
if data_load_id:
    print("Waiting for data load to complete...")
    while True:
        status = check_load_status(data_load_id)
        if status in ['LOAD_COMPLETED', 'LOAD_FAILED', 'LOAD_CANCELLED']:
            break
        time.sleep(30)  # Check every 30 seconds for large file

print("\n🎉 Loading complete!")
print("\nNext steps:")
print("1. Check CloudWatch logs: /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3")
print("2. Verify FTS indexing in OpenSearch")
print("3. Test FTS queries")

# =============================================================================
# STEP 3: Test FTS Query (run after loading completes)
# =============================================================================

def test_fts_query(search_term="Jakarta"):
    """Test FTS query to verify the integration works"""
    
    sparql_endpoint = f"https://{NEPTUNE_ENDPOINT}:{NEPTUNE_PORT}/sparql"
    
    query = f"""
    PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    
    SELECT ?place ?name ?graph WHERE {{
        GRAPH ?graph {{
            ?place ?predicate ?name .
            FILTER(neptune-fts:query(neptune-fts:field('object'), '{search_term}'))
        }}
    }} LIMIT 10
    """
    
    response = requests.post(
        sparql_endpoint,
        data={'query': query},
        headers={'Accept': 'application/sparql-results+json'},
        timeout=30
    )
    
    if response.status_code == 200:
        results = response.json()
        bindings = results.get('results', {}).get('bindings', [])
        
        print(f"FTS Query Results for '{search_term}':")
        for binding in bindings:
            place = binding.get('place', {}).get('value', 'N/A')
            name = binding.get('name', {}).get('value', 'N/A')
            graph = binding.get('graph', {}).get('value', 'N/A')
            print(f"  {name} ({place}) in {graph}")
        
        return len(bindings)
    else:
        print(f"FTS query failed: {response.status_code} - {response.text}")
        return 0

# Uncomment to test FTS after loading:
# test_fts_query("Jakarta")
# test_fts_query("London")
# test_fts_query("Tokyo")
