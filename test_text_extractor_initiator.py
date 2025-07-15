#!/usr/bin/env python3
"""
Test script for Text Extractor Initiator Lambda function
"""

import json
import boto3
import sys
from datetime import datetime

def test_text_extractor_initiator():
    """Test the text extractor initiator Lambda function"""
    
    lambda_client = boto3.client('lambda')
    
    # Test payload - simulate S3 event
    test_payload = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {
                        "name": "solve-global-kr-source-documents"
                    },
                    "object": {
                        "key": "data_lake/test_document_001.pdf"
                    }
                }
            }
        ]
    }
    
    print("Testing Text Extractor Initiator Lambda function...")
    print(f"Test payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())
        
        print(f"\nLambda Response Status: {status_code}")
        print(f"Response Payload: {json.dumps(payload, indent=2, default=str)}")
        
        # Check for errors
        if 'errorMessage' in payload:
            print(f"\nERROR: {payload['errorMessage']}")
            if 'errorType' in payload:
                print(f"Error Type: {payload['errorType']}")
            if 'stackTrace' in payload:
                print("Stack Trace:")
                for line in payload['stackTrace']:
                    print(f"  {line}")
        
        return payload
        
    except Exception as e:
        print(f"Error invoking Lambda function: {str(e)}")
        return None

def test_direct_invocation():
    """Test with direct invocation format"""
    
    lambda_client = boto3.client('lambda')
    
    # Direct test payload
    test_payload = {
        "bucket": "solve-global-kr-source-documents",
        "key": "data_lake/test_document_002.pdf"
    }
    
    print("\nTesting with direct invocation format...")
    print(f"Test payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        status_code = response['StatusCode']
        payload = json.loads(response['Payload'].read())
        
        print(f"\nDirect Invocation Status: {status_code}")
        print(f"Response Payload: {json.dumps(payload, indent=2, default=str)}")
        
        return payload
        
    except Exception as e:
        print(f"Error with direct invocation: {str(e)}")
        return None

def check_lambda_configuration():
    """Check Lambda function configuration"""
    
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.get_function(
            FunctionName='solve-global-kr-textextractor-initiator'
        )
        
        config = response['Configuration']
        
        print("\nLambda Function Configuration:")
        print(f"Function Name: {config['FunctionName']}")
        print(f"Runtime: {config['Runtime']}")
        print(f"Handler: {config['Handler']}")
        print(f"Timeout: {config['Timeout']} seconds")
        print(f"Memory: {config['MemorySize']} MB")
        print(f"Last Modified: {config['LastModified']}")
        
        # Check environment variables
        env_vars = config.get('Environment', {}).get('Variables', {})
        print(f"\nEnvironment Variables:")
        for key, value in env_vars.items():
            # Mask sensitive values
            if 'PASSWORD' in key.upper() or 'SECRET' in key.upper():
                print(f"  {key}: ***MASKED***")
            else:
                print(f"  {key}: {value}")
        
        return config
        
    except Exception as e:
        print(f"Error getting Lambda configuration: {str(e)}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("TEXT EXTRACTOR INITIATOR DEBUG TEST")
    print("=" * 60)
    
    # Check configuration first
    config = check_lambda_configuration()
    
    if config:
        print("\n" + "=" * 60)
        
        # Test S3 event format
        result1 = test_text_extractor_initiator()
        
        print("\n" + "=" * 60)
        
        # Test direct invocation format
        result2 = test_direct_invocation()
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
    else:
        print("Cannot proceed without Lambda configuration")
        sys.exit(1)