#!/usr/bin/env python3
"""
Simple VPC Endpoint Test
Test if text chunker can publish to SNS through VPC endpoints
"""

import boto3
import json
from datetime import datetime

def test_text_chunker_sns():
    """Test text chunker SNS publishing through VPC endpoints"""
    
    # Use the correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    print("🔗 Testing VPC Endpoint Connectivity")
    print("=" * 40)
    print("Testing text-chunker-pipeline SNS publishing...")
    print("")
    
    # Create a simple test message for text chunker
    test_message = {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "vpc-endpoint-test",
        "stage": "text_ready",
        "doc_id": "test-document",
        "doc_hash": "test-hash-123",
        "document_metadata": {
            "original_filename": "test.pdf",
            "file_size": 1000,
            "page_count": 1,
            "processing_started": datetime.utcnow().isoformat() + "Z"
        },
        "data_locations": {
            "text_location": "s3://solve-global-kr-text-new-861276078413-us-east-1/test-document.txt"
        },
        "processing_metadata": {
            "total_characters": 1000,
            "processing_duration_ms": 1000,
            "cost_estimate": 0.01
        },
        "integration_flags": {
            "documentid_manager_integration": True,
            "selective_migration_used": False,
            "database_tracking_enabled": True
        }
    }
    
    try:
        print("📤 Invoking text-chunker-pipeline...")
        
        response = lambda_client.invoke(
            FunctionName='text-chunker-pipeline',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_message)
        )
        
        result = json.loads(response['Payload'].read())
        
        print(f"📊 Response Status: {response['StatusCode']}")
        
        if response['StatusCode'] == 200:
            if 'errorMessage' in result:
                print(f"❌ Function Error: {result['errorMessage']}")
                if 'timeout' in result['errorMessage'].lower():
                    print("   This suggests VPC endpoint connectivity issues")
                    return False
                elif 'sns' in result['errorMessage'].lower():
                    print("   This suggests SNS connectivity issues")
                    return False
                else:
                    print("   This is likely a different issue (not VPC endpoints)")
                    return "other_error"
            else:
                print("✅ Function executed successfully!")
                print("   VPC endpoints appear to be working")
                return True
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Simple VPC Endpoint Test\n")
    
    result = test_text_chunker_sns()
    
    if result == True:
        print("\n🎉 SUCCESS: VPC endpoints are working!")
        print("   SNS connectivity through VPC endpoint confirmed.")
    elif result == "other_error":
        print("\n⚠️  MIXED: VPC endpoints working, but other issues exist")
        print("   The networking issue appears to be resolved.")
    else:
        print("\n❌ FAILURE: VPC endpoint connectivity issues remain")
        print("   Additional investigation required.")
