#!/usr/bin/env python3
"""
Load geonames ontology files into Neptune using the bulk loader API
"""

import requests
import json
import time
import sys

def load_to_neptune(neptune_endpoint, s3_uri, named_graph=None, format_type='turtle'):
    """
    Load data into Neptune using the bulk loader API
    
    Args:
        neptune_endpoint: Neptune cluster endpoint
        s3_uri: S3 URI of the file to load
        named_graph: Optional named graph URI
        format_type: Data format (turtle, rdfxml, etc.)
    """
    
    loader_endpoint = f"https://{neptune_endpoint}:8182/loader"
    
    # Prepare the payload
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
    
    if named_graph:
        payload["namedGraphUri"] = named_graph
    
    print(f"Loading {s3_uri} into Neptune...")
    if named_graph:
        print(f"Target named graph: {named_graph}")
    
    try:
        # Start the load job
        response = requests.post(
            loader_endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            load_id = result.get('payload', {}).get('loadId')
            print(f"✅ Load job started successfully!")
            print(f"Load ID: {load_id}")
            
            # Monitor the job
            if load_id:
                monitor_load_job(neptune_endpoint, load_id)
            
            return True
        else:
            print(f"❌ Failed to start load job: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False

def monitor_load_job(neptune_endpoint, load_id):
    """Monitor a Neptune load job until completion"""
    
    status_endpoint = f"https://{neptune_endpoint}:8182/loader/{load_id}"
    
    print(f"Monitoring load job {load_id}...")
    
    while True:
        try:
            response = requests.get(status_endpoint, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('payload', {}).get('overallStatus', {}).get('status', 'UNKNOWN')
                
                print(f"Status: {status}")
                
                if status in ['LOAD_COMPLETED']:
                    print("✅ Load completed successfully!")
                    
                    # Print summary
                    stats = result.get('payload', {}).get('overallStatus', {})
                    if 'totalRecords' in stats:
                        print(f"Total records: {stats['totalRecords']}")
                    if 'totalDuplicates' in stats:
                        print(f"Total duplicates: {stats['totalDuplicates']}")
                    
                    break
                elif status in ['LOAD_FAILED', 'LOAD_CANCELLED']:
                    print(f"❌ Load failed with status: {status}")
                    
                    # Print error details
                    errors = result.get('payload', {}).get('overallStatus', {}).get('errors', [])
                    for error in errors[:5]:  # Show first 5 errors
                        print(f"Error: {error}")
                    
                    break
                elif status in ['LOAD_IN_PROGRESS']:
                    # Show progress if available
                    progress = result.get('payload', {}).get('overallStatus', {})
                    if 'totalRecords' in progress:
                        print(f"Progress: {progress.get('totalRecords', 0)} records processed")
                    
                    time.sleep(10)  # Wait 10 seconds before checking again
                else:
                    print(f"Status: {status}, waiting...")
                    time.sleep(5)
            else:
                print(f"Failed to get status: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error checking status: {e}")
            time.sleep(5)

if __name__ == "__main__":
    neptune_endpoint = "solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    
    # Load geonames ontology schema
    print("=== Loading Geonames Ontology Schema ===")
    schema_success = load_to_neptune(
        neptune_endpoint=neptune_endpoint,
        s3_uri="s3://solve-global-kr-dl-neptune-ttl-861276078413-us-east-1/geonames_ontology_v3.3.ttl",
        named_graph="http://www.geonames.org/ontology",
        format_type="turtle"
    )
    
    if schema_success:
        print("\n=== Loading Geonames Administrative Data ===")
        data_success = load_to_neptune(
            neptune_endpoint=neptune_endpoint,
            s3_uri="s3://solve-global-kr-dl-neptune-ttl-861276078413-us-east-1/geonames-adm-features-from_2020-02-14.ttl",
            named_graph="http://www.geonames.org/ontology/data",
            format_type="turtle"
        )
        
        if data_success:
            print("\n🎉 Both ontology files loaded successfully!")
            print("\nNext steps:")
            print("1. Check CloudWatch logs for Neptune stream processing")
            print("2. Verify FTS indexing in OpenSearch")
            print("3. Test FTS queries in Jupyter notebook")
        else:
            print("\n❌ Failed to load geonames data")
    else:
        print("\n❌ Failed to load geonames schema")
