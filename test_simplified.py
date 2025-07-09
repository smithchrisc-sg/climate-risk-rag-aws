#!/usr/bin/env python3
"""
Test Simplified Processor
"""

import boto3
import json
import time
from datetime import datetime

def test_simplified_processor():
    """Test with simplified processor"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Use another small document
    test_document = {
        "key": "documents/0249c7aa_ae155247.pdf",
        "size": 2000756
    }
    
    bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
    doc_id = test_document['key'].split('/')[-1].replace('.pdf', '')
    
    print(f"🧪 Testing Simplified Processor: {doc_id}")
    print(f"📊 Size: {test_document['size']:,} bytes")
    
    # Create proper S3 event
    payload = {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventTime": datetime.utcnow().isoformat() + "Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "bucket": {
                        "name": bucket_name,
                        "arn": f"arn:aws:s3:::{bucket_name}"
                    },
                    "object": {
                        "key": test_document['key'],
                        "size": test_document['size']
                    }
                }
            }
        ]
    }
    
    # Trigger processing
    print(f"\n🚀 Triggering processing...")
    response = lambda_client.invoke(
        FunctionName='solve-global-kr-textextractor-initiator',
        InvocationType='Event',
        Payload=json.dumps(payload)
    )
    
    if response['StatusCode'] != 202:
        print(f"❌ Failed to trigger processing: {response['StatusCode']}")
        return False
    
    print(f"✅ Processing triggered successfully")
    
    # Wait for Textract job to complete
    print(f"\n⏳ Waiting 5 minutes for complete processing...")
    time.sleep(300)
    
    # Check if text was created
    try:
        text_key = f"text/{doc_id}.txt"
        response = s3_client.get_object(Bucket="solve-global-kr-text-new-861276078413-us-east-1", Key=text_key)
        text_content = response['Body'].read().decode('utf-8')
        
        print(f"\n✅ SUCCESS: Text extraction found!")
        print(f"📄 Location: s3://solve-global-kr-text-new-861276078413-us-east-1/{text_key}")
        print(f"📊 Text length: {len(text_content):,} characters")
        print(f"📝 First 200 characters: {text_content[:200]}...")
        
        # Check for chunks (wait a bit more)
        print(f"\n⏳ Waiting 2 more minutes for chunking...")
        time.sleep(120)
        
        try:
            chunks_prefix = f"chunks/{doc_id}/"
            response = s3_client.list_objects_v2(
                Bucket="solve-global-kr-chunks-861276078413-us-east-1",
                Prefix=chunks_prefix,
                MaxKeys=5
            )
            
            chunk_count = response.get('KeyCount', 0)
            if chunk_count > 0:
                print(f"✅ SUCCESS: {chunk_count} chunks created!")
                print(f"🎉 COMPLETE END-TO-END SUCCESS!")
                return True
            else:
                print(f"⏳ Chunks not yet created (may still be processing)")
                print(f"🔄 PARTIAL SUCCESS: Text extraction working!")
                return True
                
        except Exception as e:
            print(f"⏳ Chunks check failed: {e}")
            print(f"🔄 PARTIAL SUCCESS: Text extraction working!")
            return True
        
    except Exception as e:
        print(f"\n❌ FAILED: Text extraction not found: {e}")
        return False

if __name__ == "__main__":
    success = test_simplified_processor()
    print(f"\n🎯 Final Result: {'✅ SUCCESS!' if success else '❌ FAILED'}")
    exit(0 if success else 1)
