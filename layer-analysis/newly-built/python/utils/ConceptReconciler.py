#!/usr/bin/env python3
"""
Concept Reconciler - Merges results from bidirectional entity-ontology matching
Resolves conflicts between EntityAligner and OntologyTermMatcher results
"""
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from collections import defaultdict
import json

# Import existing KG layer utilities (UNCHANGED)
from .KnowledgeGraphManager import KnowledgeGraphManager
from .ConfidenceScorer import ConfidenceScorer
from .kg_exceptions import KGQueryError, KGValidationError

class ConceptReconciler:
    """
    Reconciles and merges results from bidirectional entity-ontology matching
    Handles conflicts, duplicates, and creates unified concept-chunk mappings
    """
    
    def __init__(self, 
                 kg_manager: KnowledgeGraphManager,
                 reconciliation_strategy: str = 'confidence_weighted',
                 conflict_resolution: str = 'highest_confidence',
                 min_confidence_threshold: float = 0.6):
        """
        Initialize concept reconciler with existing KG infrastructure
        
        Args:
            kg_manager: Existing KnowledgeGraphManager instance (UNCHANGED interface)
            reconciliation_strategy: Strategy for merging results
                Options: 'confidence_weighted', 'union', 'intersection', 'entity_priority', 'ontology_priority'
            conflict_resolution: How to resolve conflicts
                Options: 'highest_confidence', 'average_confidence', 'entity_priority', 'ontology_priority'
            min_confidence_threshold: Minimum confidence for final mappings
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use existing KG manager (NO CHANGES to existing methods)
        self.kg_manager = kg_manager
        self.uri_manager = kg_manager.uri_manager  # Existing interface
        
        # Configuration
        self.reconciliation_strategy = reconciliation_strategy
        self.conflict_resolution = conflict_resolution
        self.min_confidence_threshold = min_confidence_threshold
        
        # Initialize confidence scorer for reconciliation
        self.confidence_scorer = ConfidenceScorer(min_confidence=min_confidence_threshold)
        
        # Statistics tracking
        self.stats = {
            'entity_mappings_processed': 0,
            'ontology_mentions_processed': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'final_mappings_created': 0,
            'duplicates_removed': 0
        }
        
        self.logger.debug(f"ConceptReconciler initialized with strategy={reconciliation_strategy}")
    
    def reconcile_bidirectional_mappings(self, 
                                       entity_mappings: Dict[str, Any], 
                                       ontology_mentions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method: Reconcile results from EntityAligner and OntologyTermMatcher
        
        Args:
            entity_mappings: Results from EntityAligner.align_entities_to_concepts()
            ontology_mentions: Results from OntologyTermMatcher.find_concept_mentions()
        
        Returns:
            Unified concept-chunk mappings with reconciliation metadata
        """
        start_time = datetime.now()
        
        try:
            self.logger.info("Starting bidirectional mapping reconciliation")
            
            # Validate input structures
            if not self._validate_input_structures(entity_mappings, ontology_mentions):
                raise KGValidationError("Invalid input structure for reconciliation")
            
            # Extract mappings from both directions
            entity_concept_mappings = self._extract_entity_mappings(entity_mappings)
            mention_concept_mappings = self._extract_mention_mappings(ontology_mentions)
            
            self.stats['entity_mappings_processed'] = len(entity_concept_mappings)
            self.stats['ontology_mentions_processed'] = len(mention_concept_mappings)
            
            # Detect conflicts and overlaps
            conflicts, overlaps = self._detect_conflicts_and_overlaps(
                entity_concept_mappings, 
                mention_concept_mappings
            )
            
            self.stats['conflicts_detected'] = len(conflicts)
            
            # Resolve conflicts based on strategy
            resolved_mappings = self._resolve_conflicts(
                entity_concept_mappings,
                mention_concept_mappings,
                conflicts,
                overlaps
            )
            
            self.stats['conflicts_resolved'] = len(conflicts)
            
            # Create final unified mappings
            final_mappings = self._create_final_mappings(resolved_mappings)
            
            # Remove duplicates and apply confidence filtering
            final_mappings = self._deduplicate_and_filter(final_mappings)
            
            self.stats['final_mappings_created'] = len(final_mappings)
            
            # Generate reconciliation metadata
            reconciliation_metadata = self._generate_reconciliation_metadata(
                entity_mappings,
                ontology_mentions,
                conflicts,
                overlaps
            )
            
            # Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'reconciled_mappings': final_mappings,
                'reconciliation_metadata': reconciliation_metadata,
                'processing_stats': {
                    'entity_mappings_input': len(entity_concept_mappings),
                    'ontology_mentions_input': len(mention_concept_mappings),
                    'conflicts_detected': self.stats['conflicts_detected'],
                    'conflicts_resolved': self.stats['conflicts_resolved'],
                    'final_mappings_output': len(final_mappings),
                    'duplicates_removed': self.stats['duplicates_removed'],
                    'processing_time_seconds': processing_time,
                    'reconciliation_success_rate': self.stats['conflicts_resolved'] / max(self.stats['conflicts_detected'], 1)
                },
                'reconciliation_strategy': self.reconciliation_strategy,
                'conflict_resolution': self.conflict_resolution,
                'min_confidence_threshold': self.min_confidence_threshold
            }
            
            self.logger.info(f"Reconciliation completed: {len(final_mappings)} final mappings, "
                           f"{self.stats['conflicts_resolved']} conflicts resolved")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Bidirectional mapping reconciliation failed: {e}")
            raise KGQueryError(f"Reconciliation error: {e}")
    
    def _validate_input_structures(self, entity_mappings: Dict[str, Any], ontology_mentions: Dict[str, Any]) -> bool:
        """Validate input structure from EntityAligner and OntologyTermMatcher"""
        
        # Validate entity mappings structure
        if 'aligned_entities' not in entity_mappings:
            self.logger.error("Missing 'aligned_entities' in entity_mappings")
            return False
        
        # Validate ontology mentions structure
        if 'concept_mentions' not in ontology_mentions:
            self.logger.error("Missing 'concept_mentions' in ontology_mentions")
            return False
        
        return True
    
    def _extract_entity_mappings(self, entity_mappings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and normalize entity-concept mappings"""
        mappings = []
        
        for entity in entity_mappings.get('aligned_entities', []):
            mapping = {
                'source': 'entity_aligner',
                'chunk_id': entity.get('chunk_id', ''),
                'text': entity.get('entity_text', ''),
                'concept_uri': entity.get('concept_uri', ''),
                'concept_label': entity.get('concept_label', ''),
                'confidence': entity.get('confidence', 0.0),
                'confidence_factors': entity.get('confidence_factors', {}),
                'entity_type': entity.get('entity_type', 'UNKNOWN'),
                'entity_uri': entity.get('entity_uri', ''),
                'alignment_method': entity.get('alignment_method', 'fuzzy_semantic'),
                'original_data': entity
            }
            mappings.append(mapping)
        
        return mappings
    
    def _extract_mention_mappings(self, ontology_mentions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract and normalize ontology mention mappings"""
        mappings = []
        
        for mention in ontology_mentions.get('concept_mentions', []):
            mapping = {
                'source': 'ontology_term_matcher',
                'chunk_id': mention.get('chunk_id', ''),
                'text': mention.get('mention_text', ''),
                'concept_uri': mention.get('concept_uri', ''),
                'concept_label': mention.get('concept_label', ''),
                'confidence': mention.get('confidence', 0.0),
                'confidence_factors': mention.get('confidence_factors', {}),
                'start_offset': mention.get('start_offset', 0),
                'end_offset': mention.get('end_offset', 0),
                'mention_uri': mention.get('mention_uri', ''),
                'detection_method': mention.get('detection_method', 'aho_corasick_pattern'),
                'original_data': mention
            }
            mappings.append(mapping)
        
        return mappings
    
    def _detect_conflicts_and_overlaps(self, 
                                     entity_mappings: List[Dict[str, Any]], 
                                     mention_mappings: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Detect conflicts and overlaps between the two mapping sets"""
        
        conflicts = []
        overlaps = []
        
        # Group mappings by chunk for efficient comparison
        entity_by_chunk = defaultdict(list)
        mention_by_chunk = defaultdict(list)
        
        for mapping in entity_mappings:
            entity_by_chunk[mapping['chunk_id']].append(mapping)
        
        for mapping in mention_mappings:
            mention_by_chunk[mapping['chunk_id']].append(mapping)
        
        # Check each chunk for conflicts and overlaps
        all_chunks = set(entity_by_chunk.keys()) | set(mention_by_chunk.keys())
        
        for chunk_id in all_chunks:
            chunk_entities = entity_by_chunk.get(chunk_id, [])
            chunk_mentions = mention_by_chunk.get(chunk_id, [])
            
            # Compare all pairs within the chunk
            for entity_mapping in chunk_entities:
                for mention_mapping in chunk_mentions:
                    
                    # Check for text overlap
                    text_similarity = self._calculate_text_overlap(
                        entity_mapping['text'],
                        mention_mapping['text']
                    )
                    
                    # Check for concept agreement
                    concept_agreement = entity_mapping['concept_uri'] == mention_mapping['concept_uri']
                    
                    if text_similarity > 0.5:  # Significant text overlap
                        if concept_agreement:
                            # Overlap - same concept, overlapping text
                            overlaps.append({
                                'chunk_id': chunk_id,
                                'entity_mapping': entity_mapping,
                                'mention_mapping': mention_mapping,
                                'text_similarity': text_similarity,
                                'concept_agreement': True,
                                'conflict_type': 'overlap'
                            })
                        else:
                            # Conflict - different concepts, overlapping text
                            conflicts.append({
                                'chunk_id': chunk_id,
                                'entity_mapping': entity_mapping,
                                'mention_mapping': mention_mapping,
                                'text_similarity': text_similarity,
                                'concept_agreement': False,
                                'conflict_type': 'concept_disagreement'
                            })
        
        return conflicts, overlaps
    
    def _calculate_text_overlap(self, text1: str, text2: str) -> float:
        """Calculate text overlap between two strings"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based overlap calculation
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _resolve_conflicts(self, 
                         entity_mappings: List[Dict[str, Any]],
                         mention_mappings: List[Dict[str, Any]],
                         conflicts: List[Dict[str, Any]],
                         overlaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve conflicts based on configured strategy"""
        
        resolved_mappings = []
        
        # Start with all non-conflicting mappings
        conflicted_mappings = set()
        
        # Mark conflicted mappings
        for conflict in conflicts:
            conflicted_mappings.add(id(conflict['entity_mapping']))
            conflicted_mappings.add(id(conflict['mention_mapping']))
        
        for overlap in overlaps:
            conflicted_mappings.add(id(overlap['entity_mapping']))
            conflicted_mappings.add(id(overlap['mention_mapping']))
        
        # Add non-conflicting entity mappings
        for mapping in entity_mappings:
            if id(mapping) not in conflicted_mappings:
                resolved_mappings.append(mapping)
        
        # Add non-conflicting mention mappings
        for mapping in mention_mappings:
            if id(mapping) not in conflicted_mappings:
                resolved_mappings.append(mapping)
        
        # Resolve overlaps (same concept, overlapping text)
        for overlap in overlaps:
            resolved_mapping = self._resolve_overlap(overlap)
            if resolved_mapping:
                resolved_mappings.append(resolved_mapping)
        
        # Resolve conflicts (different concepts, overlapping text)
        for conflict in conflicts:
            resolved_mapping = self._resolve_conflict(conflict)
            if resolved_mapping:
                resolved_mappings.append(resolved_mapping)
        
        return resolved_mappings
    
    def _resolve_overlap(self, overlap: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve overlap between mappings with same concept"""
        entity_mapping = overlap['entity_mapping']
        mention_mapping = overlap['mention_mapping']
        
        # Since they agree on concept, merge them with highest confidence
        if entity_mapping['confidence'] >= mention_mapping['confidence']:
            base_mapping = entity_mapping.copy()
            base_mapping['reconciliation_info'] = {
                'type': 'overlap_resolved',
                'primary_source': 'entity_aligner',
                'secondary_source': 'ontology_term_matcher',
                'confidence_boost': mention_mapping['confidence'] * 0.1,  # Small boost for agreement
                'text_similarity': overlap['text_similarity']
            }
            base_mapping['confidence'] = min(1.0, base_mapping['confidence'] + base_mapping['reconciliation_info']['confidence_boost'])
        else:
            base_mapping = mention_mapping.copy()
            base_mapping['reconciliation_info'] = {
                'type': 'overlap_resolved',
                'primary_source': 'ontology_term_matcher',
                'secondary_source': 'entity_aligner',
                'confidence_boost': entity_mapping['confidence'] * 0.1,
                'text_similarity': overlap['text_similarity']
            }
            base_mapping['confidence'] = min(1.0, base_mapping['confidence'] + base_mapping['reconciliation_info']['confidence_boost'])
        
        return base_mapping
    
    def _resolve_conflict(self, conflict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve conflict between mappings with different concepts"""
        entity_mapping = conflict['entity_mapping']
        mention_mapping = conflict['mention_mapping']
        
        if self.conflict_resolution == 'highest_confidence':
            # Choose mapping with highest confidence
            if entity_mapping['confidence'] > mention_mapping['confidence']:
                winner = entity_mapping.copy()
                loser = mention_mapping
            else:
                winner = mention_mapping.copy()
                loser = entity_mapping
            
            winner['reconciliation_info'] = {
                'type': 'conflict_resolved',
                'resolution_method': 'highest_confidence',
                'winner_confidence': winner['confidence'],
                'loser_confidence': loser['confidence'],
                'confidence_difference': abs(winner['confidence'] - loser['confidence']),
                'text_similarity': conflict['text_similarity']
            }
            
            return winner
            
        elif self.conflict_resolution == 'entity_priority':
            # Always prefer entity aligner results
            winner = entity_mapping.copy()
            winner['reconciliation_info'] = {
                'type': 'conflict_resolved',
                'resolution_method': 'entity_priority',
                'preferred_source': 'entity_aligner',
                'text_similarity': conflict['text_similarity']
            }
            return winner
            
        elif self.conflict_resolution == 'ontology_priority':
            # Always prefer ontology term matcher results
            winner = mention_mapping.copy()
            winner['reconciliation_info'] = {
                'type': 'conflict_resolved',
                'resolution_method': 'ontology_priority',
                'preferred_source': 'ontology_term_matcher',
                'text_similarity': conflict['text_similarity']
            }
            return winner
            
        else:
            # Default to highest confidence
            return self._resolve_conflict({
                **conflict,
                'resolution_method': 'highest_confidence'
            })
    
    def _create_final_mappings(self, resolved_mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create final unified mapping structure"""
        final_mappings = []
        
        for mapping in resolved_mappings:
            # Generate unified URI using EXISTING uri_manager
            unified_uri = self._mint_unified_concept_mapping_uri(
                mapping['chunk_id'],
                mapping['concept_uri'],
                mapping['text']
            )
            
            final_mapping = {
                'chunk_id': mapping['chunk_id'],
                'concept_uri': mapping['concept_uri'],
                'concept_label': mapping['concept_label'],
                'text': mapping['text'],
                'unified_mapping_uri': str(unified_uri),
                'confidence': mapping['confidence'],
                'confidence_factors': mapping['confidence_factors'],
                'source_method': mapping['source'],
                'reconciliation_info': mapping.get('reconciliation_info', {'type': 'no_conflict'}),
                'original_entity_type': mapping.get('entity_type'),
                'original_detection_method': mapping.get('detection_method', mapping.get('alignment_method')),
                'position_info': {
                    'start_offset': mapping.get('start_offset'),
                    'end_offset': mapping.get('end_offset')
                }
            }
            
            final_mappings.append(final_mapping)
        
        return final_mappings
    
    def _deduplicate_and_filter(self, mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and apply confidence filtering"""
        
        # Filter by confidence threshold
        filtered_mappings = [
            mapping for mapping in mappings 
            if mapping['confidence'] >= self.min_confidence_threshold
        ]
        
        # Remove exact duplicates
        seen_keys = set()
        deduplicated = []
        
        for mapping in filtered_mappings:
            # Create key for deduplication
            key = (
                mapping['chunk_id'],
                mapping['concept_uri'],
                mapping['text'].lower()
            )
            
            if key not in seen_keys:
                seen_keys.add(key)
                deduplicated.append(mapping)
            else:
                self.stats['duplicates_removed'] += 1
        
        return deduplicated
    
    def _mint_unified_concept_mapping_uri(self, chunk_id: str, concept_uri: str, text: str) -> str:
        """Generate URI for unified concept mapping using EXISTING uri_manager"""
        
        # Create unique identifier
        unique_id = f"{chunk_id}_{hash(concept_uri)}_{hash(text.lower())}"
        
        # Use EXISTING mint_uri method
        unified_uri = self.kg_manager.mint_uri(
            unique_id=unique_id,
            namespace=self.kg_manager.kr_ns,
            ontology_concept="UnifiedConceptMapping",
            ontology_uri=self.kg_manager.kr_ns
        )
        
        return unified_uri
    
    def _generate_reconciliation_metadata(self, 
                                        entity_mappings: Dict[str, Any],
                                        ontology_mentions: Dict[str, Any],
                                        conflicts: List[Dict[str, Any]],
                                        overlaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive reconciliation metadata"""
        
        return {
            'input_summary': {
                'entity_aligner_results': {
                    'total_aligned': len(entity_mappings.get('aligned_entities', [])),
                    'total_unaligned': len(entity_mappings.get('unaligned_entities', [])),
                    'success_rate': entity_mappings.get('processing_stats', {}).get('success_rate', 0.0)
                },
                'ontology_term_matcher_results': {
                    'total_mentions': len(ontology_mentions.get('concept_mentions', [])),
                    'high_confidence_mentions': ontology_mentions.get('processing_stats', {}).get('high_confidence_mentions', 0),
                    'co_occurrences': len(ontology_mentions.get('co_occurrences', []))
                }
            },
            'conflict_analysis': {
                'total_conflicts': len(conflicts),
                'total_overlaps': len(overlaps),
                'conflict_types': self._analyze_conflict_types(conflicts),
                'overlap_types': self._analyze_overlap_types(overlaps)
            },
            'reconciliation_decisions': {
                'strategy_used': self.reconciliation_strategy,
                'conflict_resolution_method': self.conflict_resolution,
                'confidence_threshold': self.min_confidence_threshold
            },
            'quality_metrics': {
                'reconciliation_success_rate': self.stats['conflicts_resolved'] / max(self.stats['conflicts_detected'], 1),
                'duplicate_removal_count': self.stats['duplicates_removed'],
                'final_mapping_quality': self._calculate_quality_metrics()
            }
        }
    
    def _analyze_conflict_types(self, conflicts: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze types of conflicts detected"""
        conflict_types = defaultdict(int)
        
        for conflict in conflicts:
            conflict_types[conflict.get('conflict_type', 'unknown')] += 1
        
        return dict(conflict_types)
    
    def _analyze_overlap_types(self, overlaps: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze types of overlaps detected"""
        overlap_types = defaultdict(int)
        
        for overlap in overlaps:
            overlap_types[overlap.get('conflict_type', 'unknown')] += 1
        
        return dict(overlap_types)
    
    def _calculate_quality_metrics(self) -> Dict[str, float]:
        """Calculate quality metrics for reconciliation"""
        return {
            'conflict_resolution_rate': self.stats['conflicts_resolved'] / max(self.stats['conflicts_detected'], 1),
            'mapping_retention_rate': self.stats['final_mappings_created'] / max(self.stats['entity_mappings_processed'] + self.stats['ontology_mentions_processed'], 1),
            'duplicate_rate': self.stats['duplicates_removed'] / max(self.stats['final_mappings_created'] + self.stats['duplicates_removed'], 1)
        }
    
    def get_reconciler_statistics(self) -> Dict[str, Any]:
        """Get comprehensive reconciler statistics"""
        return {
            'processing_stats': dict(self.stats),
            'configuration': {
                'reconciliation_strategy': self.reconciliation_strategy,
                'conflict_resolution': self.conflict_resolution,
                'min_confidence_threshold': self.min_confidence_threshold
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # This would be used in Lambda functions
    kg_manager = KnowledgeGraphManager()
    reconciler = ConceptReconciler(
        kg_manager, 
        reconciliation_strategy='confidence_weighted',
        conflict_resolution='highest_confidence'
    )
    
    # Mock input data (would come from EntityAligner and OntologyTermMatcher)
    entity_mappings = {
        'aligned_entities': [
            {
                'chunk_id': 'doc123_chunk_0001',
                'entity_text': 'climate change',
                'concept_uri': 'ontology:ClimateChange',
                'concept_label': 'Climate Change',
                'confidence': 0.85
            }
        ]
    }
    
    ontology_mentions = {
        'concept_mentions': [
            {
                'chunk_id': 'doc123_chunk_0001',
                'mention_text': 'climate change',
                'concept_uri': 'ontology:ClimateChange',
                'concept_label': 'Climate Change',
                'confidence': 0.92,
                'start_offset': 10,
                'end_offset': 24
            }
        ]
    }
    
    # Reconcile results
    result = reconciler.reconcile_bidirectional_mappings(entity_mappings, ontology_mentions)
    
    print(f"Reconciliation result: {json.dumps(result, indent=2)}")
