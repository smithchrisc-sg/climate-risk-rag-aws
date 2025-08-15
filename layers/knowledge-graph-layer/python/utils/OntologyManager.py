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
from rdflib.namespace import RDF, RDFS, OWL, SKOS, DCTERMS, FOAF, XSD

from .kg_exceptions import KGQueryError, KGValidationError, KGDataFormatError

# =============================================================================
# GRAPH IRI CONSTANTS
# =============================================================================

# String constants for SPARQL queries and general use
GEONAMES_ONTOLOGY_GRAPH_IRI = "http://www.geonames.org/ontology"
GEONAMES_ONTOLOGY_DATA_GRAPH_IRI = "http://www.geonames.org/ontology/data"
CLIMATE_RISK_ONTOLOGY_GRAPH_IRI = "http://solve.global/knowledge-commons/climate-risk-ontology"
NEPTUNE_DEFAULT_GRAPH_IRI = "http://aws.amazon.com/neptune/vocab/v01/DefaultNamedGraph"

# RDFLib URIRef constants for RDFLib operations
GEONAMES_ONTOLOGY_GRAPH = URIRef(GEONAMES_ONTOLOGY_GRAPH_IRI)
GEONAMES_ONTOLOGY_DATA_GRAPH = URIRef(GEONAMES_ONTOLOGY_DATA_GRAPH_IRI)
CLIMATE_RISK_ONTOLOGY_GRAPH = URIRef(CLIMATE_RISK_ONTOLOGY_GRAPH_IRI)
NEPTUNE_DEFAULT_GRAPH = URIRef(NEPTUNE_DEFAULT_GRAPH_IRI)

# =============================================================================
# NAMESPACE PREFIX CONSTANTS
# =============================================================================

# String constants for SPARQL PREFIX declarations
GEONAMES_PREFIX_IRI = "http://www.geonames.org/ontology#"
CLIMATE_RISK_PREFIX_IRI = "https://solve.global/kr/"
SOLVE_GLOBAL_PREFIX_IRI = "https://solve.global/"

# RDFLib Namespace objects for RDFLib operations
GEONAMES_PREFIX = Namespace(GEONAMES_PREFIX_IRI)
CLIMATE_RISK_PREFIX = Namespace(CLIMATE_RISK_PREFIX_IRI)
SOLVE_GLOBAL_PREFIX = Namespace(SOLVE_GLOBAL_PREFIX_IRI)

# Common aliases for convenience
GN = GEONAMES_PREFIX
KR = CLIMATE_RISK_PREFIX
SG = SOLVE_GLOBAL_PREFIX

