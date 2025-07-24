#!/usr/bin/env python3
"""
Ontology Manager - Handles ontology loading and concept operations with RDFLib integration
Provides interface for ontology concept retrieval and management using proper RDF parsing
"""
import logging
from typing import Dict, List, Any, Optional, Union
import json
import boto3
import time
from datetime import datetime, timedelta

# RDFLib imports for proper ontology handling
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, SKOS

from .kg_exceptions import KGQueryError, KGValidationError, KGDataFormatError

class OntologyManager:
    """Manages ontology concepts and relationships using RDFLib for proper RDF handling"""
    
    def __init__(self, kg_manager):
        """
        Initialize ontology manager with RDFLib integration
        
        Args:
            kg_manager: KnowledgeGraphManager instance for SPARQL operations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kg_manager = kg_manager
        self.uri_manager = kg_manager.uri_manager
        self.query_builder = kg_manager.query_builder
        
        # S3 client for ontology data loading
        self.s3_client = boto3.client('s3')
        
        # Set up namespaces using RDFLib
        self.kr_ns = kg_manager.kr_ns
        self.dcterms_ns = kg_manager.dcterms_ns
        self.foaf_ns = kg_manager.foaf_ns
        self.skos_ns = kg_manager.skos_ns
        
        # Configuration
        self.ontology_bucket = self._get_env_var('ONTOLOGY_BUCKET', 'solve-global-kr-dl-ontology-861276078413-us-east-1')
        self.ontology_graph_uri = URIRef("https://solve.global/graphs/ontology")
        
        # RDFLib graph for ontology data
        self.ontology_graph = Graph()
        self._setup_ontology_namespaces()
        
        # Caching for performance
        self._concept_cache = {}
        self._relationship_cache = {}
        self._ontology_loaded = False
        self._cache_ttl = 3600  # 1 hour cache TTL
        self._last_cache_update = None
        
        self.logger.debug(f"OntologyManager initialized with RDFLib integration, bucket: {self.ontology_bucket}")
    
    def _setup_ontology_namespaces(self):
        """Setup standard ontology namespaces in the ontology graph"""
        self.ontology_graph.bind("kr", self.kr_ns)
        self.ontology_graph.bind("dcterms", self.dcterms_ns)
        self.ontology_graph.bind("foaf", self.foaf_ns)
        self.ontology_graph.bind("skos", self.skos_ns)
        self.ontology_graph.bind("rdf", RDF)
        self.ontology_graph.bind("rdfs", RDFS)
        self.ontology_graph.bind("owl", OWL)
        
        self.logger.debug("Ontology namespaces configured")
    
    def _get_env_var(self, var_name: str, default: str) -> str:
        """Get environment variable with default"""
        import os
        return os.environ.get(var_name, default)
    
    def load_ontology_from_s3(self, s3_key: str, format: str = 'turtle', force_reload: bool = False) -> bool:
        """
        Load ontology from S3 using RDFLib parsing
        
        Args:
            s3_key: S3 key for the ontology file
            format: RDF format ('turtle', 'xml', 'n3', 'json-ld')
            force_reload: Force reload even if already loaded
            
        Returns:
            True if loading successful
        """
        try:
            if self._ontology_loaded and not force_reload:
                self.logger.debug("Ontology already loaded, skipping")
                return True
            
            self.logger.info(f"Loading ontology from S3: s3://{self.ontology_bucket}/{s3_key}")
            
            # Download ontology file from S3
            response = self.s3_client.get_object(Bucket=self.ontology_bucket, Key=s3_key)
            ontology_content = response['Body'].read().decode('utf-8')
            
            # Parse using RDFLib
            temp_graph = Graph()
            temp_graph.parse(data=ontology_content, format=format)
            
            # Clear existing ontology and load new one
            self.ontology_graph.remove((None, None, None))
            self.ontology_graph += temp_graph
            
            # Clear caches
            self._concept_cache.clear()
            self._relationship_cache.clear()
            self._ontology_loaded = True
            self._last_cache_update = datetime.now()
            
            self.logger.info(f"Successfully loaded ontology: {len(self.ontology_graph)} triples")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology from S3: {e}")
            raise KGDataFormatError(f"Ontology loading failed: {e}")
    
    def load_ontology_from_ttl(self, ttl_content: str, force_reload: bool = False) -> bool:
        """
        Load ontology from TTL content using RDFLib parsing
        
        Args:
            ttl_content: TTL content string
            force_reload: Force reload even if already loaded
            
        Returns:
            True if loading successful
        """
        try:
            if self._ontology_loaded and not force_reload:
                self.logger.debug("Ontology already loaded, skipping")
                return True
            
            self.logger.info("Loading ontology from TTL content")
            
            # Parse using RDFLib
            temp_graph = Graph()
            temp_graph.parse(data=ttl_content, format='turtle')
            
            # Clear existing ontology and load new one
            self.ontology_graph.remove((None, None, None))
            self.ontology_graph += temp_graph
            
            # Clear caches
            self._concept_cache.clear()
            self._relationship_cache.clear()
            self._ontology_loaded = True
            self._last_cache_update = datetime.now()
            
            self.logger.info(f"Successfully loaded ontology from TTL: {len(self.ontology_graph)} triples")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology from TTL: {e}")
            raise KGDataFormatError(f"Ontology TTL parsing failed: {e}")
    
    def get_concepts(self, concept_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get ontology concepts using RDFLib queries, optionally filtered by type
        
        Args:
            concept_type: Optional filter by concept type ('domain', 'process', etc.)
            
        Returns:
            List of concept dictionaries
        """
        try:
            self._ensure_ontology_loaded()
            
            # Check cache first
            cache_key = f"concepts_{concept_type or 'all'}"
            if self._is_cache_valid() and cache_key in self._concept_cache:
                return self._concept_cache[cache_key]
            
            concepts = []
            
            # Query ontology graph using RDFLib
            if concept_type:
                # Filter by specific type
                query_results = self.ontology_graph.query(f"""
                    SELECT ?concept ?label ?comment ?type
                    WHERE {{
                        ?concept rdf:type ?conceptClass .
                        ?concept rdfs:label ?label .
                        OPTIONAL {{ ?concept rdfs:comment ?comment }}
                        OPTIONAL {{ ?concept kr:conceptType ?type }}
                        FILTER(?type = "{concept_type}")
                    }}
                    ORDER BY ?label
                """)
            else:
                # Get all concepts
                query_results = self.ontology_graph.query("""
                    SELECT ?concept ?label ?comment ?type
                    WHERE {
                        ?concept rdf:type ?conceptClass .
                        ?concept rdfs:label ?label .
                        OPTIONAL { ?concept rdfs:comment ?comment }
                        OPTIONAL { ?concept kr:conceptType ?type }
                        FILTER(?conceptClass IN (owl:Class, skos:Concept, kr:DomainConcept, kr:ProcessConcept))
                    }
                    ORDER BY ?label
                """)
            
            # Process results
            for row in query_results:
                concept_dict = {
                    'uri': str(row.concept),
                    'label': str(row.label) if row.label else None,
                    'description': str(row.comment) if row.comment else None,
                    'type': str(row.type) if row.type else 'unknown'
                }
                concepts.append(concept_dict)
            
            # Cache results
            self._concept_cache[cache_key] = concepts
            
            self.logger.debug(f"Retrieved {len(concepts)} concepts (type: {concept_type or 'all'})")
            return concepts
            
        except Exception as e:
            self.logger.error(f"Error retrieving concepts: {e}")
            raise KGQueryError(f"Failed to get concepts: {e}")
    
    def get_concept_details(self, concept_uri: Union[str, URIRef]) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific concept using RDFLib queries
        
        Args:
            concept_uri: URI of the concept
            
        Returns:
            Concept details dictionary or None if not found
        """
        try:
            self._ensure_ontology_loaded()
            
            # Validate and convert URI
            if isinstance(concept_uri, str):
                concept_uri = URIRef(concept_uri)
            
            # Check cache first
            cache_key = f"concept_details_{concept_uri}"
            if self._is_cache_valid() and cache_key in self._concept_cache:
                return self._concept_cache[cache_key]
            
            # Query for concept details
            query_results = self.ontology_graph.query(f"""
                SELECT ?label ?comment ?type ?broader ?narrower ?related
                WHERE {{
                    OPTIONAL {{ <{concept_uri}> rdfs:label ?label }}
                    OPTIONAL {{ <{concept_uri}> rdfs:comment ?comment }}
                    OPTIONAL {{ <{concept_uri}> kr:conceptType ?type }}
                    OPTIONAL {{ <{concept_uri}> skos:broader ?broader }}
                    OPTIONAL {{ <{concept_uri}> skos:narrower ?narrower }}
                    OPTIONAL {{ <{concept_uri}> skos:related ?related }}
                }}
            """)
            
            # Process first result (should be unique)
            result_row = None
            for row in query_results:
                result_row = row
                break
            
            if not result_row:
                return None
            
            # Build concept details
            concept_details = {
                'uri': str(concept_uri),
                'label': str(result_row.label) if result_row.label else None,
                'description': str(result_row.comment) if result_row.comment else None,
                'type': str(result_row.type) if result_row.type else 'unknown',
                'broader_concepts': [],
                'narrower_concepts': [],
                'related_concepts': []
            }
            
            # Get hierarchical relationships
            for broader in self.ontology_graph.objects(concept_uri, SKOS.broader):
                concept_details['broader_concepts'].append(str(broader))
            
            for narrower in self.ontology_graph.objects(concept_uri, SKOS.narrower):
                concept_details['narrower_concepts'].append(str(narrower))
            
            for related in self.ontology_graph.objects(concept_uri, SKOS.related):
                concept_details['related_concepts'].append(str(related))
            
            # Cache results
            self._concept_cache[cache_key] = concept_details
            
            self.logger.debug(f"Retrieved concept details for: {concept_uri}")
            return concept_details
            
        except Exception as e:
            self.logger.error(f"Error retrieving concept details for {concept_uri}: {e}")
            raise KGQueryError(f"Failed to get concept details: {e}")
    
    def search_by_label(self, label: str, fuzzy: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search concepts by label using RDFLib text matching
        
        Args:
            label: Label text to search for
            fuzzy: Enable fuzzy matching (case-insensitive contains)
            limit: Maximum number of results
            
        Returns:
            List of matching concepts
        """
        try:
            self._ensure_ontology_loaded()
            
            if not label:
                raise KGValidationError("Search label cannot be empty")
            
            # Check cache first
            cache_key = f"search_{label}_{fuzzy}_{limit}"
            if self._is_cache_valid() and cache_key in self._concept_cache:
                return self._concept_cache[cache_key]
            
            matching_concepts = []
            
            # Search through all concepts with labels
            for concept, predicate, label_obj in self.ontology_graph.triples((None, RDFS.label, None)):
                label_text = str(label_obj)
                
                # Apply matching logic
                if fuzzy:
                    if label.lower() in label_text.lower():
                        # Get additional details
                        concept_type = None
                        description = None
                        
                        for _, _, type_obj in self.ontology_graph.triples((concept, self.kr_ns.conceptType, None)):
                            concept_type = str(type_obj)
                            break
                        
                        for _, _, desc_obj in self.ontology_graph.triples((concept, RDFS.comment, None)):
                            description = str(desc_obj)
                            break
                        
                        matching_concepts.append({
                            'uri': str(concept),
                            'label': label_text,
                            'description': description,
                            'type': concept_type or 'unknown',
                            'match_score': self._calculate_match_score(label, label_text)
                        })
                else:
                    if label == label_text:
                        # Exact match
                        concept_details = self.get_concept_details(concept)
                        if concept_details:
                            concept_details['match_score'] = 1.0
                            matching_concepts.append(concept_details)
            
            # Sort by match score and limit results
            matching_concepts.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            matching_concepts = matching_concepts[:limit]
            
            # Cache results
            self._concept_cache[cache_key] = matching_concepts
            
            self.logger.debug(f"Found {len(matching_concepts)} concepts matching '{label}'")
            return matching_concepts
            
        except Exception as e:
            self.logger.error(f"Error searching concepts by label '{label}': {e}")
            raise KGQueryError(f"Failed to search concepts: {e}")
    
    def get_relationships(self, concept_uri: Union[str, URIRef]) -> List[Dict[str, Any]]:
        """
        Get all relationships for a concept using RDFLib graph traversal
        
        Args:
            concept_uri: URI of the concept
            
        Returns:
            List of relationship dictionaries
        """
        try:
            self._ensure_ontology_loaded()
            
            # Validate and convert URI
            if isinstance(concept_uri, str):
                concept_uri = URIRef(concept_uri)
            
            # Check cache first
            cache_key = f"relationships_{concept_uri}"
            if self._is_cache_valid() and cache_key in self._relationship_cache:
                return self._relationship_cache[cache_key]
            
            relationships = []
            
            # Get all outgoing relationships
            for predicate, obj in self.ontology_graph.predicate_objects(concept_uri):
                if predicate in [SKOS.broader, SKOS.narrower, SKOS.related, self.kr_ns.relatedTo]:
                    relationship = {
                        'subject': str(concept_uri),
                        'predicate': str(predicate),
                        'object': str(obj),
                        'direction': 'outgoing',
                        'relationship_type': self._get_relationship_type(predicate)
                    }
                    relationships.append(relationship)
            
            # Get all incoming relationships
            for subj, predicate in self.ontology_graph.subject_predicates(concept_uri):
                if predicate in [SKOS.broader, SKOS.narrower, SKOS.related, self.kr_ns.relatedTo]:
                    relationship = {
                        'subject': str(subj),
                        'predicate': str(predicate),
                        'object': str(concept_uri),
                        'direction': 'incoming',
                        'relationship_type': self._get_relationship_type(predicate)
                    }
                    relationships.append(relationship)
            
            # Cache results
            self._relationship_cache[cache_key] = relationships
            
            self.logger.debug(f"Retrieved {len(relationships)} relationships for: {concept_uri}")
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error retrieving relationships for {concept_uri}: {e}")
            raise KGQueryError(f"Failed to get relationships: {e}")
    
    def validate_concept(self, concept_uri: Union[str, URIRef], ontology_concept: str) -> bool:
        """
        Validate that a concept exists in the ontology and matches the expected type
        
        Args:
            concept_uri: URI of the concept to validate
            ontology_concept: Expected ontology concept type
            
        Returns:
            True if concept is valid
        """
        try:
            self._ensure_ontology_loaded()
            
            # Validate and convert URI
            if isinstance(concept_uri, str):
                concept_uri = URIRef(concept_uri)
            
            # Check if concept exists in ontology
            concept_exists = (concept_uri, None, None) in self.ontology_graph
            
            if not concept_exists:
                self.logger.warning(f"Concept not found in ontology: {concept_uri}")
                return False
            
            # Check concept type if specified
            if ontology_concept:
                concept_details = self.get_concept_details(concept_uri)
                if concept_details and concept_details.get('type') != ontology_concept:
                    self.logger.warning(f"Concept type mismatch for {concept_uri}: expected {ontology_concept}, got {concept_details.get('type')}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating concept {concept_uri}: {e}")
            return False
    
    def _ensure_ontology_loaded(self):
        """Ensure ontology is loaded, attempt to load default if not"""
        if not self._ontology_loaded:
            # Try to load default ontology
            try:
                self.load_ontology_from_s3('climate-risk-ontology.ttl')
            except Exception as e:
                self.logger.warning(f"Could not load default ontology: {e}")
                # Create minimal ontology for testing
                self._create_minimal_ontology()
    
    def _create_minimal_ontology(self):
        """Create a minimal ontology for testing purposes"""
        self.logger.info("Creating minimal ontology for testing")
        
        # Add basic concept types
        self.ontology_graph.add((self.kr_ns.DomainConcept, RDF.type, OWL.Class))
        self.ontology_graph.add((self.kr_ns.ProcessConcept, RDF.type, OWL.Class))
        self.ontology_graph.add((self.kr_ns.Document, RDF.type, OWL.Class))
        self.ontology_graph.add((self.kr_ns.DocumentChunk, RDF.type, OWL.Class))
        
        # Add labels
        self.ontology_graph.add((self.kr_ns.DomainConcept, RDFS.label, Literal("Domain Concept")))
        self.ontology_graph.add((self.kr_ns.ProcessConcept, RDFS.label, Literal("Process Concept")))
        self.ontology_graph.add((self.kr_ns.Document, RDFS.label, Literal("Document")))
        self.ontology_graph.add((self.kr_ns.DocumentChunk, RDFS.label, Literal("Document Chunk")))
        
        self._ontology_loaded = True
        self.logger.info("Minimal ontology created")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on TTL"""
        if not self._last_cache_update:
            return False
        
        return (datetime.now() - self._last_cache_update).total_seconds() < self._cache_ttl
    
    def _calculate_match_score(self, search_term: str, label: str) -> float:
        """Calculate match score for fuzzy search"""
        search_lower = search_term.lower()
        label_lower = label.lower()
        
        if search_lower == label_lower:
            return 1.0
        elif label_lower.startswith(search_lower):
            return 0.8
        elif search_lower in label_lower:
            return 0.6
        else:
            # Calculate similarity based on common characters
            common_chars = set(search_lower) & set(label_lower)
            return len(common_chars) / max(len(search_lower), len(label_lower))
    
    def _get_relationship_type(self, predicate: URIRef) -> str:
        """Get human-readable relationship type from predicate"""
        predicate_map = {
            SKOS.broader: 'broader',
            SKOS.narrower: 'narrower',
            SKOS.related: 'related',
            self.kr_ns.relatedTo: 'related_to'
        }
        
        return predicate_map.get(predicate, 'unknown')
    
    def clear_cache(self):
        """Clear all cached data"""
        self._concept_cache.clear()
        self._relationship_cache.clear()
        self._last_cache_update = None
        self.logger.info("Ontology cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'concept_cache_size': len(self._concept_cache),
            'relationship_cache_size': len(self._relationship_cache),
            'cache_valid': self._is_cache_valid(),
            'last_update': self._last_cache_update.isoformat() if self._last_cache_update else None,
            'cache_ttl_seconds': self._cache_ttl
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ontology manager statistics"""
        return {
            'manager_type': 'OntologyManager',
            'rdflib_integration': True,
            'ontology_loaded': self._ontology_loaded,
            'ontology_triples': len(self.ontology_graph),
            'ontology_bucket': self.ontology_bucket,
            'cache_stats': self.get_cache_stats()
        }
