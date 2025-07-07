#!/usr/bin/env python3
"""
Test script for Text Chunker Processor
Tests chunking with existing processed documents
"""

import boto3
import json
import sys
import os
from datetime import datetime

# Add lambda directory to path for imports
sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/text_chunker')
sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/shared_layer/python')

def test_text_chunker_with_existing_doc():
    """Test text chunker with an existing processed document"""
    
    # Set up AWS session
    session = boto3.Session(profile_name='solve-global')
    s3 = session.client('s3', region_name='us-east-1')
    
    # Get list of available documents
    text_bucket = 'solve-global-kr-text-861276078413-us-east-1'
    
    try:
        # List available documents
        response = s3.list_objects_v2(
            Bucket=text_bucket,
            Prefix='extracted_text/',
            MaxKeys=5
        )
        
        if 'Contents' not in response:
            print("No processed documents found")
            return
        
        # Pick the first document
        first_doc = response['Contents'][0]
        doc_key = first_doc['Key']
        doc_size = first_doc['Size']
        
        print(f"Testing with document: {doc_key}")
        print(f"Document size: {doc_size} bytes")
        
        # Extract doc_id from key (remove prefix and extension)
        doc_id = doc_key.replace('extracted_text/', '').replace('.txt', '')
        
        # Read the document content
        doc_response = s3.get_object(Bucket=text_bucket, Key=doc_key)
        doc_content = doc_response['Body'].read().decode('utf-8')
        
        print(f"Document content length: {len(doc_content)} characters")
        print(f"First 200 characters: {doc_content[:200]}...")
        
        # Create test event for the chunker
        test_event = {
            'Records': [{
                'body': json.dumps({
                    'Message': json.dumps({
                        'doc_id': doc_id,
                        'stage': 'text_ready',
                        'full_text_location': {
                            'bucket': text_bucket,
                            'key': doc_key
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    })
                })
            }]
        }
        
        # Set environment variables
        os.environ['CHUNKS_BUCKET'] = 'solve-global-kr-chunks-861276078413-us-east-1'
        os.environ['TEXT_BUCKET'] = text_bucket
        
        # Import and test the chunker
        from text_chunker_processor import TextChunkerProcessor
        
        processor = TextChunkerProcessor()
        result = processor.lambda_handler(test_event, None)
        
        print("\n" + "="*50)
        print("CHUNKING RESULT:")
        print("="*50)
        print(json.dumps(result, indent=2))
        
        # Check if chunks were created in S3 (v2-chunks structure)
        chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'
        chunks_prefix = f'v2-chunks/{doc_id}/'
        
        print(f"\nChecking for v2 chunks in s3://{chunks_bucket}/{chunks_prefix}")
        
        chunks_response = s3.list_objects_v2(
            Bucket=chunks_bucket,
            Prefix=chunks_prefix
        )
        
        if 'Contents' in chunks_response:
            print(f"Found {len(chunks_response['Contents'])} files:")
            for obj in chunks_response['Contents']:
                print(f"  - {obj['Key']} ({obj['Size']} bytes)")
                
            # Read and display first chunk
            first_chunk_key = None
            for obj in chunks_response['Contents']:
                if obj['Key'].endswith('chunk_000.json'):
                    first_chunk_key = obj['Key']
                    break
            
            if first_chunk_key:
                print(f"\nFirst chunk content:")
                chunk_response = s3.get_object(Bucket=chunks_bucket, Key=first_chunk_key)
                chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                print(json.dumps(chunk_data, indent=2))
        else:
            print("No v2 chunks found in S3")
            
            # Also check if there are any existing migrated chunks (for reference)
            old_chunks_prefix = f'chunks/{doc_id}/'
            print(f"\nChecking for existing migrated chunks in s3://{chunks_bucket}/{old_chunks_prefix}")
            
            old_chunks_response = s3.list_objects_v2(
                Bucket=chunks_bucket,
                Prefix=old_chunks_prefix
            )
            
            if 'Contents' in old_chunks_response:
                print(f"Found {len(old_chunks_response['Contents'])} migrated chunk files (these are separate from our v2 implementation)")
            else:
                print("No existing chunks found either")
        
    except Exception as e:
        print(f"Error testing text chunker: {e}")
        import traceback
        traceback.print_exc()

def test_direct_chunking():
    """Test direct chunking with sample text"""
    
    print("Testing direct chunking...")
    
    sample_text = """
    Climate Risk Assessment Report
    
    Executive Summary
    This report analyzes the climate risks facing our organization over the next decade.
    
    Key Findings
    1. Temperature increases of 2-3°C are expected by 2030
    2. Precipitation patterns will shift significantly
    3. Extreme weather events will become more frequent
    
    Risk Categories
    
    Physical Risks
    Physical climate risks include acute risks from extreme weather events and chronic risks from long-term climate changes.
    
    Transition Risks
    Transition risks arise from the shift to a low-carbon economy and include policy, technology, and market risks.
    
    Recommendations
    We recommend implementing a comprehensive climate adaptation strategy that addresses both physical and transition risks.
    """
    
    # Create test event
    test_event = {
        'Records': [{
            'body': json.dumps({
                'doc_id': 'test_sample_doc',
                'text_content': sample_text,
                'stage': 'direct_chunking'
            })
        }]
    }
    
    # Set environment variables
    os.environ['CHUNKS_BUCKET'] = 'solve-global-kr-chunks-861276078413-us-east-1'
    os.environ['TEXT_BUCKET'] = 'solve-global-kr-text-861276078413-us-east-1'
    
    try:
        # Import and test the chunker
        from text_chunker_processor import TextChunkerProcessor
        
        processor = TextChunkerProcessor()
        result = processor.lambda_handler(test_event, None)
        
        print("\n" + "="*50)
        print("DIRECT CHUNKING RESULT:")
        print("="*50)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error in direct chunking test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Text Chunker Processor Test")
    print("="*50)
    
    # Test 1: Direct chunking with sample text
    test_direct_chunking()
    
    print("\n" + "="*70 + "\n")
    
    # Test 2: Chunking with existing processed document
    test_text_chunker_with_existing_doc()
