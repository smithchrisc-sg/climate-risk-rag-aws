#!/usr/bin/env python3
"""
Comprehensive PDF Compatibility Test Suite
Tests Textract with PDFs from various sources and generation methods
"""

import boto3
import json
import os
import tempfile
import subprocess
from typing import List, Dict, Tuple

def create_test_pdfs() -> List[Dict]:
    """Create test PDFs using different generation methods"""
    
    test_pdfs = []
    
    # Test 1: ReportLab (Python-generated)
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_reportlab.pdf')
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        c.drawString(100, 750, "ReportLab Generated PDF")
        c.drawString(100, 730, "This PDF was created using Python ReportLab library")
        c.drawString(100, 710, "Should be very compatible with modern PDF readers")
        c.showPage()
        c.save()
        
        test_pdfs.append({
            'name': 'ReportLab (Python)',
            'path': temp_file.name,
            'source': 'programmatic',
            'expected': 'success'
        })
        
    except ImportError:
        print("ReportLab not available")
    
    # Test 2: WeasyPrint (HTML to PDF)
    try:
        import weasyprint
        
        html_content = """
        <html>
        <body>
            <h1>WeasyPrint Generated PDF</h1>
            <p>This PDF was generated from HTML using WeasyPrint</p>
            <p>It represents web-to-PDF conversion</p>
            <p>Should be modern and compatible</p>
        </body>
        </html>
        """
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_weasyprint.pdf')
        weasyprint.HTML(string=html_content).write_pdf(temp_file.name)
        
        test_pdfs.append({
            'name': 'WeasyPrint (HTML→PDF)',
            'path': temp_file.name,
            'source': 'web_conversion',
            'expected': 'success'
        })
        
    except ImportError:
        print("WeasyPrint not available - trying to install...")
        try:
            subprocess.check_call(['pip', 'install', 'weasyprint'])
            import weasyprint
            
            html_content = """
            <html><body>
                <h1>WeasyPrint Generated PDF</h1>
                <p>This PDF was generated from HTML using WeasyPrint</p>
            </body></html>
            """
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_weasyprint.pdf')
            weasyprint.HTML(string=html_content).write_pdf(temp_file.name)
            
            test_pdfs.append({
                'name': 'WeasyPrint (HTML→PDF)',
                'path': temp_file.name,
                'source': 'web_conversion',
                'expected': 'success'
            })
            
        except Exception as e:
            print(f"Could not use WeasyPrint: {e}")
    
    # Test 3: Create a "problematic" PDF with specific characteristics
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='_complex.pdf')
        c = canvas.Canvas(temp_file.name, pagesize=letter)
        
        # Add metadata (similar to institutional docs)
        c.setTitle("Complex Test Document")
        c.setAuthor("Test Institution")
        c.setSubject("Compatibility Testing")
        c.setCreator("Test PDF Generator v1.0")
        
        # Add content
        c.drawString(100, 750, "Complex PDF with Metadata")
        c.drawString(100, 730, "This PDF has institutional-style metadata")
        c.drawString(100, 710, "Testing if metadata affects Textract compatibility")
        
        c.showPage()
        c.save()
        
        test_pdfs.append({
            'name': 'Complex (with metadata)',
            'path': temp_file.name,
            'source': 'programmatic_complex',
            'expected': 'success'
        })
        
    except Exception as e:
        print(f"Could not create complex PDF: {e}")
    
    return test_pdfs

