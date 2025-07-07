#!/usr/bin/env python3
"""
Test different Textract API methods to match console behavior
"""

import boto3
import os
import time

def test_all_textract_methods(pdf_path):
    """Test all available Textract methods with the same PDF"""
    
    print(f"Testing All Textract Methods")
    print("=" * 60)
    print(f"PDF: {os.path.basename(pdf_path)}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    session = boto3.Session(profile_name='solve-global')
    textract = session.client('textract', region_name='us-east-1')
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    print(f"PDF size: {len(pdf_bytes):,} bytes")
    print()
    
    # Method 1: DetectDocumentText (what we've been using)
    print("1. DetectDocumentText (Standard Text Detection)")
    print("-" * 50)
    try:
        response = textract.detect_document_text(
            Document={'Bytes': pdf_bytes}
        )
        
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        
        print(f"✅ SUCCESS: {len(lines)} lines extracted")
        if lines:
            print(f"   First line: {lines[0][:80]}...")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
    
    print()
    
    # Method 2: AnalyzeDocument (More advanced analysis)
    print("2. AnalyzeDocument (Advanced Analysis)")
    print("-" * 50)
    try:
        response = textract.analyze_document(
            Document={'Bytes': pdf_bytes},
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        
        print(f"✅ SUCCESS: {len(lines)} lines extracted")
        if lines:
            print(f"   First line: {lines[0][:80]}...")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
    
    print()
    
    # Method 3: AnalyzeDocument with different features
    print("3. AnalyzeDocument (Text Only)")
    print("-" * 50)
    try:
        response = textract.analyze_document(
            Document={'Bytes': pdf_bytes},
            FeatureTypes=[]  # No special features, just text
        )
        
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        
        print(f"✅ SUCCESS: {len(lines)} lines extracted")
        if lines:
            print(f"   First line: {lines[0][:80]}...")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
    
    print()
    
    # Method 4: Try async processing (what console might use)
    print("4. StartDocumentTextDetection (Async Processing)")
    print("-" * 50)
    
    # First upload to S3 for async processing
    s3 = session.client('s3', region_name='us-east-1')
    test_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
    test_key = 'async-test/test-document.pdf'
    
    try:
        # Upload PDF
        s3.put_object(
            Bucket=test_bucket,
            Key=test_key,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        
        # Start async job
        response = textract.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': test_bucket,
                    'Name': test_key
                }
            }
        )
        
        job_id = response['JobId']
        print(f"Started async job: {job_id}")
        
        # Poll for completion (wait up to 60 seconds)
        max_wait = 60
        poll_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            result = textract.get_document_text_detection(JobId=job_id)
            status = result['JobStatus']
            
            print(f"   Status after {elapsed}s: {status}")
            
            if status == 'SUCCEEDED':
                blocks = result.get('Blocks', [])
                lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
                
                print(f"✅ ASYNC SUCCESS: {len(lines)} lines extracted")
                if lines:
                    print(f"   First line: {lines[0][:80]}...")
                break
                
            elif status == 'FAILED':
                print(f"❌ ASYNC FAILED: {result.get('StatusMessage', 'Unknown error')}")
                break
                
            elif status in ['IN_PROGRESS']:
                continue
            else:
                print(f"❌ Unexpected status: {status}")
                break
        
        if elapsed >= max_wait:
            print(f"⏰ TIMEOUT: Job still running after {max_wait} seconds")
        
        # Clean up
        s3.delete_object(Bucket=test_bucket, Key=test_key)
        
    except Exception as e:
        print(f"❌ ASYNC FAILED: {str(e)}")
        
        # Clean up on error
        try:
            s3.delete_object(Bucket=test_bucket, Key=test_key)
        except:
            pass

def test_console_working_pdf():
    """Test the PDF that works in console"""
    
    console_working_pdf = "/Users/chris/climate-risk-rag-aws/test_pdfs/Dynamic Evolving Neural-Fuzzy Inference System for Rainfall-Runoff Modelling.pdf"
    
    if os.path.exists(console_working_pdf):
        print(f"\n" + "="*60)
        print("TESTING PDF THAT WORKS IN CONSOLE")
        print("="*60)
        test_all_textract_methods(console_working_pdf)
    else:
        print(f"\n❌ Console-working PDF not found: {console_working_pdf}")

if __name__ == "__main__":
    test_console_working_pdf()
    
    print(f"\n" + "="*60)
    print("ANALYSIS:")
    print("If any method works, it suggests the console uses that method.")
    print("If all methods fail, the console might preprocess PDFs differently.")
    print("="*60)
