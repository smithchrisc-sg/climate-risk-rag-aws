#!/usr/bin/env python3
"""
Simple test script for Phase 1 solution search implementation
"""

import json
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utilities.validation import validate_request
from search.solution_searcher import SolutionSearcher
from utilities.response_formatter import SolutionResponseFormatter

def test_validation():
    """Test request validation"""
    print("Testing request validation...")
    
    # Valid API v2 request
    valid_request = {
        "query": "climate risk",
        "parameters": {
            "max_results": 10
        },
        "filters": {
            "solution_category": ["natural-catastrophe"],
            "risk_type": ["pandemic"]
        }
    }
    
    try:
        search_request = validate_request(valid_request)
        print(f"✅ Validation passed: {search_request}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
    
    return True

def test_solution_searcher():
    """Test solution searcher (requires AWS credentials and KG access)"""
    print("Testing solution searcher...")
    
    try:
        searcher = SolutionSearcher()
        
        # Test SPARQL query building
        filters = {
            "solution_category": ["natural-catastrophe"],
            "risk_type": ["pandemic"]
        }
        
        sparql_query = searcher._build_solution_sparql(filters)
        print(f"✅ SPARQL query built successfully")
        print(f"Query preview: {sparql_query[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Solution searcher test failed: {e}")
        return False

def test_response_formatter():
    """Test response formatter"""
    print("Testing response formatter...")
    
    try:
        formatter = SolutionResponseFormatter()
        
        # Mock solution data
        mock_solutions = [{
            'doc_id': 'sol_test123',
            'content': {
                'assembled_description': 'This is a test solution for climate risk management.',
                'chunk_metadata': {
                    'solution_name': 'Test Climate Solution',
                    'country': 'Singapore',
                    'type_of_risk': 'Climate Change',
                    'type_of_solution': 'Risk Reduction, Prevention',
                    'year_of_implementation': '2023',
                    'ppp': 'Yes',
                    'source_url': 'https://example.com/test'
                }
            },
            'relevance_score': 0.85
        }]
        
        mock_request = {
            'query': 'climate risk',
            'filters': {},
            'parameters': {'max_results': 10}
        }
        
        response = formatter.format_solution_results(mock_solutions, mock_request, 0.5)
        
        print(f"✅ Response formatted successfully")
        print(f"Response structure: {list(response.keys())}")
        print(f"Solutions count: {len(response['results']['solutions'])}")
        
        # Check first solution structure
        if response['results']['solutions']:
            solution = response['results']['solutions'][0]
            required_fields = ['document_id', 'content_type', 'solution_name', 'relevance_score']
            missing_fields = [field for field in required_fields if field not in solution]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print(f"✅ All required fields present")
        
        return True
        
    except Exception as e:
        print(f"❌ Response formatter test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Phase 1 Implementation Tests ===\n")
    
    tests = [
        ("Request Validation", test_validation),
        ("Solution Searcher", test_solution_searcher),
        ("Response Formatter", test_response_formatter)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    print(f"\n=== Test Results ===")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(success for _, success in results)
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
