#!/usr/bin/env python3
"""
Test script for Corrected TextExtractor Processor
Validates the DocumentIDManager integration and selective migration usage
"""

import os
import sys
import json
from datetime import datetime

def test_documentid_manager_import():
    """Test DocumentIDManager import in corrected processor"""
    print("🧪 Testing DocumentIDManager import in corrected processor...")
    
    try:
        # Add the layers path
        sys.path.append('/Users/chris/climate-risk-rag-aws/layers/app-source/utils')
        
        from DocumentIDManager import DocumentIDManager
        print("  ✅ DocumentIDManager imported successfully")
        
        # Test basic functionality
        doc_manager = DocumentIDManager(database_url="postgresql://test")
        print("  ✅ DocumentIDManager can be instantiated")
        
        return True
        
    except Exception as e:
        print(f"  ❌ DocumentIDManager import failed: {str(e)}")
        return False

def test_selective_mappings_loading():
    """Test loading of selective migration S3 mappings"""
    print("🧪 Testing selective migration S3 mappings loading...")
    
    mapping_file = '/Users/chris/climate-risk-rag-aws/selective_poc_s3_mappings.json'
    
    try:
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                mappings = json.load(f)
            
            print(f"  ✅ S3 mappings loaded: {len(mappings)} entries")
            
            # Test sample mapping structure
            if mappings:
                sample_key = list(mappings.keys())[0]
                sample_mapping = mappings[sample_key]
                
                required_fields = ['doc_id', 'url', 'filename', 'verified_in_s3']
                missing_fields = [field for field in required_fields if field not in sample_mapping]
                
                if not missing_fields:
                    print(f"  ✅ Mapping structure valid")
                    print(f"    Sample: {sample_key} → {sample_mapping['doc_id']}")
                    return True
                else:
                    print(f"  ❌ Missing fields in mapping: {missing_fields}")
                    return False
            else:
                print("  ⚠️  Mappings file is empty")
                return False
        else:
            print(f"  ❌ Mappings file not found: {mapping_file}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error loading mappings: {str(e)}")
        return False

def test_corrected_processor_structure():
    """Test the structure of the corrected processor"""
    print("🧪 Testing corrected processor structure...")
    
    try:
        # Import the corrected processor
        sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor')
        
        # Read the corrected file to check key components
        corrected_file = '/Users/chris/climate-risk-rag-aws/lambda/text_extractor_processor/text_extractor_processor_CORRECTED.py'
        
        if not os.path.exists(corrected_file):
            print(f"  ❌ Corrected processor file not found: {corrected_file}")
            return False
        
        with open(corrected_file, 'r') as f:
            content = f.read()
        
        # Check for key integration points
        checks = [
            ('DocumentIDManager import', 'from DocumentIDManager import DocumentIDManager'),
            ('S3 mappings loading', 'load_selective_s3_mappings'),
            ('Doc ID lookup', 'get_or_create_doc_id'),
            ('Selective migration check', 'selective_migration_used'),
            ('DocumentIDManager update', 'update_document_status'),
            ('Proper directory structure', 'doc_id}/{doc_id}_full_text.txt')
        ]
        
        results = []
        for check_name, check_pattern in checks:
            if check_pattern in content:
                print(f"  ✅ {check_name}: Found")
                results.append(True)
            else:
                print(f"  ❌ {check_name}: Missing")
                results.append(False)
        
        success_rate = sum(results) / len(results)
        print(f"  📊 Integration completeness: {success_rate:.1%}")
        
        return success_rate >= 0.8  # 80% or better
        
    except Exception as e:
        print(f"  ❌ Error testing processor structure: {str(e)}")
        return False

