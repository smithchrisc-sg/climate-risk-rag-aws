#!/usr/bin/env python3
"""
Test Textract in different regions with the same PDF
"""

import boto3
import os

def test_regions():
    """Test the same PDF in different AWS regions"""
    
    print("Multi-Region Textract Test")
    print("=" * 50)
    
    # Use a small test PDF
    test_pdf = "/Users/chris/climate-risk-rag-aws/test_pdfs/Factorization Machines - Amazon SageMaker.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"❌ Test PDF not found: {test_pdf}")
        return
    
    print(f"Testing PDF: {os.path.basename(test_pdf)}")
    print(f"Size: {os.path.getsize(test_pdf):,} bytes")
    
    # Read PDF once
    with open(test_pdf, 'rb') as f:
        pdf_bytes = f.read()
    
    # Test regions
    regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    session = boto3.Session(profile_name='solve-global')
    
    for region in regions:
        print(f"\nTesting region: {region}")
        print("-" * 30)
        
        try:
            textract = session.client('textract', region_name=region)
            
            response = textract.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            
            blocks = response.get('Blocks', [])
            lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
            
            print(f"✅ SUCCESS in {region}!")
            print(f"   Detected {len(blocks)} blocks, {len(lines)} lines")
            
            if lines:
                print(f"   First line: {lines[0]}")
            
            return True  # Success in at least one region
            
        except Exception as e:
            error_type = type(e).__name__
            print(f"❌ FAILED in {region}: {error_type}")
            if 'UnsupportedDocumentException' in str(e):
                print(f"   Same UnsupportedDocumentException error")
            else:
                print(f"   Different error: {str(e)[:100]}...")
    
    return False

if __name__ == "__main__":
    success = test_regions()
    
    if not success:
        print(f"\n" + "="*50)
        print("🚨 CRITICAL FINDING:")
        print("ALL regions fail with the same error!")
        print("This suggests a fundamental account or service issue.")
        print("="*50)
    else:
        print(f"\n" + "="*50)
        print("✅ Found working region!")
        print("The issue may be region-specific.")
        print("="*50)
