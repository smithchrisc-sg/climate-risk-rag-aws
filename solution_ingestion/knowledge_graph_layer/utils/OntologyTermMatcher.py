#!/usr/bin/env python3
"""
Ontology Term Matcher - Finds ontology concept mentions in text using Aho-Corasick
Implements high-performance pattern matching for ontology-driven annotation
"""
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from collections import defaultdict
import re
import json

# Optional high-performance pattern matching
try:
    import ahocorasick_rs
    AHOCORASICK_AVAILABLE = True
except ImportError:
    AHOCORASICK_AVAILABLE = False

# Import existing KG layer utilities (UNCHANGED)
from .KnowledgeGraphManager import KnowledgeGraphManager
from .TextNormalizer import TextNormalizer
from .ConfidenceScorer import ConfidenceScorer
from .kg_exceptions import KGQueryError, KGValidationError

class OntologyTermMatcher:
    """
    Finds ontology concept mentions in text using efficient Aho-Corasick pattern matching
    Integrates with existing KnowledgeGraphManager for consistent ontology access and URI patterns
    """
    
    def __init__(self, 
                 kg_manager: KnowledgeGraphManager,
                 min_confidence: float = 0.7,
                 min_term_length: int = 3,
                 max_term_distance: int = 100,
                 enable_fuzzy_boundaries: bool = True):
        """
        Initialize ontology term matcher with existing KG infrastructure
        
        Args:
            kg_manager: Existing KnowledgeGraphManager instance (UNCHANGED interface)
            min_confidence: Minimum confidence threshold for matches
            min_term_length: Minimum length for terms to match
            max_term_distance: Maximum distance for co-occurrence detection
            enable_fuzzy_boundaries: Whether to allow fuzzy word boundaries
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use existing KG manager (NO CHANGES to existing methods)
        self.kg_manager = kg_manager
        self.ontology_manager = kg_manager.ontology_manager  # Existing interface
        self.uri_manager = kg_manager.uri_manager            # Existing interface
        
        # Initialize utilities
        self.text_normalizer = TextNormalizer()
        self.confidence_scorer = ConfidenceScorer(min_confidence=min_confidence)
        
        # Configuration
        self.min_confidence = min_confidence
        self.min_term_length = min_term_length
        self.max_term_distance = max_term_distance
        self.enable_fuzzy_boundaries = enable_fuzzy_boundaries
        
        # Pattern matching infrastructure
        self.automaton = None
        self.term_to_concepts = {}  # Maps normalized terms to concept metadata
        self.concept_metadata = {}  # Concept URI to full metadata
        
        # Statistics
        self.stats = {
            'terms_indexed': 0,
            'concepts_indexed': 0,
            'texts_processed': 0,
            'matches_found': 0,
            'high_confidence_matches': 0
        }
        
        self.logger.debug(f"OntologyTermMatcher initialized with min_confidence={min_confidence}")
    
    def build_pattern_automaton(self, ontology_domains: List[str] = None, force_rebuild: bool = False) -> bool:
        """
        Build Aho-Corasick automaton from ontology concepts
        
        Args:
            ontology_domains: Optional list of domains to focus on
            force_rebuild: Whether to force rebuilding even if automaton exists
        
        Returns:
            True if automaton was built successfully
        """
        if self.automaton is not None and not force_rebuild:
            self.logger.debug("Pattern automaton already exists, skipping build")
            return True
        
        try:
            start_time = datetime.now()
            self.logger.info("Building pattern matching automaton from ontology")
            
            # Load concepts using EXISTING ontology manager methods
            concepts = self._load_ontology_concepts(ontology_domains)
            
            if not concepts:
                self.logger.warning("No concepts available for pattern building")
                return False
            
            # Initialize automaton (with fallback)
            if AHOCORASICK_AVAILABLE:
                self.automaton = ahocorasick_rs.AhoCorasick([])
            else:
                self.automaton = None
                self.logger.info("Using fallback pattern matching (ahocorasick_rs not available)")
                
            self.term_to_concepts = {}
            self.concept_metadata = {}
            
            # Extract terms from concepts
            terms_to_add = []
            
            for concept in concepts:
                concept_uri = concept.get('uri', '')
                concept_label = concept.get('label', '')
                
                if not concept_uri or not concept_label:
                    continue
                
                # Store concept metadata
                self.concept_metadata[concept_uri] = concept
                
                # Generate term variants for matching
                term_variants = self._generate_term_variants(concept_label)
                
                for variant in term_variants:
                    if len(variant) >= self.min_term_length:
                        terms_to_add.append(variant)
                        
                        # Map term to concept(s)
                        if variant not in self.term_to_concepts:
                            self.term_to_concepts[variant] = []
                        self.term_to_concepts[variant].append({
                            'concept_uri': concept_uri,
                            'concept_label': concept_label,
                            'variant_type': 'primary' if variant == concept_label.lower() else 'normalized',
                            'concept_metadata': concept
                        })
            
            # Build automaton with all terms
            if terms_to_add:
                if AHOCORASICK_AVAILABLE:
                    self.automaton = ahocorasick_rs.AhoCorasick(terms_to_add)
                else:
                    # Store terms for fallback matching
                    self.fallback_terms = set(terms_to_add)
                
                self.stats['terms_indexed'] = len(set(terms_to_add))
                self.stats['concepts_indexed'] = len(concepts)
                
                build_time = (datetime.now() - start_time).total_seconds()
                matcher_type = "Aho-Corasick" if AHOCORASICK_AVAILABLE else "fallback"
                self.logger.info(f"Pattern automaton built ({matcher_type}): {self.stats['terms_indexed']} terms, "
                               f"{self.stats['concepts_indexed']} concepts in {build_time:.2f}s")
                return True
            else:
                self.logger.warning("No valid terms found for pattern matching")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to build pattern automaton: {e}")
            return False
    
    def find_concept_mentions(self, 
                            chunks: List[Dict[str, Any]], 
                            ontology_domains: List[str] = None,
                            include_co_occurrences: bool = True) -> Dict[str, Any]:
        """
        Find ontology concept mentions in text chunks
        
        Args:
            chunks: List of chunk data with text content
                Format: [{'chunk_id': str, 'text': str, 'section_type': str, ...}, ...]
            ontology_domains: Optional list of domains to focus on
            include_co_occurrences: Whether to detect concept co-occurrences
        
        Returns:
            Dictionary with concept mentions and metadata
        """
        start_time = datetime.now()
        
        try:
            # Ensure automaton is built
            if not self.automaton:
                if not self.build_pattern_automaton(ontology_domains):
                    return self._create_empty_mentions_result()
            
            self.logger.info(f"Finding concept mentions in {len(chunks)} chunks")
            
            all_mentions = []
            chunk_mentions = {}
            co_occurrences = []
            
            for chunk_data in chunks:
                chunk_id = chunk_data.get('chunk_id', '')
                chunk_text = chunk_data.get('text', '')
                
                if not chunk_text or not chunk_id:
                    continue
                
                self.stats['texts_processed'] += 1
                
                # Find mentions in this chunk
                chunk_mentions_list = self._find_mentions_in_text(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    chunk_metadata=chunk_data
                )
                
                all_mentions.extend(chunk_mentions_list)
                chunk_mentions[chunk_id] = chunk_mentions_list
                
                # Detect co-occurrences within chunk
                if include_co_occurrences and len(chunk_mentions_list) > 1:
                    chunk_co_occurrences = self._detect_co_occurrences(
                        chunk_mentions_list,
                        chunk_text,
                        chunk_id
                    )
                    co_occurrences.extend(chunk_co_occurrences)
            
            # Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            high_confidence_count = sum(1 for m in all_mentions if m['confidence'] >= self.min_confidence)
            
            result = {
                'concept_mentions': all_mentions,
                'mentions_by_chunk': chunk_mentions,
                'co_occurrences': co_occurrences,
                'processing_stats': {
                    'total_chunks': len(chunks),
                    'chunks_with_mentions': len([c for c in chunk_mentions.values() if c]),
                    'total_mentions': len(all_mentions),
                    'high_confidence_mentions': high_confidence_count,
                    'co_occurrences_found': len(co_occurrences),
                    'processing_time_seconds': processing_time,
                    'mentions_per_chunk': len(all_mentions) / len(chunks) if chunks else 0.0
                },
                'ontology_domains': ontology_domains or ['all'],
                'min_confidence_threshold': self.min_confidence
            }
            
            self.stats['matches_found'] += len(all_mentions)
            self.stats['high_confidence_matches'] += high_confidence_count
            
            self.logger.info(f"Found {len(all_mentions)} concept mentions "
                           f"({high_confidence_count} high confidence) in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Concept mention finding failed: {e}")
            raise KGQueryError(f"Concept mention error: {e}")
    
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
    
    def _generate_term_variants(self, concept_label: str) -> List[str]:
        """Generate normalized variants of concept label for matching"""
        variants = set()
        
        # Get normalized versions from text normalizer
        normalized_variants = self.text_normalizer.normalize_entity_text(concept_label)
        
        for variant_name, variant_text in normalized_variants.items():
            if variant_text and len(variant_text) >= self.min_term_length:
                variants.add(variant_text.lower())
        
        # Add original label
        if len(concept_label) >= self.min_term_length:
            variants.add(concept_label.lower())
        
        # Add key terms from label
        key_terms = self.text_normalizer.extract_key_terms(concept_label, min_length=self.min_term_length)
        for term in key_terms:
            if len(term) >= self.min_term_length:
                variants.add(term.lower())
        
        return list(variants)
    
    def _find_mentions_in_text(self, 
                             text: str, 
                             chunk_id: str, 
                             chunk_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find concept mentions in a single text using pattern matching"""
        mentions = []
        
        if not text or (not self.automaton and not hasattr(self, 'fallback_terms')):
            return mentions
        
        # Normalize text for matching
        normalized_text = self.text_normalizer.normalize_entity_text(text, ['basic'])['basic']
        
        try:
            if AHOCORASICK_AVAILABLE and self.automaton:
                # Use high-performance Aho-Corasick matching
                matches = self.automaton.find_overlapping(normalized_text)
                
                # Process each match
                for match in matches:
                    start_pos, end_pos, pattern = match
                    matched_text = normalized_text[start_pos:end_pos]
                    
                    # Get concept candidates for this pattern
                    concept_candidates = self.term_to_concepts.get(pattern, [])
                    
                    for candidate in concept_candidates:
                        mention = self._create_mention(
                            matched_text, candidate, text, chunk_id, chunk_metadata, start_pos, end_pos
                        )
                        if mention:  # Only add if confidence threshold met
                            mentions.append(mention)
            else:
                # Fallback: simple string matching
                mentions = self._fallback_pattern_matching(normalized_text, text, chunk_id, chunk_metadata)
                
        except Exception as e:
            self.logger.error(f"Pattern matching failed for chunk {chunk_id}: {e}")
            
        return mentions
    
    def _fallback_pattern_matching(self, normalized_text: str, original_text: str, 
                                 chunk_id: str, chunk_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback pattern matching when Aho-Corasick is not available"""
        mentions = []
        
        if not hasattr(self, 'fallback_terms'):
            return mentions
        
        # Simple substring matching
        for term in self.fallback_terms:
            start_pos = 0
            while True:
                pos = normalized_text.find(term, start_pos)
                if pos == -1:
                    break
                
                end_pos = pos + len(term)
                matched_text = normalized_text[pos:end_pos]
                
                # Get concept candidates for this term
                concept_candidates = self.term_to_concepts.get(term, [])
                
                for candidate in concept_candidates:
                    mention = self._create_mention(
                        matched_text, candidate, original_text, chunk_id, chunk_metadata, pos, end_pos
                    )
                    if mention:  # Only add if confidence threshold met
                        mentions.append(mention)
                
                start_pos = pos + 1  # Continue searching for overlapping matches
        
        return mentions
    
    def _create_mention(self, matched_text: str, candidate: Dict[str, Any], 
                       original_text: str, chunk_id: str, chunk_metadata: Dict[str, Any],
                       start_pos: int, end_pos: int) -> Dict[str, Any]:
        """Create a mention object from a match"""
        # Calculate confidence for this mention
        confidence, factors = self.confidence_scorer.calculate_alignment_confidence(
            entity_text=matched_text,
            concept_label=candidate['concept_label'],
            concept_metadata=candidate['concept_metadata'],
            context_text=original_text,
            entity_metadata={
                'chunk_id': chunk_id,
                'position': start_pos / len(original_text) if original_text else 0.0,
                'section_type': chunk_metadata.get('section_type', 'unknown')
            }
        )
        
        if confidence >= self.min_confidence:
            # Generate URI for this mention
            mention_uri = f"mention_{chunk_id}_{candidate['concept_uri'].split('#')[-1]}_{start_pos}"
            
            mention = {
                'mention_uri': mention_uri,
                'concept_uri': candidate['concept_uri'],
                'concept_label': candidate['concept_label'],
                'matched_text': matched_text,
                'confidence': confidence,
                'confidence_factors': factors,
                'start_offset': start_pos,
                'end_offset': end_pos,
                'chunk_id': chunk_id,
                'variant_type': candidate.get('variant_type', 'unknown'),
                'context_snippet': original_text[max(0, start_pos-50):end_pos+50]
            }
            
            return mention
        
        return None

    def _deduplicate_mentions(self, mentions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate mentions based on concept and position overlap"""
        if not mentions:
            return mentions
        
        # Sort by confidence (highest first)
        mentions.sort(key=lambda x: x['confidence'], reverse=True)
        
        deduplicated = []
        used_positions = set()
        
        for mention in mentions:
            concept_uri = mention['concept_uri']
            start_pos = mention['start_offset']
            end_pos = mention['end_offset']
            
            # Check for overlap with existing mentions
            overlap_found = False
            for used_start, used_end, used_concept in used_positions:
                if (concept_uri == used_concept and 
                    not (end_pos <= used_start or start_pos >= used_end)):
                    overlap_found = True
                    break
            
            if not overlap_found:
                deduplicated.append(mention)
                used_positions.add((start_pos, end_pos, concept_uri))
        
        return deduplicated
    
    def _detect_co_occurrences(self, 
                             mentions: List[Dict[str, Any]], 
                             chunk_text: str, 
                             chunk_id: str) -> List[Dict[str, Any]]:
        """Detect co-occurrences between concept mentions within a chunk"""
        co_occurrences = []
        
        if len(mentions) < 2:
            return co_occurrences
        
        # Check all pairs of mentions
        for i, mention1 in enumerate(mentions):
            for j, mention2 in enumerate(mentions[i+1:], i+1):
                
                # Calculate distance between mentions
                distance = abs(mention1['start_offset'] - mention2['start_offset'])
                
                if distance <= self.max_term_distance:
                    # Generate URI for co-occurrence using EXISTING uri_manager
                    co_occurrence_uri = self._mint_co_occurrence_uri(
                        chunk_id,
                        mention1['concept_uri'],
                        mention2['concept_uri']
                    )
                    
                    co_occurrence = {
                        'chunk_id': chunk_id,
                        'concept1_uri': mention1['concept_uri'],
                        'concept2_uri': mention2['concept_uri'],
                        'concept1_label': mention1['concept_label'],
                        'concept2_label': mention2['concept_label'],
                        'co_occurrence_uri': str(co_occurrence_uri),
                        'distance': distance,
                        'confidence': min(mention1['confidence'], mention2['confidence']),
                        'mention1_position': mention1['start_offset'],
                        'mention2_position': mention2['start_offset'],
                        'detection_method': 'proximity_based'
                    }
                    
                    co_occurrences.append(co_occurrence)
        
        return co_occurrences
    
    def _mint_concept_mention_uri(self, chunk_id: str, concept_uri: str, position: int) -> str:
        """Generate URI for concept mention using EXISTING uri_manager"""
        # Use EXISTING method - no changes to interface
        return self.kg_manager.mint_concept_mention_uri(chunk_id, concept_uri, position)
    
    def _mint_co_occurrence_uri(self, chunk_id: str, concept1_uri: str, concept2_uri: str) -> str:
        """Generate URI for co-occurrence using EXISTING uri_manager"""
        
        # Create unique identifier for co-occurrence
        unique_id = f"{chunk_id}_{hash(concept1_uri)}_{hash(concept2_uri)}"
        
        # Use EXISTING mint_uri method
        co_occurrence_uri = self.kg_manager.mint_uri(
            unique_id=unique_id,
            namespace=self.kg_manager.kr_ns,
            ontology_concept="ConceptCoOccurrence",
            ontology_uri=self.kg_manager.kr_ns
        )
        
        return co_occurrence_uri
    
    def _create_empty_mentions_result(self) -> Dict[str, Any]:
        """Create empty result structure"""
        return {
            'concept_mentions': [],
            'mentions_by_chunk': {},
            'co_occurrences': [],
            'processing_stats': {
                'total_chunks': 0,
                'chunks_with_mentions': 0,
                'total_mentions': 0,
                'high_confidence_mentions': 0,
                'co_occurrences_found': 0,
                'processing_time_seconds': 0.0,
                'mentions_per_chunk': 0.0
            },
            'ontology_domains': [],
            'min_confidence_threshold': self.min_confidence
        }
    
    def get_matcher_statistics(self) -> Dict[str, Any]:
        """Get comprehensive matcher statistics"""
        return {
            'processing_stats': dict(self.stats),
            'automaton_stats': {
                'automaton_built': self.automaton is not None,
                'terms_indexed': self.stats['terms_indexed'],
                'concepts_indexed': self.stats['concepts_indexed']
            },
            'configuration': {
                'min_confidence': self.min_confidence,
                'min_term_length': self.min_term_length,
                'max_term_distance': self.max_term_distance,
                'enable_fuzzy_boundaries': self.enable_fuzzy_boundaries
            },
            'text_normalizer_stats': self.text_normalizer.get_normalization_stats(),
            'confidence_scorer_stats': self.confidence_scorer.get_scorer_stats()
        }
    
    def rebuild_automaton(self, ontology_domains: List[str] = None) -> bool:
        """Force rebuild of pattern matching automaton"""
        self.automaton = None
        self.term_to_concepts = {}
        self.concept_metadata = {}
        return self.build_pattern_automaton(ontology_domains, force_rebuild=True)

# Example usage and testing
if __name__ == "__main__":
    # This would be used in Lambda functions
    kg_manager = KnowledgeGraphManager()
    term_matcher = OntologyTermMatcher(kg_manager, min_confidence=0.7)
    
    # Build pattern automaton
    term_matcher.build_pattern_automaton(['climate', 'financial'])
    
    # Test chunks
    test_chunks = [
        {
            'chunk_id': 'doc123_chunk_0001',
            'text': 'Climate change poses significant risks to financial institutions and requires comprehensive risk management frameworks.',
            'section_type': 'paragraph',
            'hierarchy_level': 3
        },
        {
            'chunk_id': 'doc123_chunk_0002',
            'text': 'The Federal Reserve has issued guidance on climate-related financial risks for banking organizations.',
            'section_type': 'paragraph', 
            'hierarchy_level': 3
        }
    ]
    
    # Find concept mentions
    result = term_matcher.find_concept_mentions(
        chunks=test_chunks,
        ontology_domains=['climate', 'financial', 'regulatory'],
        include_co_occurrences=True
    )
    
    print(f"Concept mentions result: {json.dumps(result, indent=2)}")