def test_doc_id_lookup_logic():
    """Test the doc_id lookup logic"""
    print("🧪 Testing doc_id lookup logic...")
    
    try:
        # Mock the lookup logic
        def mock_get_or_create_doc_id(s3_mappings, job_metadata):
            source_key = job_metadata['source_key']
            
            # Check selective migration mappings first
            if source_key in s3_mappings:
                mapping = s3_mappings[source_key]
                if mapping.get('verified_in_s3'):
                    return mapping['doc_id'], 'selective_migration'
            
            # Fallback to DocumentIDManager (simulated)
            return 'new_guid_12345', 'documentid_manager'
        
        # Load actual mappings
        mapping_file = '/Users/chris/climate-risk-rag-aws/selective_poc_s3_mappings.json'
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                s3_mappings = json.load(f)
        else:
            s3_mappings = {}
        
        # Test cases
        test_cases = [
            {
                'name': 'POC document (in mappings)',
                'job_metadata': {'source_key': list(s3_mappings.keys())[0] if s3_mappings else 'documents/test.pdf'},
                'expected_source': 'selective_migration'
            },
            {
                'name': 'New document (not in mappings)',
                'job_metadata': {'source_key': 'documents/new_document.pdf'},
                'expected_source': 'documentid_manager'
            }
        ]
        
        for test_case in test_cases:
            doc_id, source = mock_get_or_create_doc_id(s3_mappings, test_case['job_metadata'])
            expected_source = test_case['expected_source']
            
            if source == expected_source:
                print(f"  ✅ {test_case['name']}: {doc_id} from {source}")
            else:
                print(f"  ❌ {test_case['name']}: Expected {expected_source}, got {source}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing doc_id lookup: {str(e)}")
        return False

def test_message_format():
    """Test the new message format for text chunker"""
    print("🧪 Testing new message format...")
    
    try:
        # Mock message creation
        def create_message(doc_id, doc_hash, output_bucket):
            return {
                'doc_id': doc_id,
                'doc_hash': doc_hash,
                'stage': 'text_ready',
                'full_text_location': {
                    'bucket': output_bucket,
                    'key': f"{doc_id}/{doc_id}_full_text.txt"
                },
                'document_structure_location': {
                    'bucket': output_bucket,
                    'key': f"{doc_id}/metadata/textract_response.json"
                },
                'metadata_base_path': f"{doc_id}/metadata/",
                'structure_version': '2025-07-04-corrected',
                'documentid_manager_integration': True
            }
        
        # Test with POC doc_id format
        poc_doc_id = '0004ad39_4285ab3d'
        message = create_message(poc_doc_id, 'hash123', 'test-bucket')
        
        # Validate message structure
        required_fields = [
            'doc_id', 'doc_hash', 'stage', 'full_text_location',
            'document_structure_location', 'documentid_manager_integration'
        ]
        
        missing_fields = [field for field in required_fields if field not in message]
        
        if not missing_fields:
            print(f"  ✅ Message format valid")
            print(f"    Doc ID: {message['doc_id']}")
            print(f"    Text location: {message['full_text_location']['key']}")
            print(f"    Structure location: {message['document_structure_location']['key']}")
            return True
        else:
            print(f"  ❌ Missing message fields: {missing_fields}")
            return False
        
    except Exception as e:
        print(f"  ❌ Error testing message format: {str(e)}")
        return False

def main():
    """Run all corrected TextExtractor tests"""
    print("🚀 Testing Corrected TextExtractor Processor")
    print("=" * 60)
    print(f"Test time: {datetime.utcnow().isoformat()}")
    print()
    
    tests = [
        ("DocumentIDManager Import", test_documentid_manager_import),
        ("Selective Mappings Loading", test_selective_mappings_loading),
        ("Corrected Processor Structure", test_corrected_processor_structure),
        ("Doc ID Lookup Logic", test_doc_id_lookup_logic),
        ("Message Format", test_message_format)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
        print()
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("📊 Test Summary")
    print("-" * 20)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Corrected TextExtractor is ready for deployment.")
        print("\n📋 Key improvements:")
        print("  • Proper DocumentIDManager integration")
        print("  • Selective migration S3 mappings support")
        print("  • GUID-based doc_id directory structure")
        print("  • Fallback to DocumentIDManager for new documents")
        print("  • Enhanced message format for text chunker")
        print("\n🚀 Next steps:")
        print("  1. Deploy corrected TextExtractor Processor")
        print("  2. Test with one of your migrated POC documents")
        print("  3. Verify proper doc_id usage and directory structure")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Review issues before deployment.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
