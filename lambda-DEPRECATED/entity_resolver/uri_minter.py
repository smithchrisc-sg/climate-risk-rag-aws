#!/usr/bin/env python3
"""
URI Minter for Entity Resolution
Generates consistent, deterministic URIs for entities
"""

import re
import hashlib
from typing import str

class URIMinter:
    """Generates consistent URIs for entities"""
    
    def __init__(self):
        # Use the correct namespace as specified
        self.base_namespace = "http://solve.global/knowledge-commons/schema#"
        self.kr_prefix = "kr:"
    
    def mint_person_uri(self, person_name: str) -> str:
        """Generate consistent URI for person entities"""
        normalized = self.normalize_person_name(person_name)
        return f"{self.kr_prefix}person/{normalized}"
    
    def mint_organization_uri(self, org_name: str) -> str:
        """Generate consistent URI for organization entities"""
        normalized = self.normalize_organization_name(org_name)
        return f"{self.kr_prefix}organization/{normalized}"
    
    def mint_location_uri(self, location_name: str) -> str:
        """Generate consistent URI for location entities"""
        normalized = self._normalize_generic(location_name)
        return f"{self.kr_prefix}location/{normalized}"
    
    def mint_date_uri(self, date_text: str) -> str:
        """Generate consistent URI for date entities"""
        normalized = self._normalize_generic(date_text)
        return f"{self.kr_prefix}date/{normalized}"
    
    def mint_quantity_uri(self, quantity_text: str) -> str:
        """Generate consistent URI for quantity entities"""
        # Use hash for quantities to handle complex expressions
        normalized = self._hash_normalize(quantity_text)
        return f"{self.kr_prefix}quantity/{normalized}"
    
    def mint_concept_uri(self, concept_text: str) -> str:
        """Generate consistent URI for concept entities"""
        normalized = self._normalize_generic(concept_text)
        return f"{self.kr_prefix}concept/{normalized}"
    
    def mint_generic_uri(self, entity_text: str, entity_type: str) -> str:
        """Generate URI for generic/unknown entity types"""
        normalized = self._normalize_generic(entity_text)
        type_normalized = entity_type.lower().replace('_', '')
        return f"{self.kr_prefix}{type_normalized}/{normalized}"
    
    def mint_chunk_uri(self, document_id: str, chunk_sequence: int) -> str:
        """Generate URI for document chunk"""
        return f"{self.kr_prefix}chunk/{document_id}_chunk_{chunk_sequence:04d}"
    
    def mint_document_uri(self, document_id: str) -> str:
        """Generate URI for document"""
        return f"{self.kr_prefix}document/{document_id}"
    
    def normalize_person_name(self, name: str) -> str:
        """Normalize person name for consistent URI generation"""
        # Remove common titles
        normalized = name.strip()
        for title in ['Dr.', 'Prof.', 'Mr.', 'Ms.', 'Mrs.', 'Dr', 'Prof', 'Mr', 'Ms', 'Mrs']:
            normalized = re.sub(rf'\b{re.escape(title)}\.?\s+', '', normalized, flags=re.IGNORECASE)
        
        # Basic normalization
        normalized = self._normalize_generic(normalized)
        
        return normalized
    
    def normalize_organization_name(self, name: str) -> str:
        """Normalize organization name for consistent URI generation"""
        normalized = name.strip()
        
        # Handle common organization abbreviations and expansions
        # IPCC = Intergovernmental Panel on Climate Change
        abbreviation_map = {
            'Intergovernmental Panel on Climate Change': 'ipcc',
            'United Nations': 'un',
            'World Bank': 'world_bank',
            'International Monetary Fund': 'imf',
            'Environmental Protection Agency': 'epa',
            'National Aeronautics and Space Administration': 'nasa'
        }
        
        # Check for known abbreviations
        for full_name, abbrev in abbreviation_map.items():
            if normalized.lower() == full_name.lower():
                return abbrev
        
        # Check if it's already an abbreviation
        for full_name, abbrev in abbreviation_map.items():
            if normalized.lower() == abbrev.lower():
                return abbrev
        
        # Default normalization
        return self._normalize_generic(normalized)
    
    def _normalize_generic(self, text: str) -> str:
        """Generic text normalization for URI generation"""
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove punctuation except hyphens and underscores
        normalized = re.sub(r'[^\w\s\-]', '', normalized)
        
        # Replace spaces and multiple whitespace with underscores
        normalized = re.sub(r'\s+', '_', normalized)
        
        # Remove multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        # Limit length and ensure it's not empty
        if len(normalized) > 50:
            # For very long names, use a hash-based approach
            return self._hash_normalize(text)
        
        return normalized if normalized else self._hash_normalize(text)
    
    def _hash_normalize(self, text: str) -> str:
        """Generate hash-based normalized identifier for complex cases"""
        # Create a short hash for very long or complex entity names
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
        
        # Try to preserve some readable part
        readable_part = re.sub(r'[^\w]', '', text.lower())[:8]
        
        if readable_part:
            return f"{readable_part}_{text_hash}"
        else:
            return text_hash
    
    def get_namespace_prefixes(self) -> dict:
        """Get namespace prefixes for RDF serialization"""
        return {
            'kr': self.base_namespace,
            'foaf': 'http://xmlns.com/foaf/0.1/',
            'schema': 'https://schema.org/',
            'dcterms': 'http://purl.org/dc/terms/',
            'skos': 'http://www.w3.org/2004/02/skos/core#',
            'qudt': 'http://qudt.org/schema/qudt/',
            'time': 'http://www.w3.org/2006/time#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'xsd': 'http://www.w3.org/2001/XMLSchema#'
        }
    
    def expand_uri(self, prefixed_uri: str) -> str:
        """Expand prefixed URI to full URI"""
        prefixes = self.get_namespace_prefixes()
        
        if ':' in prefixed_uri:
            prefix, local_part = prefixed_uri.split(':', 1)
            if prefix in prefixes:
                return prefixes[prefix] + local_part
        
        return prefixed_uri
    
    def validate_uri(self, uri: str) -> bool:
        """Validate that URI is well-formed"""
        try:
            # Basic URI validation
            if not uri or len(uri) < 3:
                return False
            
            # Check for valid characters
            if re.search(r'[<>"\s]', uri):
                return False
            
            return True
        except:
            return False