class OntologyManager:
    """Manages ontology concepts and relationships using RDFLib for proper RDF handling"""
    
    # Standard RDF namespace constants
    KR_NS = Namespace("https://solve.global/kr/")
    
    def __init__(self, kg_manager=None):
        """
        Initialize ontology manager with standard RDF namespaces
        
        Args:
            kg_manager: KnowledgeGraphManager instance for Neptune operations (optional for backward compatibility)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # KnowledgeGraphManager for Neptune operations
        self.kg_manager = kg_manager
        
        # S3 client for ontology data loading
        self.s3_client = boto3.client('s3')
        
        # Set up namespaces using standard constants
        self.kr_ns = self.KR_NS
        
        # Configuration
        self.ontology_bucket = self._get_env_var('ONTOLOGY_BUCKET', 'solve-global-kr-dl-ontology-861276078413-us-east-1')
        self.ontology_graph_uri = URIRef("https://solve.global/graphs/ontology")
        
        # RDFLib graph for ontology data (use ConjunctiveGraph for named graph support)
        from rdflib import ConjunctiveGraph
        self.ontology_graph = ConjunctiveGraph()
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
        self.ontology_graph.bind("dcterms", DCTERMS)
        self.ontology_graph.bind("foaf", FOAF)
        self.ontology_graph.bind("skos", SKOS)
        self.ontology_graph.bind("rdf", RDF)
        self.ontology_graph.bind("rdfs", RDFS)
        self.ontology_graph.bind("owl", OWL)
        
        self.logger.debug("Ontology namespaces configured")
    
    def _get_env_var(self, var_name: str, default: str) -> str:
        """Get environment variable with default"""
        import os
        return os.environ.get(var_name, default)
    
    def load_ontology_from_s3(self, s3_key: str, format: str = 'turtle', force_reload: bool = False, named_graph: str = None) -> bool:
        """
        Load ontology from S3 using RDFLib parsing
        
        Args:
            s3_key: S3 key for the ontology file
            format: RDF format ('turtle', 'xml', 'n3', 'json-ld')
            force_reload: Force reload even if already loaded
            named_graph: Optional named graph URI to load ontology into
            
        Returns:
            True if loading successful
        """
        try:
            if self._ontology_loaded and not force_reload:
                self.logger.debug("Ontology already loaded, skipping")
                return True
            
            # FIXME need to fix the caller, but also need to put the ontology into the bucket.  Need to consider whether we should really be retrieving it from Neptune via SPARQL query 
            # FIXME or if this is even needed anymore - we should be just doing alignment queries via SPARQL FTS queries. 
            self.logger.info(f"Loading ontology from S3: s3://{self.ontology_bucket}/{s3_key}")
            
            # Download ontology file from S3
            response = self.s3_client.get_object(Bucket=self.ontology_bucket, Key=s3_key)
            ontology_content = response['Body'].read().decode('utf-8')
            
            # Parse using RDFLib
            temp_graph = Graph()
            temp_graph.parse(data=ontology_content, format=format)
            
            # Handle named graph loading
            if named_graph:
                named_graph_uri = URIRef(named_graph)
                self.logger.info(f"Loading ontology into named graph: {named_graph}")
                
                # Get or create the named graph
                named_graph_obj = self.ontology_graph.get_context(named_graph_uri)
                
                # Clear existing named graph content
                named_graph_obj.remove((None, None, None))
                
                # Add triples to named graph
                for triple in temp_graph:
                    named_graph_obj.add(triple)
            else:
                # Clear existing ontology and load new one (default behavior)
                self.ontology_graph.remove((None, None, None))
                self.ontology_graph += temp_graph
            
            # Clear caches
            self._concept_cache.clear()
            self._relationship_cache.clear()
            self._ontology_loaded = True
            self._last_cache_update = datetime.now()
            
            graph_info = f"named graph {named_graph}" if named_graph else "default graph"
            self.logger.info(f"Successfully loaded ontology into {graph_info}: {len(temp_graph)} triples")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology from S3: {e}")
            raise KGDataFormatError(f"Ontology loading failed: {e}")
    
    def load_ontology_from_ttl(self, ttl_content: str, force_reload: bool = False, named_graph: str = None) -> bool:
        """
        Load ontology from TTL content using RDFLib parsing
        
        Args:
            ttl_content: TTL content string
            force_reload: Force reload even if already loaded
            named_graph: Optional named graph URI to load ontology into
            
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
            
            # Handle named graph loading
            if named_graph:
                named_graph_uri = URIRef(named_graph)
                self.logger.info(f"Loading TTL ontology into named graph: {named_graph}")
                
                # Get or create the named graph
                named_graph_obj = self.ontology_graph.get_context(named_graph_uri)
                
                # Clear existing named graph content
                named_graph_obj.remove((None, None, None))
                
                # Add triples to named graph
                for triple in temp_graph:
                    named_graph_obj.add(triple)
            else:
                # Clear existing ontology and load new one (default behavior)
                self.ontology_graph.remove((None, None, None))
                self.ontology_graph += temp_graph
            
            # Clear caches
            self._concept_cache.clear()
            self._relationship_cache.clear()
            self._ontology_loaded = True
            self._last_cache_update = datetime.now()
            
            graph_info = f"named graph {named_graph}" if named_graph else "default graph"
            self.logger.info(f"Successfully loaded TTL ontology into {graph_info}: {len(temp_graph)} triples")
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
    
    def load_ontology_from_url(self, url: str, format: str = 'turtle', force_reload: bool = False, named_graph: str = None) -> bool:
        """
        Load ontology from a URL
        
        Args:
            url: URL to load ontology from
            format: RDF format (turtle, xml, n3, etc.)
            force_reload: Force reload even if already loaded
            named_graph: Optional named graph URI
            
        Returns:
            True if loading successful
        """
        try:
            if self._ontology_loaded and not force_reload:
                self.logger.debug("Ontology already loaded, skipping")
                return True
            
            self.logger.info(f"Loading ontology from URL: {url}")
            
            # Parse using RDFLib
            temp_graph = Graph()
            temp_graph.parse(url, format=format)
            
            # Handle named graph loading
            if named_graph:
                named_graph_uri = URIRef(named_graph)
                self.logger.info(f"Loading URL ontology into named graph: {named_graph}")
                
                # Get or create the named graph
                named_graph_obj = self.ontology_graph.get_context(named_graph_uri)
                
                # Add triples to the named graph
                for triple in temp_graph:
                    named_graph_obj.add(triple)
                    
                self.logger.info(f"Added {len(temp_graph)} triples to named graph {named_graph}")
            else:
                # Add to default graph
                self.ontology_graph += temp_graph
                self.logger.info(f"Added {len(temp_graph)} triples to default graph")
            
            self._ontology_loaded = True
            self._invalidate_cache()
            
            self.logger.info(f"Successfully loaded ontology from URL: {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology from URL {url}: {e}")
            return False
    
    def load_ontology_from_file(self, file_path: str, format: str = 'turtle', force_reload: bool = False, named_graph: str = None) -> bool:
        """
        Load ontology from a local file
        
        Args:
            file_path: Path to the ontology file
            format: RDF format (turtle, xml, n3, etc.)
            force_reload: Force reload even if already loaded
            named_graph: Optional named graph URI
            
        Returns:
            True if loading successful
        """
        try:
            if self._ontology_loaded and not force_reload:
                self.logger.debug("Ontology already loaded, skipping")
                return True
            
            self.logger.info(f"Loading ontology from file: {file_path}")
            
            # Check if file exists
            import os
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Ontology file not found: {file_path}")
            
            # Parse using RDFLib
            temp_graph = Graph()
            temp_graph.parse(file_path, format=format)
            
            # Handle named graph loading
            if named_graph:
                named_graph_uri = URIRef(named_graph)
                self.logger.info(f"Loading file ontology into named graph: {named_graph}")
                
                # Get or create the named graph
                named_graph_obj = self.ontology_graph.get_context(named_graph_uri)
                
                # Add triples to the named graph
                for triple in temp_graph:
                    named_graph_obj.add(triple)
                    
                self.logger.info(f"Added {len(temp_graph)} triples to named graph {named_graph}")
            else:
                # Add to default graph
                self.ontology_graph += temp_graph
                self.logger.info(f"Added {len(temp_graph)} triples to default graph")
            
            self._ontology_loaded = True
            self._invalidate_cache()
            
            self.logger.info(f"Successfully loaded ontology from file: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology from file {file_path}: {e}")
            return False

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
    
    def list_ontologies(self) -> List[Dict[str, Any]]:
        """
        List available ontologies with metadata and priority ordering.
        
        Returns:
            List of ontology metadata with search configuration:
            [
                {
                    'id': 'climate-risk',
                    'domain': 'climate', 
                    'priority': 1,
                    'version': 'v3',
                    'search_fields': ['rdfs:label', 'skos:prefLabel', 'skos:altLabel', 'cro:description'],
                    'entity_types': ['ORGANIZATION', 'EVENT', 'OTHER'],
                    'graph_context': '<http://climate-risk-ontology>',
                    'fts_enabled': True
                },
                {
                    'id': 'geonames',
                    'domain': 'geography',
                    'priority': 2, 
                    'version': 'latest',
                    'search_fields': ['gn:name', 'gn:alternateName', 'gn:asciiname'],
                    'entity_types': ['LOCATION'],
                    'graph_context': f'<{GEONAMES_ONTOLOGY_DATA_GRAPH_IRI}>',
                    'fts_enabled': True
                }
            ]
        """
        try:
            ontology_configs = {
                'climate-risk': {
                    'id': 'climate-risk',
                    'domain': 'climate',
                    'priority': 1,
                    'version': 'v3',
                    'search_fields': ['rdfs:label', 'skos:prefLabel', 'skos:altLabel', 'cro:description'],
                    'entity_types': ['ORGANIZATION', 'EVENT', 'OTHER'],
                    'graph_context': '<http://climate-risk-ontology>',
                    'fts_enabled': True,
                    'neptune_endpoint': self._get_env_var('NEPTUNE_ENDPOINT', ''),
                    'multilanguage_enabled': False
                },
                'geonames': {
                    'id': 'geonames',
                    'domain': 'geography', 
                    'priority': 2,
                    'version': 'latest',
                    'search_fields': ['gn:name', 'gn:alternateName', 'gn:asciiname'],
                    'entity_types': ['LOCATION'],
                    'graph_context': f'<{GEONAMES_ONTOLOGY_DATA_GRAPH_IRI}>',
                    'fts_enabled': True,
                    'neptune_endpoint': self._get_env_var('NEPTUNE_ENDPOINT', ''),
                    'multilanguage_enabled': True
                }
            }
            
            # Return as sorted list by priority
            ontology_list = list(ontology_configs.values())
            ontology_list.sort(key=lambda x: x['priority'])
            
            self.logger.debug(f"Listed {len(ontology_list)} available ontologies")
            return ontology_list
            
        except Exception as e:
            self.logger.error(f"Failed to list ontologies: {str(e)}")
            raise KGQueryError(f"Ontology listing failed: {str(e)}")
    
    def load_ontology(self, ontology_id: str) -> Dict[str, Any]:
        """
        Load specific ontology by ID using Neptune-FTS integration.
        
        Args:
            ontology_id: Ontology identifier ('climate-risk', 'geonames', etc.)
            
        Returns:
            Loaded ontology metadata and status
        """
        try:
            # Get ontology configuration
            available_ontologies = self.list_ontologies()
            ontology_config = None
            
            for config in available_ontologies:
                if config['id'] == ontology_id:
                    ontology_config = config
                    break
            
            if not ontology_config:
                raise KGValidationError(f"Unknown ontology ID: {ontology_id}")
            
            # For now, return the configuration as "loaded"
            # In a full implementation, this would load the ontology data into Neptune
            # if not already present, but since we're using existing Neptune data,
            # we assume ontologies are already loaded
            
            self.logger.info(f"Loaded ontology: {ontology_id}")
            
            return {
                'ontology_id': ontology_id,
                'status': 'loaded',
                'config': ontology_config,
                'fts_ready': ontology_config.get('fts_enabled', False),
                'load_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load ontology {ontology_id}: {str(e)}")
            raise KGQueryError(f"Ontology loading failed: {str(e)}")
    
    def search_ontology_specific(self, ontology_id: str, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search within specific ontology using Neptune FTS.
        
        Args:
            ontology_id: Target ontology ID ('climate-risk', 'geonames')
            search_term: Search query text
            limit: Maximum results to return
            
        Returns:
            List of matching concepts with relevance scores
        """
        try:
            # Get ontology configuration
            available_ontologies = self.list_ontologies()
            ontology_config = None
            
            for config in available_ontologies:
                if config['id'] == ontology_id:
                    ontology_config = config
                    break
            
            if not ontology_config:
                raise KGValidationError(f"Unknown ontology ID: {ontology_id}")
            
            if not ontology_config.get('fts_enabled', False):
                raise KGValidationError(f"FTS not enabled for ontology: {ontology_id}")
            
            # Build search fields string
            search_fields = ' '.join(ontology_config['search_fields'])
            
            # Escape special characters in search term
            escaped_term = self._escape_fts_query(search_term)
            
            # Build Neptune FTS SPARQL query
            query = f"""
            PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX cro: <http://climate-risk-ontology#>
            PREFIX gn: <http://www.geonames.org/ontology#>
            
            SELECT ?concept ?label ?type ?description ?score
            FROM {ontology_config['graph_context']}
            WHERE {{
                ?concept ?labelProp ?label .
                OPTIONAL {{ ?concept rdf:type ?type }}
                OPTIONAL {{ ?concept rdfs:comment|cro:description|gn:featureClass ?description }}
                FILTER(neptune-fts:query(
                    neptune-fts:field('{search_fields}'), 
                    '{escaped_term}'
                ))
                BIND(neptune-fts:score() AS ?score)
            }}
            ORDER BY DESC(?score)
            LIMIT {limit}
            """
            
            # Execute SPARQL query (this would use existing Neptune connection)
            results = self._execute_sparql_query(query)
            
            # Convert to standardized format
            standardized_results = []
            for result in results:
                standardized_results.append({
                    'concept': result.get('concept', {}).get('value', ''),
                    'label': result.get('label', {}).get('value', ''),
                    'type': result.get('type', {}).get('value', ''),
                    'description': result.get('description', {}).get('value', ''),
                    'score': float(result.get('score', {}).get('value', 0.0)),
                    'ontology_id': ontology_id,
                    'search_term': search_term,
                    'matching_method': 'neptune-fts'
                })
            
            self.logger.info(f"Found {len(standardized_results)} results for '{search_term}' in {ontology_id}")
            return standardized_results
            
        except Exception as e:
            self.logger.error(f"FTS search failed for {ontology_id} with term '{search_term}': {str(e)}")
            raise KGQueryError(f"Ontology search failed: {str(e)}")
    
    def _escape_fts_query(self, query_text: str) -> str:
        """
        Escape special characters for Neptune FTS queries.
        
        Args:
            query_text: Raw search text
            
        Returns:
            Escaped query text safe for FTS
        """
        # Characters that need escaping in FTS queries
        # Note: backslash must be escaped first to avoid double-escaping
        special_chars = ['\\', ':', '(', ')', '[', ']', '{', '}', '~', '^', '"', '+', '-', '!']
        
        escaped = query_text
        for char in special_chars:
            escaped = escaped.replace(char, f'\\{char}')
        
        return escaped
    
    def _execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SPARQL query against Neptune endpoint using KnowledgeGraphManager.
        
        Args:
            query: SPARQL query string
            
        Returns:
            Query results in standard format
        """
        try:
            if not self.kg_manager:
                self.logger.warning("No KnowledgeGraphManager available - returning empty results")
                return []
            
            self.logger.debug(f"Executing SPARQL query via KnowledgeGraphManager: {query[:100]}...")
            
            # Use KnowledgeGraphManager to execute the query
            results = self.kg_manager.execute_sparql_query(query)
            
            # KnowledgeGraphManager returns results in the format we expect
            if isinstance(results, dict) and 'results' in results and 'bindings' in results['results']:
                return results['results']['bindings']
            elif isinstance(results, list):
                return results
            else:
                self.logger.warning(f"Unexpected query result format: {type(results)}")
                return []
                
        except Exception as e:
            self.logger.error(f"SPARQL query execution failed: {str(e)}")
            raise KGQueryError(f"SPARQL query failed: {str(e)}")

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
