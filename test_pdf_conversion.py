#!/usr/bin/env python3
"""
Test PDF conversion to see if we can make a working PDF fail like the others
"""

import boto3
import os
import tempfile
import subprocess
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_working_pdf():
    """Create a PDF we know works with Textract"""
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_working.pdf')
    
    c = canvas.Canvas(temp_file.name, pagesize=letter)
    c.drawString(100, 750, "This is a working PDF")
    c.drawString(100, 730, "Created with ReportLab")
    c.drawString(100, 710, "Should work with Textract")
    c.showPage()
    c.save()
    
    return temp_file.name

def test_pdf_with_textract(pdf_path, description):
    """Test a PDF with Textract"""
    
    print(f"\nTesting: {description}")
    print(f"File: {os.path.basename(pdf_path)}")
    print(f"Size: {os.path.getsize(pdf_path):,} bytes")
    
    try:
        session = boto3.Session(profile_name='solve-global')
        textract = session.client('textract', region_name='us-east-1')
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        response = textract.detect_document_text(
            Document={'Bytes': pdf_bytes}
        )
        
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        
        print(f"✅ SUCCESS: {len(lines)} lines extracted")
        if lines:
            print(f"   First line: {lines[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def compare_pdf_internals():
    """Compare internal structure of working vs failing PDFs"""
    
    print("PDF Internal Structure Comparison")
    print("=" * 60)
    
    # Create working PDF
    working_pdf = create_working_pdf()
    failing_pdf = "/Users/chris/climate-risk-rag-aws/test_pdfs/Factorization Machines - Amazon SageMaker.pdf"
    
    try:
        # Test both
        working_result = test_pdf_with_textract(working_pdf, "ReportLab Generated (Known Working)")
        failing_result = test_pdf_with_textract(failing_pdf, "Amazon SageMaker PDF (Known Failing)")
        
        if working_result and not failing_result:
            print(f"\n🔍 ANALYZING DIFFERENCES:")
            print("-" * 40)
            
            # Compare file info
            try:
                working_info = subprocess.check_output(['file', working_pdf], text=True).strip()
                failing_info = subprocess.check_output(['file', failing_pdf], text=True).strip()
                
                print(f"Working PDF: {working_info}")
                print(f"Failing PDF: {failing_info}")
                
            except Exception as e:
                print(f"Could not get file info: {e}")
            
            # Compare with pdfinfo if available
            try:
                print(f"\nWorking PDF info:")
                working_pdfinfo = subprocess.check_output(['pdfinfo', working_pdf], text=True)
                print(working_pdfinfo)
                
                print(f"\nFailing PDF info:")
                failing_pdfinfo = subprocess.check_output(['pdfinfo', failing_pdf], text=True)
                print(failing_pdfinfo)
                
            except Exception as e:
                print(f"pdfinfo not available: {e}")
            
            # Try to identify specific differences
            print(f"\n🤔 HYPOTHESIS:")
            print("The failing PDF may have:")
            print("• Different PDF version/features")
            print("• Specific metadata that Textract rejects")
            print("• Compression or encoding Textract doesn't support")
            print("• Security settings or restrictions")
            
        elif not working_result:
            print(f"\n🚨 CRITICAL: Even our working PDF now fails!")
            print("This suggests a broader Textract service issue")
            
    finally:
        # Clean up
        if os.path.exists(working_pdf):
            os.unlink(working_pdf)

def test_textract_with_simple_content():
    """Test Textract with the absolute simplest possible content"""
    
    print(f"\n" + "="*60)
    print("TESTING WITH MINIMAL CONTENT")
    print("="*60)
    
    # Create the most basic PDF possible
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_minimal.pdf')
    
    c = canvas.Canvas(temp_file.name, pagesize=letter)
    c.drawString(100, 750, "Hello World")
    c.showPage()
    c.save()
    
    try:
        result = test_pdf_with_textract(temp_file.name, "Minimal PDF (2 words)")
        
        if not result:
            print(f"\n🚨 CRITICAL FINDING:")
            print("Even minimal PDFs fail!")
            print("This indicates a fundamental Textract service issue")
            
            # Test if it's a recent issue
            print(f"\n🔍 TESTING SERVICE STATUS:")
            
            session = boto3.Session(profile_name='solve-global')
            textract = session.client('textract', region_name='us-east-1')
            
            try:
                # Try to get service status
                response = textract.get_document_analysis(JobId='test')
            except Exception as e:
                if 'InvalidJobIdException' in str(e):
                    print("✅ Textract service is responding normally")
                else:
                    print(f"⚠️  Unexpected service response: {str(e)}")
        
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

if __name__ == "__main__":
    compare_pdf_internals()
    test_textract_with_simple_content()
    
    print(f"\n" + "="*60)
    print("FINAL ANALYSIS:")
    print("If even simple ReportLab PDFs now fail, there's a service issue.")
    print("If simple PDFs work but real-world PDFs don't, it's a format issue.")
    print("="*60)
