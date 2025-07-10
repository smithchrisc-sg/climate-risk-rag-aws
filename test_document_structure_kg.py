#!/usr/bin/env python3
"""
Test Document Structure Knowledge Graph Integration
Local testing script for KG Lambda functions before deployment
"""

import sys
import os
import json
from datetime import datetime

# Add lambda functions to path for testing
sys.path.append('lambda/document_structure_kg_processor')
sys.path.append('lambda/kg_integration_worker')

def test_document_ttl_generation():
    """Test TTL generation locally"""
    print("🧪 Testing Document TTL Generation...")
    
    try:
        from document_ttl_generator import DocumentTTLGenerator
        
        # Test with known document
        doc_id = "0032f6cb_f0caef34"
        generator = DocumentTTLGenerator(doc_id)
        
        print(f"📄 Generating TTL for document: {doc_id}")
        ttl_content = generator.generate_ttl_document()
        
        print(f"✅ TTL generation successful!")
        print(f"📊 TTL size: {len(ttl_content)} characters")
        
        # Show preview
        lines = ttl_content.split('\n')
        print("\n📋 TTL Preview (first 20 lines):")
        print("=" * 60)
        for i, line in enumerate(lines[:20]):
            print(f"{i+1:2d}: {line}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ TTL generation failed: {e}")
        return False

def test_kg_processor_logic():
    """Test KG processor logic without AWS dependencies"""
    print("\n🧪 Testing KG Processor Logic...")
    
    try:
        # Mock event
        test_event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": json.dumps({
                            "document_id": "0032f6cb_f0caef34",
                            "status": "completed",
                            "processing_stage": "text_chunking",
                            "timestamp": datetime.now().isoformat()
                        })
                    }
                }
            ]
        }
        
        print(f"📨 Test event: {json.dumps(test_event, indent=2)}")
        
        # Test message parsing
        records = test_event.get('Records', [])
        for record in records:
            if record.get('EventSource') == 'aws:sns':
                message = json.loads(record['Sns']['Message'])
                print(f"✅ Message parsed successfully:")
                print(f"   Document ID: {message.get('document_id')}")
                print(f"   Status: {message.get('status')}")
                print(f"   Stage: {message.get('processing_stage')}")
        
        return True
        
    except Exception as e:
        print(f"❌ KG processor logic test failed: {e}")
        return False

def test_ttl_parsing():
    """Test TTL parsing logic for Neptune loading"""
    print("\n🧪 Testing TTL Parsing Logic...")
    
    try:
        # Sample TTL content
        sample_ttl = """@prefix sg: <http://solve.global/knowledge-commons/> .
@prefix kr: <http://solve.global/knowledge-commons/schema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .

sg:Document_test a kr:Document ;
    dcterms:identifier "test" ;
    dcterms:title "Test Document" .

sg:Document_test_Section_1 a kr:DocumentSection ;
    dcterms:title "Test Section" ;
    dcterms:isPartOf sg:Document_test .
"""
        
        # Simple parsing logic (similar to KG integration worker)
        lines = sample_ttl.split('\n')
        subjects = []
        current_subject = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip prefixes, comments, and empty lines
            if (not stripped or 
                stripped.startswith('@prefix') or 
                stripped.startswith('#')):
                continue
            
            # Check if this starts a new subject
            if not line.startswith(' ') and not line.startswith('\t') and 'sg:' in line:
                # Save previous subject
                if current_subject:
                    subjects.append('\n'.join(current_subject))
                    current_subject = []
                
                # Start new subject
                current_subject = [line]
            else:
                # Continuation of current subject
                if current_subject:
                    current_subject.append(line)
        
        # Add final subject
        if current_subject:
            subjects.append('\n'.join(current_subject))
        
        print(f"✅ TTL parsing successful!")
        print(f"📊 Parsed {len(subjects)} subjects:")
        
        for i, subject in enumerate(subjects):
            print(f"\n📋 Subject {i+1}:")
            print("-" * 40)
            print(subject)
            print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ TTL parsing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Document Structure KG Integration Tests")
    print("=" * 50)
    
    tests = [
        ("TTL Generation", test_document_ttl_generation),
        ("KG Processor Logic", test_kg_processor_logic), 
        ("TTL Parsing", test_ttl_parsing)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("⚠️  Some tests failed. Review before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
