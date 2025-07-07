#!/usr/bin/env python3
"""
Test script for Hybrid TextExtractor
"""

import sys
import os

def test_hybrid_extractor():
    """Test the hybrid TextExtractor locally"""
    print("Testing Hybrid TextExtractor...")
    print("-" * 60)
    
    # Add path and import
    sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/text_extractor')
    
    try:
        from text_extractor_hybrid import HybridTextExtractor
        
        # Set environment variables
        os.environ['OUTPUT_BUCKET'] = 'solve-global-kr-text-new-861276078413-us-east-1'
        os.environ['AWS_REGION'] = 'us-east-1'
        
        # Initialize extractor with profile
        extractor = HybridTextExtractor(profile_name='solve-global')
        
        # Test with the document we know has issues with Textract
        bucket = "solve-global-kr-documents-861276078413-us-east-1"
        key = "documents/0032f6cb_f0caef34.pdf"
        
        print(f"Testing with: s3://{bucket}/{key}")
        print("This document failed with Textract, should fall back to PyPDF2...")
        
        # Extract text
        extracted_data = extractor.extract_text_from_pdf(bucket, key)
        
        print("\n✅ Extraction completed successfully!")
        print(f"Method used: {extracted_data['metadata']['extraction_info']['method']}")
        print(f"Text length: {len(extracted_data['text_content'])} characters")
        print(f"Word count: {extracted_data['metadata']['extraction_info']['word_count']}")
        print(f"Pages: {extracted_data['metadata']['document_structure']['statistics']['total_pages']}")
        
        # Save the extracted text
        document_id = os.path.splitext(os.path.basename(key))[0]
        output_location = extractor.save_extracted_text(extracted_data, document_id)
        
        print(f"Saved to: {output_location}")
        
        # Show sample of extracted text
        print(f"\nFirst 500 characters of extracted text:")
        print("-" * 40)
        print(extracted_data['text_content'][:500])
        if len(extracted_data['text_content']) > 500:
            print("...")
        print("-" * 40)
        
        # Compare with original extracted text
        print(f"\nComparing with original Tika extraction...")
        
        # Download original for comparison
        import boto3
        session = boto3.Session(profile_name='solve-global')
        s3 = session.client('s3', region_name='us-east-1')
        
        try:
            original_obj = s3.get_object(
                Bucket='solve-global-kr-text-861276078413-us-east-1',
                Key=f'extracted_text/{document_id}.txt'
            )
            original_text = original_obj['Body'].read().decode('utf-8')
            
            print(f"Original text length: {len(original_text)} characters")
            print(f"New text length: {len(extracted_data['text_content'])} characters")
            print(f"Length ratio: {len(extracted_data['text_content']) / len(original_text):.2f}")
            
            # Check if key phrases match
            original_words = set(original_text.lower().split())
            new_words = set(extracted_data['text_content'].lower().split())
            
            common_words = original_words.intersection(new_words)
            print(f"Common words: {len(common_words)} / {len(original_words)} ({len(common_words)/len(original_words)*100:.1f}%)")
            
        except Exception as e:
            print(f"Could not compare with original: {str(e)}")
        
        return True
        
    except ImportError as e:
        print(f"Import error: {str(e)}")
        print("Installing PyPDF2...")
        
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
            print("PyPDF2 installed successfully. Please run the test again.")
        except Exception as install_error:
            print(f"Failed to install PyPDF2: {str(install_error)}")
        
        return False
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Hybrid TextExtractor Test")
    print("=" * 60)
    
    success = test_hybrid_extractor()
    
    if success:
        print("\n✅ Hybrid TextExtractor test passed!")
        print("Ready to deploy and use for production text extraction.")
    else:
        print("\n❌ Test failed!")
        print("Check the error messages above.")
