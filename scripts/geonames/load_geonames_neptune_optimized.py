#!/usr/bin/env python3
"""
Optimized Neptune bulk loader for large datasets with IAM authentication.
Addresses timeout and connection issues when loading 6M+ triples.
"""

import json
import time
import requests
from requests_aws4auth import AWS4Auth
import boto3
from datetime import datetime

# Configuration
_REGION = "us-east-1"
_BASE = "https://solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com:8182"

def get_aws_auth():
    """Get fresh AWS credentials for SigV4 signing."""
    session = boto3.Session()
    credentials = session.get_credentials()
    return AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        _REGION,
        'neptune-db',
        session_token=credentials.token
    )

def _signed_post(url, data, region, timeout=300, content_type="application/json", accept="application/json"):
    """Make signed POST request with fresh credentials."""
    auth = get_aws_auth()
    headers = {
        'Content-Type': content_type,
        'Accept': accept
    }
    
    response = requests.post(
        url,
        data=data,
        headers=headers,
        auth=auth,
        timeout=timeout
    )
    return response

def _signed_get(url, region, timeout=60):
    """Make signed GET request with fresh credentials."""
    auth = get_aws_auth()
    response = requests.get(url, auth=auth, timeout=timeout)
    return response

def load_to_neptune_optimized(s3_uri, named_graph=None, format_type="turtle"):
    """
    Load data into Neptune using optimized settings for IAM auth and large datasets.
    
    Key optimizations:
    - Reduced parallelism to avoid overwhelming IAM auth
    - Increased timeout for large datasets
    - Better error handling and retry logic
    - Fresh credentials for each request
    """
    loader_endpoint = f"{_BASE}/loader"

    # Optimized payload for IAM auth + large datasets
    payload = {
        "source": s3_uri,
        "format": format_type,
        "iamRoleArn": "arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role",
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "LOW",  # Reduced from MEDIUM to avoid IAM auth overhead
        "updateSingleCardinalityProperties": "FALSE",
        "queueRequest": "TRUE",
        "dependencies": [],  # Ensure no dependency conflicts
        "userProvidedS3Configuration": {
            "region": "us-east-1"
        }
    }
    
    if named_graph:
        payload["parserConfiguration"] = {"namedGraphUri": named_graph}

    print(f"🚀 Loading {s3_uri} with optimized IAM auth settings...")
    if named_graph:
        print(f"📊 Into named graph: {named_graph}")
    print(f"⚙️  Parallelism: LOW (optimized for IAM auth)")
    print(f"🔐 Using IAM Role: NeptuneLoadFromS3Role")

    try:
        resp = _signed_post(
            loader_endpoint,
            json.dumps(payload),
            _REGION,
            timeout=120,  # Increased timeout for initial request
            content_type="application/json",
            accept="application/json",
        )

        if resp.status_code == 200:
            result = resp.json()
            load_id = result.get("payload", {}).get("loadId")
            print(f"✅ Load job started! Load ID: {load_id}")
            print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return load_id
        else:
            print(f"❌ Failed to start load: {resp.status_code}")
            print(f"📝 Response: {resp.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - Neptune may be busy or IAM auth is slow")
        return None
    except Exception as e:
        print(f"❌ Error starting load: {e}")
        return None

def monitor_load_status_enhanced(load_id, check_interval=30, max_wait_minutes=60):
    """
    Enhanced monitoring with better error handling for IAM auth.
    
    Args:
        load_id: Neptune load job ID
        check_interval: Seconds between status checks
        max_wait_minutes: Maximum time to wait before giving up
    """
    if not load_id:
        print("❌ No load ID provided")
        return False
        
    status_endpoint = f"{_BASE}/loader/{load_id}"
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    print(f"🔍 Monitoring load {load_id}...")
    print(f"⏱️  Check interval: {check_interval} seconds")
    print(f"⏰ Max wait time: {max_wait_minutes} minutes")
    
    while True:
        try:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                print(f"⏰ Timeout reached ({max_wait_minutes} minutes)")
                return False
                
            # Get fresh credentials for each status check
            resp = _signed_get(status_endpoint, _REGION, timeout=60)
            
            if resp.status_code == 200:
                status_data = resp.json()
                payload = status_data.get("payload", {})
                
                overall_status = payload.get("overallStatus", {})
                status = overall_status.get("status", "UNKNOWN")
                
                # Get detailed statistics
                stats = overall_status.get("totalTimeSpent", 0)
                records_loaded = overall_status.get("totalRecords", 0)
                
                print(f"📊 Status: {status} | Records: {records_loaded:,} | Time: {elapsed:.1f}s")
                
                if status == "LOAD_COMPLETED":
                    print(f"🎉 Load completed successfully!")
                    print(f"📈 Total records loaded: {records_loaded:,}")
                    print(f"⏱️  Total time: {elapsed:.1f} seconds")
                    return True
                elif status in ["LOAD_FAILED", "LOAD_CANCELLED"]:
                    print(f"❌ Load failed with status: {status}")
                    
                    # Print detailed error information
                    errors = payload.get("errorLogs", [])
                    if errors:
                        print("🔍 Error details:")
                        for error in errors[:3]:  # Show first 3 errors
                            print(f"   • {error}")
                    return False
                elif status in ["LOAD_IN_PROGRESS", "LOAD_DATA_IN_PROGRESS"]:
                    # Continue monitoring
                    pass
                else:
                    print(f"⚠️  Unknown status: {status}")
                    
            else:
                print(f"⚠️  Status check failed: {resp.status_code}")
                print(f"📝 Response: {resp.text}")
                
        except requests.exceptions.Timeout:
            print("⚠️  Status check timed out - retrying...")
        except Exception as e:
            print(f"⚠️  Error checking status: {e}")
            
        time.sleep(check_interval)

def load_geonames_with_retry(s3_uri, named_graph=None, max_retries=2):
    """
    Load geonames data with retry logic for IAM auth issues.
    
    Args:
        s3_uri: S3 URI of the geonames TTL file
        named_graph: Optional named graph URI
        max_retries: Maximum number of retry attempts
    """
    for attempt in range(max_retries + 1):
        print(f"\n🔄 Attempt {attempt + 1} of {max_retries + 1}")
        
        # Start the load
        load_id = load_to_neptune_optimized(s3_uri, named_graph)
        
        if not load_id:
            print(f"❌ Failed to start load on attempt {attempt + 1}")
            if attempt < max_retries:
                print("⏳ Waiting 60 seconds before retry...")
                time.sleep(60)
                continue
            else:
                print("❌ All attempts failed")
                return False
        
        # Monitor the load
        success = monitor_load_status_enhanced(load_id, check_interval=30, max_wait_minutes=90)
        
        if success:
            print(f"🎉 Load completed successfully on attempt {attempt + 1}")
            return True
        else:
            print(f"❌ Load failed on attempt {attempt + 1}")
            if attempt < max_retries:
                print("⏳ Waiting 120 seconds before retry...")
                time.sleep(120)
            else:
                print("❌ All attempts failed")
                return False

# Example usage
if __name__ == "__main__":
    # Example: Load geonames data
    s3_uri = "s3://solve-global-kr-dl-neptune-ttl-861276078413-us-east-1/geonames-adm-features-from_2020-02-14.ttl"
    named_graph = "http://geonames-ontology"
    
    print("🌍 Starting optimized geonames load with IAM authentication...")
    success = load_geonames_with_retry(s3_uri, named_graph, max_retries=2)
    
    if success:
        print("✅ Geonames data loaded successfully!")
    else:
        print("❌ Failed to load geonames data after all retries")
