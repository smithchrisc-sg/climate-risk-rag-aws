#!/usr/bin/env python3
"""
Test script for TextExtractor Lambda function
Tests the text extraction functionality with sample documents
"""

import json
import boto3
import sys
import os
from datetime import datetime

def test_text_extractor():
    """Test the TextExtractor Lambda function"""
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1', profile_name='solve-global')
    
    # Test with a sample document from our migrated bucket
    test_event = {
        "bucket": "solve-global-kr-documents-861276078413-us-east-1",
        "key": "documents/0004ad39_4285ab3d.pdf"  # Using one of the documents we saw earlier
    }
    
    print(f"Testing TextExtractor with document: {test_event['key']}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-" * 60)
    
    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName='TextExtractor',  # Assuming this is the deployed function name
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print("Lambda Response:")
        print(f"Status Code: {response['StatusCode']}")
        print(f"Response: {json.dumps(response_payload, indent=2)}")
        
        if response_payload.get('statusCode') == 200:
            body = json.loads(response_payload['body'])
            print("\nExtraction Results:")
            print(f"Document ID: {body.get('document_id')}")
            print(f"Output Location: {body.get('output_location')}")
            print(f"Text Length: {body.get('text_length')} characters")
            print(f"Word Count: {body.get('word_count')} words")
            
            # Try to read the extracted text
            if 'output_location' in body:
                output_location = body['output_location']
                if output_location.startswith('s3://'):
                    bucket_name = output_location.split('/')[2]
                    key_name = '/'.join(output_location.split('/')[3:])
                    
                    s3_client = boto3.client('s3', region_name='us-east-1', profile_name='solve-global')
                    
                    try:
                        obj = s3_client.get_object(Bucket=bucket_name, Key=key_name)
                        extracted_text = obj['Body'].read().decode('utf-8')
                        
                        print(f"\nFirst 500 characters of extracted text:")
                        print("-" * 40)
                        print(extracted_text[:500])
                        if len(extracted_text) > 500:
                            print("...")
                        print("-" * 40)
                        
                    except Exception as e:
                        print(f"Could not read extracted text: {str(e)}")
        else:
            print(f"Error: {response_payload}")
            
    except Exception as e:
        print(f"Error invoking Lambda function: {str(e)}")
        return False
    
    return True

def test_local_extraction():
    """Test text extraction logic locally (without Lambda)"""
    print("Testing TextExtractor logic locally...")
    print("-" * 60)
    
    # Import the TextExtractor class
    sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/text_extractor')
    
    try:
        from text_extractor import TextExtractor
        
        # Set environment variables
        os.environ['OUTPUT_BUCKET'] = 'solve-global-kr-text-new-861276078413-us-east-1'
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['AWS_PROFILE'] = 'solve-global'
        
        # Initialize extractor with profile
        extractor = TextExtractor(profile_name='solve-global')
        
        # Test with sample document
        bucket = "solve-global-kr-documents-861276078413-us-east-1"
        key = "documents/0004ad39_4285ab3d.pdf"
        
        print(f"Extracting text from: s3://{bucket}/{key}")
        
        # Extract text
        extracted_data = extractor.extract_text_from_pdf(bucket, key)
        
        print("Extraction completed successfully!")
        print(f"Text length: {len(extracted_data['text_content'])} characters")
        print(f"Pages processed: {extracted_data['metadata']['textract_metadata']['pages_processed']}")
        
        # Save the extracted text
        document_id = os.path.splitext(os.path.basename(key))[0]
        output_location = extractor.save_extracted_text(extracted_data, document_id)
        
        print(f"Saved to: {output_location}")
        
        # Show sample of extracted text
        print(f"\nFirst 500 characters:")
        print("-" * 40)
        print(extracted_data['text_content'][:500])
        if len(extracted_data['text_content']) > 500:
            print("...")
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"Local test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("TextExtractor Test Suite")
    print("=" * 60)
    
    # Test locally first
    print("\n1. Testing locally...")
    local_success = test_local_extraction()
    
    if local_success:
        print("\n✅ Local test passed!")
        
        # Ask if user wants to test deployed Lambda
        response = input("\nTest deployed Lambda function? (y/N): ")
        if response.lower() == 'y':
            print("\n2. Testing deployed Lambda...")
            lambda_success = test_text_extractor()
            
            if lambda_success:
                print("\n✅ Lambda test passed!")
            else:
                print("\n❌ Lambda test failed!")
        else:
            print("\nSkipping Lambda test.")
    else:
        print("\n❌ Local test failed!")
        print("Fix local issues before testing Lambda deployment.")
