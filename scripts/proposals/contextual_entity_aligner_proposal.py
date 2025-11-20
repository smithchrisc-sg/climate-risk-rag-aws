#!/usr/bin/env python3
"""
Contextual Entity Aligner - Enhanced entity alignment with FTS-SPARQL and context scoring

Implements multi-level context analysis for accurate entity disambiguation,
particularly for ambiguous LOCATION entities using geonames ontology.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

from .KnowledgeGraphManager import KnowledgeGraphManager
from .FTSSparqlQueryBuilder import FTSSparqlQueryBuilder
from .ContextualScoringEngine import ContextualScoringEngine

@dataclass
class EntityAlignment:
    """Represents an aligned entity with context information"""
    entity_text: str
    entity_type: str
    aligned_uri: str
    ontology: str
    confidence_score: float
    context_signals: List[str]
    chunk_id: str
    document_id: str
    additional_metadata: Dict[str, Any]

class ContextualEntityAligner:
    """
    Enhanced entity alignment using FTS-SPARQL queries and contextual scoring
    
    Focuses on LOCATION entities with geonames ontology for initial implementation
    """
    
    def __init__(self, kg_manager: KnowledgeGraphManager):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kg_manager = kg_manager
        
        # Initialize components
        self.fts_query_builder = FTSSparqlQueryBuilder()
        self.scoring_engine = ContextualScoringEngine()
        
        # Configuration from environment
        self.fts_timeout_ms = int(os.getenv('FTS_QUERY_TIMEOUT_MS', '2000'))
        self.max_results_per_ontology = int(os.getenv('FTS_MAX_RESULTS_PER_ONTOLOGY', '10'))
        self.confidence_threshold = float(os.getenv('CONTEXTUAL_CONFIDENCE_THRESHOLD', '0.3'))
        
        # Supported ontologies (controlled by environment)
        self.supported_ontologies = self._load_supported_ontologies()
        
        self.logger.info(f"ContextualEntityAligner initialized with {len(self.supported_ontologies)} ontologies")
    
    def align_entities_with_context(self, entities_by_chunk: List[Dict[str, Any]], 
                                   document_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Main entry point for contextual entity alignment
        
        Args:
            entities_by_chunk: List of entity mappings from nlp-worker
            document_metadata: Document title, keywords, domain signals
            
        Returns:
            List of aligned entities in format compatible with existing pipeline
        """
        
        self.logger.info(f"Starting contextual alignment for {len(entities_by_chunk)} entities")
        
        # Group entities by chunk for co-occurrence analysis
        chunks_with_entities = self._group_entities_by_chunk(entities_by_chunk)
        
        aligned_entities = []
        
        for chunk_id, chunk_entities in chunks_with_entities.items():
            # Build chunk context
            chunk_context = self._build_chunk_context(chunk_entities, chunk_id)
            
            # Process each entity with full context
            for entity in chunk_entities:
                alignments = self._align_entity_with_context(
                    entity, 
                    document_metadata, 
                    chunk_context
                )
                
                # Convert to pipeline format and add best alignment
                if alignments:
                    best_alignment = max(alignments, key=lambda x: x.confidence_score)
                    pipeline_format = self._convert_to_pipeline_format(best_alignment, entity)
                    aligned_entities.append(pipeline_format)
        
        self.logger.info(f"Aligned {len(aligned_entities)} entities with contextual analysis")
        return aligned_entities
    
    def _group_entities_by_chunk(self, entities_by_chunk: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group entities by chunk for co-occurrence analysis"""
        
        chunks = {}
        for entity in entities_by_chunk:
            chunk_id = entity.get('chunk_id', 'unknown')
            if chunk_id not in chunks:
                chunks[chunk_id] = []
            chunks[chunk_id].append(entity)
        
        return chunks
    
    def _build_chunk_context(self, chunk_entities: List[Dict[str, Any]], chunk_id: str) -> Dict[str, Any]:
        """Build rich context for chunk-level entity disambiguation"""
        
        # Group entities by type for co-occurrence analysis
        entities_by_type = {}
        for entity in chunk_entities:
            entity_type = entity.get('type', 'OTHER')
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity['entity'])
        
        # Extract semantic signals (simplified for initial implementation)
        semantic_signals = self._extract_semantic_signals(chunk_entities)
        
        return {
            'chunk_id': chunk_id,
            'entities_by_type': entities_by_type,
            'co_occurring_entities': chunk_entities,
            'semantic_signals': semantic_signals
        }
    
    def _extract_semantic_signals(self, chunk_entities: List[Dict[str, Any]]) -> List[str]:
        """Extract semantic signals from chunk entities"""
        
        signals = []
        
        # Look for geographic signals
        location_entities = [e['entity'].lower() for e in chunk_entities if e.get('type') == 'LOCATION']
        if location_entities:
            # Check for regional patterns
            if any('north' in loc or 'south' in loc or 'east' in loc or 'west' in loc for loc in location_entities):
                signals.append('geographic:regional_directional')
            
            # Check for country/state patterns
            known_countries = ['usa', 'canada', 'mexico', 'france', 'germany', 'uk', 'united kingdom']
            if any(country in ' '.join(location_entities) for country in known_countries):
                signals.append('geographic:country_context')
        
        return signals
    
    def _align_entity_with_context(self, entity: Dict[str, Any], document_metadata: Dict[str, Any], 
                                  chunk_context: Dict[str, Any]) -> List[EntityAlignment]:
        """Align single entity using contextual FTS-SPARQL queries"""
        
        entity_text = entity['entity']
        entity_type = entity.get('type', 'OTHER')
        chunk_id = chunk_context['chunk_id']
        
        self.logger.debug(f"Aligning entity: {entity_text} (type: {entity_type})")
        
        # Determine relevant ontologies for this entity type
        relevant_ontologies = self._get_relevant_ontologies(entity_type)
        
        all_alignments = []
        
        # Query each relevant ontology
        for ontology_name in relevant_ontologies:
            alignments = self._query_ontology_for_entity(
                entity_text, entity_type, ontology_name, document_metadata, chunk_context
            )
            all_alignments.extend(alignments)
        
        # Apply contextual scoring
        scored_alignments = self.scoring_engine.score_alignments_with_context(
            all_alignments, entity_text, entity_type, document_metadata, chunk_context
        )
        
        # Filter by confidence threshold
        return [alignment for alignment in scored_alignments 
                if alignment.confidence_score >= self.confidence_threshold]
    
    def _get_relevant_ontologies(self, entity_type: str) -> List[str]:
        """Determine which ontologies to query for given entity type"""
        
        # For initial implementation, focus on LOCATION -> geonames
        if entity_type == 'LOCATION':
            return ['geonames'] if 'geonames' in self.supported_ontologies else []
        
        return []
    
    def _query_ontology_for_entity(self, entity_text: str, entity_type: str, ontology_name: str,
                                  document_metadata: Dict[str, Any], chunk_context: Dict[str, Any]) -> List[EntityAlignment]:
        """Query specific ontology using FTS-enhanced SPARQL"""
        
        try:
            # Build FTS-SPARQL query
            query = self.fts_query_builder.build_location_query(
                entity_text, document_metadata, chunk_context
            )
            
            # Execute query via Neptune
            results = self.kg_manager.execute_sparql_query(query)
            
            # Convert results to EntityAlignment objects
            alignments = []
            for result in results:
                alignment = self._create_alignment_from_sparql_result(
                    result, entity_text, entity_type, ontology_name, chunk_context['chunk_id']
                )
                if alignment:
                    alignments.append(alignment)
            
            self.logger.debug(f"Found {len(alignments)} alignments in {ontology_name} for {entity_text}")
            return alignments
            
        except Exception as e:
            self.logger.error(f"Error querying {ontology_name} for {entity_text}: {e}")
            return []
    
    def _create_alignment_from_sparql_result(self, result: Dict, entity_text: str, 
                                           entity_type: str, ontology_name: str, 
                                           chunk_id: str) -> Optional[EntityAlignment]:
        """Create EntityAlignment from SPARQL query result"""
        
        # Extract URI and label from result
        aligned_uri = result.get('entity') or result.get('concept')
        label = result.get('label')
        
        if not aligned_uri or not label:
            return None
        
        # Calculate base confidence from FTS score or string similarity
        base_confidence = self._calculate_base_confidence(entity_text, label, result)
        
        # Extract ontology-specific metadata
        additional_metadata = self._extract_ontology_metadata(result, ontology_name)
        
        return EntityAlignment(
            entity_text=entity_text,
            entity_type=entity_type,
            aligned_uri=aligned_uri,
            ontology=ontology_name,
            confidence_score=base_confidence,
            context_signals=[],  # Will be populated during scoring
            chunk_id=chunk_id,
            document_id="",  # Will be set by caller
            additional_metadata=additional_metadata
        )
    
    def _calculate_base_confidence(self, entity_text: str, label: str, result: Dict) -> float:
        """Calculate base confidence score from SPARQL result"""
        
        # Use FTS score if available
        if 'fts_score' in result:
            return min(float(result['fts_score']), 1.0)
        
        # Fall back to string similarity
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, entity_text.lower(), label.lower()).ratio()
        return similarity
    
    def _extract_ontology_metadata(self, result: Dict, ontology_name: str) -> Dict[str, Any]:
        """Extract ontology-specific metadata from SPARQL result"""
        
        metadata = {}
        
        if ontology_name == 'geonames':
            # Geographic ontology metadata
            metadata.update({
                'country': result.get('country'),
                'admin1': result.get('parentAdmin1Name'),
                'feature_class': result.get('featureClass'),
                'coordinates': {
                    'lat': result.get('lat'),
                    'lon': result.get('lon')
                } if result.get('lat') and result.get('lon') else None,
                'population': result.get('population')
            })
        
        return metadata
    
    def _convert_to_pipeline_format(self, alignment: EntityAlignment, original_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert EntityAlignment to format expected by existing pipeline"""
        
        return {
            'entity': alignment.entity_text,
            'type': alignment.entity_type,
            'chunk_id': alignment.chunk_id,
            'score': original_entity.get('score', 0.0),
            'ontology_alignment': {
                'aligned_uri': alignment.aligned_uri,
                'ontology': alignment.ontology,
                'confidence_score': alignment.confidence_score,
                'context_signals': alignment.context_signals,
                'metadata': alignment.additional_metadata
            }
        }
    
    def _load_supported_ontologies(self) -> List[str]:
        """Load supported ontologies from environment configuration"""
        
        env_ontologies = os.getenv('CONTEXTUAL_ALIGNMENT_ONTOLOGIES', 'geonames')
        return [ont.strip() for ont in env_ontologies.split(',') if ont.strip()]
    
    def get_alignment_statistics(self) -> Dict[str, Any]:
        """Get alignment statistics for monitoring"""
        
        return {
            'supported_ontologies': self.supported_ontologies,
            'confidence_threshold': self.confidence_threshold,
            'fts_timeout_ms': self.fts_timeout_ms,
            'max_results_per_ontology': self.max_results_per_ontology
        }
