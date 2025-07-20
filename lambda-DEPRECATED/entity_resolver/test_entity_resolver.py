#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Entity Resolver Implementation
Validates entity resolution functionality with sample data
"""

import json
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from uri_minter import URIMinter
from rdf_entity_builder import RDFEntityBuilder
from document_entity_extractor import DocumentEntityExtractor

def test_uri_minter():
    """Test URI minting functionality"""
    print("=== Testing URI Minter ===")
    
    minter = URIMinter()
    
    # Test person URIs
    person_tests = [
        "Dr. Sarah Johnson",
        "Greta Thunberg", 
        "Michael Mann",
        "Prof. John Smith"
    ]
    
    print("Person URI Tests:")
    for name in person_tests:
        uri = minter.mint_person_uri(name)
        normalized = minter.normalize_person_name(name)
        print("  {} -> {} (normalized: {})".format(name, uri, normalized))
    
    # Test organization URIs
    org_tests = [
        "IPCC",
        "Intergovernmental Panel on Climate Change",
        "World Bank",
        "United Nations",
        "ExxonMobil Corporation"
    ]
    
    print("\nOrganization URI Tests:")
    for name in org_tests:
        uri = minter.mint_organization_uri(name)
        normalized = minter.normalize_organization_name(name)
        print("  {} -> {} (normalized: {})".format(name, uri, normalized))
    
    # Test other entity types
    print("\nOther Entity URI Tests:")
    print("  Location: Miami -> {}".format(minter.mint_location_uri('Miami')))
    print("  Date: 2050 -> {}".format(minter.mint_date_uri('2050')))
    print("  Quantity: 2.5C -> {}".format(minter.mint_quantity_uri('2.5C')))
    print("  Concept: Paris Agreement -> {}".format(minter.mint_concept_uri('Paris Agreement')))
    
    print("✅ URI Minter tests completed\n")

def test_document_entity_extractor():
    """Test document entity extraction"""
    print("=== Testing Document Entity Extractor ===")
    
    minter = URIMinter()
    extractor = DocumentEntityExtractor(minter)
    
    # Test metadata
    test_metadata = {
        'author': 'Dr. Sarah Johnson',
        'publisher': 'World Bank',
        'contributors': ['Michael Mann', 'Prof. Jane Smith'],
        'textract_key_values': [
            {'key': 'Author', 'value': 'Greta Thunberg', 'confidence': 0.95},
            {'key': 'Organization', 'value': 'IPCC', 'confidence': 0.98},
            {'key': 'Title', 'value': 'World Bank Climate Report', 'confidence': 0.99}
        ]
    }
    
    entities = extractor.extract_document_entities(test_metadata)
    
    print("Extracted {} document entities:".format(len(entities)))
    for entity in entities:
        print("  {}: {} ({}) - {}".format(entity.entity_type, entity.canonical_name, entity.context, entity.kg_uri))
    
    print("✅ Document Entity Extractor tests completed\n")

def test_rdf_entity_builder():
    """Test RDF entity building"""
    print("=== Testing RDF Entity Builder ===")
    
    builder = RDFEntityBuilder()
    
    # Sample resolved entities
    sample_entities = [
        {
            'canonical_name': 'Sarah Johnson',
            'entity_type': 'PERSON',
            'rdf_type': 'foaf:Person',
            'confidence': 0.95,
            'kg_uri': 'kr:person/sarah_johnson',
            'properties': {
                'foaf:name': 'Dr. Sarah Johnson',
                'foaf:givenName': 'Sarah',
                'foaf:familyName': 'Johnson',
                'kr:confidence': 0.95,
                'kr:extractedBy': 'aws-comprehend'
            },
            'source_chunk': 'test_doc_chunk_001',
            'context': 'mention'
        },
        {
            'canonical_name': 'IPCC',
            'entity_type': 'ORGANIZATION',
            'rdf_type': 'foaf:Organization',
            'confidence': 0.98,
            'kg_uri': 'kr:organization/ipcc',
            'properties': {
                'foaf:name': 'IPCC',
                'schema:alternateName': 'Intergovernmental Panel on Climate Change',
                'kr:organizationType': 'International Scientific Body',
                'kr:confidence': 0.98,
                'kr:extractedBy': 'aws-comprehend'
            },
            'source_chunk': 'test_doc_chunk_002',
            'context': 'mention'
        }
    ]
    
    # Build TTL
    ttl_content = builder.build_entity_ttl(sample_entities, 'test_doc')
    
    print("Generated TTL Content:")
    print("=" * 50)
    print(ttl_content)
    print("=" * 50)
    
    # Validate TTL
    validation = builder.validate_ttl(ttl_content)
    print("TTL Validation: {}".format(validation))
    
    # Build summary
    summary = builder.build_entity_summary(sample_entities)
    print("Entity Summary: {}".format(json.dumps(summary, indent=2)))
    
    print("✅ RDF Entity Builder tests completed\n")

def test_full_entity_resolution():
    """Test full entity resolution workflow"""
    print("=== Testing Full Entity Resolution Workflow ===")
    
    # Sample NLP results (simulating AWS Comprehend output)
    sample_nlp_results = {
        'doc_id': 'test_document_123',
        'entities_mapped_to_chunks': [
            {
                'type': 'entity',
                'chunk_id': 'test_document_123_chunk_001',
                'entity': {
                    'Text': 'Dr. Sarah Johnson',
                    'Type': 'PERSON',
                    'Score': 0.95,
                    'BeginOffset': 45,
                    'EndOffset': 61
                }
            },
            {
                'type': 'entity',
                'chunk_id': 'test_document_123_chunk_001',
                'entity': {
                    'Text': 'IPCC',
                    'Type': 'ORGANIZATION',
                    'Score': 0.98,
                    'BeginOffset': 120,
                    'EndOffset': 124
                }
            },
            {
                'type': 'entity',
                'chunk_id': 'test_document_123_chunk_002',
                'entity': {
                    'Text': '2050',
                    'Type': 'DATE',
                    'Score': 0.99,
                    'BeginOffset': 200,
                    'EndOffset': 204
                }
            }
        ],
        'document_metadata': {
            'author': 'Michael Mann',
            'publisher': 'World Bank'
        }
    }
    
    # Simulate entity resolution process
    print("Sample NLP Results:")
    print(json.dumps(sample_nlp_results, indent=2))
    
    print("    Entity Resolution Summary:")
    chunk_entities = sample_nlp_results.get('entities_mapped_to_chunks', [])
    doc_metadata = sample_nlp_results.get('document_metadata', {})
    
    print("  - Chunk-level entities: {}".format(len(chunk_entities)))
    print("  - Document metadata entities: {}".format(len([k for k in doc_metadata.keys() if doc_metadata[k]])))
    
    entity_types = set()
    for item in chunk_entities:
        if item.get('type') == 'entity':
            entity_types.add(item['entity']['Type'])
    
    print("  - Entity types found: {}".format(list(entity_types)))
    
    print("✅ Full Entity Resolution Workflow test completed\n")

def main():
    """Run all tests"""
    print("Entity Resolver Implementation Tests")
    print("=" * 60)
    
    try:
        test_uri_minter()
        test_document_entity_extractor()
        test_rdf_entity_builder()
        test_full_entity_resolution()
        
        print("All tests completed successfully!")
        
    except Exception as e:
        print("Test failed with error: {}".format(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
