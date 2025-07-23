#!/usr/bin/env python3
"""
Ontology Manager - Handles ontology loading and concept operations
Provides interface for ontology concept retrieval and management
"""
import logging
from typing import Dict, List, Any, Optional
import json
import boto3
from .kg_exceptions import KGQueryError, KGValidationError

class OntologyManager:
    """Manages ontology concepts and relationships"""
    
    def __init__(self, kg_manager):
        """
        Initialize ontology manager
        
        Args:
            kg_manager: KnowledgeGraphManager instance for SPARQL operations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kg_manager = kg_manager
        self.uri_manager = kg_manager.uri_manager
        self.query_builder = kg_manager.query_builder
        
        # S3 client for ontology data loading
        self.s3_client = boto3.client('s3')
        
        # Configuration
        self.ontology_bucket = self._get_env_var('ONTOLOGY_BUCKET', 'solve-global-kr-dl-ontology-861276078413-us-east-1')
        self.ontology_graph_uri = self.uri_manager.mint_graph_uri('ontology', 'main')
        
        # Caching for performance
        self._concept_cache = {}
        self._relationship_cache = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
        
        self.logger.debug(f"OntologyManager initialized with bucket: {self.ontology_bucket}")
    
    def get_concepts(self, concept_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get ontology concepts, optionally filtered by type
        
        Args:
            concept_type: Optional filter by concept type ('domain' or 'range')
            
        Returns:
            List of concept dictionaries
        """
        try:
            # Check cache first
            cache_key = f"concepts_{concept_type or 'all'}"
            if cache_key in self._concept_cache:
                self.logger.debug(f"Returning cached concepts for type: {concept_type}")
                return self._concept_cache[cache_key]
            
            # Build and execute query
            query = self.query_builder.build_ontology_concepts_query(concept_type)
            results = self.kg_manager.execute_sparql_query(query)
            
            # Process results
            concepts = []
            for result in results:
                concept = {
                    'uri': result.get('concept', ''),
                    'label': result.get('label', ''),
                    'concept_type': result.get('conceptType', ''),
                    'description': result.get('description', '')
                }
                concepts.append(concept)
            
            # Cache results
            self._concept_cache[cache_key] = concepts
            
            self.logger.info(f"Retrieved {len(concepts)} concepts (type: {concept_type})")
            return concepts
            
        except Exception as e:
            self.logger.error(f"Error retrieving concepts: {e}")
            raise KGQueryError(f"Failed to retrieve concepts: {e}")
    
    def get_concept_details(self, concept_uri: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific concept
        
        Args:
            concept_uri: URI of the concept
            
        Returns:
            Concept details dictionary or None if not found
        """
        try:
            if not concept_uri:
                raise KGValidationError("Concept URI cannot be empty")
            
            if not self.uri_manager.is_valid_uri(concept_uri):
                raise KGValidationError(f"Invalid concept URI: {concept_uri}")
            
            # Check cache first
            if concept_uri in self._concept_cache:
                self.logger.debug(f"Returning cached concept details for: {concept_uri}")
                return self._concept_cache[concept_uri]
            
            # Build query for specific concept
            prefixes = self.uri_manager.get_prefixes_sparql()
            query = f"""
            {prefixes}
            
            SELECT ?label ?conceptType ?description ?broader ?narrower
            WHERE {{
                <{concept_uri}> rdfs:label ?label .
                
                OPTIONAL {{ <{concept_uri}> kcc:conceptType ?conceptType }}
                OPTIONAL {{ <{concept_uri}> rdfs:comment ?description }}
                OPTIONAL {{ <{concept_uri}> rdfs:subClassOf ?broader }}
                OPTIONAL {{ ?narrower rdfs:subClassOf <{concept_uri}> }}
            }}
            """
            
            results = self.kg_manager.execute_sparql_query(query)
            
            if not results:
                self.logger.warning(f"Concept not found: {concept_uri}")
                return None
            
            # Process first result (should be unique)
            result = results[0]
            concept_details = {
                'uri': concept_uri,
                'label': result.get('label', ''),
                'concept_type': result.get('conceptType', ''),
                'description': result.get('description', ''),
                'broader_concepts': [],
                'narrower_concepts': []
            }
            
            # Collect broader and narrower concepts from all results
            broader_concepts = set()
            narrower_concepts = set()
            
            for result in results:
                if result.get('broader'):
                    broader_concepts.add(result['broader'])
                if result.get('narrower'):
                    narrower_concepts.add(result['narrower'])
            
            concept_details['broader_concepts'] = list(broader_concepts)
            concept_details['narrower_concepts'] = list(narrower_concepts)
            
            # Cache result
            self._concept_cache[concept_uri] = concept_details
            
            self.logger.debug(f"Retrieved concept details for: {concept_uri}")
            return concept_details
            
        except Exception as e:
            self.logger.error(f"Error retrieving concept details for {concept_uri}: {e}")
            raise KGQueryError(f"Failed to retrieve concept details: {e}")
    
    def search_by_label(self, label: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        Search concepts by label with optional fuzzy matching
        
        Args:
            label: Label text to search for
            fuzzy: Enable fuzzy matching
            
        Returns:
            List of matching concepts
        """
        try:
            if not label:
                raise KGValidationError("Search label cannot be empty")
            
            # Escape label for SPARQL
            escaped_label = self.query_builder.escape_literal(label)
            
            # Build search query
            prefixes = self.uri_manager.get_prefixes_sparql()
            
            if fuzzy:
                # Use CONTAINS for fuzzy matching
                filter_clause = f'FILTER(CONTAINS(LCASE(?label), LCASE("{escaped_label}")))'
            else:
                # Exact match
                filter_clause = f'FILTER(?label = "{escaped_label}")'
            
            query = f"""
            {prefixes}
            
            SELECT DISTINCT ?concept ?label ?conceptType ?description
            WHERE {{
                ?concept rdfs:label ?label .
                {filter_clause}
                
                OPTIONAL {{ ?concept kcc:conceptType ?conceptType }}
                OPTIONAL {{ ?concept rdfs:comment ?description }}
            }}
            ORDER BY ?label
            LIMIT 50
            """
            
            results = self.kg_manager.execute_sparql_query(query)
            
            # Process results
            concepts = []
            for result in results:
                concept = {
                    'uri': result.get('concept', ''),
                    'label': result.get('label', ''),
                    'concept_type': result.get('conceptType', ''),
                    'description': result.get('description', ''),
                    'match_type': 'fuzzy' if fuzzy else 'exact'
                }
                concepts.append(concept)
            
            self.logger.info(f"Found {len(concepts)} concepts matching '{label}' (fuzzy: {fuzzy})")
            return concepts
            
        except Exception as e:
            self.logger.error(f"Error searching concepts by label '{label}': {e}")
            raise KGQueryError(f"Failed to search concepts: {e}")
    
    def get_relationships(self, concept_uri: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for a concept (domain/range properties)
        
        Args:
            concept_uri: URI of the concept
            
        Returns:
            List of relationship dictionaries
        """
        try:
            if not concept_uri:
                raise KGValidationError("Concept URI cannot be empty")
            
            if not self.uri_manager.is_valid_uri(concept_uri):
                raise KGValidationError(f"Invalid concept URI: {concept_uri}")
            
            # Check cache first
            cache_key = f"relationships_{concept_uri}"
            if cache_key in self._relationship_cache:
                self.logger.debug(f"Returning cached relationships for: {concept_uri}")
                return self._relationship_cache[cache_key]
            
            # Build and execute query
            query = self.query_builder.build_concept_relationships_query(concept_uri)
            results = self.kg_manager.execute_sparql_query(query)
            
            # Process results
            relationships = []
            for result in results:
                relationship = {
                    'property_uri': result.get('property', ''),
                    'property_label': result.get('propertyLabel', ''),
                    'related_concept_uri': result.get('relatedConcept', ''),
                    'related_concept_label': result.get('relatedLabel', ''),
                    'relationship_type': result.get('relationshipType', ''),  # 'domain' or 'range'
                    'concept_uri': concept_uri
                }
                relationships.append(relationship)
            
            # Cache results
            self._relationship_cache[cache_key] = relationships
            
            self.logger.info(f"Retrieved {len(relationships)} relationships for concept: {concept_uri}")
            return relationships
            
        except Exception as e:
            self.logger.error(f"Error retrieving relationships for {concept_uri}: {e}")
            raise KGQueryError(f"Failed to retrieve relationships: {e}")
    
    def load_ontology_from_s3(self, ontology_key: str) -> Dict[str, Any]:
        """
        Load ontology data from S3
        
        Args:
            ontology_key: S3 key for ontology file
            
        Returns:
            Ontology data dictionary
        """
        try:
            self.logger.info(f"Loading ontology from S3: {self.ontology_bucket}/{ontology_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.ontology_bucket,
                Key=ontology_key
            )
            
            content = response['Body'].read().decode('utf-8')
            
            # Try to parse as JSON first, then as TTL
            try:
                ontology_data = json.loads(content)
                self.logger.debug("Loaded ontology as JSON")
                return ontology_data
            except json.JSONDecodeError:
                # Assume TTL format
                self.logger.debug("Loading ontology as TTL")
                return {'ttl_content': content, 'format': 'ttl'}
            
        except Exception as e:
            self.logger.error(f"Error loading ontology from S3: {e}")
            raise KGQueryError(f"Failed to load ontology: {e}")
    
    def get_domain_concepts(self) -> List[Dict[str, Any]]:
        """
        Get all domain concepts from ontology
        
        Returns:
            List of domain concept dictionaries
        """
        return self.get_concepts(concept_type='domain')
    
    def get_range_concepts(self) -> List[Dict[str, Any]]:
        """
        Get all range concepts from ontology
        
        Returns:
            List of range concept dictionaries
        """
        return self.get_concepts(concept_type='range')
    
    def find_concept_by_label(self, label: str) -> Optional[Dict[str, Any]]:
        """
        Find a single concept by exact label match
        
        Args:
            label: Exact label to match
            
        Returns:
            Concept dictionary or None if not found
        """
        results = self.search_by_label(label, fuzzy=False)
        return results[0] if results else None
    
    def get_concept_hierarchy(self, concept_uri: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Get concept hierarchy (broader/narrower concepts) up to specified depth
        
        Args:
            concept_uri: URI of the root concept
            max_depth: Maximum depth to traverse
            
        Returns:
            Hierarchical concept structure
        """
        try:
            if not concept_uri:
                raise KGValidationError("Concept URI cannot be empty")
            
            if max_depth < 1:
                raise KGValidationError("Max depth must be at least 1")
            
            # Get root concept details
            root_concept = self.get_concept_details(concept_uri)
            if not root_concept:
                return {}
            
            # Build hierarchy recursively
            hierarchy = {
                'concept': root_concept,
                'broader': [],
                'narrower': []
            }
            
            # Get broader concepts (parents)
            if max_depth > 1:
                for broader_uri in root_concept.get('broader_concepts', []):
                    broader_hierarchy = self.get_concept_hierarchy(broader_uri, max_depth - 1)
                    if broader_hierarchy:
                        hierarchy['broader'].append(broader_hierarchy)
            
            # Get narrower concepts (children)
            if max_depth > 1:
                for narrower_uri in root_concept.get('narrower_concepts', []):
                    narrower_hierarchy = self.get_concept_hierarchy(narrower_uri, max_depth - 1)
                    if narrower_hierarchy:
                        hierarchy['narrower'].append(narrower_hierarchy)
            
            return hierarchy
            
        except Exception as e:
            self.logger.error(f"Error building concept hierarchy for {concept_uri}: {e}")
            raise KGQueryError(f"Failed to build concept hierarchy: {e}")
    
    def clear_cache(self):
        """Clear all cached ontology data"""
        self._concept_cache.clear()
        self._relationship_cache.clear()
        self.logger.info("Cleared ontology cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'concept_cache_size': len(self._concept_cache),
            'relationship_cache_size': len(self._relationship_cache),
            'total_cached_items': len(self._concept_cache) + len(self._relationship_cache)
        }
    
    def _get_env_var(self, var_name: str, default_value: str) -> str:
        """
        Get environment variable with default value
        
        Args:
            var_name: Environment variable name
            default_value: Default value if not set
            
        Returns:
            Environment variable value or default
        """
        import os
        return os.environ.get(var_name, default_value)
