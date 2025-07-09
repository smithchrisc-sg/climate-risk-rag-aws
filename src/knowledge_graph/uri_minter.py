#!/usr/bin/env python3
"""
URI Minting Facility for Knowledge Graph
Extensible system for generating systematic URIs for different entity types
"""

import re
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class URIType(Enum):
    """Enumeration of different URI types supported by the minting facility"""
    DOCUMENT = "document"
    DOCUMENT_PAGE = "document_page"
    DOCUMENT_SECTION = "document_section"
    DOCUMENT_CHUNK = "document_chunk"
    TEXTRACT_ELEMENT = "textract_element"
    ENTITY_INSTANCE = "entity_instance"
    ONTOLOGY_CONCEPT = "ontology_concept"
    RELATIONSHIP = "relationship"

@dataclass
class URIComponents:
    """Components used to construct URIs"""
    namespace: str
    entity_type: str
    doc_id: Optional[str] = None
    page_number: Optional[int] = None
    section_sequence: Optional[int] = None
    subsection_sequence: Optional[int] = None
    chunk_sequence: Optional[int] = None
    element_type: Optional[str] = None
    element_sequence: Optional[int] = None
    entity_id: Optional[str] = None
    additional_components: Optional[Dict[str, Any]] = None

class URIMinter(ABC):
    """Abstract base class for URI minting strategies"""
    
    @abstractmethod
    def mint_uri(self, components: URIComponents) -> str:
        """Generate a URI from the provided components"""
        pass
    
    @abstractmethod
    def parse_uri(self, uri: str) -> Optional[URIComponents]:
        """Parse a URI back into its components"""
        pass
    
    @abstractmethod
    def validate_uri(self, uri: str) -> bool:
        """Validate that a URI follows the expected pattern"""
        pass

class DocumentURIMinter(URIMinter):
    """URI minter for document structure elements"""
    
    def __init__(self, base_namespace: str = "http://solve.global/knowledge-commons/"):
        self.base_namespace = base_namespace.rstrip('/')
        self.patterns = {
            URIType.DOCUMENT: r"^{}/Document_([a-f0-9_]+)$",
            URIType.DOCUMENT_PAGE: r"^{}/Document_([a-f0-9_]+)_Page_(\d+)$",
            URIType.DOCUMENT_SECTION: r"^{}/Document_([a-f0-9_]+)_Section_(\d+(?:_\d+)*)$",
            URIType.DOCUMENT_CHUNK: r"^{}/Document_([a-f0-9_]+)_Section_(\d+(?:_\d+)*)_Chunk_(\d+)$",
        }
    
    def mint_uri(self, components: URIComponents) -> str:
        """Generate document structure URI"""
        if not components.doc_id:
            raise ValueError("doc_id is required for document URIs")
        
        # Sanitize doc_id
        clean_doc_id = self._sanitize_doc_id(components.doc_id)
        
        if components.entity_type == URIType.DOCUMENT.value:
            return f"{self.base_namespace}/Document_{clean_doc_id}"
        
        elif components.entity_type == URIType.DOCUMENT_PAGE.value:
            if not components.page_number:
                raise ValueError("page_number is required for page URIs")
            return f"{self.base_namespace}/Document_{clean_doc_id}_Page_{components.page_number}"
        
        elif components.entity_type == URIType.DOCUMENT_SECTION.value:
            if not components.section_sequence:
                raise ValueError("section_sequence is required for section URIs")
            
            # Handle subsections
            if components.subsection_sequence:
                section_path = f"{components.section_sequence}_{components.subsection_sequence}"
            else:
                section_path = str(components.section_sequence)
            
            return f"{self.base_namespace}/Document_{clean_doc_id}_Section_{section_path}"
        
        elif components.entity_type == URIType.DOCUMENT_CHUNK.value:
            if not components.section_sequence or not components.chunk_sequence:
                raise ValueError("section_sequence and chunk_sequence are required for chunk URIs")
            
            # Handle subsections in chunk URIs
            if components.subsection_sequence:
                section_path = f"{components.section_sequence}_{components.subsection_sequence}"
            else:
                section_path = str(components.section_sequence)
            
            return f"{self.base_namespace}/Document_{clean_doc_id}_Section_{section_path}_Chunk_{components.chunk_sequence}"
        
        else:
            raise ValueError(f"Unsupported entity type: {components.entity_type}")
    
    def parse_uri(self, uri: str) -> Optional[URIComponents]:
        """Parse document URI back into components"""
        for uri_type, pattern in self.patterns.items():
            regex = pattern.format(re.escape(self.base_namespace))
            match = re.match(regex, uri)
            
            if match:
                groups = match.groups()
                components = URIComponents(
                    namespace=self.base_namespace,
                    entity_type=uri_type.value,
                    doc_id=groups[0]
                )
                
                if uri_type == URIType.DOCUMENT_PAGE:
                    components.page_number = int(groups[1])
                
                elif uri_type == URIType.DOCUMENT_SECTION:
                    section_parts = groups[1].split('_')
                    components.section_sequence = int(section_parts[0])
                    if len(section_parts) > 1:
                        components.subsection_sequence = int(section_parts[1])
                
                elif uri_type == URIType.DOCUMENT_CHUNK:
                    section_parts = groups[1].split('_')
                    components.section_sequence = int(section_parts[0])
                    if len(section_parts) > 1:
                        components.subsection_sequence = int(section_parts[1])
                    components.chunk_sequence = int(groups[2])
                
                return components
        
        return None
    
    def validate_uri(self, uri: str) -> bool:
        """Validate document URI format"""
        return self.parse_uri(uri) is not None
    
    def _sanitize_doc_id(self, doc_id: str) -> str:
        """Sanitize document ID for URI use"""
        # Remove any characters that aren't alphanumeric, underscore, or hyphen
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)
        return sanitized

