#!/usr/bin/env python3
"""
Entity Aligner - Maps Comprehend entities to ontology concepts
Implements bidirectional fuzzy matching with confidence scoring and URI minting
"""
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from collections import defaultdict
import json

# Import existing KG layer utilities (UNCHANGED)
from .KnowledgeGraphManager import KnowledgeGraphManager
from .TextNormalizer import TextNormalizer
from .ConfidenceScorer import ConfidenceScorer, ConfidenceFactors
from .kg_exceptions import KGQueryError, KGValidationError

class EntityAligner:
    """
    Maps Comprehend entities to ontology concepts using fuzzy matching and confidence scoring
    Integrates with existing KnowledgeGraphManager for consistent URI patterns and ontology access
    """
    
    def __init__(self, 
                 kg_manager: KnowledgeGraphManager,
                 min_confidence: float = 0.6,
                 max_candidates: int = 5,
                 enable_caching: bool = True):
        """
        Initialize entity aligner with existing KG infrastructure
        
        Args:
            kg_manager: Existing KnowledgeGraphManager instance (UNCHANGED interface)
            min_confidence: Minimum confidence threshold for alignments
            max_candidates: Maximum candidate concepts to consider per entity
            enable_caching: Whether to cache alignment results
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use existing KG manager (NO CHANGES to existing methods)
        self.kg_manager = kg_manager
        self.ontology_manager = kg_manager.ontology_manager  # Existing interface
        self.uri_manager = kg_manager.uri_manager            # Existing interface
        
        # Initialize new utilities
        self.text_normalizer = TextNormalizer()
        self.confidence_scorer = ConfidenceScorer(min_confidence=min_confidence)
        
        # Configuration
        self.min_confidence = min_confidence
        self.max_candidates = max_candidates
        self.enable_caching = enable_caching
        
        # Caching for performance
        self.alignment_cache = {} if enable_caching else None
        self.concept_cache = {}
        
        # Statistics tracking
        self.stats = {
            'entities_processed': 0,
            'successful_alignments': 0,
            'failed_alignments': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        self.logger.debug(f"EntityAligner initialized with min_confidence={min_confidence}")
    
    def align_entities_to_concepts(self, 
                                 entities_by_chunk: List[Dict[str, Any]], 
                                 ontology_domains: List[str] = None) -> Dict[str, Any]:
        """
        Main method: Align Comprehend entities to ontology concepts
        
        Args:
            entities_by_chunk: List of entity mappings from corrected nlp-worker
                Format: [{'chunk_id': str, 'entity': str, 'type': str, 'score': float, ...}, ...]
            ontology_domains: Optional list of domains to focus on ['climate', 'financial', 'regulatory']
        
        Returns:
            Dictionary with aligned entities and metadata
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting entity alignment for {len(entities_by_chunk)} entities")
            
            # Load ontology concepts (using EXISTING ontology_manager methods)
            available_concepts = self._load_ontology_concepts(ontology_domains)
            
            if not available_concepts:
                self.logger.warning("No ontology concepts available for alignment")
                return self._create_empty_result()
            
            # Process entities in batches for efficiency
            aligned_entities = []
            unaligned_entities = []
            alignment_metadata = []
            
            for entity_data in entities_by_chunk:
                self.stats['entities_processed'] += 1
                
                # Extract entity information
                entity_text = entity_data.get('entity', '').strip()
                entity_type = entity_data.get('type', 'UNKNOWN')
                chunk_id = entity_data.get('chunk_id', '')
                
                if not entity_text:
                    continue
                
                # Check cache first
                cache_key = self._create_cache_key(entity_text, entity_type, ontology_domains)
                if self.enable_caching and cache_key in self.alignment_cache:
                    cached_result = self.alignment_cache[cache_key]
                    self.stats['cache_hits'] += 1
                    
                    # Add chunk-specific information to cached result
                    aligned_result = dict(cached_result)
                    aligned_result.update({
                        'chunk_id': chunk_id,
                        'original_entity_data': entity_data
                    })
                    aligned_entities.append(aligned_result)
                    continue
                
                self.stats['cache_misses'] += 1
                
                # Find candidate concepts
                candidates = self._find_candidate_concepts(
                    entity_text, 
                    entity_type, 
                    available_concepts
                )
                
                if not candidates:
                    unaligned_entities.append({
                        'entity_text': entity_text,
                        'entity_type': entity_type,
                        'chunk_id': chunk_id,
                        'reason': 'no_candidates_found',
                        'original_entity_data': entity_data
                    })
                    self.stats['failed_alignments'] += 1
                    continue
                
                # Score candidates and select best alignment
                best_alignment = self._select_best_alignment(
                    entity_text,
                    entity_type, 
                    candidates,
                    entity_data
                )
                
                if best_alignment and best_alignment['confidence'] >= self.min_confidence:
                    # Generate URI using EXISTING uri_manager methods
                    entity_uri = self._mint_entity_concept_uri(
                        entity_text,
                        best_alignment['concept_uri'],
                        chunk_id
                    )
                    
                    aligned_result = {
                        'entity_text': entity_text,
                        'entity_type': entity_type,
                        'chunk_id': chunk_id,
                        'concept_uri': best_alignment['concept_uri'],
                        'concept_label': best_alignment['concept_label'],
                        'entity_uri': str(entity_uri),
                        'confidence': best_alignment['confidence'],
                        'confidence_factors': best_alignment['confidence_factors'].to_dict(),
                        'alignment_method': 'fuzzy_semantic',
                        'original_entity_data': entity_data
                    }
                    
                    aligned_entities.append(aligned_result)
                    alignment_metadata.append(best_alignment['metadata'])
                    
                    # Cache successful alignment
                    if self.enable_caching:
                        cache_result = {k: v for k, v in aligned_result.items() 
                                      if k not in ['chunk_id', 'original_entity_data']}
                        self.alignment_cache[cache_key] = cache_result
                    
                    self.stats['successful_alignments'] += 1
                    
                else:
                    unaligned_entities.append({
                        'entity_text': entity_text,
                        'entity_type': entity_type,
                        'chunk_id': chunk_id,
                        'reason': 'low_confidence',
                        'best_confidence': best_alignment['confidence'] if best_alignment else 0.0,
                        'original_entity_data': entity_data
                    })
                    self.stats['failed_alignments'] += 1
            
            # Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'aligned_entities': aligned_entities,
                'unaligned_entities': unaligned_entities,
                'alignment_metadata': alignment_metadata,
                'processing_stats': {
                    'total_entities': len(entities_by_chunk),
                    'successful_alignments': len(aligned_entities),
                    'failed_alignments': len(unaligned_entities),
                    'success_rate': len(aligned_entities) / len(entities_by_chunk) if entities_by_chunk else 0.0,
                    'processing_time_seconds': processing_time,
                    'cache_hit_rate': self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0.0
                },
                'ontology_domains': ontology_domains or ['all'],
                'min_confidence_threshold': self.min_confidence
            }
            
            self.logger.info(f"Entity alignment completed: {len(aligned_entities)} aligned, {len(unaligned_entities)} unaligned")
            return result
            
        except Exception as e:
            self.logger.error(f"Entity alignment failed: {e}")
            raise KGQueryError(f"Entity alignment error: {e}")
    
    def _load_ontology_concepts(self, domains: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Load ontology concepts using EXISTING ontology manager methods"""
        try:
            # Use EXISTING method - no changes to interface
            all_concepts = self.ontology_manager.get_concepts()
            
            if not domains:
                return all_concepts
            
            # Filter by domains if specified
            filtered_concepts = []
            for concept in all_concepts:
                concept_domain = concept.get('domain', '').lower()
                concept_type = concept.get('type', '').lower()
                concept_label = concept.get('label', '').lower()
                
                # Check if concept matches any specified domain
                for domain in domains:
                    domain_lower = domain.lower()
                    if (domain_lower in concept_domain or 
                        domain_lower in concept_type or
                        domain_lower in concept_label):
                        filtered_concepts.append(concept)
                        break
            
            self.logger.debug(f"Loaded {len(filtered_concepts)} concepts from {len(all_concepts)} total")
            return filtered_concepts
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology concepts: {e}")
            return []
    
    def _find_candidate_concepts(self, 
                               entity_text: str, 
                               entity_type: str, 
                               available_concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find candidate concepts for entity using multiple matching strategies"""
        
        # Normalize entity text for matching
        normalized_variants = self.text_normalizer.normalize_entity_text(entity_text)
        
        candidates = []
        seen_uris = set()
        
        # Strategy 1: Exact label matching
        for concept in available_concepts:
            concept_label = concept.get('label', '')
            concept_uri = concept.get('uri', '')
            
            if concept_uri in seen_uris:
                continue
            
            # Check exact matches with normalized variants
            for variant_name, variant_text in normalized_variants.items():
                if variant_text and variant_text.lower() == concept_label.lower():
                    candidates.append({
                        'concept': concept,
                        'match_type': f'exact_{variant_name}',
                        'match_score': 1.0
                    })
                    seen_uris.add(concept_uri)
                    break
        
        # Strategy 2: Fuzzy label matching using EXISTING search method
        if len(candidates) < self.max_candidates:
            try:
                # Use EXISTING method - no changes to interface
                fuzzy_matches = self.ontology_manager.search_by_label(entity_text, fuzzy=True, limit=self.max_candidates * 2)
                
                for match in fuzzy_matches:
                    concept_uri = match.get('uri', '')
                    if concept_uri not in seen_uris and len(candidates) < self.max_candidates:
                        candidates.append({
                            'concept': match,
                            'match_type': 'fuzzy_label',
                            'match_score': match.get('similarity_score', 0.8)
                        })
                        seen_uris.add(concept_uri)
                        
            except Exception as e:
                self.logger.warning(f"Fuzzy search failed for '{entity_text}': {e}")
        
        # Strategy 3: Partial word matching
        if len(candidates) < self.max_candidates:
            entity_words = set(entity_text.lower().split())
            
            for concept in available_concepts:
                concept_uri = concept.get('uri', '')
                if concept_uri in seen_uris or len(candidates) >= self.max_candidates:
                    continue
                
                concept_label = concept.get('label', '')
                concept_words = set(concept_label.lower().split())
                
                # Calculate word overlap
                overlap = len(entity_words.intersection(concept_words))
                total_words = len(entity_words.union(concept_words))
                
                if total_words > 0:
                    overlap_score = overlap / total_words
                    if overlap_score > 0.3:  # At least 30% word overlap
                        candidates.append({
                            'concept': concept,
                            'match_type': 'word_overlap',
                            'match_score': overlap_score
                        })
                        seen_uris.add(concept_uri)
        
        # Sort candidates by match score
        candidates.sort(key=lambda x: x['match_score'], reverse=True)
        
        return candidates[:self.max_candidates]
    
    def _select_best_alignment(self, 
                             entity_text: str,
                             entity_type: str,
                             candidates: List[Dict[str, Any]],
                             entity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select best alignment using confidence scoring"""
        
        best_alignment = None
        best_confidence = 0.0
        
        # Get context from entity data
        context_text = entity_data.get('context', '')
        
        for candidate in candidates:
            concept = candidate['concept']
            concept_label = concept.get('label', '')
            concept_uri = concept.get('uri', '')
            
            # Calculate confidence using confidence scorer
            confidence, factors = self.confidence_scorer.calculate_alignment_confidence(
                entity_text=entity_text,
                concept_label=concept_label,
                concept_metadata=concept,
                context_text=context_text,
                entity_metadata=entity_data
            )
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_alignment = {
                    'concept_uri': concept_uri,
                    'concept_label': concept_label,
                    'confidence': confidence,
                    'confidence_factors': factors,
                    'match_type': candidate['match_type'],
                    'match_score': candidate['match_score'],
                    'metadata': {
                        'concept_metadata': concept,
                        'entity_metadata': entity_data,
                        'alignment_timestamp': datetime.now().isoformat()
                    }
                }
        
        return best_alignment
    
    def _mint_entity_concept_uri(self, entity_text: str, concept_uri: str, chunk_id: str) -> str:
        """Generate URI for entity-concept alignment using EXISTING uri_manager"""
        
        # Create unique identifier for this entity-concept pair
        unique_id = f"{chunk_id}_{hash(entity_text)}_{hash(concept_uri)}"
        
        # Use EXISTING mint_uri method - no changes to interface
        entity_uri = self.kg_manager.mint_uri(
            unique_id=unique_id,
            namespace=self.kg_manager.kr_ns,
            ontology_concept="EntityConceptAlignment",
            ontology_uri=self.kg_manager.kr_ns
        )
        
        return entity_uri
    
    def _create_cache_key(self, entity_text: str, entity_type: str, domains: Optional[List[str]]) -> str:
        """Create cache key for alignment results"""
        domain_key = '_'.join(sorted(domains)) if domains else 'all'
        return f"{entity_text.lower()}_{entity_type}_{domain_key}"
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create empty result structure"""
        return {
            'aligned_entities': [],
            'unaligned_entities': [],
            'alignment_metadata': [],
            'processing_stats': {
                'total_entities': 0,
                'successful_alignments': 0,
                'failed_alignments': 0,
                'success_rate': 0.0,
                'processing_time_seconds': 0.0,
                'cache_hit_rate': 0.0
            },
            'ontology_domains': [],
            'min_confidence_threshold': self.min_confidence
        }
    
    def get_alignment_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alignment statistics"""
        return {
            'processing_stats': dict(self.stats),
            'cache_stats': {
                'cache_enabled': self.enable_caching,
                'cache_size': len(self.alignment_cache) if self.alignment_cache else 0,
                'concept_cache_size': len(self.concept_cache)
            },
            'configuration': {
                'min_confidence': self.min_confidence,
                'max_candidates': self.max_candidates,
                'enable_caching': self.enable_caching
            },
            'text_normalizer_stats': self.text_normalizer.get_normalization_stats(),
            'confidence_scorer_stats': self.confidence_scorer.get_scorer_stats()
        }
    
    def clear_caches(self):
        """Clear all caches"""
        if self.alignment_cache:
            self.alignment_cache.clear()
        self.concept_cache.clear()
        self.logger.info("EntityAligner caches cleared")
    
    def validate_alignment_result(self, result: Dict[str, Any]) -> bool:
        """Validate alignment result structure"""
        required_keys = ['aligned_entities', 'unaligned_entities', 'processing_stats']
        
        for key in required_keys:
            if key not in result:
                return False
        
        # Validate aligned entities structure
        for entity in result['aligned_entities']:
            required_entity_keys = ['entity_text', 'concept_uri', 'confidence', 'chunk_id']
            if not all(key in entity for key in required_entity_keys):
                return False
        
        return True

# Example usage and testing
if __name__ == "__main__":
    # This would be used in Lambda functions
    kg_manager = KnowledgeGraphManager()
    entity_aligner = EntityAligner(kg_manager, min_confidence=0.6)
    
    # Test entities from corrected nlp-worker
    test_entities = [
        {
            'chunk_id': 'doc123_chunk_0001',
            'entity': 'climate change',
            'type': 'OTHER',
            'score': 0.95,
            'context': 'The impact of climate change on financial institutions'
        },
        {
            'chunk_id': 'doc123_chunk_0002', 
            'entity': 'Federal Reserve',
            'type': 'ORG',
            'score': 0.88,
            'context': 'Federal Reserve guidance on climate risk management'
        }
    ]
    
    # Align entities to concepts
    result = entity_aligner.align_entities_to_concepts(
        entities_by_chunk=test_entities,
        ontology_domains=['climate', 'financial', 'regulatory']
    )
    
    print(f"Alignment result: {json.dumps(result, indent=2)}")
