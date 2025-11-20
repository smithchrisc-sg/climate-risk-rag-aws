#!/usr/bin/env python3
import requests
import json
import time

def test_vpc_fix():
    """Test if VPC configuration fixed the timeout issue"""
    
    api_url = "https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search"
    
    payload = {
        'query': 'climate risk North Macedonia',
        'filters': {},
        'parameters': {'limit': 5}
    }
    
    print("🧪 Testing VPC-enabled Lambda...")
    print(f"📡 Endpoint: {api_url}")
    print(f"🔍 Query: {payload['query']}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=45)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'infrastructure_status' in data:
                status = data['infrastructure_status']
                print(f"🏗️  Infrastructure Status: {status}")
                
                if status == 'phase1_success':
                    print("✅ SUCCESS: Phase 1 infrastructure connected!")
                    print(f"📈 Results: {data['pagination']['returned_results']}")
                    
                    if data['results']:
                        result = data['results'][0]
                        print(f"📄 First Result: {result['title']}")
                        print(f"⭐ Score: {result['score']}")
                        
                elif status == 'phase1_error':
                    print("⚠️  Phase 1 connection attempted but failed")
                    if 'results' in data and data['results']:
                        error_details = data['results'][0].get('metadata', {}).get('error_details', 'Unknown error')
                        print(f"❌ Error: {error_details}")
                        
                elif status == 'phase1_connecting':
                    print("🔄 Phase 1 still connecting...")
                    
            else:
                print("⚠️  No infrastructure status in response")
                print(f"Response keys: {list(data.keys())}")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - VPC configuration may still be in progress")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("🔧 Testing VPC fix for Lambda timeout issue...")
    
    # Wait for Lambda to be ready
    print("⏳ Waiting for Lambda VPC configuration to complete...")
    time.sleep(60)
    
    success = test_vpc_fix()
    
    if success:
        print("\n✅ VPC fix test completed!")
    else:
        print("\n❌ VPC fix test failed - may need more time")
        print("💡 Try running this test again in a few minutes")
