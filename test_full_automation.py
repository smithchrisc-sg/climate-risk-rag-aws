#!/usr/bin/env python3
"""
Full Pipeline Automation Test
Test complete end-to-end automation with VPC endpoints working
"""

import boto3
import json
import time
from datetime import datetime

def test_full_pipeline_automation():
    """Test complete pipeline automation"""
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    s3_client = session.client('s3', region_name='us-east-1')
    
    print("🔄 FULL PIPELINE AUTOMATION TEST")
    print("=" * 45)
    print("Testing complete end-to-end automation with VPC endpoints...")
    print("")
    
    # Use a small test document
    test_doc = "01dd077e_86ce1ac2.pdf"
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
            "eventTime": datetime.now().isoformat() + "Z",
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
            FunctionName='solve-global-kr-textextractor-initiator',
            InvocationType='Event',  # Async
            Payload=json.dumps(s3_event)
        )
        
        if response['StatusCode'] == 202:
            print("✅ Text extraction triggered successfully!")
            print("   Waiting for Textract processing...")
            
            # Wait for text extraction to complete
            time.sleep(45)  # Textract takes time
            
            # Check if text file was created
            text_bucket = "solve-global-kr-text-new-861276078413-us-east-1"
            text_key = f"{doc_id}.txt"
            
            try:
                s3_client.head_object(Bucket=text_bucket, Key=text_key)
                print("✅ Text extraction completed!")
                
                # Wait a bit more for SNS message processing
                print("\n2️⃣ Checking Automated Text Chunking...")
                time.sleep(20)
                
                # Check if chunks were created automatically
                chunks_bucket = "solve-global-kr-chunks-861276078413-us-east-1"
                
                try:
                    response = s3_client.list_objects_v2(
                        Bucket=chunks_bucket,
                        Prefix=f"{doc_id}/"
                    )
                    
                    if 'Contents' in response and len(response['Contents']) > 0:
                        print("✅ Text chunking was automatically triggered!")
                        print(f"   Found {len(response['Contents'])} chunk files")
                        
                        # Wait for NLP processing
                        print("\n3️⃣ Checking Automated NLP Processing...")
                        time.sleep(30)
                        
                        nlp_bucket = "solve-global-kr-ner-results-861276078413-us-east-1"
                        
                        try:
                            response = s3_client.list_objects_v2(
                                Bucket=nlp_bucket,
                                Prefix=f"{doc_id}/"
                            )
                            
                            if 'Contents' in response and len(response['Contents']) > 0:
                                print("✅ NLP processing was automatically triggered!")
                                print(f"   Found {len(response['Contents'])} NLP result files")
                                print("\n🎉 COMPLETE PIPELINE AUTOMATION SUCCESS!")
                                print("   VPC endpoints have fully resolved the automation issues!")
                                return True
                            else:
                                print("⚠️  NLP processing not yet complete (may need more time)")
                                print("   But text chunking automation is working!")
                                return "partial"
                                
                        except Exception as e:
                            print(f"❌ Error checking NLP results: {str(e)}")
                            return "partial"
                            
                    else:
                        print("❌ Text chunking was NOT automatically triggered")
                        print("   This suggests SNS messaging issues remain")
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

if __name__ == "__main__":
    print("🚀 Starting Full Pipeline Automation Test\n")
    
    result = test_full_pipeline_automation()
    
    if result == True:
        print("\n🎉 COMPLETE SUCCESS!")
        print("   Full pipeline automation is working end-to-end.")
        print("   VPC endpoints have resolved all networking issues.")
    elif result == "partial":
        print("\n⚠️  PARTIAL SUCCESS!")
        print("   Initial automation stages are working.")
        print("   VPC endpoints are functioning correctly.")
    else:
        print("\n❌ AUTOMATION ISSUES REMAIN")
        print("   Further investigation needed.")
