#!/usr/bin/env python3
"""
URI Manager - Consistent URI generation for knowledge graph entities
Ensures all URIs follow consistent patterns across the system
"""
import hashlib
import re
from typing import Optional
from urllib.parse import quote
import logging

class URIManager:
    """Manages consistent URI generation across the knowledge graph"""
    
    def __init__(self, base_namespace: Optional[str] = None):
        """
        Initialize URI manager with configurable base namespace
        
        Args:
            base_namespace: Base namespace for all URIs (defaults to solve.global)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Base namespaces - configurable for different environments
        self.base_namespace = base_namespace or "http://solve.global/knowledge-commons/"
        self.document_namespace = f"{self.base_namespace}document/"
        self.chunk_namespace = f"{self.base_namespace}chunk/"
        self.mention_namespace = f"{self.base_namespace}mention/"
        self.co_occurrence_namespace = f"{self.base_namespace}co-occurrence/"
        self.ontology_namespace = f"{self.base_namespace}ontology/"
        
        # Common prefixes for TTL generation
        self.prefixes = {
            'kcc': self.base_namespace,
            'doc': self.document_namespace,
            'chunk': self.chunk_namespace,
            'mention': self.mention_namespace,
            'cooc': self.co_occurrence_namespace,
            'ont': self.ontology_namespace
        }
        
        self.logger.debug(f"URIManager initialized with base namespace: {self.base_namespace}")
    
    def mint_document_uri(self, doc_id: str) -> str:
        """
        Generate consistent document URI
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Consistent document URI
        """
        if not doc_id:
            raise ValueError("Document ID cannot be empty")
        
        clean_id = self._clean_identifier(doc_id)
        uri = f"{self.document_namespace}{clean_id}"
        self.logger.debug(f"Minted document URI: {uri}")
        return uri
    
    def mint_chunk_uri(self, doc_id: str, chunk_id: str) -> str:
        """
        Generate consistent chunk URI
        
        Args:
            doc_id: Document identifier
            chunk_id: Chunk identifier
            
        Returns:
            Consistent chunk URI
        """
        if not doc_id or not chunk_id:
            raise ValueError("Document ID and Chunk ID cannot be empty")
        
        clean_doc_id = self._clean_identifier(doc_id)
        clean_chunk_id = self._clean_identifier(chunk_id)
        uri = f"{self.chunk_namespace}{clean_doc_id}/{clean_chunk_id}"
        self.logger.debug(f"Minted chunk URI: {uri}")
        return uri
    
    def mint_concept_mention_uri(self, chunk_id: str, concept_uri: str, position: int) -> str:
        """
        Generate consistent concept mention URI
        
        Args:
            chunk_id: Chunk identifier
            concept_uri: Concept URI being mentioned
            position: Position in text (start offset)
            
        Returns:
            Consistent concept mention URI
        """
        if not chunk_id or not concept_uri:
            raise ValueError("Chunk ID and Concept URI cannot be empty")
        
        # Create deterministic hash from chunk + concept + position
        content = f"{chunk_id}#{concept_uri}#{position}"
        mention_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        uri = f"{self.mention_namespace}{mention_hash}"
        self.logger.debug(f"Minted concept mention URI: {uri}")
        return uri
    
    def mint_co_occurrence_uri(self, chunk_id: str, concept1_uri: str, concept2_uri: str) -> str:
        """
        Generate consistent co-occurrence URI
        
        Args:
            chunk_id: Chunk identifier
            concept1_uri: First concept URI
            concept2_uri: Second concept URI
            
        Returns:
            Consistent co-occurrence URI
        """
        if not chunk_id or not concept1_uri or not concept2_uri:
            raise ValueError("Chunk ID and both Concept URIs cannot be empty")
        
        # Sort concepts for consistent ordering regardless of input order
        concepts = sorted([concept1_uri, concept2_uri])
        content = f"{chunk_id}#{concepts[0]}#{concepts[1]}"
        cooc_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        uri = f"{self.co_occurrence_namespace}{cooc_hash}"
        self.logger.debug(f"Minted co-occurrence URI: {uri}")
        return uri
    
    def mint_graph_uri(self, graph_type: str, identifier: str) -> str:
        """
        Generate consistent named graph URI
        
        Args:
            graph_type: Type of graph (e.g., 'document', 'ontology', 'inference')
            identifier: Graph identifier
            
        Returns:
            Consistent named graph URI
        """
        if not graph_type or not identifier:
            raise ValueError("Graph type and identifier cannot be empty")
        
        clean_type = self._clean_identifier(graph_type)
        clean_id = self._clean_identifier(identifier)
        uri = f"{self.base_namespace}graph/{clean_type}/{clean_id}"
        self.logger.debug(f"Minted graph URI: {uri}")
        return uri
    
    def get_prefixes_ttl(self) -> str:
        """
        Get TTL prefix declarations for use in SPARQL queries and TTL files
        
        Returns:
            TTL prefix declarations
        """
        prefixes = []
        for prefix, namespace in self.prefixes.items():
            prefixes.append(f"@prefix {prefix}: <{namespace}> .")
        
        # Add common RDF prefixes
        prefixes.extend([
            "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix dcterms: <http://purl.org/dc/terms/> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."
        ])
        
        return "\n".join(prefixes)
    
    def get_prefixes_sparql(self) -> str:
        """
        Get SPARQL prefix declarations for use in SPARQL queries
        
        Returns:
            SPARQL prefix declarations
        """
        prefixes = []
        for prefix, namespace in self.prefixes.items():
            prefixes.append(f"PREFIX {prefix}: <{namespace}>")
        
        # Add common RDF prefixes
        prefixes.extend([
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>",
            "PREFIX dcterms: <http://purl.org/dc/terms/>",
            "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"
        ])
        
        return "\n".join(prefixes)
    
    def extract_local_name(self, uri: str) -> str:
        """
        Extract local name from URI (part after last # or /)
        
        Args:
            uri: Full URI
            
        Returns:
            Local name portion of URI
        """
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        else:
            return uri
    
    def is_valid_uri(self, uri: str) -> bool:
        """
        Validate URI format
        
        Args:
            uri: URI to validate
            
        Returns:
            True if URI is valid format
        """
        # Basic URI validation - starts with http/https and contains valid characters
        uri_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(uri_pattern.match(uri))
    
    def _clean_identifier(self, identifier: str) -> str:
        """
        Clean identifier for URI usage
        
        Args:
            identifier: Raw identifier
            
        Returns:
            Cleaned identifier safe for URI usage
        """
        if not identifier:
            raise ValueError("Identifier cannot be empty")
        
        # Replace problematic characters
        cleaned = identifier.replace(' ', '_').replace('#', '_').replace('?', '_')
        
        # Remove any remaining problematic characters
        cleaned = re.sub(r'[^\w\-_.]', '_', cleaned)
        
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        # URL encode for safety
        return quote(cleaned, safe='_-.')
    
    def validate_namespace_consistency(self, uri: str) -> bool:
        """
        Validate that URI uses consistent namespace
        
        Args:
            uri: URI to validate
            
        Returns:
            True if URI uses expected namespace
        """
        return uri.startswith(self.base_namespace)
    
    def get_namespace_info(self) -> dict:
        """
        Get information about configured namespaces
        
        Returns:
            Dictionary with namespace information
        """
        return {
            'base_namespace': self.base_namespace,
            'document_namespace': self.document_namespace,
            'chunk_namespace': self.chunk_namespace,
            'mention_namespace': self.mention_namespace,
            'co_occurrence_namespace': self.co_occurrence_namespace,
            'ontology_namespace': self.ontology_namespace,
            'prefixes': self.prefixes
        }
