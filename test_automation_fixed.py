#!/usr/bin/env python3
"""
Test End-to-End Pipeline Automation
Test if VPC endpoints have resolved the automation issues
"""

import boto3
import json
import time
from datetime import datetime

def test_pipeline_automation():
    """Test if pipeline automation works with VPC endpoints"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    print("🔄 PIPELINE AUTOMATION TEST")
    print("=" * 40)
    print("Testing if VPC endpoints have resolved automation issues...")
    print("")
    
    # Use a small document for testing
    test_doc = "01dd077e_86ce1ac2.pdf"  # Known small document
    doc_id = test_doc.replace('.pdf', '')
    bucket_name = "solve-global-kr-documents-861276078413-us-east-1"
    
    print(f"📄 Test Document: {doc_id}")
    print("")
    
    # Step 1: Trigger text extraction
    print("1️⃣ Triggering Text Extraction...")
    
    s3_event = {
        "Records": [{
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
                    "key": f"documents/{test_doc}",
                    "size": 538035
                }
            }
        }]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-textextractor-processor',
            InvocationType='Event',  # Async
            Payload=json.dumps(s3_event)
        )
        
        if response['StatusCode'] == 202:
            print("✅ Text extraction triggered successfully!")
            print("   Waiting for processing...")
            
            # Wait for text extraction to complete
            time.sleep(30)
            
            # Check if text file was created
            text_bucket = "solve-global-kr-text-new-861276078413-us-east-1"
            text_key = f"{doc_id}.txt"
            
            try:
                s3_client.head_object(Bucket=text_bucket, Key=text_key)
                print("✅ Text extraction completed!")
                
                # Now check if text chunker was automatically triggered
                print("\n2️⃣ Checking Text Chunker Automation...")
                time.sleep(15)  # Wait for SNS message processing
                
                # Check if chunks were created
                chunks_bucket = "solve-global-kr-chunks-861276078413-us-east-1"
                
                try:
                    response = s3_client.list_objects_v2(
                        Bucket=chunks_bucket,
                        Prefix=f"{doc_id}/"
                    )
                    
                    if 'Contents' in response and len(response['Contents']) > 0:
                        print("✅ Text chunker was automatically triggered!")
                        print(f"   Found {len(response['Contents'])} chunk files")
                        
                        # Check if NLP processing was triggered
                        print("\n3️⃣ Checking NLP Processing Automation...")
                        time.sleep(20)  # Wait for NLP processing
                        
                        nlp_bucket = "solve-global-kr-ner-results-861276078413-us-east-1"
                        
                        try:
                            response = s3_client.list_objects_v2(
                                Bucket=nlp_bucket,
                                Prefix=f"{doc_id}/"
                            )
                            
                            if 'Contents' in response and len(response['Contents']) > 0:
                                print("✅ NLP processing was automatically triggered!")
                                print(f"   Found {len(response['Contents'])} NLP result files")
                                print("\n🎉 FULL PIPELINE AUTOMATION WORKING!")
                                return True
                            else:
                                print("⚠️  NLP processing not yet triggered (may need more time)")
                                return "partial"
                                
                        except Exception as e:
                            print(f"❌ Error checking NLP results: {str(e)}")
                            return False
                            
                    else:
                        print("❌ Text chunker was NOT automatically triggered")
                        print("   VPC endpoints may not be fully working")
                        return False
                        
                except Exception as e:
                    print(f"❌ Error checking chunks: {str(e)}")
                    return False
                    
            except Exception as e:
                print(f"❌ Text extraction failed or incomplete: {str(e)}")
                return False
                
        else:
            print(f"❌ Text extraction trigger failed: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during test: {str(e)}")
        return False

def check_vpc_endpoints_summary():
    """Show summary of VPC endpoints"""
    
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    
    print("📡 VPC ENDPOINTS SUMMARY")
    print("=" * 25)
    
    try:
        response = ec2_client.describe_vpc_endpoints(
            Filters=[
                {'Name': 'vpc-id', 'Values': ['vpc-051c21d88c7dc3819']}
            ]
        )
        
        endpoints = {}
        for endpoint in response['VpcEndpoints']:
            service = endpoint['ServiceName'].split('.')[-1]
            state = endpoint['State']
            endpoints[service] = state
            
        for service, state in sorted(endpoints.items()):
            status = "✅" if state == "available" else "❌"
            print(f"{status} {service.upper()}: {state}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking endpoints: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Pipeline Automation Test\n")
    
    # Show VPC endpoint status
    if not check_vpc_endpoints_summary():
        print("❌ Cannot check VPC endpoint status")
        exit(1)
    
    print("")
    
    # Test automation
    result = test_pipeline_automation()
    
    if result == True:
        print("\n🎉 SUCCESS: Full pipeline automation is working!")
        print("   VPC endpoints have resolved the networking issues.")
    elif result == "partial":
        print("\n⚠️  PARTIAL SUCCESS: Some automation working, may need more time")
        print("   VPC endpoints appear to be working for initial stages.")
    else:
        print("\n❌ FAILURE: Pipeline automation still not working")
        print("   Additional investigation required.")
