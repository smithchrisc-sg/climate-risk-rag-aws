#!/usr/bin/env python3
"""
Comprehensive PDF Content Analysis
Determines if PDFs contain extractable text or are image-based scans
"""

import os
import subprocess
import PyPDF2
import io
from pathlib import Path

def analyze_pdf_content(pdf_path: str) -> dict:
    """Analyze PDF to determine if it contains extractable text or images"""
    
    result = {
        'filename': os.path.basename(pdf_path),
        'size_mb': round(os.path.getsize(pdf_path) / (1024*1024), 2),
        'has_text_layer': False,
        'text_length': 0,
        'page_count': 0,
        'is_likely_scanned': False,
        'pdf_info': {},
        'analysis': ''
    }
    
    try:
        # PyPDF2 analysis
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        result['page_count'] = len(pdf_reader.pages)
        
        # Try to extract text
        full_text = ""
        text_pages = 0
        
        for i, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    full_text += page_text
                    text_pages += 1
            except Exception as e:
                print(f"  Error extracting from page {i+1}: {str(e)}")
        
        result['text_length'] = len(full_text.strip())
        result['has_text_layer'] = result['text_length'] > 0
        
        # Get PDF metadata
        if pdf_reader.metadata:
            result['pdf_info'] = {
                'creator': pdf_reader.metadata.get('/Creator', 'Unknown'),
                'producer': pdf_reader.metadata.get('/Producer', 'Unknown'),
                'title': pdf_reader.metadata.get('/Title', 'Unknown'),
                'subject': pdf_reader.metadata.get('/Subject', 'Unknown')
            }
        
        # Analysis
        if result['text_length'] == 0:
            result['is_likely_scanned'] = True
            result['analysis'] = "No extractable text found - likely scanned/image-based PDF"
        elif result['text_length'] < 100:
            result['is_likely_scanned'] = True
            result['analysis'] = "Very little text found - possibly scanned with poor OCR"
        elif text_pages < result['page_count'] * 0.5:
            result['is_likely_scanned'] = True
            result['analysis'] = "Mixed content - some pages may be scanned images"
        else:
            result['analysis'] = "Good text content - should work with text extraction"
        
    except Exception as e:
        result['analysis'] = f"Error analyzing PDF: {str(e)}"
    
    return result

def analyze_test_collection():
    """Analyze the entire test PDF collection"""
    
    print("PDF Content Analysis")
    print("=" * 80)
    print("Checking if PDFs contain extractable text or are image-based scans")
    print()
    
    test_dir = "/Users/chris/climate-risk-rag-aws/test_pdfs"
    
    if not os.path.exists(test_dir):
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    pdf_files = [f for f in os.listdir(test_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ No PDF files found")
        return
    
    print(f"Analyzing {len(pdf_files)} PDF files...")
    print()
    
    results = []
    text_based_count = 0
    scanned_count = 0
    
    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(test_dir, pdf_file)
        
        print(f"Analyzing: {pdf_file}")
        result = analyze_pdf_content(pdf_path)
        results.append(result)
        
        print(f"  Size: {result['size_mb']} MB | Pages: {result['page_count']}")
        print(f"  Text length: {result['text_length']:,} characters")
        print(f"  Has text layer: {'✅ YES' if result['has_text_layer'] else '❌ NO'}")
        print(f"  Analysis: {result['analysis']}")
        
        if result['pdf_info'].get('creator') != 'Unknown':
            print(f"  Creator: {result['pdf_info']['creator']}")
        if result['pdf_info'].get('producer') != 'Unknown':
            print(f"  Producer: {result['pdf_info']['producer']}")
        
        if result['is_likely_scanned']:
            scanned_count += 1
            print("  🔍 LIKELY SCANNED/IMAGE-BASED")
        else:
            text_based_count += 1
            print("  📄 TEXT-BASED")
        
        print("-" * 60)
    
    # Summary
    print(f"\nSUMMARY:")
    print("=" * 80)
    print(f"Total PDFs analyzed: {len(results)}")
    print(f"Text-based PDFs: {text_based_count}")
    print(f"Scanned/Image-based PDFs: {scanned_count}")
    print(f"Scanned percentage: {scanned_count/len(results)*100:.1f}%")
    
    if scanned_count == len(results):
        print("\n🚨 CRITICAL FINDING:")
        print("ALL PDFs appear to be scanned/image-based!")
        print("This explains why Textract fails - it needs OCR, not text extraction!")
        
        print("\n💡 SOLUTION:")
        print("Use Textract's AnalyzeDocument with OCR features instead of DetectDocumentText")
        
    elif scanned_count > len(results) * 0.8:
        print("\n⚠️  MAJOR FINDING:")
        print("Most PDFs are scanned/image-based")
        print("Mixed collection requires OCR capabilities")
        
    else:
        print("\n🤔 MIXED RESULTS:")
        print("Some PDFs have text, others are scanned")
        print("This suggests a different issue with Textract")
    
    # Show detailed breakdown
    print(f"\nDETAILED BREAKDOWN:")
    print("-" * 80)
    for result in results:
        status = "📄 TEXT" if not result['is_likely_scanned'] else "🖼️  SCAN"
        print(f"{status} | {result['filename'][:50]:50} | {result['text_length']:>8,} chars")
    
    return results

def test_ocr_hypothesis():
    """Test if these PDFs work with Textract's OCR features"""
    
    print(f"\n" + "="*80)
    print("TESTING OCR HYPOTHESIS")
    print("="*80)
    print("If PDFs are image-based, they need OCR (AnalyzeDocument) not text extraction")
    
    # Test with a small PDF
    test_pdf = "/Users/chris/climate-risk-rag-aws/test_pdfs/Factorization Machines - Amazon SageMaker.pdf"
    
    if not os.path.exists(test_pdf):
        print("❌ Test PDF not found")
        return
    
    try:
        import boto3
        
        session = boto3.Session(profile_name='solve-global')
        textract = session.client('textract', region_name='us-east-1')
        
        with open(test_pdf, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"Testing OCR with: {os.path.basename(test_pdf)}")
        
        # Try AnalyzeDocument instead of DetectDocumentText
        try:
            response = textract.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES', 'FORMS']  # OCR with structure detection
            )
            
            blocks = response.get('Blocks', [])
            lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
            
            print(f"✅ OCR SUCCESS! Detected {len(lines)} lines")
            
            if lines:
                print("First few lines:")
                for i, line in enumerate(lines[:3]):
                    print(f"  {i+1}: {line}")
            
            return True
            
        except Exception as e:
            print(f"❌ OCR also failed: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Could not test OCR: {str(e)}")
        return False

if __name__ == "__main__":
    results = analyze_test_collection()
    
    # Test OCR hypothesis
    test_ocr_hypothesis()
    
    print(f"\n" + "="*80)
    print("CONCLUSIONS:")
    print("If most PDFs are scanned/image-based, this explains:")
    print("1. Why DetectDocumentText fails (no text layer)")
    print("2. Why PyPDF2 works (extracts what little text exists)")
    print("3. Why AWS Console shows 'no text found'")
    print("4. Why we need OCR-based processing instead")
    print("="*80)