class TextractElementURIMinter(URIMinter):
    """URI minter for Textract structure elements"""
    
    def __init__(self, base_namespace: str = "http://solve.global/knowledge-commons/"):
        self.base_namespace = base_namespace.rstrip('/')
        self.element_types = {
            'LINE': 'Line',
            'WORD': 'Word', 
            'TABLE': 'Table',
            'CELL': 'Cell',
            'TITLE': 'Title',
            'SELECTION_ELEMENT': 'Selection'
        }
    
    def mint_uri(self, components: URIComponents) -> str:
        """Generate Textract element URI"""
        if not all([components.doc_id, components.page_number, components.element_type]):
            raise ValueError("doc_id, page_number, and element_type are required for Textract element URIs")
        
        clean_doc_id = self._sanitize_doc_id(components.doc_id)
        element_name = self.element_types.get(components.element_type.upper(), components.element_type)
        
        # Base pattern: Document_{doc_id}_Page_{page}_ElementType_{sequence}
        uri = f"{self.base_namespace}/Document_{clean_doc_id}_Page_{components.page_number}_{element_name}_{components.element_sequence}"
        
        # Handle nested elements (e.g., words within lines)
        if components.additional_components:
            for key, value in components.additional_components.items():
                if key.endswith('_sequence'):
                    parent_type = key.replace('_sequence', '').title()
                    uri = f"{self.base_namespace}/Document_{clean_doc_id}_Page_{components.page_number}_{parent_type}_{value}_{element_name}_{components.element_sequence}"
                    break
        
        return uri
    
    def parse_uri(self, uri: str) -> Optional[URIComponents]:
        """Parse Textract element URI"""
        # Pattern: namespace/Document_docid_Page_num_ElementType_seq
        pattern = rf"^{re.escape(self.base_namespace)}/Document_([a-f0-9_]+)_Page_(\d+)_(\w+)_(\d+)(?:_(\w+)_(\d+))?$"
        match = re.match(pattern, uri)
        
        if match:
            groups = match.groups()
            components = URIComponents(
                namespace=self.base_namespace,
                entity_type=URIType.TEXTRACT_ELEMENT.value,
                doc_id=groups[0],
                page_number=int(groups[1]),
                element_type=groups[2],
                element_sequence=int(groups[3])
            )
            
            # Handle nested elements
            if groups[4] and groups[5]:
                components.additional_components = {
                    f"{groups[2].lower()}_sequence": int(groups[3])
                }
                components.element_type = groups[4]
                components.element_sequence = int(groups[5])
            
            return components
        
        return None
    
    def validate_uri(self, uri: str) -> bool:
        """Validate Textract element URI"""
        return self.parse_uri(uri) is not None
    
    def _sanitize_doc_id(self, doc_id: str) -> str:
        """Sanitize document ID for URI use"""
        return re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)

