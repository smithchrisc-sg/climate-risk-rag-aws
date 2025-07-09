#!/usr/bin/env python3
"""
Test VPC Endpoints for SNS/SQS Connectivity
Verify that Lambda functions can now reach SNS/SQS through VPC endpoints
"""

import boto3
import json
import time
from datetime import datetime

def test_vpc_endpoints():
    """Test VPC endpoint connectivity by triggering a simple pipeline step"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("🔗 VPC ENDPOINTS CONNECTIVITY TEST")
    print("=" * 40)
    print("Testing SNS/SQS connectivity through new VPC endpoints...")
    print("")
    
    # Test 1: Trigger text chunker (which should publish to SNS)
    print("1️⃣ Testing Text Chunker SNS Publishing...")
    
    # Use a document we know has text ready
    test_payload = {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "vpc-endpoint-test",
        "stage": "text_ready",
        "doc_id": "0004ad39_4285ab3d",  # Known processed document
        "doc_hash": "test-hash",
        "document_metadata": {
            "original_filename": "test-document.pdf",
            "file_size": 145000,
            "page_count": 3,
            "processing_started": datetime.utcnow().isoformat() + "Z"
        },
        "data_locations": {
            "text_location": "s3://solve-global-kr-text-new-861276078413-us-east-1/0004ad39_4285ab3d.txt",
            "structure_location": "s3://solve-global-kr-text-new-861276078413-us-east-1/0004ad39_4285ab3d_structure.json"
        },
        "processing_metadata": {
            "total_characters": 145000,
            "processing_duration_ms": 5000,
            "cost_estimate": 0.02
        },
        "integration_flags": {
            "documentid_manager_integration": True,
            "selective_migration_used": False,
            "database_tracking_enabled": True
        }
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='text-chunker-pipeline',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            print("✅ Text Chunker invocation successful!")
            print(f"   Response: {result.get('statusCode', 'Unknown')}")
            
            if 'errorMessage' in result:
                print(f"❌ Error in function: {result['errorMessage']}")
                return False
            else:
                print("✅ No errors detected - VPC endpoints likely working!")
                return True
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during test: {str(e)}")
        return False

def check_vpc_endpoint_status():
    """Check the status of our VPC endpoints"""
    
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    
    print("\n🔍 VPC ENDPOINT STATUS CHECK")
    print("=" * 30)
    
    try:
        response = ec2_client.describe_vpc_endpoints(
            VpcEndpointIds=['vpce-009ef65a59a688965', 'vpce-0240799d7eda94515']
        )
        
        for endpoint in response['VpcEndpoints']:
            service = endpoint['ServiceName'].split('.')[-1]  # Extract service name
            state = endpoint['State']
            print(f"📡 {service.upper()} VPC Endpoint: {state}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking VPC endpoints: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting VPC Endpoint Connectivity Test\n")
    
    # Check endpoint status first
    if not check_vpc_endpoint_status():
        print("❌ VPC endpoint status check failed")
        exit(1)
    
    # Test connectivity
    if test_vpc_endpoints():
        print("\n🎉 SUCCESS: VPC endpoints appear to be working!")
        print("   Pipeline automation should now function correctly.")
    else:
        print("\n❌ FAILURE: VPC endpoint connectivity issues detected")
        print("   Manual investigation required.")