def test_pdf_with_textract(pdf_info: Dict) -> Dict:
    """Test a single PDF with Textract"""
    
    result = {
        'name': pdf_info['name'],
        'source': pdf_info['source'],
        'expected': pdf_info['expected'],
        'textract_success': False,
        'pypdf2_success': False,
        'error': None,
        'lines_extracted': 0,
        'file_size': 0
    }
    
    try:
        # Get file info
        if os.path.exists(pdf_info['path']):
            result['file_size'] = os.path.getsize(pdf_info['path'])
        else:
            result['error'] = 'File not found'
            return result
        
        # Initialize clients
        session = boto3.Session(profile_name='solve-global')
        textract = session.client('textract', region_name='us-east-1')
        
        # Read PDF
        with open(pdf_info['path'], 'rb') as f:
            pdf_bytes = f.read()
        
        # Test Textract
        try:
            response = textract.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            
            blocks = response.get('Blocks', [])
            lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
            
            result['textract_success'] = True
            result['lines_extracted'] = len(lines)
            
        except Exception as textract_error:
            result['error'] = str(textract_error)
        
        # Test PyPDF2 for comparison
        try:
            import PyPDF2
            import io
            
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text()
            
            if text_content.strip():
                result['pypdf2_success'] = True
            
        except Exception as pypdf2_error:
            pass  # PyPDF2 failure is less critical for this test
        
    except Exception as e:
        result['error'] = f"General error: {str(e)}"
    
    return result

def run_comprehensive_test():
    """Run comprehensive PDF compatibility test"""
    
    print("Comprehensive PDF Compatibility Test")
    print("=" * 60)
    print("Testing Textract with PDFs from various sources...")
    print()
    
    # Create test PDFs
    print("Creating test PDFs...")
    test_pdfs = create_test_pdfs()
    
    if not test_pdfs:
        print("❌ Could not create any test PDFs")
        return
    
    print(f"✅ Created {len(test_pdfs)} test PDFs")
    print()
    
    # Test each PDF
    results = []
    for pdf_info in test_pdfs:
        print(f"Testing: {pdf_info['name']}")
        print(f"Source: {pdf_info['source']}")
        print(f"Size: {os.path.getsize(pdf_info['path']):,} bytes")
        
        result = test_pdf_with_textract(pdf_info)
        results.append(result)
        
        if result['textract_success']:
            print(f"✅ Textract: SUCCESS ({result['lines_extracted']} lines)")
        else:
            print(f"❌ Textract: FAILED - {result['error']}")
        
        if result['pypdf2_success']:
            print(f"✅ PyPDF2: SUCCESS")
        else:
            print(f"⚠️  PyPDF2: Limited success")
        
        print("-" * 40)
    
    # Summary
    print("\nSUMMARY:")
    print("=" * 60)
    
    textract_successes = sum(1 for r in results if r['textract_success'])
    total_tests = len(results)
    
    print(f"Textract Success Rate: {textract_successes}/{total_tests} ({textract_successes/total_tests*100:.1f}%)")
    
    if textract_successes == total_tests:
        print("✅ ALL programmatically generated PDFs work with Textract")
        print("   This strongly suggests the issue is with institutional PDF sources")
    elif textract_successes == 0:
        print("❌ NO PDFs work with Textract")
        print("   This suggests a broader Textract configuration/permission issue")
    else:
        print("🤔 MIXED results - some PDFs work, others don't")
        print("   This suggests specific PDF characteristics cause the issue")
    
    # Detailed analysis
    print("\nDETAILED RESULTS:")
    for result in results:
        status = "✅ PASS" if result['textract_success'] else "❌ FAIL"
        print(f"{status} {result['name']} ({result['source']})")
        if not result['textract_success'] and result['error']:
            print(f"      Error: {result['error']}")
    
    # Clean up
    print("\nCleaning up test files...")
    for pdf_info in test_pdfs:
        try:
            if os.path.exists(pdf_info['path']):
                os.unlink(pdf_info['path'])
        except:
            pass
    
    return results

if __name__ == "__main__":
    results = run_comprehensive_test()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("Based on these results, we can:")
    print("1. Confirm if it's source-specific (institutional vs programmatic)")
    print("2. Identify specific PDF characteristics that cause issues")
    print("3. Validate our hybrid approach covers the compatibility gaps")
    print("="*60)
