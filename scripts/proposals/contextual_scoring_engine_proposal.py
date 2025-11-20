#!/usr/bin/env python3
"""
Contextual Scoring Engine - Applies context-based scoring to entity alignments

Implements geographic context scoring for LOCATION entities using document
and chunk-level context signals.
"""

import os
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

# Import the EntityAlignment dataclass from the main aligner
# from .ContextualEntityAligner import EntityAlignment

class ContextualScoringEngine:
    """
    Applies contextual scoring to enhance entity alignment confidence
    
    Uses document title, chunk co-occurrence, and semantic signals
    to improve disambiguation accuracy for ambiguous entities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load scoring weights from environment
        self.weight_document_title = float(os.getenv('CONTEXT_WEIGHT_DOCUMENT_TITLE', '0.3'))
        self.weight_chunk_cooccurrence = float(os.getenv('CONTEXT_WEIGHT_CHUNK_COOCCURRENCE', '0.4'))
        self.weight_semantic_signals = float(os.getenv('CONTEXT_WEIGHT_SEMANTIC_SIGNALS', '0.2'))
        self.weight_entity_type_match = float(os.getenv('CONTEXT_WEIGHT_ENTITY_TYPE_MATCH', '0.1'))
        
        self.logger.info(f"ContextualScoringEngine initialized with weights: "
                        f"doc={self.weight_document_title}, chunk={self.weight_chunk_cooccurrence}, "
                        f"semantic={self.weight_semantic_signals}, type={self.weight_entity_type_match}")
    
    def score_alignments_with_context(self, alignments: List[Any], entity_text: str, entity_type: str,
                                     document_metadata: Dict[str, Any], 
                                     chunk_context: Dict[str, Any]) -> List[Any]:
        """
        Apply context-based scoring to enhance alignment confidence
        
        Args:
            alignments: List of EntityAlignment objects
            entity_text: Original entity text
            entity_type: Entity type (LOCATION, ORG, etc.)
            document_metadata: Document context
            chunk_context: Chunk-level context
            
        Returns:
            List of EntityAlignment objects with updated confidence scores
        """
        
        for alignment in alignments:
            # Apply ontology-specific context scoring
            if alignment.ontology == 'geonames':
                context_boost = self._score_geographic_context(
                    alignment, document_metadata, chunk_context
                )
            else:
                context_boost = self._score_generic_context(
                    alignment, document_metadata, chunk_context
                )
            
            # Update confidence score with context boost
            alignment.confidence_score = min(alignment.confidence_score + context_boost, 1.0)
            
            # Record context signals that contributed to the score
            alignment.context_signals = self._identify_context_signals(
                alignment, document_metadata, chunk_context
            )
        
        # Sort by confidence score
        return sorted(alignments, key=lambda x: x.confidence_score, reverse=True)
    
    def _score_geographic_context(self, alignment: Any, document_metadata: Dict[str, Any], 
                                 chunk_context: Dict[str, Any]) -> float:
        """Score geographic entity alignment using contextual signals"""
        
        boost = 0.0
        metadata = alignment.additional_metadata
        
        # Document region alignment
        doc_title = document_metadata.get('title', '').lower()
        
        # North American context boost
        if any(signal in doc_title for signal in ['north american', 'usa', 'united states', 'canada']):
            if metadata.get('country') in ['US', 'CA']:
                boost += self.weight_document_title
                self.logger.debug(f"Applied North American context boost: +{self.weight_document_title}")
            else:
                boost -= self.weight_document_title * 0.5  # Penalty for non-North American
        
        # European context boost
        elif any(signal in doc_title for signal in ['european', 'europe', 'eu']):
            eu_countries = ['FR', 'DE', 'IT', 'ES', 'NL', 'BE', 'AT', 'PT', 'GR']
            if metadata.get('country') in eu_countries:
                boost += self.weight_document_title
                self.logger.debug(f"Applied European context boost: +{self.weight_document_title}")
        
        # Asian context boost
        elif any(signal in doc_title for signal in ['asian', 'asia', 'south asia']):
            asian_countries = ['IN', 'CN', 'JP', 'KR', 'TH', 'VN', 'ID', 'MY', 'SG', 'PH', 'BD', 'PK', 'LK', 'NP']
            if metadata.get('country') in asian_countries:
                boost += self.weight_document_title
                self.logger.debug(f"Applied Asian context boost: +{self.weight_document_title}")
        
        # Chunk co-occurrence alignment
        entities_by_type = chunk_context.get('entities_by_type', {})
        chunk_locations = entities_by_type.get('LOCATION', [])
        
        # State/province co-occurrence
        admin1 = metadata.get('admin1', '')
        if admin1 and any(admin1.lower() in loc.lower() for loc in chunk_locations):
            boost += self.weight_chunk_cooccurrence
            self.logger.debug(f"Applied state/province co-occurrence boost: +{self.weight_chunk_cooccurrence}")
        
        # Country co-occurrence
        country = metadata.get('country', '')
        country_names = self._get_country_names(country)
        if any(country_name.lower() in ' '.join(chunk_locations).lower() for country_name in country_names):
            boost += self.weight_chunk_cooccurrence * 0.8
            self.logger.debug(f"Applied country co-occurrence boost: +{self.weight_chunk_cooccurrence * 0.8}")
        
        # Population-based relevance (larger cities more likely to be mentioned)
        population = metadata.get('population', 0)
        if population:
            if population > 1000000:  # Major city
                boost += self.weight_entity_type_match
            elif population > 100000:  # Medium city
                boost += self.weight_entity_type_match * 0.5
        
        # Semantic signals boost
        semantic_signals = chunk_context.get('semantic_signals', [])
        if 'geographic:country_context' in semantic_signals:
            boost += self.weight_semantic_signals
        if 'geographic:regional_directional' in semantic_signals:
            boost += self.weight_semantic_signals * 0.5
        
        return boost
    
    def _score_generic_context(self, alignment: Any, document_metadata: Dict[str, Any], 
                              chunk_context: Dict[str, Any]) -> float:
        """Generic context scoring for non-geographic entities"""
        
        boost = 0.0
        
        # Basic keyword matching between document and entity
        doc_text = (document_metadata.get('title', '') + ' ' + 
                   ' '.join(document_metadata.get('keywords', []))).lower()
        
        entity_text = alignment.entity_text.lower()
        if entity_text in doc_text:
            boost += self.weight_document_title * 0.5
        
        return boost
    
    def _identify_context_signals(self, alignment: Any, document_metadata: Dict[str, Any],
                                 chunk_context: Dict[str, Any]) -> List[str]:
        """Identify which context signals contributed to the alignment score"""
        
        signals = []
        
        # Document-level signals
        doc_title = document_metadata.get('title', '').lower()
        if 'north american' in doc_title or 'usa' in doc_title:
            signals.append('doc_north_american_context')
        elif 'european' in doc_title or 'europe' in doc_title:
            signals.append('doc_european_context')
        elif 'asian' in doc_title or 'asia' in doc_title:
            signals.append('doc_asian_context')
        
        # Chunk-level signals
        entities_by_type = chunk_context.get('entities_by_type', {})
        chunk_locations = entities_by_type.get('LOCATION', [])
        
        if len(chunk_locations) > 1:
            signals.append(f"co_occurrence_with_{len(chunk_locations)}_locations")
        
        # Semantic signals
        semantic_signals = chunk_context.get('semantic_signals', [])
        signals.extend([f"semantic_{signal}" for signal in semantic_signals[:3]])  # Top 3
        
        # Population-based signals
        metadata = alignment.additional_metadata
        population = metadata.get('population', 0)
        if population > 1000000:
            signals.append('major_city_population')
        elif population > 100000:
            signals.append('medium_city_population')
        
        return signals
    
    def _get_country_names(self, country_code: str) -> List[str]:
        """Get common names for a country code"""
        
        country_mapping = {
            'US': ['usa', 'united states', 'america', 'us'],
            'CA': ['canada', 'canadian'],
            'FR': ['france', 'french'],
            'DE': ['germany', 'german'],
            'UK': ['united kingdom', 'britain', 'british', 'england'],
            'IN': ['india', 'indian'],
            'CN': ['china', 'chinese'],
            'JP': ['japan', 'japanese'],
            'NP': ['nepal', 'nepalese']
        }
        
        return country_mapping.get(country_code, [country_code.lower()])
    
    def get_scoring_statistics(self) -> Dict[str, Any]:
        """Get scoring configuration and statistics"""
        
        return {
            'weights': {
                'document_title': self.weight_document_title,
                'chunk_cooccurrence': self.weight_chunk_cooccurrence,
                'semantic_signals': self.weight_semantic_signals,
                'entity_type_match': self.weight_entity_type_match
            }
        }
