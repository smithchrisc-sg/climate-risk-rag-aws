#!/usr/bin/env python3
"""
Confidence Scorer - Multi-factor confidence calculation for entity-ontology alignment
Combines fuzzy matching, semantic similarity, context analysis, and domain relevance
"""
import logging
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from fuzzywuzzy import fuzz
import numpy as np

@dataclass
class ConfidenceFactors:
    """Individual confidence factors for alignment scoring"""
    text_similarity: float = 0.0      # Fuzzy string similarity
    semantic_similarity: float = 0.0   # Semantic/contextual similarity  
    domain_relevance: float = 0.0      # Domain-specific relevance
    context_support: float = 0.0       # Surrounding context support
    frequency_boost: float = 0.0       # Frequency-based confidence boost
    length_penalty: float = 0.0        # Penalty for very short/long matches
    position_weight: float = 0.0       # Position-based weighting
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization"""
        return {
            'text_similarity': self.text_similarity,
            'semantic_similarity': self.semantic_similarity,
            'domain_relevance': self.domain_relevance,
            'context_support': self.context_support,
            'frequency_boost': self.frequency_boost,
            'length_penalty': self.length_penalty,
            'position_weight': self.position_weight
        }

class ConfidenceScorer:
    """
    Multi-factor confidence scoring for entity-ontology alignment
    Provides transparent, explainable confidence calculations
    """
    
    def __init__(self, 
                 min_confidence: float = 0.5,
                 weights: Optional[Dict[str, float]] = None,
                 track_evidence: bool = True):
        """
        Initialize confidence scorer
        
        Args:
            min_confidence: Minimum confidence threshold
            weights: Custom weights for confidence factors
            track_evidence: Whether to track evidence for explanations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.min_confidence = min_confidence
        self.track_evidence = track_evidence
        
        # Default weights for confidence factors
        self.weights = weights or {
            'text_similarity': 0.30,      # Primary factor
            'semantic_similarity': 0.25,   # Secondary factor
            'domain_relevance': 0.20,      # Domain importance
            'context_support': 0.15,       # Context validation
            'frequency_boost': 0.05,       # Frequency bonus
            'length_penalty': -0.05,       # Length adjustment
            'position_weight': 0.10        # Position importance
        }
        
        # Validate weights sum to 1.0 (approximately)
        weight_sum = sum(abs(w) for w in self.weights.values())
        if abs(weight_sum - 1.0) > 0.1:
            self.logger.warning(f"Confidence weights sum to {weight_sum:.3f}, not 1.0")
        
        # Domain-specific terms for relevance scoring
        self._setup_domain_indicators()
        
        self.logger.debug(f"ConfidenceScorer initialized with min_confidence={min_confidence}")
    
    def _setup_domain_indicators(self):
        """Setup domain-specific indicators for relevance scoring"""
        
        # Climate risk indicators
        self.climate_indicators = {
            'high': {'climate', 'warming', 'carbon', 'emissions', 'greenhouse', 'temperature', 
                    'sea level', 'extreme weather', 'drought', 'flood', 'hurricane', 'wildfire'},
            'medium': {'environmental', 'sustainability', 'renewable', 'energy', 'pollution',
                      'ecosystem', 'biodiversity', 'conservation', 'green', 'clean'},
            'low': {'weather', 'natural', 'resource', 'water', 'air', 'land', 'forest'}
        }
        
        # Financial indicators
        self.financial_indicators = {
            'high': {'bank', 'financial', 'investment', 'credit', 'loan', 'asset', 'portfolio',
                    'risk', 'capital', 'regulatory', 'compliance', 'audit'},
            'medium': {'economic', 'market', 'trading', 'securities', 'insurance', 'pension',
                      'fund', 'equity', 'debt', 'derivative', 'liquidity'},
            'low': {'business', 'company', 'corporate', 'industry', 'sector', 'commercial'}
        }
        
        # Regulatory indicators
        self.regulatory_indicators = {
            'high': {'regulation', 'regulatory', 'compliance', 'oversight', 'supervision',
                    'enforcement', 'policy', 'framework', 'standard', 'requirement'},
            'medium': {'governance', 'reporting', 'disclosure', 'transparency', 'accountability',
                      'monitoring', 'assessment', 'evaluation', 'review'},
            'low': {'guideline', 'recommendation', 'best practice', 'procedure', 'process'}
        }
    
    def calculate_alignment_confidence(self, 
                                     entity_text: str,
                                     concept_label: str,
                                     concept_metadata: Dict[str, Any],
                                     context_text: str = "",
                                     entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[float, ConfidenceFactors]:
        """
        Calculate comprehensive confidence score for entity-concept alignment
        
        Args:
            entity_text: Text of the entity from NER
            concept_label: Label of the ontology concept
            concept_metadata: Metadata about the concept (type, domain, etc.)
            context_text: Surrounding context text
            entity_metadata: Optional metadata about the entity
        
        Returns:
            Tuple of (confidence_score, confidence_factors)
        """
        factors = ConfidenceFactors()
        
        # Calculate individual confidence factors
        factors.text_similarity = self._calculate_text_similarity(entity_text, concept_label)
        factors.semantic_similarity = self._calculate_semantic_similarity(entity_text, concept_label, context_text)
        factors.domain_relevance = self._calculate_domain_relevance(entity_text, concept_metadata, context_text)
        factors.context_support = self._calculate_context_support(entity_text, concept_label, context_text)
        factors.frequency_boost = self._calculate_frequency_boost(entity_text, entity_metadata)
        factors.length_penalty = self._calculate_length_penalty(entity_text, concept_label)
        factors.position_weight = self._calculate_position_weight(entity_text, context_text, entity_metadata)
        
        # Calculate weighted confidence score
        confidence = self._combine_factors(factors)
        
        # Apply minimum confidence threshold
        if confidence < self.min_confidence:
            confidence = 0.0
        
        self.logger.debug(f"Confidence for '{entity_text}' -> '{concept_label}': {confidence:.3f}")
        
        return confidence, factors
    
    def _calculate_text_similarity(self, entity_text: str, concept_label: str) -> float:
        """Calculate fuzzy text similarity between entity and concept"""
        if not entity_text or not concept_label:
            return 0.0
        
        # Use multiple fuzzy matching algorithms
        ratio = fuzz.ratio(entity_text.lower(), concept_label.lower()) / 100.0
        partial_ratio = fuzz.partial_ratio(entity_text.lower(), concept_label.lower()) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(entity_text.lower(), concept_label.lower()) / 100.0
        token_set_ratio = fuzz.token_set_ratio(entity_text.lower(), concept_label.lower()) / 100.0
        
        # Take the maximum of different similarity measures
        similarity = max(ratio, partial_ratio, token_sort_ratio, token_set_ratio)
        
        return similarity
    
    def _calculate_semantic_similarity(self, entity_text: str, concept_label: str, context_text: str) -> float:
        """Calculate semantic similarity (placeholder for sentence transformers)"""
        # This would use sentence transformers in full implementation
        # For now, use word overlap as proxy
        
        entity_words = set(entity_text.lower().split())
        concept_words = set(concept_label.lower().split())
        context_words = set(context_text.lower().split()) if context_text else set()
        
        # Calculate word overlap
        direct_overlap = len(entity_words.intersection(concept_words))
        total_words = len(entity_words.union(concept_words))
        
        if total_words == 0:
            return 0.0
        
        base_similarity = direct_overlap / total_words
        
        # Boost if context supports the match
        if context_words:
            context_support = len(concept_words.intersection(context_words)) / len(concept_words)
            base_similarity += context_support * 0.2  # 20% boost from context
        
        return min(base_similarity, 1.0)
    
    def _calculate_domain_relevance(self, entity_text: str, concept_metadata: Dict[str, Any], context_text: str) -> float:
        """Calculate domain-specific relevance score"""
        entity_lower = entity_text.lower()
        context_lower = context_text.lower() if context_text else ""
        combined_text = f"{entity_lower} {context_lower}"
        
        # Get concept domain from metadata
        concept_domain = concept_metadata.get('domain', 'unknown').lower()
        
        relevance_score = 0.0
        
        # Check against domain indicators
        if 'climate' in concept_domain or 'environmental' in concept_domain:
            relevance_score = self._score_domain_indicators(combined_text, self.climate_indicators)
        elif 'financial' in concept_domain or 'economic' in concept_domain:
            relevance_score = self._score_domain_indicators(combined_text, self.financial_indicators)
        elif 'regulatory' in concept_domain or 'legal' in concept_domain:
            relevance_score = self._score_domain_indicators(combined_text, self.regulatory_indicators)
        else:
            # Generic relevance based on concept type
            concept_type = concept_metadata.get('type', '').lower()
            if any(term in combined_text for term in ['organization', 'institution', 'company']):
                relevance_score = 0.7 if 'organization' in concept_type else 0.3
            elif any(term in combined_text for term in ['location', 'place', 'region']):
                relevance_score = 0.7 if 'location' in concept_type else 0.3
        
        return min(relevance_score, 1.0)
    
    def _score_domain_indicators(self, text: str, indicators: Dict[str, set]) -> float:
        """Score text against domain indicators"""
        score = 0.0
        
        # High relevance indicators
        high_matches = sum(1 for term in indicators['high'] if term in text)
        score += high_matches * 0.4
        
        # Medium relevance indicators  
        medium_matches = sum(1 for term in indicators['medium'] if term in text)
        score += medium_matches * 0.2
        
        # Low relevance indicators
        low_matches = sum(1 for term in indicators['low'] if term in text)
        score += low_matches * 0.1
        
        return min(score, 1.0)
    
    def _calculate_context_support(self, entity_text: str, concept_label: str, context_text: str) -> float:
        """Calculate how well context supports the entity-concept alignment"""
        if not context_text:
            return 0.5  # Neutral score when no context
        
        context_lower = context_text.lower()
        concept_words = set(concept_label.lower().split())
        
        # Count concept words in context
        context_support = sum(1 for word in concept_words if word in context_lower)
        
        if len(concept_words) == 0:
            return 0.5
        
        support_ratio = context_support / len(concept_words)
        
        # Boost for exact phrase matches in context
        if concept_label.lower() in context_lower:
            support_ratio += 0.3
        
        return min(support_ratio, 1.0)
    
    def _calculate_frequency_boost(self, entity_text: str, entity_metadata: Optional[Dict[str, Any]]) -> float:
        """Calculate frequency-based confidence boost"""
        if not entity_metadata:
            return 0.0
        
        frequency = entity_metadata.get('frequency', 1)
        
        # Logarithmic boost for frequency
        if frequency > 1:
            boost = min(math.log(frequency) / math.log(10), 0.3)  # Max 30% boost
            return boost
        
        return 0.0
    
    def _calculate_length_penalty(self, entity_text: str, concept_label: str) -> float:
        """Calculate penalty for very short or very long matches"""
        entity_len = len(entity_text.split())
        concept_len = len(concept_label.split())
        
        # Penalty for very short entities (likely noise)
        if entity_len == 1 and len(entity_text) < 3:
            return -0.3
        
        # Penalty for very long entities (likely over-extraction)
        if entity_len > 8:
            return -0.2
        
        # Penalty for large length mismatch
        length_ratio = min(entity_len, concept_len) / max(entity_len, concept_len)
        if length_ratio < 0.3:
            return -0.1
        
        return 0.0
    
    def _calculate_position_weight(self, entity_text: str, context_text: str, entity_metadata: Optional[Dict[str, Any]]) -> float:
        """Calculate position-based weighting"""
        if not entity_metadata:
            return 0.5  # Neutral weight
        
        # Boost for entities in titles or headers
        section_type = entity_metadata.get('section_type', '').lower()
        if section_type in ['title', 'header', 'heading']:
            return 0.8
        
        # Boost for entities early in document/chunk
        position = entity_metadata.get('position', 0.5)
        if position < 0.2:  # First 20% of document
            return 0.7
        
        return 0.5  # Neutral weight for other positions
    
    def _combine_factors(self, factors: ConfidenceFactors) -> float:
        """Combine individual factors into overall confidence score"""
        score = 0.0
        
        # Apply weighted combination
        score += factors.text_similarity * self.weights['text_similarity']
        score += factors.semantic_similarity * self.weights['semantic_similarity']
        score += factors.domain_relevance * self.weights['domain_relevance']
        score += factors.context_support * self.weights['context_support']
        score += factors.frequency_boost * self.weights['frequency_boost']
        score += factors.length_penalty * self.weights['length_penalty']
        score += factors.position_weight * self.weights['position_weight']
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def explain_confidence(self, confidence: float, factors: ConfidenceFactors) -> Dict[str, Any]:
        """Generate explanation for confidence score"""
        explanation = {
            'overall_confidence': confidence,
            'meets_threshold': confidence >= self.min_confidence,
            'factors': factors.to_dict(),
            'weighted_contributions': {},
            'key_strengths': [],
            'key_weaknesses': []
        }
        
        # Calculate weighted contributions
        for factor_name, factor_value in factors.to_dict().items():
            weight = self.weights.get(factor_name, 0.0)
            explanation['weighted_contributions'][factor_name] = factor_value * weight
        
        # Identify strengths and weaknesses
        for factor_name, factor_value in factors.to_dict().items():
            if factor_value > 0.7:
                explanation['key_strengths'].append(factor_name)
            elif factor_value < 0.3:
                explanation['key_weaknesses'].append(factor_name)
        
        return explanation
    
    def batch_score_alignments(self, alignments: List[Dict[str, Any]]) -> List[Tuple[float, ConfidenceFactors]]:
        """Score multiple alignments in batch"""
        results = []
        
        for alignment in alignments:
            confidence, factors = self.calculate_alignment_confidence(
                entity_text=alignment['entity_text'],
                concept_label=alignment['concept_label'],
                concept_metadata=alignment.get('concept_metadata', {}),
                context_text=alignment.get('context_text', ''),
                entity_metadata=alignment.get('entity_metadata', {})
            )
            results.append((confidence, factors))
        
        return results
    
    def get_scorer_stats(self) -> Dict[str, Any]:
        """Get statistics about the confidence scorer"""
        return {
            'min_confidence': self.min_confidence,
            'weights': self.weights,
            'track_evidence': self.track_evidence,
            'domain_indicators': {
                'climate_terms': len(self.climate_indicators['high']) + len(self.climate_indicators['medium']) + len(self.climate_indicators['low']),
                'financial_terms': len(self.financial_indicators['high']) + len(self.financial_indicators['medium']) + len(self.financial_indicators['low']),
                'regulatory_terms': len(self.regulatory_indicators['high']) + len(self.regulatory_indicators['medium']) + len(self.regulatory_indicators['low'])
            }
        }

# Example usage and testing
if __name__ == "__main__":
    scorer = ConfidenceScorer(min_confidence=0.6)
    
    # Test alignment
    confidence, factors = scorer.calculate_alignment_confidence(
        entity_text="climate change",
        concept_label="Climate Change Risk",
        concept_metadata={'domain': 'climate', 'type': 'risk_factor'},
        context_text="The impact of climate change on financial institutions requires careful assessment of climate-related risks.",
        entity_metadata={'frequency': 3, 'section_type': 'paragraph', 'position': 0.2}
    )
    
    print(f"Confidence: {confidence:.3f}")
    explanation = scorer.explain_confidence(confidence, factors)
    print(f"Explanation: {explanation}")
