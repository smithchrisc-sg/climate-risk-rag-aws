#!/usr/bin/env python3
"""
Document Entity Extractor
Extracts document-level entities from metadata (author, publisher, etc.)
"""

import json
import boto3
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DocumentEntity:
    """Document-level entity representation"""
    canonical_name: str
    entity_type: str
    rdf_type: str
    confidence: float
    properties: Dict[str, Any]
    context: str  # "author", "publisher", "creator", etc.
    kg_uri: str

class DocumentEntityExtractor:
    """Extracts entities from document metadata and Textract key-values"""
    
    def __init__(self, uri_minter):
        self.uri_minter = uri_minter
        self.s3_client = boto3.client('s3')
    
    def extract_document_entities(self, document_metadata: Dict[str, Any]) -> List[DocumentEntity]:
        """
        Extract document-level entities from various metadata sources
        
        Args:
            document_metadata: Document metadata including Textract key-values
            
        Returns:
            List of document-level entities
        """
        entities = []
        
        try:
            # Extract from basic metadata fields
            basic_entities = self._extract_from_basic_metadata(document_metadata)
            entities.extend(basic_entities)
            
            # Extract from Textract key-value pairs if available
            if 'textract_key_values' in document_metadata:
                textract_entities = self._extract_from_textract_key_values(document_metadata['textract_key_values'])
                entities.extend(textract_entities)
            
            # Extract from document structure if available
            if 'document_structure' in document_metadata:
                structure_entities = self._extract_from_document_structure(document_metadata['document_structure'])
                entities.extend(structure_entities)
            
            logger.info(f"Extracted {len(entities)} document-level entities")
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting document entities: {e}")
            return []
    
    def _extract_from_basic_metadata(self, metadata: Dict[str, Any]) -> List[DocumentEntity]:
        """Extract entities from basic metadata fields"""
        entities = []
        
        # Author extraction
        author = metadata.get('author') or metadata.get('creator')
        if author and isinstance(author, str) and author.strip():
            author_entity = self._create_person_entity(
                name=author.strip(),
                context='author',
                confidence=1.0  # Metadata is considered certain
            )
            entities.append(author_entity)
        
        # Publisher extraction
        publisher = metadata.get('publisher') or metadata.get('organization')
        if publisher and isinstance(publisher, str) and publisher.strip():
            publisher_entity = self._create_organization_entity(
                name=publisher.strip(),
                context='publisher',
                confidence=1.0
            )
            entities.append(publisher_entity)
        
        # Additional creators/contributors
        contributors = metadata.get('contributors', [])
        if isinstance(contributors, list):
            for contributor in contributors:
                if isinstance(contributor, str) and contributor.strip():
                    contributor_entity = self._create_person_entity(
                        name=contributor.strip(),
                        context='contributor',
                        confidence=0.9
                    )
                    entities.append(contributor_entity)
        
        return entities
    
    def _extract_from_textract_key_values(self, key_values: List[Dict[str, Any]]) -> List[DocumentEntity]:
        """Extract entities from Textract key-value pairs"""
        entities = []
        
        # Define patterns for different entity types
        author_patterns = ['author', 'written by', 'by', 'prepared by', 'created by']
        organization_patterns = ['organization', 'company', 'institution', 'agency', 'department']
        
        try:
            for kv_pair in key_values:
                key = kv_pair.get('key', '').lower().strip()
                value = kv_pair.get('value', '').strip()
                confidence = kv_pair.get('confidence', 0.8)
                
                if not key or not value or len(value) < 2:
                    continue
                
                # Check for author patterns
                if any(pattern in key for pattern in author_patterns):
                    if self._is_likely_person_name(value):
                        author_entity = self._create_person_entity(
                            name=value,
                            context='author',
                            confidence=confidence * 0.8  # Reduce confidence for extracted metadata
                        )
                        entities.append(author_entity)
                
                # Check for organization patterns
                elif any(pattern in key for pattern in organization_patterns):
                    if self._is_likely_organization_name(value):
                        org_entity = self._create_organization_entity(
                            name=value,
                            context='publisher',
                            confidence=confidence * 0.8
                        )
                        entities.append(org_entity)
                
                # Check for specific known fields
                elif key in ['title', 'document title']:
                    # Extract organizations from titles (e.g., "World Bank Report")
                    org_from_title = self._extract_organization_from_title(value)
                    if org_from_title:
                        title_org_entity = self._create_organization_entity(
                            name=org_from_title,
                            context='publisher',
                            confidence=0.7
                        )
                        entities.append(title_org_entity)
        
        except Exception as e:
            logger.error(f"Error extracting from Textract key-values: {e}")
        
        return entities
    
    def _extract_from_document_structure(self, structure: Dict[str, Any]) -> List[DocumentEntity]:
        """Extract entities from document structure information"""
        entities = []
        
        try:
            # Look for header information that might contain author/organization
            if 'headers' in structure:
                for header in structure['headers']:
                    header_text = header.get('text', '').strip()
                    
                    # Check if header contains organization names
                    if self._is_likely_organization_name(header_text):
                        header_org_entity = self._create_organization_entity(
                            name=header_text,
                            context='publisher',
                            confidence=0.6
                        )
                        entities.append(header_org_entity)
            
            # Look for footer information
            if 'footers' in structure:
                for footer in structure['footers']:
                    footer_text = footer.get('text', '').strip()
                    
                    # Extract copyright or organization info from footers
                    org_from_footer = self._extract_organization_from_footer(footer_text)
                    if org_from_footer:
                        footer_org_entity = self._create_organization_entity(
                            name=org_from_footer,
                            context='publisher',
                            confidence=0.5
                        )
                        entities.append(footer_org_entity)
        
        except Exception as e:
            logger.error(f"Error extracting from document structure: {e}")
        
        return entities
    
    def _create_person_entity(self, name: str, context: str, confidence: float) -> DocumentEntity:
        """Create a person entity from metadata"""
        canonical_name = self.uri_minter.normalize_person_name(name)
        entity_uri = self.uri_minter.mint_person_uri(name)
        
        # Parse name components
        name_parts = self._parse_person_name(name)
        
        properties = {
            'foaf:name': name,
            'foaf:givenName': name_parts.get('given_name'),
            'foaf:familyName': name_parts.get('family_name'),
            'kr:entityContext': context,
            'kr:confidence': confidence,
            'kr:extractedBy': 'document-metadata',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return DocumentEntity(
            canonical_name=canonical_name,
            entity_type='PERSON',
            rdf_type='foaf:Person',
            confidence=confidence,
            properties=properties,
            context=context,
            kg_uri=entity_uri
        )
    
    def _create_organization_entity(self, name: str, context: str, confidence: float) -> DocumentEntity:
        """Create an organization entity from metadata"""
        canonical_name = self.uri_minter.normalize_organization_name(name)
        entity_uri = self.uri_minter.mint_organization_uri(name)
        
        properties = {
            'foaf:name': canonical_name,
            'schema:alternateName': name if name != canonical_name else None,
            'kr:organizationType': self._classify_organization_type(name),
            'kr:entityContext': context,
            'kr:confidence': confidence,
            'kr:extractedBy': 'document-metadata',
            'kr:extractedAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        return DocumentEntity(
            canonical_name=canonical_name,
            entity_type='ORGANIZATION',
            rdf_type='foaf:Organization',
            confidence=confidence,
            properties=properties,
            context=context,
            kg_uri=entity_uri
        )
    
    def _is_likely_person_name(self, text: str) -> bool:
        """Heuristic to determine if text is likely a person name"""
        if not text or len(text) < 2:
            return False
        
        # Basic checks
        words = text.split()
        
        # Too many words is unlikely to be a person name
        if len(words) > 5:
            return False
        
        # Check for common person name patterns
        has_title = any(word.lower().rstrip('.') in ['dr', 'prof', 'mr', 'ms', 'mrs'] for word in words)
        has_proper_case = any(word[0].isupper() for word in words if word)
        
        # Exclude obvious non-names
        exclude_patterns = ['report', 'document', 'page', 'section', 'chapter', 'table', 'figure']
        if any(pattern in text.lower() for pattern in exclude_patterns):
            return False
        
        return has_title or (has_proper_case and len(words) >= 2)
    
    def _is_likely_organization_name(self, text: str) -> bool:
        """Heuristic to determine if text is likely an organization name"""
        if not text or len(text) < 3:
            return False
        
        # Check for common organization indicators
        org_indicators = [
            'bank', 'university', 'college', 'institute', 'foundation', 'agency',
            'department', 'ministry', 'corporation', 'company', 'inc', 'ltd',
            'organization', 'association', 'society', 'council', 'commission',
            'authority', 'bureau', 'office', 'center', 'centre'
        ]
        
        text_lower = text.lower()
        has_org_indicator = any(indicator in text_lower for indicator in org_indicators)
        
        # Check for proper capitalization
        words = text.split()
        has_proper_case = any(word[0].isupper() for word in words if word)
        
        # Exclude obvious non-organizations
        exclude_patterns = ['page', 'section', 'chapter', 'table', 'figure', 'appendix']
        if any(pattern in text_lower for pattern in exclude_patterns):
            return False
        
        return has_org_indicator or (has_proper_case and len(words) >= 2)
    
    def _extract_organization_from_title(self, title: str) -> Optional[str]:
        """Extract organization name from document title"""
        # Look for patterns like "World Bank Report", "IPCC Assessment"
        org_patterns = [
            r'(World Bank)',
            r'(IPCC)',
            r'(United Nations)',
            r'(UN)',
            r'(EPA)',
            r'(NASA)',
            r'(\w+\s+Bank)',
            r'(\w+\s+University)',
            r'(\w+\s+Institute)'
        ]
        
        import re
        for pattern in org_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_organization_from_footer(self, footer_text: str) -> Optional[str]:
        """Extract organization from footer text (copyright, etc.)"""
        import re
        
        # Look for copyright patterns
        copyright_pattern = r'©\s*\d{4}\s*([^.]+)'
        match = re.search(copyright_pattern, footer_text)
        if match:
            org_name = match.group(1).strip()
            if self._is_likely_organization_name(org_name):
                return org_name
        
        return None
    
    def _parse_person_name(self, name: str) -> Dict[str, str]:
        """Parse person name into components"""
        # Remove titles
        clean_name = name.strip()
        for title in ['Dr.', 'Prof.', 'Mr.', 'Ms.', 'Mrs.', 'Dr', 'Prof', 'Mr', 'Ms', 'Mrs']:
            clean_name = clean_name.replace(title, '').strip()
        
        parts = clean_name.split()
        if len(parts) >= 2:
            return {
                'given_name': parts[0],
                'family_name': ' '.join(parts[1:])
            }
        elif len(parts) == 1:
            return {
                'given_name': parts[0],
                'family_name': None
            }
        return {}
    
    def _classify_organization_type(self, org_name: str) -> str:
        """Classify organization type based on name patterns"""
        name_lower = org_name.lower()
        
        if any(word in name_lower for word in ['university', 'college', 'institute', 'school']):
            return 'Educational Institution'
        elif any(word in name_lower for word in ['government', 'agency', 'department', 'ministry']):
            return 'Government Agency'
        elif any(word in name_lower for word in ['bank', 'financial', 'fund', 'investment']):
            return 'Financial Institution'
        elif any(word in name_lower for word in ['corporation', 'company', 'inc', 'ltd', 'llc']):
            return 'Corporation'
        elif any(word in name_lower for word in ['foundation', 'ngo', 'nonprofit', 'charity']):
            return 'Non-Profit Organization'
        else:
            return 'Organization'
