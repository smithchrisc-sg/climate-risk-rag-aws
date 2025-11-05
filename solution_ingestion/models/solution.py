#!/usr/bin/env python3
"""
Solution Model for Solution Ingestion
Defines the Solution data structure with production database integration.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging
import sys
import os
from pathlib import Path

# Import DocumentIDManager at module level
try:
    from database_core_layer.utils.DocumentIDManager import DocumentIDManager
    DOCUMENT_ID_MANAGER_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import DocumentIDManager: {e}")
    raise RuntimeError(f"DocumentIDManager import failed - this is a critical system error: {e}")

logger = logging.getLogger(__name__)

@dataclass
class Solution:
    """Represents a climate risk solution from CSV data."""
    
    # Core identifiers
    id: str
    source_file: str
    row_number: int
    
    # Solution metadata
    number: str
    name: str
    country: str
    
    # Organizations
    public_organisations: str
    international_organisations: str
    private_organisations: str
    
    # Classification
    type_of_risk: str
    type_of_solution: str
    ppp: str
    theme: str
    year_of_implementation: str
    
    # Content
    description: str
    key_highlights: str
    results: str
    
    # Sources
    organization_sources: str
    other_sources: str
    contact_information: str
    
    # Timestamps
    date_added: str
    last_updated: str
    most_recent_changes: str
    
    # Database integration
    doc_id: Optional[str] = None
    source_url: Optional[str] = None
    pseudo_document_text: Optional[str] = None
    _doc_id_manager = None
    
    def __post_init__(self):
        """Validate and normalize solution data after initialization."""
        # Ensure required fields are not empty
        if not self.name.strip():
            raise ValueError(f"Solution name cannot be empty for {self.id}")
        
        # Extract source URL from CSV fields
        self.source_url = self._extract_source_url()
        
        # Generate document ID using production DocumentIDManager
        self.doc_id = self._generate_production_doc_id()
    
    def _extract_source_url(self) -> str:
        """Extract source URL from Organization Sources or Other Sources fields."""
        import re
        
        # URL pattern to match http/https URLs
        url_pattern = r'https?://[^\s,;]+(?:\.[^\s,;]+)*'
        
        # First check Organization Sources
        if self.organization_sources.strip():
            urls = re.findall(url_pattern, self.organization_sources)
            if urls:
                return urls[0].strip()
        
        # Then check Other Sources
        if self.other_sources.strip():
            urls = re.findall(url_pattern, self.other_sources)
            if urls:
                return urls[0].strip()
        
        # Error if no URL found - this should not happen per spec
        raise ValueError(f"No source URL found in Organization Sources or Other Sources for solution {self.id}. "
                        f"Organization Sources: '{self.organization_sources}', "
                        f"Other Sources: '{self.other_sources}'")
    
    def _get_doc_id_manager(self):
        """Get DocumentIDManager instance."""
        if self._doc_id_manager is None:
            try:
                self._doc_id_manager = DocumentIDManager()
                logger.info("DocumentIDManager initialized successfully")
            except Exception as e:
                logger.error(f"Could not initialize DocumentIDManager: {e}")
                raise RuntimeError(f"DocumentIDManager initialization failed - this is a critical system error: {e}")
        return self._doc_id_manager
    
    def _generate_production_doc_id(self) -> str:
        """Generate document ID using DocumentIDManager."""
        doc_id_manager = self._get_doc_id_manager()
        
        try:
            # Use the actual extracted source URL
            doc_id = doc_id_manager.add_solution(self.source_url, self.name)
            logger.debug(f"Generated production doc_id via add_solution: {doc_id} for {self.id}")
            return doc_id
        except Exception as e:
            logger.error(f"Production doc_id generation failed: {e}")
            raise RuntimeError(f"Document ID generation failed - this is a critical system error: {e}")
    
    def get_full_text(self) -> str:
        """Get combined text content for processing."""
        parts = []
        
        # Add non-empty text fields
        for field in ['name', 'description', 'key_highlights', 'results']:
            value = getattr(self, field, '').strip()
            if value:
                parts.append(value)
        
        return ' '.join(parts)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get solution metadata for database storage."""
        return {
            'source_file': self.source_file,
            'row_number': self.row_number,
            'country': self.country,
            'type_of_risk': self.type_of_risk,
            'type_of_solution': self.type_of_solution,
            'theme': self.theme,
            'year_of_implementation': self.year_of_implementation,
            'ppp': self.ppp,
            'date_added': self.date_added,
            'last_updated': self.last_updated
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert solution to dictionary."""
        return {
            'id': self.id,
            'doc_id': self.doc_id,
            'source_file': self.source_file,
            'row_number': self.row_number,
            'number': self.number,
            'name': self.name,
            'country': self.country,
            'public_organisations': self.public_organisations,
            'international_organisations': self.international_organisations,
            'private_organisations': self.private_organisations,
            'type_of_risk': self.type_of_risk,
            'type_of_solution': self.type_of_solution,
            'ppp': self.ppp,
            'theme': self.theme,
            'year_of_implementation': self.year_of_implementation,
            'description': self.description,
            'key_highlights': self.key_highlights,
            'results': self.results,
            'organization_sources': self.organization_sources,
            'other_sources': self.other_sources,
            'contact_information': self.contact_information,
            'date_added': self.date_added,
            'last_updated': self.last_updated,
            'most_recent_changes': self.most_recent_changes,
            'full_text': self.get_full_text(),
            'metadata': self.get_metadata()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Solution':
        """Create Solution from dictionary (e.g., from CSV parser)."""
        return cls(
            id=data['id'],
            source_file=data['source_file'],
            row_number=data['row_number'],
            number=data['number'],
            name=data['name'],
            country=data['country'],
            public_organisations=data['public_organisations'],
            international_organisations=data['international_organisations'],
            private_organisations=data['private_organisations'],
            type_of_risk=data['type_of_risk'],
            type_of_solution=data['type_of_solution'],
            ppp=data['ppp'],
            theme=data['theme'],
            year_of_implementation=data['year_of_implementation'],
            description=data['description'],
            key_highlights=data['key_highlights'],
            results=data['results'],
            organization_sources=data['organization_sources'],
            other_sources=data['other_sources'],
            contact_information=data['contact_information'],
            date_added=data['date_added'],
            last_updated=data['last_updated'],
            most_recent_changes=data['most_recent_changes']
        )
    
    def __str__(self) -> str:
        return f"Solution({self.id}: {self.name[:50]}...)"
    
    def __repr__(self) -> str:
        return self.__str__()
