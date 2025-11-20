#!/usr/bin/env python3
"""
Entity Alignment Manager - Routes between basic and contextual alignment

Provides backward compatibility while enabling enhanced contextual alignment
for specific entity types and ontologies based on environment variables.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from .EntityAligner import EntityAligner
from .ContextualEntityAligner import ContextualEntityAligner

class EntityAlignmentManager:
    """
    Manages entity alignment routing between basic and contextual approaches
    
    Uses environment variables to control which entities get contextual alignment:
    - ENABLE_CONTEXTUAL_ALIGNMENT=true/false
    - CONTEXTUAL_ALIGNMENT_ENTITY_TYPES=LOCATION,ORG (comma-separated)
    - CONTEXTUAL_ALIGNMENT_ONTOLOGIES=geonames,climate_risk (comma-separated)
    """
    
    def __init__(self, kg_manager):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize both aligners
        self.basic_aligner = EntityAligner(kg_manager)
        
        # Feature flag configuration
        self.contextual_enabled = os.getenv('ENABLE_CONTEXTUAL_ALIGNMENT', 'false').lower() == 'true'
        self.contextual_entity_types = self._parse_env_list('CONTEXTUAL_ALIGNMENT_ENTITY_TYPES', ['LOCATION'])
        self.contextual_ontologies = self._parse_env_list('CONTEXTUAL_ALIGNMENT_ONTOLOGIES', ['geonames'])
        
        # Initialize contextual aligner if enabled
        self.contextual_aligner = None
        if self.contextual_enabled:
            try:
                self.contextual_aligner = ContextualEntityAligner(kg_manager)
                self.logger.info(f"Contextual alignment enabled for types: {self.contextual_entity_types}, ontologies: {self.contextual_ontologies}")
            except Exception as e:
                self.logger.error(f"Failed to initialize contextual aligner: {e}")
                self.contextual_enabled = False
        
        if not self.contextual_enabled:
            self.logger.info("Using basic entity alignment only")
    
    def align_entities_to_ontologies(self, entities_by_chunk: List[Dict[str, Any]], 
                                   climate_ontology=None, geonames_ontology=None) -> List[Dict[str, Any]]:
        """
        Main alignment method - routes entities to appropriate aligner
        
        Args:
            entities_by_chunk: List of entity mappings from nlp-worker
            climate_ontology: Climate risk ontology (for backward compatibility)
            geonames_ontology: Geonames ontology (for backward compatibility)
            
        Returns:
            List of aligned entities with ontology_alignment field
        """
        
        if not self.contextual_enabled or not self.contextual_aligner:
            # Fall back to basic alignment
            return self.basic_aligner.align_entities_to_concepts(entities_by_chunk)
        
        # Separate entities for contextual vs basic alignment
        contextual_entities = []
        basic_entities = []
        
        for entity in entities_by_chunk:
            entity_type = entity.get('type', 'OTHER')
            
            if self._should_use_contextual_alignment(entity_type):
                contextual_entities.append(entity)
            else:
                basic_entities.append(entity)
        
        aligned_entities = []
        
        # Process contextual entities
        if contextual_entities:
            self.logger.info(f"Processing {len(contextual_entities)} entities with contextual alignment")
            
            # Extract document metadata for context
            document_metadata = self._extract_document_metadata(entities_by_chunk)
            
            # Use contextual alignment
            contextual_results = self.contextual_aligner.align_entities_with_context(
                contextual_entities, 
                document_metadata
            )
            aligned_entities.extend(contextual_results)
        
        # Process basic entities
        if basic_entities:
            self.logger.info(f"Processing {len(basic_entities)} entities with basic alignment")
            basic_results = self.basic_aligner.align_entities_to_concepts(basic_entities)
            aligned_entities.extend(basic_results.get('aligned_entities', []))
        
        return aligned_entities
    
    def _should_use_contextual_alignment(self, entity_type: str) -> bool:
        """Determine if entity should use contextual alignment"""
        return entity_type in self.contextual_entity_types
    
    def _parse_env_list(self, env_var: str, default: List[str]) -> List[str]:
        """Parse comma-separated environment variable into list"""
        value = os.getenv(env_var, '')
        if not value:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def _extract_document_metadata(self, entities_by_chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract document-level metadata from entity chunks"""
        
        # Get document ID from first entity
        doc_id = None
        if entities_by_chunk:
            chunk_id = entities_by_chunk[0].get('chunk_id', '')
            if '_chunk_' in chunk_id:
                doc_id = chunk_id.split('_chunk_')[0]
        
        # TODO: Fetch document title from database using doc_id
        # For now, return basic metadata
        return {
            'document_id': doc_id,
            'title': '',  # Will be populated from database
            'keywords': [],
            'domain_signals': []
        }
    
    def get_alignment_statistics(self) -> Dict[str, Any]:
        """Get combined alignment statistics"""
        stats = {
            'contextual_enabled': self.contextual_enabled,
            'contextual_entity_types': self.contextual_entity_types,
            'contextual_ontologies': self.contextual_ontologies
        }
        
        if self.contextual_aligner:
            stats['contextual_stats'] = self.contextual_aligner.get_alignment_statistics()
        
        stats['basic_stats'] = self.basic_aligner.get_alignment_statistics()
        
        return stats
