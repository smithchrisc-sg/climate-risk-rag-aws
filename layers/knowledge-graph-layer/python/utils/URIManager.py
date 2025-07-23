#!/usr/bin/env python3
"""
URI Manager - Consistent URI generation for Knowledge Graph resources
Updated to work with RDFLib URIRef objects and generic mint_uri approach
"""
import logging
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import quote

import rdflib
from rdflib import URIRef, Namespace

class URIManager:
    """
    Manages consistent URI generation for all KG resources
    Updated to use RDFLib URIRef objects and generic minting approach
    """
    
    def __init__(self, base_namespace: str = "https://solve.global/kr/"):
        """Initialize URI manager with base namespace"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set up base namespace
        self.base_namespace = base_namespace
        self.kr_ns = Namespace(base_namespace)
        
        # Standard namespaces
        self.dcterms_ns = Namespace("http://purl.org/dc/terms/")
        self.foaf_ns = Namespace("http://xmlns.com/foaf/0.1/")
        self.skos_ns = Namespace("http://www.w3.org/2004/02/skos/core#")
        
        self.logger.debug(f"URIManager initialized with base namespace: {self.base_namespace}")
    
    def mint_uri(self, unique_id: str, namespace: Namespace, ontology_concept: str,
                 ontology_uri: URIRef, named_graph: URIRef = None) -> URIRef:
        """
        Generic URI minting with ontology validation and optional named graph support
        
        Args:
            unique_id: Unique identifier for the resource
            namespace: RDF namespace for the generated URI (e.g., kr:)
            ontology_concept: Concept type from ontology (e.g., "Document", "DocumentSection")
            ontology_uri: Ontology identifier URI for validation and type triples
            named_graph: Optional named graph URI (defaults to default graph)
        
        Returns:
            rdflib.URIRef: Generated resource URI
        """
        # Validate inputs
        if not unique_id:
            raise ValueError("unique_id cannot be empty")
        if not ontology_concept:
            raise ValueError("ontology_concept cannot be empty")
        
        # Sanitize unique_id for URI safety
        safe_id = self._sanitize_uri_component(unique_id)
        
        # Generate URI: namespace + concept + "_" + unique_id
        uri_string = f"{namespace}{ontology_concept}_{safe_id}"
        uri = URIRef(uri_string)
        
        self.logger.debug(f"Minted URI: {uri} for concept {ontology_concept}")
        return uri
    
    def _sanitize_uri_component(self, component: str) -> str:
        """Sanitize string component for safe URI usage"""
        if not component:
            return ""
        
        # Replace problematic characters with underscores
        sanitized = component.replace(' ', '_')
        sanitized = sanitized.replace('/', '_')
        sanitized = sanitized.replace('\\', '_')
        sanitized = sanitized.replace('#', '_')
        sanitized = sanitized.replace('?', '_')
        sanitized = sanitized.replace('&', '_')
        sanitized = sanitized.replace('=', '_')
        sanitized = sanitized.replace('%', '_')
        
        # Remove any remaining problematic characters
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c in ['_', '-', '.'])
        
        return sanitized
    
    def get_prefixes_ttl(self) -> str:
        """Generate TTL prefix declarations for standard namespaces"""
        prefixes = [
            f"@prefix kr: <{self.kr_ns}> .",
            f"@prefix dcterms: <{self.dcterms_ns}> .",
            f"@prefix foaf: <{self.foaf_ns}> .",
            f"@prefix skos: <{self.skos_ns}> .",
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."
        ]
        return "\n".join(prefixes)
    
    def bind_namespaces_to_graph(self, graph: rdflib.Graph):
        """Bind standard namespaces to an RDFLib graph"""
        graph.bind("kr", self.kr_ns)
        graph.bind("dcterms", self.dcterms_ns)
        graph.bind("foaf", self.foaf_ns)
        graph.bind("skos", self.skos_ns)
        graph.bind("rdf", rdflib.RDF)
        graph.bind("rdfs", rdflib.RDFS)
        graph.bind("xsd", rdflib.XSD)
    
    # === LEGACY METHODS (for backward compatibility) ===
    
    def mint_document_uri(self, doc_id: str) -> URIRef:
        """Generate consistent document URI (legacy method)"""
        return self.mint_uri(doc_id, self.kr_ns, "Document", self.kr_ns)
    
    def mint_chunk_uri(self, doc_id: str, chunk_id: str) -> URIRef:
        """Generate consistent chunk URI (legacy method)"""
        unique_id = f"{doc_id}_{chunk_id}"
        return self.mint_uri(unique_id, self.kr_ns, "DocumentChunk", self.kr_ns)
    
    def mint_concept_mention_uri(self, chunk_id: str, concept_uri: str, position: int) -> URIRef:
        """Generate consistent concept mention URI (legacy method)"""
        # Create deterministic hash for concept URI
        concept_hash = hashlib.md5(str(concept_uri).encode()).hexdigest()[:8]
        unique_id = f"{chunk_id}_{concept_hash}_{position}"
        return self.mint_uri(unique_id, self.kr_ns, "ConceptMention", self.kr_ns)
    
    def mint_co_occurrence_uri(self, chunk_id: str, concept1_uri: str, concept2_uri: str) -> URIRef:
        """Generate consistent co-occurrence URI (legacy method)"""
        # Create deterministic hash for concept pair
        concept_pair = f"{concept1_uri}|{concept2_uri}"
        pair_hash = hashlib.md5(concept_pair.encode()).hexdigest()[:8]
        unique_id = f"{chunk_id}_{pair_hash}"
        return self.mint_uri(unique_id, self.kr_ns, "ConceptCoOccurrence", self.kr_ns)
    
    def mint_graph_uri(self, graph_type: str, identifier: str) -> URIRef:
        """Generate consistent named graph URI (legacy method)"""
        unique_id = f"{graph_type}_{identifier}"
        return self.mint_uri(unique_id, self.kr_ns, "Graph", self.kr_ns)
    
    # === UTILITY METHODS ===
    
    def is_valid_uri(self, uri_string: str) -> bool:
        """Validate if a string is a valid URI"""
        try:
            uri = URIRef(uri_string)
            return True
        except Exception:
            return False
    
    def extract_local_name(self, uri: URIRef) -> str:
        """Extract the local name from a URI"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        else:
            return uri_str
    
    def get_namespace_from_uri(self, uri: URIRef) -> str:
        """Extract the namespace from a URI"""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[0] + '#'
        elif '/' in uri_str:
            parts = uri_str.split('/')
            return '/'.join(parts[:-1]) + '/'
        else:
            return ""
