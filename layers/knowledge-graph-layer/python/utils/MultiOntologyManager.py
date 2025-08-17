"""
Multi-Ontology Manager for Climate Risk RAG System

Handles multiple ontologies with different scopes, priorities, and sources.
Extends the existing OntologyManager to support 1-to-n ontology integration.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import logging
from rdflib import Graph, ConjunctiveGraph, URIRef, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL

from .OntologyManager import OntologyManager
from .kg_exceptions import KGValidationError, KGDataFormatError


class OntologyScope(Enum):
    """Predefined ontology scopes for document processing"""
    CLIMATE_RISK = "climate_risk"
    INSURANCE = "insurance" 
    FINANCIAL = "financial"
    GEOGRAPHIC = "geographic"
    GENERAL = "general"


@dataclass
class OntologyConfig:
    """Configuration for a single ontology in the multi-ontology system"""
    uri: str
    named_graph_uri: str
    priority: int  # Lower number = higher priority
    scopes: List[OntologyScope]
    source_type: str  # 's3', 'url', 'local'
    source_location: str
    format: str = 'turtle'
    enabled: bool = True
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'uri': self.uri,
            'named_graph_uri': self.named_graph_uri,
            'priority': self.priority,
            'scopes': [scope.value for scope in self.scopes],
            'source_type': self.source_type,
            'source_location': self.source_location,
            'format': self.format,
            'enabled': self.enabled,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OntologyConfig':
        return cls(
            uri=data['uri'],
            named_graph_uri=data['named_graph_uri'],
            priority=data['priority'],
            scopes=[OntologyScope(scope) for scope in data['scopes']],
            source_type=data['source_type'],
            source_location=data['source_location'],
            format=data.get('format', 'turtle'),
            enabled=data.get('enabled', True),
            description=data.get('description')
        )


@dataclass
class ConceptMatch:
    """Represents a concept match from ontology search"""
    concept_uri: str
    concept_label: str
    ontology_uri: str
    ontology_priority: int
    match_type: str  # 'exact', 'partial', 'fuzzy', 'semantic'
    confidence: float
    context: Optional[Dict[str, Any]] = None


class MultiOntologyManager:
    """
    Manages multiple ontologies for comprehensive concept resolution.
    
    Supports:
    - Loading ontologies from different sources (S3, URLs, local files)
    - Prioritized concept search across ontologies
    - Scope-based ontology selection
    - Cross-ontology concept alignment
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.ontology_configs: Dict[str, OntologyConfig] = {}
        self.ontology_managers: Dict[str, OntologyManager] = {}
        self.conjunctive_graph = ConjunctiveGraph()
        
        # Indexes for fast lookup
        self.concept_index: Dict[str, List[ConceptMatch]] = {}  # label -> matches
        self.scope_index: Dict[OntologyScope, List[str]] = {}  # scope -> ontology_uris
        self.uri_to_ontology: Dict[str, str] = {}  # concept_uri -> ontology_uri
        
        # Configuration
        self.default_config_path = config_path
        self.cache_enabled = True
        self.fuzzy_matching_threshold = 0.7
        
        if config_path:
            self.load_configuration(config_path)
    
    def load_configuration(self, config_path: str) -> None:
        """Load multi-ontology configuration from file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            self.ontology_configs = {}
            for ontology_id, ontology_data in config_data.get('ontologies', {}).items():
                self.ontology_configs[ontology_id] = OntologyConfig.from_dict(ontology_data)
            
            # Update global settings
            settings = config_data.get('settings', {})
            self.cache_enabled = settings.get('cache_enabled', True)
            self.fuzzy_matching_threshold = settings.get('fuzzy_matching_threshold', 0.7)
            
            self.logger.info(f"Loaded configuration for {len(self.ontology_configs)} ontologies")
            
        except Exception as e:
            raise KGDataFormatError(f"Failed to load ontology configuration: {e}")
    
    def add_ontology(self, ontology_id: str, config: OntologyConfig) -> None:
        """Add a new ontology to the manager"""
        self.ontology_configs[ontology_id] = config
        self._update_indexes()
        self.logger.info(f"Added ontology: {ontology_id}")
    
    def load_ontologies(self, ontology_ids: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Load specified ontologies (or all if none specified)
        
        Returns:
            Dict mapping ontology_id to success status
        """
        if ontology_ids is None:
            ontology_ids = list(self.ontology_configs.keys())
        
        results = {}
        
        for ontology_id in ontology_ids:
            if ontology_id not in self.ontology_configs:
                results[ontology_id] = False
                self.logger.warning(f"Ontology config not found: {ontology_id}")
                continue
            
            config = self.ontology_configs[ontology_id]
            if not config.enabled:
                results[ontology_id] = False
                self.logger.info(f"Ontology disabled: {ontology_id}")
                continue
            
            try:
                # Create individual ontology manager with required namespaces
                from rdflib import Namespace
                kr_ns = Namespace("https://solve.global/kr/")
                dcterms_ns = Namespace("http://purl.org/dc/terms/")
                foaf_ns = Namespace("http://xmlns.com/foaf/0.1/")
                skos_ns = Namespace("http://www.w3.org/2004/02/skos/core#")
                
                ontology_manager = OntologyManager()
                
                # Load based on source type
                if config.source_type == 's3':
                    success = ontology_manager.load_ontology_from_s3(
                        config.source_location,
                        config.format,
                        force_reload=True,
                        named_graph=config.named_graph_uri
                    )
                elif config.source_type == 'url':
                    success = ontology_manager.load_ontology_from_url(
                        config.source_location,
                        config.format,
                        named_graph=config.named_graph_uri
                    )
                elif config.source_type == 'local':
                    success = ontology_manager.load_ontology_from_file(
                        config.source_location,
                        config.format,
                        named_graph=config.named_graph_uri
                    )
                else:
                    raise KGValidationError(f"Unsupported source type: {config.source_type}")
                
                if success:
                    self.ontology_managers[ontology_id] = ontology_manager
                    # Add to conjunctive graph
                    self.conjunctive_graph += ontology_manager.ontology_graph
                    results[ontology_id] = True
                    self.logger.info(f"Successfully loaded ontology: {ontology_id}")
                else:
                    results[ontology_id] = False
                    self.logger.error(f"Failed to load ontology: {ontology_id}")
                    
            except Exception as e:
                results[ontology_id] = False
                self.logger.error(f"Error loading ontology {ontology_id}: {e}")
        
        # Rebuild indexes after loading
        self._rebuild_indexes()
        
        return results
    
    def find_concepts(self, 
                     text: str, 
                     scopes: Optional[List[OntologyScope]] = None,
                     max_results: int = 10,
                     min_confidence: float = 0.5) -> List[ConceptMatch]:
        """
        Find concepts across multiple ontologies
        
        Args:
            text: Text to search for
            scopes: Limit search to specific ontology scopes
            max_results: Maximum number of results to return
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of ConceptMatch objects, sorted by confidence and priority
        """
        if not text or not text.strip():
            return []
        
        # Determine which ontologies to search
        target_ontologies = self._get_target_ontologies(scopes)
        
        all_matches = []
        
        for ontology_id in target_ontologies:
            if ontology_id not in self.ontology_managers:
                continue
                
            config = self.ontology_configs[ontology_id]
            ontology_manager = self.ontology_managers[ontology_id]
            
            try:
                # Search in this ontology
                concepts = ontology_manager.search_concepts_by_label(text, fuzzy=True)
                
                for concept in concepts:
                    # Calculate confidence based on text similarity and ontology priority
                    confidence = self._calculate_confidence(
                        text, 
                        concept.get('label', ''),
                        config.priority
                    )
                    
                    if confidence >= min_confidence:
                        match = ConceptMatch(
                            concept_uri=concept['uri'],
                            concept_label=concept['label'],
                            ontology_uri=config.uri,
                            ontology_priority=config.priority,
                            match_type=self._determine_match_type(text, concept['label']),
                            confidence=confidence,
                            context={
                                'ontology_id': ontology_id,
                                'description': concept.get('description'),
                                'scopes': [scope.value for scope in config.scopes]
                            }
                        )
                        all_matches.append(match)
                        
            except Exception as e:
                self.logger.error(f"Error searching ontology {ontology_id}: {e}")
        
        # Sort by confidence (desc) then priority (asc)
        all_matches.sort(key=lambda x: (-x.confidence, x.ontology_priority))
        
        return all_matches[:max_results]
    
    def get_concept_details(self, concept_uri: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a concept across all ontologies"""
        for ontology_id, ontology_manager in self.ontology_managers.items():
            concept = ontology_manager.get_concept_by_uri(concept_uri)
            if concept:
                config = self.ontology_configs[ontology_id]
                concept['ontology_info'] = {
                    'ontology_id': ontology_id,
                    'ontology_uri': config.uri,
                    'scopes': [scope.value for scope in config.scopes],
                    'priority': config.priority
                }
                return concept
        return None
    
    def get_ontology_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded ontologies"""
        stats = {
            'total_ontologies': len(self.ontology_configs),
            'loaded_ontologies': len(self.ontology_managers),
            'total_concepts': 0,
            'ontologies': {}
        }
        
        for ontology_id, ontology_manager in self.ontology_managers.items():
            config = self.ontology_configs[ontology_id]
            ontology_stats = ontology_manager.get_stats()
            
            stats['ontologies'][ontology_id] = {
                'uri': config.uri,
                'scopes': [scope.value for scope in config.scopes],
                'priority': config.priority,
                'concepts': ontology_stats.get('ontology_triples', 0),
                'enabled': config.enabled
            }
            
            stats['total_concepts'] += ontology_stats.get('ontology_triples', 0)
        
        return stats
    
    def _get_target_ontologies(self, scopes: Optional[List[OntologyScope]]) -> List[str]:
        """Determine which ontologies to search based on scopes"""
        if not scopes:
            return list(self.ontology_managers.keys())
        
        target_ontologies = set()
        for scope in scopes:
            for ontology_id, config in self.ontology_configs.items():
                if scope in config.scopes and config.enabled:
                    target_ontologies.add(ontology_id)
        
        return list(target_ontologies)
    
    def _calculate_confidence(self, query_text: str, concept_label: str, priority: int) -> float:
        """Calculate confidence score for a concept match"""
        # Simple text similarity (can be enhanced with semantic similarity)
        query_lower = query_text.lower().strip()
        label_lower = concept_label.lower().strip()
        
        if query_lower == label_lower:
            base_confidence = 1.0
        elif query_lower in label_lower or label_lower in query_lower:
            base_confidence = 0.8
        else:
            # Simple word overlap
            query_words = set(query_lower.split())
            label_words = set(label_lower.split())
            if query_words and label_words:
                overlap = len(query_words & label_words)
                base_confidence = overlap / max(len(query_words), len(label_words))
            else:
                base_confidence = 0.0
        
        # Adjust for ontology priority (higher priority = slight boost)
        priority_boost = max(0, (10 - priority) * 0.01)  # Max 9% boost for priority 1
        
        return min(1.0, base_confidence + priority_boost)
    
    def _determine_match_type(self, query_text: str, concept_label: str) -> str:
        """Determine the type of match between query and concept"""
        query_lower = query_text.lower().strip()
        label_lower = concept_label.lower().strip()
        
        if query_lower == label_lower:
            return 'exact'
        elif query_lower in label_lower or label_lower in query_lower:
            return 'partial'
        else:
            return 'fuzzy'
    
    def _rebuild_indexes(self) -> None:
        """Rebuild internal indexes after ontology changes"""
        self.concept_index.clear()
        self.scope_index.clear()
        self.uri_to_ontology.clear()
        
        # Build scope index
        for ontology_id, config in self.ontology_configs.items():
            for scope in config.scopes:
                if scope not in self.scope_index:
                    self.scope_index[scope] = []
                self.scope_index[scope].append(ontology_id)
        
        # Build concept indexes (can be done lazily for performance)
        self._update_indexes()
    
    def _update_indexes(self) -> None:
        """Update indexes incrementally"""
        # This can be implemented for performance optimization
        # For now, we'll rely on real-time search
        pass


# Default configuration template
DEFAULT_MULTI_ONTOLOGY_CONFIG = {
    "settings": {
        "cache_enabled": True,
        "fuzzy_matching_threshold": 0.7
    },
    "ontologies": {
        "climate-risk-core": {
            "uri": "https://solve.global/kr/climate-risk-impact",
            "named_graph_uri": "https://solve.global/kr/climate-risk-impact",
            "priority": 1,
            "scopes": ["climate_risk"],
            "source_type": "s3",
            "source_location": "ontology/climate-risk-ontology-v3.ttl",
            "format": "turtle",
            "enabled": True,
            "description": "Core climate risk ontology with disaster types, risks, and adaptation concepts"
        },
        "insurance-protection-gaps": {
            "uri": "https://solve.global/kr/insurance-protection-gaps",
            "named_graph_uri": "https://solve.global/kr/insurance-protection-gaps", 
            "priority": 2,
            "scopes": ["insurance"],
            "source_type": "s3",
            "source_location": "ontology/insurance-protection-gaps-v1.ttl",
            "format": "turtle",
            "enabled": False,
            "description": "Insurance protection gaps and solutions ontology"
        }
    }
}
