#!/usr/bin/env python3
"""
Test script to verify enhanced search functionality with country names and type labels
"""
import boto3
import json

def test_enhanced_search():
    """Test the enhanced search Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test payload with filters
    test_payload = {
        "httpMethod": "POST",
        "path": "/search",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "filters": {
                "countries": ["thailand", "singapore"]
            },
            "query": "",
            "max_results": 5,
            "offset": 0
        })
    }
    
    print("Testing enhanced search functionality...")
    print("Test payload: " + json.dumps(test_payload, indent=2))
    
    try:
        response = lambda_client.invoke(
            FunctionName='gaip-search-lambda',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print("Lambda response status: " + str(response['StatusCode']))
        
        if 'body' in result:
            body = json.loads(result['body'])
            print("API response status: " + str(result.get('statusCode')))
            print("Number of results: " + str(len(body.get('results', []))))
            
            # Check if we have results with enhanced data
            if body.get('results'):
                first_result = body['results'][0]
                print("\nFirst result enhanced data:")
                print("- Country regions covered: " + str(first_result.get('country_regions_covered', [])))
                print("- Risk types addressed: " + str(first_result.get('risk_types_addressed', [])))
                print("- Solution types: " + str(first_result.get('solution_types', [])))
                print("- Solution name: " + str(first_result.get('solution_name', 'N/A')))
                
                # Check if we got actual country names instead of empty arrays
                if first_result.get('country_regions_covered'):
                    print("SUCCESS: Country names are being returned!")
                else:
                    print("ISSUE: Country regions covered is still empty")
                    
                if first_result.get('risk_types_addressed'):
                    print("SUCCESS: Risk type labels are being returned!")
                else:
                    print("ISSUE: Risk types addressed is still empty")
                    
                if first_result.get('solution_types'):
                    print("SUCCESS: Solution type labels are being returned!")
                else:
                    print("ISSUE: Solution types is still empty")
            else:
                print("No results returned")
        else:
            print("Error in Lambda response: " + str(result))
            
    except Exception as e:
        print("Error testing Lambda function: " + str(e))

if __name__ == "__main__":
    test_enhanced_search()
