#!/usr/bin/env python3
"""
Test Textract with original local PDF file to isolate the issue
"""

import boto3
import json
import os

def test_original_pdf():
    """Test Textract with the original PDF file from local filesystem"""
    
    # Path to original PDF
    original_pdf_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/data/raw/0032f6cb_f0caef34.pdf"
    
    print("Testing Original PDF File with Textract")
    print("=" * 60)
    print(f"File: {original_pdf_path}")
    
    # Check if file exists
    if not os.path.exists(original_pdf_path):
        print(f"❌ File not found: {original_pdf_path}")
        return False
    
    # Get file info
    file_size = os.path.getsize(original_pdf_path)
    print(f"Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # Initialize Textract client
    session = boto3.Session(profile_name='solve-global')
    textract = session.client('textract', region_name='us-east-1')
    
    print("\n1. Testing with local file bytes...")
    print("-" * 40)
    
    try:
        # Read the PDF file
        with open(original_pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"✅ Successfully read {len(pdf_bytes):,} bytes from local file")
        
        # Test with Textract using bytes
        print("Calling Textract detect_document_text with bytes...")
        
        response = textract.detect_document_text(
            Document={
                'Bytes': pdf_bytes
            }
        )
        
        print("✅ SUCCESS! Textract processed the original PDF successfully!")
        
        # Show results
        blocks = response.get('Blocks', [])
        lines = [block['Text'] for block in blocks if block['BlockType'] == 'LINE']
        
        print(f"Detected {len(blocks)} total blocks")
        print(f"Detected {len(lines)} text lines")
        
        if lines:
            print(f"\nFirst few lines of extracted text:")
            for i, line in enumerate(lines[:5]):
                print(f"  {i+1}: {line}")
        
        # Compare with S3 version
        print(f"\n2. Now testing the SAME file uploaded to S3...")
        print("-" * 40)
        
        # Upload to a test location in S3
        s3 = session.client('s3')
        test_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'  # Use our test bucket
        test_key = 'test/original_0032f6cb_f0caef34.pdf'
        
        print(f"Uploading to s3://{test_bucket}/{test_key}")
        
        s3.put_object(
            Bucket=test_bucket,
            Key=test_key,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        
        print("✅ Upload completed")
        
        # Now test Textract with S3 reference
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
            
            print("✅ SUCCESS! Textract also works with S3 reference!")
            
            s3_blocks = s3_response.get('Blocks', [])
            s3_lines = [block['Text'] for block in s3_blocks if block['BlockType'] == 'LINE']
            
            print(f"S3 version detected {len(s3_blocks)} blocks, {len(s3_lines)} lines")
            
            # Compare results
            if len(lines) == len(s3_lines):
                print("✅ Both methods produced identical results!")
            else:
                print(f"⚠️  Different results: Local={len(lines)} lines, S3={len(s3_lines)} lines")
            
        except Exception as s3_error:
            print(f"❌ S3 version failed: {str(s3_error)}")
            print("This suggests the issue is with S3 access or the migrated files")
        
        # Clean up test file
        try:
            s3.delete_object(Bucket=test_bucket, Key=test_key)
            print("🧹 Cleaned up test file")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Failed with original PDF: {str(e)}")
        return False

def compare_files():
    """Compare the original file with the migrated S3 version"""
    print(f"\n3. Comparing original vs migrated file...")
    print("-" * 40)
    
    original_path = "/Volumes/G-RAID Photo 24TB/climate_risk_rag/data/raw/0032f6cb_f0caef34.pdf"
    
    # Download the migrated version
    session = boto3.Session(profile_name='solve-global')
    s3 = session.client('s3')
    
    migrated_bucket = 'solve-global-kr-documents-861276078413-us-east-1'
    migrated_key = 'documents/0032f6cb_f0caef34.pdf'
    
    try:
        # Download migrated version
        response = s3.get_object(Bucket=migrated_bucket, Key=migrated_key)
        migrated_bytes = response['Body'].read()
        
        # Read original
        with open(original_path, 'rb') as f:
            original_bytes = f.read()
        
        print(f"Original size: {len(original_bytes):,} bytes")
        print(f"Migrated size: {len(migrated_bytes):,} bytes")
        
        if original_bytes == migrated_bytes:
            print("✅ Files are IDENTICAL - migration preserved file perfectly")
        else:
            print("❌ Files are DIFFERENT - migration may have altered the file")
            
            # Check first few bytes
            print("First 100 bytes comparison:")
            print(f"Original: {original_bytes[:100]}")
            print(f"Migrated: {migrated_bytes[:100]}")
        
    except Exception as e:
        print(f"❌ Could not compare files: {str(e)}")

if __name__ == "__main__":
    success = test_original_pdf()
    
    if success:
        compare_files()
        
        print(f"\n" + "="*60)
        print("CONCLUSION:")
        print("If the original PDF works with Textract but the migrated version doesn't,")
        print("then the issue is likely with:")
        print("1. S3 permissions/configuration")
        print("2. File corruption during migration") 
        print("3. S3 metadata or storage class issues")
        print("="*60)
    else:
        print(f"\n" + "="*60)
        print("CONCLUSION:")
        print("If even the original PDF fails with Textract, then the issue is")
        print("inherent to the PDF format/content, not the migration process.")
        print("="*60)
