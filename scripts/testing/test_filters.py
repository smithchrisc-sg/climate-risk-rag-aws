#!/usr/bin/env python3
"""
Test script for filter functionality
"""
import requests
import json

API_ENDPOINT = "https://aels3baeae.execute-api.us-east-1.amazonaws.com/v2/search"

def test_filter(filter_name, filter_value, description):
    """Test a specific filter"""
    print(f"\n=== Testing {description} ===")
    
    payload = {
        "query": "risk management",
        "filters": {
            filter_name: [filter_value]
        },
        "parameters": {
            "max_results": 5
        }
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            solution_count = len(data.get('results', {}).get('solutions', []))
            print(f"Success: Found {solution_count} solutions")
            
            if solution_count > 0:
                first_solution = data['results']['solutions'][0]
                print(f"Sample solution: {first_solution.get('title', 'No title')}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

def test_no_filters():
    """Test search without filters"""
    print(f"\n=== Testing No Filters (Baseline) ===")
    
    payload = {
        "query": "risk management",
        "parameters": {
            "max_results": 5
        }
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            solution_count = len(data.get('results', {}).get('solutions', []))
            print(f"Success: Found {solution_count} solutions (no filters)")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    print("Testing GAIP Search API Filter Functionality")
    
    # Test baseline (no filters)
    test_no_filters()
    
    # Test solution category filters
    test_filter("solution_category", "health", "Solution Category: Health")
    test_filter("solution_category", "cyber", "Solution Category: Cyber")
    test_filter("solution_category", "natural-catastrophe", "Solution Category: Natural Catastrophe")
    
    # Test risk type filters
    test_filter("risk_type", "pandemic", "Risk Type: Pandemic")
    test_filter("risk_type", "cyber-attack", "Risk Type: Cyber Attack")
    test_filter("risk_type", "natural-disaster", "Risk Type: Natural Disaster")
    
    # Test solution type filters
    test_filter("solution_type", "prevention", "Solution Type: Prevention")
    test_filter("solution_type", "risk-financing", "Solution Type: Risk Financing")
    test_filter("solution_type", "regulation", "Solution Type: Regulation")
    
    # Test theme filters
    test_filter("theme", "technology", "Theme: Technology")
    test_filter("theme", "education", "Theme: Education")
    
    print(f"\nFilter testing complete!")
