#!/usr/bin/env python3
"""
Check current Neptune load job status and clear any stuck jobs.
"""

import requests
from requests_aws4auth import AWS4Auth
import boto3
import json
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

def check_all_loads():
    """Check all Neptune load jobs."""
    loader_endpoint = f"{_BASE}/loader"
    
    try:
        auth = get_aws_auth()
        resp = requests.get(loader_endpoint, auth=auth, timeout=30)
        
        if resp.status_code == 200:
            result = resp.json()
            loads = result.get("payload", {}).get("loadIds", [])
            
            print(f"🔍 Found {len(loads)} load jobs:")
            
            for load_id in loads:
                check_load_status(load_id)
                print("-" * 50)
                
        else:
            print(f"❌ Failed to get load list: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"❌ Error checking loads: {e}")

def check_load_status(load_id):
    """Check specific load job status."""
    status_endpoint = f"{_BASE}/loader/{load_id}"
    
    try:
        auth = get_aws_auth()
        resp = requests.get(status_endpoint, auth=auth, timeout=30)
        
        if resp.status_code == 200:
            status_data = resp.json()
            payload = status_data.get("payload", {})
            
            overall_status = payload.get("overallStatus", {})
            status = overall_status.get("status", "UNKNOWN")
            records = overall_status.get("totalRecords", 0)
            time_spent = overall_status.get("totalTimeSpent", 0)
            
            print(f"📊 Load ID: {load_id}")
            print(f"   Status: {status}")
            print(f"   Records: {records:,}")
            print(f"   Time: {time_spent} ms")
            
            # Show source information
            feed = payload.get("feed", [])
            if feed:
                for item in feed[:2]:  # Show first 2 sources
                    source = item.get("source", "Unknown")
                    print(f"   Source: {source}")
            
            # Show errors if any
            if status in ["LOAD_FAILED", "LOAD_CANCELLED"]:
                errors = payload.get("errorLogs", [])
                if errors:
                    print(f"   🚨 Errors:")
                    for error in errors[:3]:
                        print(f"      • {error}")
                        
        else:
            print(f"❌ Failed to get status for {load_id}: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Error checking load {load_id}: {e}")

def cancel_load(load_id):
    """Cancel a specific load job."""
    cancel_endpoint = f"{_BASE}/loader/{load_id}"
    
    try:
        auth = get_aws_auth()
        resp = requests.delete(cancel_endpoint, auth=auth, timeout=30)
        
        if resp.status_code == 200:
            print(f"✅ Successfully cancelled load {load_id}")
            return True
        else:
            print(f"❌ Failed to cancel load {load_id}: {resp.status_code} - {resp.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error cancelling load {load_id}: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking Neptune load jobs...")
    check_all_loads()
