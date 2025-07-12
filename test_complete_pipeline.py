#!/usr/bin/env python3
"""
Test complete pipeline with a third document
"""

import boto3
import json
import time

def test_complete_pipeline():
    """Test the complete pipeline with a fresh document"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Try with a third document
    test_payload = {
        'bucket': 'solve-global-kr-dl-source-documents-861276078413-us-east-1',
        'key': '02a2baf87408e8e9.pdf'  # Third document
    }
    
    print("Testing complete pipeline with third document...")
    print(f"Document: s3://{test_payload['bucket']}/{test_payload['key']}")
    
    try:
        # Step 1: Trigger text extraction
        print("\n🚀 Step 1: Triggering text extraction...")
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response['StatusCode'] == 200:
            payload = json.loads(response['Payload'].read())
            body = json.loads(payload['body']) if isinstance(payload['body'], str) else payload['body']
            
            if body.get('summary', {}).get('success', 0) > 0:
                job_id = body['results'][0]['job_id']
                print(f"✅ Text extraction started successfully!")
                print(f"   Job ID: {job_id}")
                
                # Step 2: Wait for processing
                print(f"\n⏳ Step 2: Waiting for Textract job to complete...")
                print(f"   This typically takes 2-5 minutes...")
                
                return True
            elif body.get('summary', {}).get('skipped', 0) > 0:
                print("ℹ️  Document already processed - pipeline should still work")
                return True
            else:
                print(f"❌ Text extraction failed: {body}")
                return False
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    if success:
        print(f"\n📋 Next steps:")
        print(f"   1. Wait 3-5 minutes for Textract job to complete")
        print(f"   2. Run: python3 monitor_pipeline_status.py")
        print(f"   3. Check for text files in solve-global-kr-dl-text bucket")
        print(f"   4. Check for chunk files in solve-global-kr-dl-chunks bucket")
    else:
        print(f"\n❌ Pipeline test failed")