class EntityInstanceURIMinter(URIMinter):
    """URI minter for entity instances found in documents"""
    
    def __init__(self, base_namespace: str = "http://solve.global/knowledge-commons/"):
        self.base_namespace = base_namespace.rstrip('/')
    
    def mint_uri(self, components: URIComponents) -> str:
        """Generate entity instance URI"""
        if not all([components.doc_id, components.entity_id]):
            raise ValueError("doc_id and entity_id are required for entity instance URIs")
        
        clean_doc_id = self._sanitize_doc_id(components.doc_id)
        clean_entity_id = self._sanitize_entity_id(components.entity_id)
        
        # Include section and chunk context if available
        if components.section_sequence and components.chunk_sequence:
            if components.subsection_sequence:
                section_path = f"{components.section_sequence}_{components.subsection_sequence}"
            else:
                section_path = str(components.section_sequence)
            
            return f"{self.base_namespace}/Entity_{clean_doc_id}_Section_{section_path}_Chunk_{components.chunk_sequence}_{clean_entity_id}"
        
        # Fallback to document-level entity
        return f"{self.base_namespace}/Entity_{clean_doc_id}_{clean_entity_id}"
    
    def parse_uri(self, uri: str) -> Optional[URIComponents]:
        """Parse entity instance URI"""
        # Pattern with section/chunk context
        pattern1 = rf"^{re.escape(self.base_namespace)}/Entity_([a-f0-9_]+)_Section_(\d+(?:_\d+)*)_Chunk_(\d+)_(.+)$"
        match = re.match(pattern1, uri)
        
        if match:
            groups = match.groups()
            section_parts = groups[1].split('_')
            
            components = URIComponents(
                namespace=self.base_namespace,
                entity_type=URIType.ENTITY_INSTANCE.value,
                doc_id=groups[0],
                section_sequence=int(section_parts[0]),
                chunk_sequence=int(groups[2]),
                entity_id=groups[3]
            )
            
            if len(section_parts) > 1:
                components.subsection_sequence = int(section_parts[1])
            
            return components
        
        # Pattern without section/chunk context
        pattern2 = rf"^{re.escape(self.base_namespace)}/Entity_([a-f0-9_]+)_(.+)$"
        match = re.match(pattern2, uri)
        
        if match:
            return URIComponents(
                namespace=self.base_namespace,
                entity_type=URIType.ENTITY_INSTANCE.value,
                doc_id=match.group(1),
                entity_id=match.group(2)
            )
        
        return None
    
    def validate_uri(self, uri: str) -> bool:
        """Validate entity instance URI"""
        return self.parse_uri(uri) is not None
    
    def _sanitize_doc_id(self, doc_id: str) -> str:
        """Sanitize document ID for URI use"""
        return re.sub(r'[^a-zA-Z0-9_-]', '_', doc_id)
    
    def _sanitize_entity_id(self, entity_id: str) -> str:
        """Sanitize entity ID for URI use"""
        # Convert to lowercase, replace spaces with underscores, remove special chars
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', entity_id.lower())
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized

