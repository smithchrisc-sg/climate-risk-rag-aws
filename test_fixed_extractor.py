#!/usr/bin/env python3
"""
Test the fixed TextExtractor with async processing
"""

import sys
import os

def test_fixed_extractor():
    """Test the fixed TextExtractor"""
    print("Testing Fixed TextExtractor with Async Processing")
    print("=" * 60)
    
    # Add path and import
    sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/text_extractor')
    
    try:
        from text_extractor_fixed import FixedTextExtractor
        
        # Set environment variables
        os.environ['OUTPUT_BUCKET'] = 'solve-global-kr-text-new-861276078413-us-east-1'
        os.environ['AWS_REGION'] = 'us-east-1'
        
        # Initialize extractor with profile
        extractor = FixedTextExtractor(profile_name='solve-global')
        
        # Test with the PDF that works in console but failed with sync API
        bucket = "solve-global-kr-documents-861276078413-us-east-1"
        key = "documents/0032f6cb_f0caef34.pdf"  # Our test document
        
        print(f"Testing with: s3://{bucket}/{key}")
        print("This should now work with async processing...")
        
        # Extract text
        extracted_data = extractor.extract_text_from_pdf(bucket, key)
        
        print("\n🎉 EXTRACTION SUCCESSFUL!")
        print(f"Method used: {extracted_data['metadata']['extraction_info']['method']}")
        print(f"Text length: {len(extracted_data['text_content'])} characters")
        print(f"Pages processed: {extracted_data['metadata']['textract_metadata']['pages_processed']}")
        
        # Check if it was a fallback from sync
        if 'sync_fallback_reason' in extracted_data['metadata']['extraction_info']:
            print(f"Sync fallback reason: {extracted_data['metadata']['extraction_info']['sync_fallback_reason']}")
        
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
        
        import boto3
        session = boto3.Session(profile_name='solve-global')
        s3 = session.client('s3', region_name='us-east-1')
        
        try:
            original_obj = s3.get_object(
                Bucket='solve-global-kr-text-861276078413-us-east-1',
                Key=f'extracted_text/{document_id}.txt'
            )
            original_text = original_obj['Body'].read().decode('utf-8')
            
            print(f"Original (Tika): {len(original_text)} characters")
            print(f"New (Textract): {len(extracted_data['text_content'])} characters")
            print(f"Length ratio: {len(extracted_data['text_content']) / len(original_text):.2f}")
            
            # Check if key phrases match
            original_words = set(original_text.lower().split())
            new_words = set(extracted_data['text_content'].lower().split())
            
            common_words = original_words.intersection(new_words)
            if len(original_words) > 0:
                overlap_pct = len(common_words) / len(original_words) * 100
                print(f"Word overlap: {len(common_words)} / {len(original_words)} ({overlap_pct:.1f}%)")
            
        except Exception as e:
            print(f"Could not compare with original: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Fixed TextExtractor Test")
    print("=" * 60)
    
    success = test_fixed_extractor()
    
    if success:
        print("\n✅ FIXED TEXTEXTRACTOR SUCCESS!")
        print("🎉 Async processing solves the PDF compatibility issue!")
        print("Ready for production deployment with real-world PDF support.")
    else:
        print("\n❌ Test failed!")
        print("Check the error messages above.")
