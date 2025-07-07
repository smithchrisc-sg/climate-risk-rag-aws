#!/usr/bin/env python3
"""
Test Textract with a different World Bank document (newsletter)
"""

import boto3
import json
import os

def test_newsletter_pdf():
    """Test Textract with the newsletter PDF"""
    
    # Path to newsletter PDF
    newsletter_path = "/Users/chris/SolveGlobalWorkspace/downloads/115355-NEWS-MDGsAndBeyond-Newsletter-January2014-PUBLIC.pdf"
    
    print("Testing Newsletter PDF with Textract")
    print("=" * 60)
    print(f"File: {os.path.basename(newsletter_path)}")
    
    # Check if file exists
    if not os.path.exists(newsletter_path):
        print(f"❌ File not found: {newsletter_path}")
        return False
    
    # Get file info
    file_size = os.path.getsize(newsletter_path)
    print(f"Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # Check file type
    import subprocess
    try:
        file_info = subprocess.check_output(['file', newsletter_path], text=True)
        print(f"File type: {file_info.strip()}")
    except:
        print("Could not determine file type")
    
    # Initialize Textract client
    session = boto3.Session(profile_name='solve-global')
    textract = session.client('textract', region_name='us-east-1')
    
    print(f"\n1. Testing newsletter PDF with Textract...")
    print("-" * 40)
    
    try:
        # Read the PDF file
        with open(newsletter_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"✅ Successfully read {len(pdf_bytes):,} bytes from file")
        
        # Test with Textract using bytes
        print("Calling Textract detect_document_text...")
        
        response = textract.detect_document_text(
            Document={
                'Bytes': pdf_bytes
            }
        )
        
        print("🎉 SUCCESS! Textract processed the newsletter PDF!")
        
        # Show results
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        pages = set(block.get('Page', 1) for block in blocks if 'Page' in block)
        
        print(f"✅ Detected {len(blocks)} total blocks")
        print(f"✅ Detected {len(lines)} text lines")
        print(f"✅ Detected {len(pages)} pages")
        
        if lines:
            print(f"\nFirst 10 lines of extracted text:")
            print("-" * 30)
            for i, line in enumerate(lines[:10]):
                print(f"  {i+1}: {line}")
            print("-" * 30)
        
        # Test with S3 upload as well
        print(f"\n2. Testing same file via S3...")
        print("-" * 40)
        
        s3 = session.client('s3')
        test_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
        test_key = 'test/newsletter_test.pdf'
        
        print(f"Uploading to s3://{test_bucket}/{test_key}")
        
        s3.put_object(
            Bucket=test_bucket,
            Key=test_key,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        
        print("✅ Upload completed")
        
        # Test Textract with S3 reference
        print("Testing Textract with S3 reference...")
        
        try:
            s3_response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': test_bucket,
                        'Name': test_key
                    }
                }
            )
            
            print("🎉 SUCCESS! Textract also works with S3 reference!")
            
            s3_blocks = s3_response.get('Blocks', [])
            s3_lines = [block['Text'] for block in s3_blocks if block['BlockType'] == 'LINE']
            
            print(f"✅ S3 version: {len(s3_blocks)} blocks, {len(s3_lines)} lines")
            
            # Compare results
            if len(lines) == len(s3_lines):
                print("✅ Both methods produced identical results!")
            else:
                print(f"⚠️  Slight difference: Local={len(lines)} lines, S3={len(s3_lines)} lines")
            
        except Exception as s3_error:
            print(f"❌ S3 version failed: {str(s3_error)}")
        
        # Clean up
        try:
            s3.delete_object(Bucket=test_bucket, Key=test_key)
            print("🧹 Cleaned up test file")
        except:
            pass
        
        return True, len(lines), len(pages)
        
    except Exception as e:
        print(f"❌ Newsletter PDF also failed: {str(e)}")
        
        # Check if it's the same error
        if "UnsupportedDocumentException" in str(e):
            print("⚠️  Same UnsupportedDocumentException - might be a broader World Bank PDF issue")
        else:
            print("🤔 Different error - this gives us more clues")
        
        return False, 0, 0

def test_with_pypdf2_comparison():
    """Test the newsletter with PyPDF2 for comparison"""
    print(f"\n3. Testing newsletter with PyPDF2 for comparison...")
    print("-" * 40)
    
    newsletter_path = "/Users/chris/SolveGlobalWorkspace/downloads/115355-NEWS-MDGsAndBeyond-Newsletter-January2014-PUBLIC.pdf"
    
    try:
        import PyPDF2
        import io
        
        with open(newsletter_path, 'rb') as f:
            pdf_bytes = f.read()
        
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        page_count = len(pdf_reader.pages)
        print(f"✅ PyPDF2 detected {page_count} pages")
        
        # Extract text from first page
        if page_count > 0:
            first_page_text = pdf_reader.pages[0].extract_text()
            print(f"✅ First page text length: {len(first_page_text)} characters")
            
            if first_page_text.strip():
                print("First few lines from PyPDF2:")
                lines = first_page_text.strip().split('\n')[:5]
                for i, line in enumerate(lines):
                    if line.strip():
                        print(f"  {i+1}: {line.strip()}")
            else:
                print("⚠️  PyPDF2 extracted empty text")
        
        return True
        
    except Exception as e:
        print(f"❌ PyPDF2 test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("World Bank Newsletter PDF Test")
    print("Testing different document to isolate the issue")
    
    success, lines, pages = test_newsletter_pdf()
    
    if success:
        print(f"\n🎉 GREAT NEWS!")
        print(f"The newsletter PDF works perfectly with Textract!")
        print(f"Extracted {lines} lines from {pages} pages")
        print(f"\nThis suggests the issue is specific to your climate risk document collection,")
        print(f"not a general World Bank PDF problem.")
        
        # Test PyPDF2 for comparison
        test_with_pypdf2_comparison()
        
    else:
        print(f"\n🤔 INTERESTING...")
        print(f"The newsletter PDF also failed with Textract.")
        print(f"This might indicate a broader compatibility issue with World Bank PDFs.")
        
        # Still test PyPDF2
        pypdf2_success = test_with_pypdf2_comparison()
        
        if pypdf2_success:
            print(f"\n✅ But PyPDF2 works - confirming our hybrid approach is correct!")
        
    print(f"\n" + "="*60)
    print("NEXT STEPS:")
    print("Based on these results, we can determine if the issue is:")
    print("1. Specific to climate risk docs (if newsletter works)")
    print("2. General World Bank PDF issue (if newsletter also fails)")
    print("3. Textract regional/account issue (if both fail but PyPDF2 works)")
    print("="*60)
