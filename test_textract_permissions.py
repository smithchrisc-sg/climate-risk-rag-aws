#!/usr/bin/env python3
"""
Test Textract permissions and configuration
"""

import boto3
import json

def test_textract_permissions():
    """Test basic Textract permissions"""
    
    # Create session with profile
    session = boto3.Session(profile_name='solve-global')
    textract = session.client('textract', region_name='us-east-1')
    s3 = session.client('s3', region_name='us-east-1')
    
    print("Testing Textract permissions...")
    print("-" * 40)
    
    # Test 1: Check if we can call Textract at all
    try:
        # This should work if we have basic Textract permissions
        response = textract.get_document_analysis(JobId='dummy-job-id')
    except Exception as e:
        if 'InvalidJobIdException' in str(e):
            print("✅ Textract API is accessible (got expected InvalidJobIdException)")
        elif 'AccessDenied' in str(e):
            print("❌ Access denied to Textract API")
            return False
        else:
            print(f"✅ Textract API accessible (got: {type(e).__name__})")
    
    # Test 2: Check S3 access
    bucket = "solve-global-kr-documents-861276078413-us-east-1"
    key = "documents/0004ad39_4285ab3d.pdf"
    
    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        print(f"✅ Can access S3 object: s3://{bucket}/{key}")
        print(f"   Size: {response['ContentLength']} bytes")
    except Exception as e:
        print(f"❌ Cannot access S3 object: {str(e)}")
        return False
    
    # Test 3: Check if Textract can access the S3 object
    try:
        print(f"Testing Textract access to S3 object...")
        response = textract.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )
        print("✅ Textract successfully accessed S3 object!")
        print(f"   Detected {len(response.get('Blocks', []))} blocks")
        
        # Show sample of detected text
        lines = [block['Text'] for block in response.get('Blocks', []) if block['BlockType'] == 'LINE']
        if lines:
            print(f"   Sample text: {lines[0][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Textract cannot access S3 object: {str(e)}")
        
        # Check if it's a permissions issue
        if 'InvalidS3ObjectException' in str(e):
            print("   This is likely a permissions issue.")
            print("   Textract needs permission to access S3 objects.")
            
            # Check current IAM user/role
            sts = session.client('sts')
            try:
                identity = sts.get_caller_identity()
                print(f"   Current identity: {identity.get('Arn')}")
            except:
                pass
                
        return False

def test_multiple_documents():
    """Test with multiple documents to find a compatible one"""
    print("\nTesting multiple documents...")
    print("-" * 40)
    
    session = boto3.Session(profile_name='solve-global')
    textract = session.client('textract', region_name='us-east-1')
    s3 = session.client('s3', region_name='us-east-1')
    
    bucket = "solve-global-kr-documents-861276078413-us-east-1"
    
    # Test documents of different sizes
    test_docs = [
        "documents/006893d2_93170cb9.pdf",  # Small: 34KB
        "documents/0068a512_1780336e.pdf",  # Small: 81KB  
        "documents/0032f6cb_f0caef34.pdf",  # Medium: 142KB
        "documents/004e17a3_3bb90d8e.pdf",  # Medium: 135KB
        "documents/002328de_230b4003.pdf",  # Medium: 602KB
    ]
    
    for key in test_docs:
        try:
            print(f"Testing: {key}")
            
            # Get file info
            head_response = s3.head_object(Bucket=bucket, Key=key)
            size_kb = head_response['ContentLength'] / 1024
            print(f"  Size: {size_kb:.1f} KB")
            
            # Try Textract
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                }
            )
            
            print(f"  ✅ SUCCESS! Detected {len(response.get('Blocks', []))} blocks")
            
            # Show sample text
            lines = [block['Text'] for block in response.get('Blocks', []) if block['BlockType'] == 'LINE']
            if lines:
                print(f"  Sample: {lines[0][:80]}...")
                print(f"  Total lines: {len(lines)}")
            
            return key  # Return the working document
            
        except Exception as e:
            print(f"  ❌ Failed: {str(e)}")
            continue
    
    return None

if __name__ == "__main__":
    print("Textract Permissions Test")
    print("=" * 50)
    
    # Test direct S3 access with original document
    success1 = test_textract_permissions()
    
    if not success1:
        # Try multiple documents to find a compatible one
        working_doc = test_multiple_documents()
        
        if working_doc:
            print(f"\n✅ Found working document: {working_doc}")
            print("   Recommendation: Use this document for testing TextExtractor")
        else:
            print("\n❌ No compatible documents found")
            print("   This might indicate an issue with the PDF format or Textract configuration")
    else:
        print("\n✅ Direct S3 access works!")
