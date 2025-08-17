#!/usr/bin/env python3
"""
Contextual Entity Aligner - Enhanced entity alignment with FTS-SPARQL and context scoring

Implements multi-level context analysis for accurate entity disambiguation,
particularly for ambiguous LOCATION entities using geonames ontology.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import json
from rdflib import URIRef

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
        
        self.BASE_CONFIDENCE_THRESHOLD = float(os.getenv('BASE_CONFIDENCE_THRESHOLD', '0.8'))   
        
        # Supported ontologies (controlled by environment)
        self.supported_ontologies = self._load_supported_ontologies()
        
        # Document-scoped alignment cache
        self.current_document_id = None
        self.alignment_cache = {}  # entity_text -> EntityAlignment or 'REJECTED'
        self.cache_stats = {'hits': 0, 'misses': 0, 'rejections': 0}
        
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
        
        # Reset cache for new document
        document_id = document_metadata.get('document_id', 'unknown')
        self._reset_document_cache(document_id)
        
        self.logger.info(f"ContextualEntityAligner: Starting contextual alignment for {len(entities_by_chunk)} entities")
        
        # Log sample of input entities
        for i, entity in enumerate(entities_by_chunk[:5]):  # Log first 5 entities
            entity_text = entity.get('entity', 'UNKNOWN')
            entity_type = entity.get('type', 'UNKNOWN')
            chunk_id = entity.get('chunk_id', 'UNKNOWN')
            self.logger.info(f"ContextualEntityAligner: Input entity {i+1}: '{entity_text}' ({entity_type}) in {chunk_id}")
        
        # Group entities by chunk for co-occurrence analysis
        chunks_with_entities = self._group_entities_by_chunk(entities_by_chunk)
        self.logger.info(f"ContextualEntityAligner: Grouped entities into {len(chunks_with_entities)} chunks")
        
        aligned_entities = []
        successful_alignments = 0
        
        for chunk_id, chunk_entities in chunks_with_entities.items():
            self.logger.info(f"ContextualEntityAligner: Processing chunk {chunk_id} with {len(chunk_entities)} entities")
            
            # Build chunk context
            chunk_context = self._build_chunk_context(chunk_entities, chunk_id)
            
            # Process each entity with full context
            for entity in chunk_entities:
                entity_text = entity.get('entity', 'UNKNOWN')
                entity_type = entity.get('type', 'UNKNOWN')
                
                self.logger.info(f"ContextualEntityAligner: Processing entity '{entity_text}' ({entity_type})")
                
                try:
                    alignments = self._align_entity_with_context(
                        entity, 
                        document_metadata, 
                        chunk_context
                    )
                    
                    self.logger.info(f"ContextualEntityAligner: Entity '{entity_text}' returned {len(alignments) if alignments else 0} potential alignments")
                    
                    # Convert to pipeline format and add best alignment
                    if alignments:
                        best_alignment = max(alignments, key=lambda x: x.confidence_score)
                        self.logger.info(f"ContextualEntityAligner: Best alignment for '{entity_text}': confidence={best_alignment.confidence_score:.3f}")
                        pipeline_format = self._convert_to_pipeline_format(best_alignment, entity)
                        aligned_entities.append(pipeline_format)
                        successful_alignments += 1
                    else:
                        self.logger.info(f"ContextualEntityAligner: No alignments found for '{entity_text}'")
                        # No alignment found - add entity without ontology_alignment
                        unaligned_format = self._convert_unaligned_to_pipeline_format(entity)
                        aligned_entities.append(unaligned_format)
                        
                except Exception as e:
                    self.logger.error(f"ContextualEntityAligner: Error processing entity '{entity_text}': {e}")
                    # Add as unaligned on error
                    unaligned_format = self._convert_unaligned_to_pipeline_format(entity)
                    aligned_entities.append(unaligned_format)
        
        self.logger.info(f"ContextualEntityAligner: Alignment complete - {successful_alignments} successful alignments out of {len(entities_by_chunk)} entities")
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
        
        # Extract semantic signals
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
            known_countries = ['usa', 'canada', 'mexico', 'france', 'germany', 'uk', 'united kingdom', 'nepal', 'india']
            if any(country in ' '.join(location_entities) for country in known_countries):
                signals.append('geographic:country_context')
        
        return signals
    
    def _align_entity_with_context(self, entity: Dict[str, Any], document_metadata: Dict[str, Any], 
                                  chunk_context: Dict[str, Any]) -> List[EntityAlignment]:
        """Align single entity using contextual FTS-SPARQL queries"""
        
        entity_text = entity['entity']
        entity_type = entity.get('type', 'OTHER')
        chunk_id = chunk_context['chunk_id']
        
        # Check cache first
        cached_result = self._get_cached_alignment(entity_text)
        if cached_result is not None:
            if cached_result == 'REJECTED':
                self.cache_stats['rejections'] += 1
                self.logger.info(f"ContextualEntityAligner: Using cached rejection for '{entity_text}'")
                return []
            else:
                self.cache_stats['hits'] += 1
                self.logger.info(f"ContextualEntityAligner: Using cached alignment for '{entity_text}': {cached_result.aligned_uri}")
                # Create new alignment with current chunk_id
                cached_alignment = EntityAlignment(
                    entity_text=cached_result.entity_text,
                    entity_type=cached_result.entity_type,
                    aligned_uri=cached_result.aligned_uri,
                    ontology=cached_result.ontology,
                    confidence_score=cached_result.confidence_score,
                    context_signals=cached_result.context_signals + ['cached'],
                    chunk_id=chunk_id,  # Update to current chunk
                    document_id=cached_result.document_id,
                    additional_metadata=cached_result.additional_metadata
                )
                return [cached_alignment]
        
        self.cache_stats['misses'] += 1
        self.logger.info(f"ContextualEntityAligner: Cache miss for '{entity_text}', processing...")
        
        self.logger.info(f"ContextualEntityAligner: Aligning entity '{entity_text}' (type: {entity_type}) in chunk {chunk_id}")
        
        # Fast country lookup for LOCATION entities
        if entity_type == 'LOCATION':
            country_uri = self._check_country_lookup(entity_text)
            if country_uri:
                self.logger.info(f"ContextualEntityAligner: Found direct country match for '{entity_text}': {country_uri}")
                # Create high-confidence alignment
                alignment = EntityAlignment(
                    entity_text=entity_text,
                    entity_type=entity_type,
                    aligned_uri=str(country_uri),
                    ontology='geonames',
                    confidence_score=0.95,  # High confidence for direct country match
                    context_signals=['direct_country_lookup'],
                    chunk_id=chunk_id,
                    document_id=document_metadata.get('document_id', ''),
                    additional_metadata={'lookup_type': 'country_direct'}
                )
                # Cache the successful alignment
                self._cache_alignment(entity_text, alignment)
                return [alignment]
        
        # Determine relevant ontologies for this entity type
        relevant_ontologies = self._get_relevant_ontologies(entity_type)
        self.logger.info(f"ContextualEntityAligner: Relevant ontologies for '{entity_text}': {relevant_ontologies}")
        
        if not relevant_ontologies:
            self.logger.info(f"ContextualEntityAligner: No relevant ontologies for entity type: {entity_type}")
            # Cache rejection
            self._cache_alignment(entity_text, None)
            return []
        
        all_alignments = []
        
        # Query each relevant ontology
        for ontology_name in relevant_ontologies:
            self.logger.info(f"ContextualEntityAligner: Querying ontology '{ontology_name}' for entity '{entity_text}'")
            
            try:
                alignments = self._query_ontology_for_entity(
                    entity_text, entity_type, ontology_name, document_metadata, chunk_context
                )
                self.logger.info(f"ContextualEntityAligner: Ontology '{ontology_name}' returned {len(alignments)} alignments for '{entity_text}'")
                
                # Log sample alignments
                for i, alignment in enumerate(alignments[:2]):  # Log first 2 alignments
                    self.logger.info(f"ContextualEntityAligner: Alignment {i+1} for '{entity_text}': URI={alignment.aligned_uri}, score={alignment.confidence_score:.3f}")
                
                all_alignments.extend(alignments)
            except Exception as e:
                self.logger.error(f"ContextualEntityAligner: Error querying ontology '{ontology_name}' for '{entity_text}': {e}")
        
        if not all_alignments:
            self.logger.info(f"ContextualEntityAligner: No alignments found for entity '{entity_text}' across all ontologies")
            # Cache rejection
            self._cache_alignment(entity_text, None)
            return []
        
        self.logger.info(f"ContextualEntityAligner: Total {len(all_alignments)} alignments found for '{entity_text}', applying contextual scoring")
        
        # Apply contextual scoring
        try:
            scored_alignments = self.scoring_engine.score_alignments_with_context(
                all_alignments, entity_text, entity_type, document_metadata, chunk_context
            )
            self.logger.info(f"ContextualEntityAligner: Contextual scoring complete for '{entity_text}', {len(scored_alignments)} scored alignments")
        except Exception as e:
            self.logger.error(f"ContextualEntityAligner: Error in contextual scoring for '{entity_text}': {e}")
            self.logger.error(f"ContextualEntityAligner: Rejecting '{entity_text}' due to scoring failure")
            # Cache rejection and return empty list - no dangerous fallback
            self._cache_alignment(entity_text, None)
            return []
        
        # Filter by confidence threshold
        filtered_alignments = [alignment for alignment in scored_alignments 
                              if alignment.confidence_score >= self.confidence_threshold]
        
        self.logger.info(f"ContextualEntityAligner: After confidence filtering (threshold={self.confidence_threshold}): {len(filtered_alignments)} alignments remain for '{entity_text}'")
        
        # Cache results
        if filtered_alignments:
            # Cache the best alignment
            best_alignment = max(filtered_alignments, key=lambda a: a.confidence_score)
            self._cache_alignment(entity_text, best_alignment)
            return filtered_alignments
        else:
            # Cache rejection
            self._cache_alignment(entity_text, None)
            return []
    
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
            self.logger.info(f"ContextualEntityAligner: Building FTS query for '{entity_text}' in ontology '{ontology_name}'")
            
            query = self.fts_query_builder.build_location_query(
                entity_text, document_metadata, chunk_context
            )
            
            # Handle skipped entities
            if query is None:
                self.logger.info(f"ContextualEntityAligner: Entity '{entity_text}' skipped due to pre-filtering")
                return []
            
            self.logger.info(f"ContextualEntityAligner: Generated SPARQL query for '{entity_text}':\n{query}")
            
            # Execute query via Neptune
            self.logger.info(f"ContextualEntityAligner: Executing FTS query for '{entity_text}' in '{ontology_name}'")
            
            results = self.kg_manager.execute_sparql_query(query)
            
            self.logger.info(f"ContextualEntityAligner: SPARQL query returned {len(results) if results else 0} results for '{entity_text}'")
            
            # Log sample results
            if results:
                for i, result in enumerate(results[:3]):  # Log first 3 results
                    aligned_uri = result.get('entity') or result.get('concept')
                    label = result.get('label')
                    self.logger.info(f"ContextualEntityAligner: Result {i+1} for '{entity_text}': URI={aligned_uri}, label={label}")
            
            # Convert results to EntityAlignment objects
            alignments = []
            for result in results:
                alignment = self._create_alignment_from_sparql_result(
                    result, entity_text, entity_type, ontology_name, chunk_context['chunk_id']
                )
                if alignment:
                    alignments.append(alignment)
                else:
                    self.logger.warning(f"ContextualEntityAligner: Failed to create alignment from result: {result}")
            
            self.logger.info(f"ContextualEntityAligner: Created {len(alignments)} valid alignments in '{ontology_name}' for '{entity_text}'")
            return alignments
            
        except Exception as e:
            self.logger.error(f"ContextualEntityAligner: Error querying '{ontology_name}' for '{entity_text}': {e}")
            import traceback
            self.logger.error(f"ContextualEntityAligner: Full traceback: {traceback.format_exc()}")
            return []
    
    def _create_alignment_from_sparql_result(self, result: Dict, entity_text: str, 
                                           entity_type: str, ontology_name: str, 
                                           chunk_id: str) -> Optional[EntityAlignment]:
        """Create EntityAlignment from SPARQL query result"""
        
        # Extract URI and label from result
        aligned_uri = result.get('entity') or result.get('concept')
        label = result.get('label')
        
        if not aligned_uri or not label:
            self.logger.debug(f"Missing URI or label in SPARQL result: {result}")
            return None
        
        # Calculate base confidence from FTS score or string similarity
        base_confidence = self._calculate_base_confidence(entity_text, label, result)
        if base_confidence < self.BASE_CONFIDENCE_THRESHOLD:
            self.logger.info(f"ContextualEntityAligner: Base confidence for {entity_text} is too low: {base_confidence}")
            return None
        
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
    
    def _convert_unaligned_to_pipeline_format(self, original_entity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert unaligned entity to pipeline format"""
        
        return {
            'entity': original_entity['entity'],
            'type': original_entity.get('type', 'OTHER'),
            'chunk_id': original_entity.get('chunk_id', ''),
            'score': original_entity.get('score', 0.0)
            # No ontology_alignment field - indicates no alignment found
        }
    
    def _reset_document_cache(self, document_id: str):
        """Reset cache for new document processing"""
        if self.current_document_id != document_id:
            self.logger.info(f"ContextualEntityAligner: Resetting cache for new document: {document_id}")
            if self.alignment_cache:
                self.logger.info(f"ContextualEntityAligner: Cache stats for previous document - Hits: {self.cache_stats['hits']}, Misses: {self.cache_stats['misses']}, Rejections: {self.cache_stats['rejections']}")
            
            self.current_document_id = document_id
            self.alignment_cache.clear()
            self.cache_stats = {'hits': 0, 'misses': 0, 'rejections': 0}

    def _get_cached_alignment(self, entity_text: str) -> Optional[Union[EntityAlignment, str]]:
        """Get cached alignment or rejection status"""
        normalized_key = entity_text.lower().strip()
        return self.alignment_cache.get(normalized_key)

    def _cache_alignment(self, entity_text: str, alignment: Optional[EntityAlignment]):
        """Cache successful alignment or rejection"""
        normalized_key = entity_text.lower().strip()
        if alignment:
            self.alignment_cache[normalized_key] = alignment
            self.logger.debug(f"ContextualEntityAligner: Cached successful alignment for '{entity_text}'")
        else:
            self.alignment_cache[normalized_key] = 'REJECTED'
            self.logger.debug(f"ContextualEntityAligner: Cached rejection for '{entity_text}'")

    def _check_country_lookup(self, entity_text: str) -> Optional[URIRef]:
        """Fast country lookup using pre-built mappings"""
        try:
            from .country_mappings import COUNTRY_NAME_TO_GEONAMES_URI
            
            # Direct lookup (case-insensitive)
            normalized_text = entity_text.strip()
            
            # Try exact match first
            if normalized_text in COUNTRY_NAME_TO_GEONAMES_URI:
                return COUNTRY_NAME_TO_GEONAMES_URI[normalized_text]
            
            # Try case-insensitive match
            for country_name, uri in COUNTRY_NAME_TO_GEONAMES_URI.items():
                if country_name.lower() == normalized_text.lower():
                    return uri
            
            return None
        except ImportError:
            self.logger.warning("ContextualEntityAligner: Country mappings not available, skipping country lookup")
            return None
    
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
            'max_results_per_ontology': self.max_results_per_ontology,
            'cache_stats': self.cache_stats.copy(),
            'cache_size': len(self.alignment_cache),
            'current_document_id': self.current_document_id
        }
