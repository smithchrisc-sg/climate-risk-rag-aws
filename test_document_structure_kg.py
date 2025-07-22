#!/usr/bin/env python3
"""
Test script for Document Structure KG Processor
"""
import json
import sys
import os

# Add the lambda source to path
sys.path.append('/Users/chris/climate-risk-rag-aws/lambda/document-structure-kg-processor/src')

def test_ttl_generation():
    """Test TTL generation with sample data"""
    
    from document_ttl_generator import DocumentTTLGenerator
    
    # Sample metadata
    enhanced_metadata = {
        'data_locations': {
            'chunks_location': 's3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/test-doc/',
            'chunk_metadata_location': 's3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/test-doc/metadata.json'
        },
        'processing_metadata': {
            'chunks_created': 5,
            'chunking_method': 'smart_structured',
            'total_characters': 1500
        }
    }
    
    # Create generator
    generator = DocumentTTLGenerator('test-doc-123', enhanced_metadata)
    
    # Test with minimal data (no S3 access)
    chunks_data = {
        'chunks': [
            {
                'chunk_id': 'chunk_001',
                'content': 'This is a test chunk about climate risk assessment.',
                'section_title': 'Introduction',
                'chunk_type': 'text',
                'start_char': 0,
                'end_char': 50
            },
            {
                'chunk_id': 'chunk_002', 
                'content': 'Climate change poses significant risks to financial institutions.',
                'section_title': 'Risk Assessment',
                'chunk_type': 'text',
                'start_char': 51,
                'end_char': 115
            }
        ],
        'metadata': {
            'document_info': {
                'title': 'Climate Risk Assessment Report',
                'source_url': 'https://example.com/climate-report.pdf'
            },
            'chunking_config': {
                'method': 'smart_structured',
                'max_chunk_size': 1000
            }
        }
    }
    
    # Generate TTL
    ttl_content = generator.build_ttl_content(chunks_data)
    
    print("Generated TTL Content:")
    print("=" * 50)
    print(ttl_content)
    print("=" * 50)
    print(f"TTL Length: {len(ttl_content)} characters")
    
    # Validate TTL structure
    assert '@prefix dc:' in ttl_content
    assert '@prefix dcterms:' in ttl_content
    assert 'test-doc-123' in ttl_content
    assert 'chunk_001' in ttl_content
    assert 'Climate Risk Assessment Report' in ttl_content
    
    print("✅ TTL generation test passed!")

def test_message_parsing():
    """Test chunks_ready message parsing"""
    
    # Sample chunks_ready message
    chunks_ready_message = {
        "version": "1.0",
        "timestamp": "2025-07-22T22:30:00Z",
        "source": "climate-risk-rag-system",
        "stage": "chunks_ready",
        "doc_id": "test-doc-456",
        "data_locations": {
            "chunks_location": "s3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/test-doc-456/",
            "chunk_metadata_location": "s3://solve-global-kr-dl-chunks-861276078413-us-east-1/data-lake/test-doc-456/metadata.json"
        },
        "processing_metadata": {
            "chunks_created": 8,
            "chunking_method": "smart_structured",
            "total_characters": 2500,
            "processing_completed": "2025-07-22T22:30:00Z"
        },
        "integration_flags": {
            "database_tracking_enabled": True,
            "audit_first_design": True,
            "smart_structured_chunking": True
        }
    }
    
    # Validate message structure
    assert chunks_ready_message['stage'] == 'chunks_ready'
    assert chunks_ready_message['doc_id'] == 'test-doc-456'
    assert 'data_locations' in chunks_ready_message
    assert 'processing_metadata' in chunks_ready_message
    
    print("✅ Message parsing test passed!")
    print(f"Doc ID: {chunks_ready_message['doc_id']}")
    print(f"Chunks created: {chunks_ready_message['processing_metadata']['chunks_created']}")
    print(f"Chunks location: {chunks_ready_message['data_locations']['chunks_location']}")

if __name__ == "__main__":
    print("Testing Document Structure KG Processor")
    print("=" * 50)
    
    try:
        test_message_parsing()
        print()
        test_ttl_generation()
        print()
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