class URIMintingFacility:
    """Central facility for minting URIs of different types"""
    
    def __init__(self, base_namespace: str = "http://solve.global/knowledge-commons/"):
        self.base_namespace = base_namespace
        self.minters: Dict[URIType, URIMinter] = {}
        
        # Register default minters
        self._register_default_minters()
    
    def _register_default_minters(self):
        """Register default URI minters"""
        document_minter = DocumentURIMinter(self.base_namespace)
        textract_minter = TextractElementURIMinter(self.base_namespace)
        entity_minter = EntityInstanceURIMinter(self.base_namespace)
        
        # Document structure minters
        self.minters[URIType.DOCUMENT] = document_minter
        self.minters[URIType.DOCUMENT_PAGE] = document_minter
        self.minters[URIType.DOCUMENT_SECTION] = document_minter
        self.minters[URIType.DOCUMENT_CHUNK] = document_minter
        
        # Textract element minter
        self.minters[URIType.TEXTRACT_ELEMENT] = textract_minter
        
        # Entity instance minter
        self.minters[URIType.ENTITY_INSTANCE] = entity_minter
    
    def register_minter(self, uri_type: URIType, minter: URIMinter):
        """Register a custom URI minter for a specific type"""
        self.minters[uri_type] = minter
        logger.info(f"Registered custom minter for {uri_type.value}")
    
    def mint_uri(self, uri_type: URIType, **kwargs) -> str:
        """Mint a URI of the specified type"""
        if uri_type not in self.minters:
            raise ValueError(f"No minter registered for URI type: {uri_type.value}")
        
        # Convert kwargs to URIComponents
        components = URIComponents(
            namespace=self.base_namespace,
            entity_type=uri_type.value,
            **kwargs
        )
        
        minter = self.minters[uri_type]
        uri = minter.mint_uri(components)
        
        logger.debug(f"Minted {uri_type.value} URI: {uri}")
        return uri
    
    def parse_uri(self, uri: str) -> Optional[URIComponents]:
        """Parse any URI back into its components"""
        for minter in self.minters.values():
            components = minter.parse_uri(uri)
            if components:
                return components
        return None
    
    def validate_uri(self, uri: str) -> bool:
        """Validate any URI format"""
        return self.parse_uri(uri) is not None
    
    def get_s3_location_from_chunk_uri(self, chunk_uri: str, 
                                     bucket_template: str = "solve-global-kr-chunks-{account_id}-{region}",
                                     account_id: str = "861276078413",
                                     region: str = "us-east-1") -> Optional[str]:
        """Generate S3 location from chunk URI"""
        components = self.parse_uri(chunk_uri)
        
        if not components or components.entity_type != URIType.DOCUMENT_CHUNK.value:
            return None
        
        bucket = bucket_template.format(account_id=account_id, region=region)
        
        # Generate S3 key from URI components
        if components.subsection_sequence:
            section_path = f"{components.section_sequence}_{components.subsection_sequence}"
        else:
            section_path = str(components.section_sequence)
        
        s3_key = f"{components.doc_id}/section_{section_path}_chunk_{components.chunk_sequence}.txt"
        
        return f"s3://{bucket}/{s3_key}"

# Convenience functions for common operations
def create_document_uri(doc_id: str, base_namespace: str = "http://solve.global/knowledge-commons/") -> str:
    """Create a document URI"""
    facility = URIMintingFacility(base_namespace)
    return facility.mint_uri(URIType.DOCUMENT, doc_id=doc_id)

def create_chunk_uri(doc_id: str, section_sequence: int, chunk_sequence: int,
                    subsection_sequence: Optional[int] = None,
                    base_namespace: str = "http://solve.global/knowledge-commons/") -> str:
    """Create a document chunk URI"""
    facility = URIMintingFacility(base_namespace)
    return facility.mint_uri(
        URIType.DOCUMENT_CHUNK,
        doc_id=doc_id,
        section_sequence=section_sequence,
        chunk_sequence=chunk_sequence,
        subsection_sequence=subsection_sequence
    )

def create_entity_instance_uri(doc_id: str, entity_id: str,
                              section_sequence: Optional[int] = None,
                              chunk_sequence: Optional[int] = None,
                              subsection_sequence: Optional[int] = None,
                              base_namespace: str = "http://solve.global/knowledge-commons/") -> str:
    """Create an entity instance URI"""
    facility = URIMintingFacility(base_namespace)
    return facility.mint_uri(
        URIType.ENTITY_INSTANCE,
        doc_id=doc_id,
        entity_id=entity_id,
        section_sequence=section_sequence,
        chunk_sequence=chunk_sequence,
        subsection_sequence=subsection_sequence
    )

if __name__ == "__main__":
    # Example usage and testing
    facility = URIMintingFacility()
    
    # Test document URI
    doc_uri = facility.mint_uri(URIType.DOCUMENT, doc_id="0032f6cb_f0caef34")
    print(f"Document URI: {doc_uri}")
    
    # Test chunk URI
    chunk_uri = facility.mint_uri(
        URIType.DOCUMENT_CHUNK,
        doc_id="0032f6cb_f0caef34",
        section_sequence=2,
        subsection_sequence=1,
        chunk_sequence=3
    )
    print(f"Chunk URI: {chunk_uri}")
    
    # Test S3 location generation
    s3_location = facility.get_s3_location_from_chunk_uri(chunk_uri)
    print(f"S3 Location: {s3_location}")
    
    # Test URI parsing
    parsed = facility.parse_uri(chunk_uri)
    print(f"Parsed components: {parsed}")
    
    # Test entity instance URI
    entity_uri = facility.mint_uri(
        URIType.ENTITY_INSTANCE,
        doc_id="0032f6cb_f0caef34",
        section_sequence=2,
        chunk_sequence=1,
        entity_id="sea_level_rise"
    )
    print(f"Entity URI: {entity_uri}")
