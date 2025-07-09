#!/usr/bin/env python3
"""
Test URI Minting Facility
Demonstrates the extensible URI generation system
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from uri_minter import (
    URIMintingFacility, URIType, URIComponents, 
    DocumentURIMinter, TextractElementURIMinter, EntityInstanceURIMinter,
    create_document_uri, create_chunk_uri, create_entity_instance_uri
)

def test_document_structure_uris():
    """Test document structure URI generation"""
    print("=" * 60)
    print("TESTING DOCUMENT STRUCTURE URI GENERATION")
    print("=" * 60)
    
    facility = URIMintingFacility()
    doc_id = "0032f6cb_f0caef34"
    
    # Document URI
    doc_uri = facility.mint_uri(URIType.DOCUMENT, doc_id=doc_id)
    print(f"Document URI: {doc_uri}")
    
    # Page URIs
    for page_num in [1, 2, 3]:
        page_uri = facility.mint_uri(URIType.DOCUMENT_PAGE, doc_id=doc_id, page_number=page_num)
        print(f"Page {page_num} URI: {page_uri}")
    
    # Section URIs (top-level)
    for section_num in [1, 2, 3, 4]:
        section_uri = facility.mint_uri(URIType.DOCUMENT_SECTION, doc_id=doc_id, section_sequence=section_num)
        print(f"Section {section_num} URI: {section_uri}")
    
    # Subsection URIs
    subsection_uri = facility.mint_uri(
        URIType.DOCUMENT_SECTION, 
        doc_id=doc_id, 
        section_sequence=2, 
        subsection_sequence=1
    )
    print(f"Subsection 2.1 URI: {subsection_uri}")
    
    # Chunk URIs
    chunk_examples = [
        (1, None, 1),  # Section 1, Chunk 1
        (1, None, 2),  # Section 1, Chunk 2
        (2, 1, 1),     # Section 2.1, Chunk 1
        (2, 1, 2),     # Section 2.1, Chunk 2
        (3, None, 4),  # Section 3, Chunk 4
    ]
    
    for section, subsection, chunk in chunk_examples:
        chunk_uri = facility.mint_uri(
            URIType.DOCUMENT_CHUNK,
            doc_id=doc_id,
            section_sequence=section,
            subsection_sequence=subsection,
            chunk_sequence=chunk
        )
        section_label = f"{section}.{subsection}" if subsection else str(section)
        print(f"Section {section_label}, Chunk {chunk} URI: {chunk_uri}")

def test_textract_element_uris():
    """Test Textract element URI generation"""
    print("\n" + "=" * 60)
    print("TESTING TEXTRACT ELEMENT URI GENERATION")
    print("=" * 60)
    
    facility = URIMintingFacility()
    doc_id = "0032f6cb_f0caef34"
    
    # Title URI
    title_uri = facility.mint_uri(
        URIType.TEXTRACT_ELEMENT,
        doc_id=doc_id,
        page_number=1,
        element_type="TITLE",
        element_sequence=1
    )
    print(f"Title URI: {title_uri}")
    
    # Text Line URIs
    for line_num in [1, 2]:
        line_uri = facility.mint_uri(
            URIType.TEXTRACT_ELEMENT,
            doc_id=doc_id,
            page_number=1,
            element_type="LINE",
            element_sequence=line_num
        )
        print(f"Line {line_num} URI: {line_uri}")
    
    # Word URIs (nested within lines)
    for word_num in [1, 2, 3, 4]:
        word_uri = facility.mint_uri(
            URIType.TEXTRACT_ELEMENT,
            doc_id=doc_id,
            page_number=1,
            element_type="WORD",
            element_sequence=word_num,
            additional_components={"line_sequence": 1}
        )
        print(f"Word {word_num} (Line 1) URI: {word_uri}")
    
    # Table URI
    table_uri = facility.mint_uri(
        URIType.TEXTRACT_ELEMENT,
        doc_id=doc_id,
        page_number=2,
        element_type="TABLE",
        element_sequence=1
    )
    print(f"Table URI: {table_uri}")
    
    # Table Cell URIs
    cell_positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for row, col in cell_positions:
        cell_uri = facility.mint_uri(
            URIType.TEXTRACT_ELEMENT,
            doc_id=doc_id,
            page_number=2,
            element_type="CELL",
            element_sequence=f"{row}_{col}",
            additional_components={"table_sequence": 1}
        )
        print(f"Cell ({row},{col}) URI: {cell_uri}")

def test_entity_instance_uris():
    """Test entity instance URI generation"""
    print("\n" + "=" * 60)
    print("TESTING ENTITY INSTANCE URI GENERATION")
    print("=" * 60)
    
    facility = URIMintingFacility()
    doc_id = "0032f6cb_f0caef34"
    
    # Entity instances with full context
    entities = [
        ("sea_level_rise", 2, 1, 1),      # Section 2.1, Chunk 1
        ("coastal_flooding", 2, 1, 1),    # Section 2.1, Chunk 1
        ("climate_change", 1, None, 1),   # Section 1, Chunk 1
        ("adaptation_strategies", 3, None, 2),  # Section 3, Chunk 2
    ]
    
    for entity_id, section, subsection, chunk in entities:
        entity_uri = facility.mint_uri(
            URIType.ENTITY_INSTANCE,
            doc_id=doc_id,
            entity_id=entity_id,
            section_sequence=section,
            subsection_sequence=subsection,
            chunk_sequence=chunk
        )
        section_label = f"{section}.{subsection}" if subsection else str(section)
        print(f"Entity '{entity_id}' (Section {section_label}, Chunk {chunk}): {entity_uri}")
    
    # Document-level entity (no specific location)
    doc_entity_uri = facility.mint_uri(
        URIType.ENTITY_INSTANCE,
        doc_id=doc_id,
        entity_id="climate_risk_assessment"
    )
    print(f"Document-level entity: {doc_entity_uri}")

def test_s3_integration():
    """Test S3 location generation from chunk URIs"""
    print("\n" + "=" * 60)
    print("TESTING S3 INTEGRATION")
    print("=" * 60)
    
    facility = URIMintingFacility()
    doc_id = "0032f6cb_f0caef34"
    
    # Generate chunk URIs and their S3 locations
    chunk_examples = [
        (1, None, 1),  # Section 1, Chunk 1
        (2, 1, 1),     # Section 2.1, Chunk 1
        (3, None, 4),  # Section 3, Chunk 4
    ]
    
    for section, subsection, chunk in chunk_examples:
        chunk_uri = facility.mint_uri(
            URIType.DOCUMENT_CHUNK,
            doc_id=doc_id,
            section_sequence=section,
            subsection_sequence=subsection,
            chunk_sequence=chunk
        )
        
        s3_location = facility.get_s3_location_from_chunk_uri(chunk_uri)
        
        section_label = f"{section}.{subsection}" if subsection else str(section)
        print(f"Section {section_label}, Chunk {chunk}:")
        print(f"  URI: {chunk_uri}")
        print(f"  S3:  {s3_location}")

def test_uri_parsing():
    """Test URI parsing back to components"""
    print("\n" + "=" * 60)
    print("TESTING URI PARSING")
    print("=" * 60)
    
    facility = URIMintingFacility()
    
    # Test URIs to parse
    test_uris = [
        "http://solve.global/knowledge-commons/Document_0032f6cb_f0caef34",
        "http://solve.global/knowledge-commons/Document_0032f6cb_f0caef34_Page_1",
        "http://solve.global/knowledge-commons/Document_0032f6cb_f0caef34_Section_2_1",
        "http://solve.global/knowledge-commons/Document_0032f6cb_f0caef34_Section_2_1_Chunk_3",
        "http://solve.global/knowledge-commons/Entity_0032f6cb_f0caef34_Section_2_1_Chunk_1_sea_level_rise",
    ]
    
    for uri in test_uris:
        components = facility.parse_uri(uri)
        if components:
            print(f"URI: {uri}")
            print(f"  Type: {components.entity_type}")
            print(f"  Doc ID: {components.doc_id}")
            if components.page_number:
                print(f"  Page: {components.page_number}")
            if components.section_sequence:
                section_label = f"{components.section_sequence}"
                if components.subsection_sequence:
                    section_label += f".{components.subsection_sequence}"
                print(f"  Section: {section_label}")
            if components.chunk_sequence:
                print(f"  Chunk: {components.chunk_sequence}")
            if components.entity_id:
                print(f"  Entity: {components.entity_id}")
            print()
        else:
            print(f"Failed to parse: {uri}")

def test_convenience_functions():
    """Test convenience functions"""
    print("\n" + "=" * 60)
    print("TESTING CONVENIENCE FUNCTIONS")
    print("=" * 60)
    
    doc_id = "0032f6cb_f0caef34"
    
    # Document URI
    doc_uri = create_document_uri(doc_id)
    print(f"Document URI: {doc_uri}")
    
    # Chunk URI
    chunk_uri = create_chunk_uri(doc_id, section_sequence=2, subsection_sequence=1, chunk_sequence=3)
    print(f"Chunk URI: {chunk_uri}")
    
    # Entity instance URI
    entity_uri = create_entity_instance_uri(
        doc_id, 
        entity_id="sea level rise",  # Test with spaces
        section_sequence=2,
        subsection_sequence=1,
        chunk_sequence=1
    )
    print(f"Entity URI: {entity_uri}")

def test_extensibility():
    """Test extensibility with custom minter"""
    print("\n" + "=" * 60)
    print("TESTING EXTENSIBILITY")
    print("=" * 60)
    
    # Create a custom minter for relationships
    class RelationshipURIMinter:
        def __init__(self, base_namespace):
            self.base_namespace = base_namespace
        
        def mint_uri(self, components):
            if not all([components.doc_id, components.additional_components]):
                raise ValueError("doc_id and relationship info required")
            
            rel_info = components.additional_components
            subject = rel_info.get('subject', 'unknown')
            predicate = rel_info.get('predicate', 'unknown')
            object_entity = rel_info.get('object', 'unknown')
            
            # Create a hash for the relationship
            import hashlib
            rel_hash = hashlib.md5(f"{subject}_{predicate}_{object_entity}".encode()).hexdigest()[:8]
            
            return f"{self.base_namespace}/Relationship_{components.doc_id}_{rel_hash}"
        
        def parse_uri(self, uri):
            # Implementation would parse relationship URIs
            return None
        
        def validate_uri(self, uri):
            return "Relationship_" in uri
    
    # Register custom minter
    facility = URIMintingFacility()
    custom_minter = RelationshipURIMinter(facility.base_namespace)
    facility.register_minter(URIType.RELATIONSHIP, custom_minter)
    
    # Use custom minter
    relationship_uri = facility.mint_uri(
        URIType.RELATIONSHIP,
        doc_id="0032f6cb_f0caef34",
        additional_components={
            'subject': 'sea_level_rise',
            'predicate': 'causes',
            'object': 'coastal_flooding'
        }
    )
    print(f"Custom relationship URI: {relationship_uri}")

if __name__ == "__main__":
    print("URI MINTING FACILITY TEST SUITE")
    print("=" * 60)
    
    test_document_structure_uris()
    test_textract_element_uris()
    test_entity_instance_uris()
    test_s3_integration()
    test_uri_parsing()
    test_convenience_functions()
    test_extensibility()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
