"""
Enhanced NLP-Knowledge Graph Integrator with Multi-Ontology Support

Extends the existing NLPKGIntegrator to work with multiple ontologies
and provides sophisticated entity linking capabilities.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
import logging
import json

from .MultiOntologyManager import MultiOntologyManager, OntologyScope, ConceptMatch
from .NLPKGIntegrator import NLPKGIntegrator
from .kg_exceptions import KGValidationError


@dataclass
class EntityLinkingResult:
    """Result of entity linking process"""
    entity_text: str
    entity_type: str
    entity_score: float
    concept_matches: List[ConceptMatch]
    best_match: Optional[ConceptMatch] = None
    linking_confidence: float = 0.0


@dataclass
class DocumentContext:
    """Context information for document processing"""
    document_type: Optional[str] = None
    domain_hints: List[str] = None
    geographic_focus: Optional[str] = None
    temporal_focus: Optional[str] = None
    language: str = 'en'


class EnhancedNLPKGIntegrator:
    """
    Enhanced NLP-KG integrator supporting multiple ontologies
    
    Features:
    - Multi-ontology concept resolution
    - Context-aware entity linking
    - Scope-based ontology selection
    - Confidence-based result ranking
    """
    
    def __init__(self, 
                 multi_ontology_manager: MultiOntologyManager,
                 config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.multi_ontology_manager = multi_ontology_manager
        
        # Configuration
        self.config = config or {}
        self.min_linking_confidence = self.config.get('min_linking_confidence', 0.6)
        self.max_concepts_per_entity = self.config.get('max_concepts_per_entity', 5)
        self.enable_context_boosting = self.config.get('enable_context_boosting', True)
        
        # Scope detection patterns
        self.scope_patterns = {
            OntologyScope.CLIMATE_RISK: [
                'climate', 'disaster', 'earthquake', 'flood', 'drought', 'storm',
                'adaptation', 'mitigation', 'vulnerability', 'resilience', 'risk'
            ],
            OntologyScope.INSURANCE: [
                'insurance', 'coverage', 'premium', 'claim', 'policy', 'underwriting',
                'reinsurance', 'catastrophe', 'protection', 'gap'
            ],
            OntologyScope.FINANCIAL: [
                'bank', 'credit', 'loan', 'investment', 'fund', 'capital',
                'financial', 'monetary', 'fiscal', 'economic'
            ],
            OntologyScope.GEOGRAPHIC: [
                'country', 'city', 'region', 'district', 'area', 'location',
                'geographic', 'spatial', 'place'
            ]
        }
    
    def process_document_entities(self, 
                                entities: List[Dict[str, Any]], 
                                keyphrases: List[Dict[str, Any]],
                                context: Optional[DocumentContext] = None) -> List[EntityLinkingResult]:
        """
        Process NLP entities and link them to ontology concepts
        
        Args:
            entities: List of NLP entities from Comprehend
            keyphrases: List of key phrases from Comprehend  
            context: Document context for better linking
            
        Returns:
            List of EntityLinkingResult objects
        """
        results = []
        
        # Detect document scopes for ontology selection
        document_scopes = self._detect_document_scopes(entities, keyphrases, context)
        self.logger.info(f"Detected document scopes: {[scope.value for scope in document_scopes]}")
        
        # Process entities
        for entity in entities:
            entity_result = self._link_entity_to_concepts(
                entity_text=entity['Text'],
                entity_type=entity['Type'], 
                entity_score=entity['Score'],
                document_scopes=document_scopes,
                context=context
            )
            
            if entity_result.concept_matches:
                results.append(entity_result)
        
        # Process high-confidence key phrases
        for keyphrase in keyphrases:
            if keyphrase['Score'] >= 0.8:  # Only high-confidence phrases
                phrase_result = self._link_entity_to_concepts(
                    entity_text=keyphrase['Text'],
                    entity_type='KEYPHRASE',
                    entity_score=keyphrase['Score'],
                    document_scopes=document_scopes,
                    context=context
                )
                
                if phrase_result.concept_matches:
                    results.append(phrase_result)
        
        # Sort by linking confidence
        results.sort(key=lambda x: x.linking_confidence, reverse=True)
        
        return results
    
    def _detect_document_scopes(self, 
                               entities: List[Dict[str, Any]], 
                               keyphrases: List[Dict[str, Any]],
                               context: Optional[DocumentContext]) -> List[OntologyScope]:
        """Detect which ontology scopes are relevant for this document"""
        scope_scores = {scope: 0 for scope in OntologyScope}
        
        # Analyze entities and keyphrases
        all_text = []
        for entity in entities:
            all_text.append(entity['Text'].lower())
        for phrase in keyphrases:
            all_text.append(phrase['Text'].lower())
        
        document_text = ' '.join(all_text)
        
        # Score each scope based on keyword presence
        for scope, keywords in self.scope_patterns.items():
            for keyword in keywords:
                if keyword in document_text:
                    scope_scores[scope] += document_text.count(keyword)
        
        # Use context hints if available
        if context and context.domain_hints:
            for hint in context.domain_hints:
                hint_lower = hint.lower()
                for scope, keywords in self.scope_patterns.items():
                    if any(keyword in hint_lower for keyword in keywords):
                        scope_scores[scope] += 5  # Boost for explicit hints
        
        # Return scopes with significant presence
        relevant_scopes = []
        total_score = sum(scope_scores.values())
        
        if total_score > 0:
            for scope, score in scope_scores.items():
                if score / total_score >= 0.1:  # At least 10% of total mentions
                    relevant_scopes.append(scope)
        
        # Always include general scope if no specific scopes detected
        if not relevant_scopes:
            relevant_scopes = [OntologyScope.GENERAL]
        
        return relevant_scopes
    
    def _link_entity_to_concepts(self,
                                entity_text: str,
                                entity_type: str, 
                                entity_score: float,
                                document_scopes: List[OntologyScope],
                                context: Optional[DocumentContext]) -> EntityLinkingResult:
        """Link a single entity to ontology concepts"""
        
        # Search for concepts across relevant ontologies
        concept_matches = self.multi_ontology_manager.find_concepts(
            text=entity_text,
            scopes=document_scopes,
            max_results=self.max_concepts_per_entity,
            min_confidence=0.3  # Lower threshold, we'll filter later
        )
        
        # Apply context boosting if enabled
        if self.enable_context_boosting and context:
            concept_matches = self._apply_context_boosting(
                concept_matches, entity_type, context
            )
        
        # Filter by minimum confidence
        filtered_matches = [
            match for match in concept_matches 
            if match.confidence >= self.min_linking_confidence
        ]
        
        # Determine best match and overall linking confidence
        best_match = filtered_matches[0] if filtered_matches else None
        linking_confidence = best_match.confidence if best_match else 0.0
        
        # Boost confidence based on entity score
        if best_match:
            linking_confidence = min(1.0, linking_confidence * (0.5 + 0.5 * entity_score))
        
        return EntityLinkingResult(
            entity_text=entity_text,
            entity_type=entity_type,
            entity_score=entity_score,
            concept_matches=filtered_matches,
            best_match=best_match,
            linking_confidence=linking_confidence
        )
    
    def _apply_context_boosting(self,
                               matches: List[ConceptMatch],
                               entity_type: str,
                               context: DocumentContext) -> List[ConceptMatch]:
        """Apply context-based confidence boosting"""
        
        for match in matches:
            boost = 0.0
            
            # Entity type alignment
            if entity_type == 'ORGANIZATION' and 'institution' in match.concept_label.lower():
                boost += 0.1
            elif entity_type == 'LOCATION' and 'geographic' in str(match.context.get('scopes', [])):
                boost += 0.1
            elif entity_type == 'EVENT' and 'disaster' in match.concept_label.lower():
                boost += 0.1
            
            # Geographic context
            if context.geographic_focus and context.geographic_focus.lower() in match.concept_label.lower():
                boost += 0.05
            
            # Domain hints
            if context.domain_hints:
                for hint in context.domain_hints:
                    if hint.lower() in match.concept_label.lower():
                        boost += 0.05
            
            # Apply boost
            match.confidence = min(1.0, match.confidence + boost)
        
        # Re-sort after boosting
        matches.sort(key=lambda x: (-x.confidence, x.ontology_priority))
        
        return matches
    
    def generate_linking_report(self, results: List[EntityLinkingResult]) -> Dict[str, Any]:
        """Generate a comprehensive linking report"""
        
        total_entities = len(results)
        linked_entities = len([r for r in results if r.best_match])
        
        # Ontology usage stats
        ontology_usage = {}
        confidence_distribution = {'high': 0, 'medium': 0, 'low': 0}
        
        for result in results:
            if result.best_match:
                ontology_id = result.best_match.context.get('ontology_id', 'unknown')
                ontology_usage[ontology_id] = ontology_usage.get(ontology_id, 0) + 1
                
                if result.linking_confidence >= 0.8:
                    confidence_distribution['high'] += 1
                elif result.linking_confidence >= 0.6:
                    confidence_distribution['medium'] += 1
                else:
                    confidence_distribution['low'] += 1
        
        return {
            'summary': {
                'total_entities': total_entities,
                'linked_entities': linked_entities,
                'linking_rate': linked_entities / total_entities if total_entities > 0 else 0,
                'average_confidence': sum(r.linking_confidence for r in results) / total_entities if total_entities > 0 else 0
            },
            'ontology_usage': ontology_usage,
            'confidence_distribution': confidence_distribution,
            'top_matches': [
                {
                    'entity': result.entity_text,
                    'concept': result.best_match.concept_label,
                    'confidence': result.linking_confidence,
                    'ontology': result.best_match.context.get('ontology_id')
                }
                for result in results[:10] if result.best_match
            ]
        }


# Configuration template for enhanced NLP-KG integration
DEFAULT_ENHANCED_CONFIG = {
    "min_linking_confidence": 0.6,
    "max_concepts_per_entity": 5,
    "enable_context_boosting": True,
    "entity_type_mappings": {
        "ORGANIZATION": ["institution", "organization", "agency"],
        "LOCATION": ["place", "area", "region", "geographic"],
        "EVENT": ["event", "disaster", "occurrence"],
        "PERSON": ["person", "individual", "stakeholder"],
        "QUANTITY": ["measure", "amount", "metric"]
    }
}
