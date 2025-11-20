#!/usr/bin/env python3
import requests
import json

def test_gaip_api():
    """Test GAIP API with generated keys"""
    
    # API endpoint
    api_url = "https://43l6kohmrf.execute-api.us-east-1.amazonaws.com/v1/search"
    
    # Load API keys
    try:
        with open('test_api_keys.json', 'r') as f:
            keys = json.load(f)
    except FileNotFoundError:
        print("❌ API keys not found. Run: python3 generate_api_keys.py")
        return
    
    # Test with admin key
    admin_key = keys['admin']
    
    # Test request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {admin_key}'
    }
    
    payload = {
        'query': 'climate risk North Macedonia',
        'filters': {
            'categories': ['climate', 'risk-assessment'],
            'regions': ['North Macedonia']
        },
        'parameters': {
            'limit': 10
        }
    }
    
    print("🧪 Testing GAIP API...")
    print(f"📡 Endpoint: {api_url}")
    print(f"🔑 Using admin key")
    print(f"🔍 Query: {payload['query']}")
    
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Test Successful!")
            print(f"📈 Results: {data['pagination']['returned_results']} of {data['pagination']['total_results']}")
            print(f"⏱️  Execution Time: {data['execution_time']}s")
            
            if data['results']:
                result = data['results'][0]
                print(f"\n📄 First Result:")
                print(f"   Title: {result['title']}")
                print(f"   Score: {result['score']}")
                print(f"   Categories: {', '.join(result['categories'])}")
                print(f"   Regions: {', '.join(result['regions'])}")
                print(f"   Search Types: {', '.join(result['metadata']['search_types'])}")
                print(f"   Matched Concepts: {', '.join(result['metadata']['matched_concepts'])}")
        else:
            print(f"❌ API Test Failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == '__main__':
    test_gaip_api()
