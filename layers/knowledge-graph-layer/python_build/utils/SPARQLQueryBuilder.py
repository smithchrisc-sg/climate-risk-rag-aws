#!/usr/bin/env python3
"""
SPARQL Query Builder - Consistent SPARQL query construction with RDFLib integration
Provides reusable query patterns and prevents SPARQL injection using proper RDF handling
"""
import logging
from typing import List, Dict, Any, Optional, Union
import re

# RDFLib imports for proper URI handling
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

from .URIManager import URIManager
from .kg_exceptions import KGValidationError

class SPARQLQueryBuilder:
    """Builds consistent SPARQL queries for common knowledge graph operations with RDFLib integration"""
    
    def __init__(self, uri_manager: Optional[URIManager] = None):
        """
        Initialize query builder with RDFLib integration
        
        Args:
            uri_manager: URIManager instance for consistent URI handling
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.uri_manager = uri_manager or URIManager()
        
        # Set up namespaces using RDFLib
        self.kr_ns = Namespace("https://solve.global/kr/")
        self.dcterms_ns = Namespace("http://purl.org/dc/terms/")
        self.foaf_ns = Namespace("http://xmlns.com/foaf/0.1/")
        self.skos_ns = Namespace("http://www.w3.org/2004/02/skos/core#")
        
        # Build prefixes for SPARQL queries
        self.prefixes = self._build_sparql_prefixes()
        
        self.logger.debug("SPARQLQueryBuilder initialized with RDFLib integration")
        
    def _build_sparql_prefixes(self) -> str:
        """Build SPARQL prefix declarations using RDFLib namespaces"""
        return f"""
        PREFIX kr: <{self.kr_ns}>
        PREFIX dcterms: <{self.dcterms_ns}>
        PREFIX foaf: <{self.foaf_ns}>
        PREFIX skos: <{self.skos_ns}>
        PREFIX rdf: <{RDF}>
        PREFIX rdfs: <{RDFS}>
        PREFIX xsd: <{XSD}>
        """
    
    def validate_uri(self, uri: Union[str, URIRef]) -> URIRef:
        """
        Validate and convert URI to RDFLib URIRef
        
        Args:
            uri: URI string or URIRef to validate
            
        Returns:
            Validated URIRef object
            
        Raises:
            KGValidationError: If URI is invalid
        """
        try:
            if isinstance(uri, URIRef):
                return uri
            elif isinstance(uri, str):
                # Use RDFLib to validate URI format
                uri_ref = URIRef(uri)
                # Additional validation - must be absolute URI
                if not uri.startswith(('http://', 'https://', 'urn:')):
                    raise KGValidationError(f"URI must be absolute: {uri}")
                return uri_ref
            else:
                raise KGValidationError(f"URI must be string or URIRef, got: {type(uri)}")
                
        except Exception as e:
            raise KGValidationError(f"Invalid URI format: {uri} - {e}")
    
    def validate_uris(self, uris: List[Union[str, URIRef]]) -> List[URIRef]:
        """
        Validate a list of URIs
        
        Args:
            uris: List of URI strings or URIRefs to validate
            
        Returns:
            List of validated URIRef objects
        """
        if not uris:
            raise KGValidationError("URI list cannot be empty")
        
        validated_uris = []
        for uri in uris:
            validated_uris.append(self.validate_uri(uri))
        
        return validated_uris
    
    def escape_literal(self, text: str) -> str:
        """
        Escape string literal for safe SPARQL usage
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for SPARQL
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Use RDFLib Literal to handle proper escaping
        literal = Literal(text)
        # Get the N3 representation which properly escapes the content
        escaped = literal.n3()
        
        # Remove the surrounding quotes since we'll add them in the query
        if escaped.startswith('"') and escaped.endswith('"'):
            escaped = escaped[1:-1]
        
        return escaped
    
    def build_document_concept_query(self, concept_uris: List[Union[str, URIRef]], limit: int = 100) -> str:
        """
        Build query to find documents containing specific concepts
        
        Args:
            concept_uris: List of concept URIs to search for
            limit: Maximum number of results
            
        Returns:
            SPARQL SELECT query
        """
        # Validate URIs using RDFLib
        validated_uris = self.validate_uris(concept_uris)
        
        # Build VALUES clause for concepts using proper URI formatting
        concept_values = " ".join([f"<{uri}>" for uri in validated_uris])
        
        query = f"""
        {self.prefixes}
        
        SELECT DISTINCT ?document ?documentTitle ?conceptCount
        WHERE {{
            VALUES ?concept {{ {concept_values} }}
            
            ?chunk kr:mentionsConcept ?concept ;
                   dcterms:isPartOf ?document .
            
            OPTIONAL {{ ?document dcterms:title ?documentTitle }}
            
            # Count concepts per document
            {{
                SELECT ?document (COUNT(DISTINCT ?concept) AS ?conceptCount)
                WHERE {{
                    VALUES ?concept {{ {concept_values} }}
                    ?chunk kr:mentionsConcept ?concept ;
                           dcterms:isPartOf ?document .
                }}
                GROUP BY ?document
            }}
        }}
        ORDER BY DESC(?conceptCount) ?documentTitle
        LIMIT {limit}
        """
        
        self.logger.debug(f"Built document concept query for {len(validated_uris)} concepts")
        return query.strip()
    
    def build_co_occurrence_query(self, concept_uri: Union[str, URIRef], limit: int = 50) -> str:
        """
        Build query to find concepts that co-occur with a given concept
        
        Args:
            concept_uri: URI of the concept
            limit: Maximum number of results
            
        Returns:
            SPARQL SELECT query
        """
        # Validate URI using RDFLib
        validated_uri = self.validate_uri(concept_uri)
        
        query = f"""
        {self.prefixes}
        
        SELECT ?coOccurringConcept ?conceptText ?confidence ?chunkId ?document
        WHERE {{
            # Find co-occurrences where our concept is concept1
            {{
                ?cooc kr:hasConcept1 <{validated_uri}> ;
                      kr:hasConcept2 ?coOccurringConcept ;
                      kr:confidence ?confidence .
            }}
            UNION
            # Find co-occurrences where our concept is concept2
            {{
                ?cooc kr:hasConcept2 <{validated_uri}> ;
                      kr:hasConcept1 ?coOccurringConcept ;
                      kr:confidence ?confidence .
            }}
            
            # Get additional information about the co-occurring concept
            ?chunk kr:hasConceptMention ?mention .
            ?mention kr:hasConcept ?coOccurringConcept ;
                     kr:hasText ?conceptText .
            
            # Get chunk and document information
            ?chunk dcterms:isPartOf ?document .
            BIND(STRAFTER(STR(?chunk), "chunk/") AS ?chunkId)
        }}
        ORDER BY DESC(?confidence)
        LIMIT {limit}
        """
        
        self.logger.debug(f"Built co-occurrence query for concept: {validated_uri}")
        return query.strip()
    
    def build_document_summary_query(self, doc_id: str) -> str:
        """
        Build query to get concept summary for a document
        
        Args:
            doc_id: Document identifier
            
        Returns:
            SPARQL SELECT query
        """
        if not doc_id:
            raise KGValidationError("Document ID cannot be empty")
        
        # Generate document URI using URIManager
        doc_uri = self.uri_manager.mint_uri(
            unique_id=doc_id,
            namespace=self.kr_ns,
            ontology_concept="Document",
            ontology_uri=self.kr_ns
        )
        
        query = f"""
        {self.prefixes}
        
        SELECT ?concept ?conceptText ?conceptType ?confidence ?chunkCount
        WHERE {{
            <{doc_uri}> ^dcterms:isPartOf ?chunk .
            
            ?chunk kr:hasConceptMention ?mention .
            ?mention kr:hasConcept ?concept ;
                     kr:hasText ?conceptText ;
                     kr:conceptType ?conceptType ;
                     kr:confidence ?confidence .
            
            # Count chunks containing this concept
            {{
                SELECT ?concept (COUNT(DISTINCT ?chunk) AS ?chunkCount)
                WHERE {{
                    <{doc_uri}> ^dcterms:isPartOf ?chunk .
                    ?chunk kr:mentionsConcept ?concept .
                }}
                GROUP BY ?concept
            }}
        }}
        ORDER BY DESC(?confidence) DESC(?chunkCount)
        """
        
        self.logger.debug(f"Built document summary query for: {doc_id}")
        return query.strip()
    
    def build_chunk_concept_search(self, concept_uri: Union[str, URIRef], confidence_threshold: float = 0.5) -> str:
        """
        Build query to search chunks containing a specific concept above confidence threshold
        
        Args:
            concept_uri: Concept URI to search for
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            SPARQL SELECT query
        """
        # Validate URI and confidence threshold
        validated_uri = self.validate_uri(concept_uri)
        
        if not 0 <= confidence_threshold <= 1:
            raise KGValidationError("Confidence threshold must be between 0 and 1")
        
        query = f"""
        {self.prefixes}
        
        SELECT ?chunk ?document ?conceptText ?confidence ?startPosition ?endPosition
        WHERE {{
            ?chunk kr:mentionsConcept <{validated_uri}> ;
                   dcterms:isPartOf ?document .
            
            ?chunk kr:hasConceptMention ?mention .
            ?mention kr:hasConcept <{validated_uri}> ;
                     kr:hasText ?conceptText ;
                     kr:confidence ?confidence ;
                     kr:startPosition ?startPosition ;
                     kr:endPosition ?endPosition .
            
            FILTER(?confidence >= {confidence_threshold})
        }}
        ORDER BY DESC(?confidence) ?document ?startPosition
        """
        
        self.logger.debug(f"Built chunk concept search for: {validated_uri} (threshold: {confidence_threshold})")
        return query.strip()
    
    def build_insert_document_query(self, doc_uri: URIRef, metadata: Dict[str, Any], 
                                   graph_uri: Optional[URIRef] = None) -> str:
        """
        Build SPARQL INSERT query for document metadata using RDFLib objects
        
        Args:
            doc_uri: Document URI as URIRef
            metadata: Document metadata dictionary
            graph_uri: Optional named graph URI
            
        Returns:
            SPARQL INSERT query
        """
        # Validate document URI
        if not isinstance(doc_uri, URIRef):
            doc_uri = self.validate_uri(doc_uri)
        
        # Build triples using RDFLib for proper formatting
        triples = []
        
        # Add type triple
        triples.append(f"<{doc_uri}> rdf:type kr:Document")
        
        # Add metadata triples with proper escaping
        for key, value in metadata.items():
            if value is None:
                continue
                
            predicate = self._get_metadata_predicate(key)
            if predicate:
                if isinstance(value, str):
                    escaped_value = self.escape_literal(value)
                    triples.append(f'<{doc_uri}> {predicate} "{escaped_value}"')
                elif isinstance(value, (int, float)):
                    triples.append(f'<{doc_uri}> {predicate} {value}')
                elif isinstance(value, bool):
                    triples.append(f'<{doc_uri}> {predicate} {str(value).lower()}')
        
        # Build complete query
        graph_clause = f"GRAPH <{graph_uri}>" if graph_uri else ""
        triples_content = " .\n    ".join(triples) + " ."
        
        query = f"""
        {self.prefixes}
        
        INSERT DATA {{
            {graph_clause} {{
                {triples_content}
            }}
        }}
        """
        
        self.logger.debug(f"Built document insert query for: {doc_uri}")
        return query.strip()
    
    def build_concept_search_query(self, search_term: str, concept_types: List[str] = None, 
                                 limit: int = 50) -> str:
        """
        Build query to search for concepts by text
        
        Args:
            search_term: Text to search for in concept labels
            concept_types: Optional list of concept types to filter by
            limit: Maximum number of results
            
        Returns:
            SPARQL SELECT query
        """
        if not search_term:
            raise KGValidationError("Search term cannot be empty")
        
        # Escape search term for SPARQL
        escaped_term = self.escape_literal(search_term)
        
        # Build type filter if provided
        type_filter = ""
        if concept_types:
            escaped_types = [f'"{self.escape_literal(t)}"' for t in concept_types]
            type_values = " ".join(escaped_types)
            type_filter = f"""
            VALUES ?conceptType {{ {type_values} }}
            ?concept kr:conceptType ?conceptType .
            """
        
        query = f"""
        {self.prefixes}
        
        SELECT DISTINCT ?concept ?label ?conceptType ?description
        WHERE {{
            ?concept rdfs:label ?label ;
                     kr:conceptType ?conceptType .
            
            OPTIONAL {{ ?concept rdfs:comment ?description }}
            
            {type_filter}
            
            # Text search in labels (case-insensitive)
            FILTER(CONTAINS(LCASE(?label), LCASE("{escaped_term}")))
        }}
        ORDER BY ?label
        LIMIT {limit}
        """
        
        self.logger.debug(f"Built concept search query for term: {search_term}")
        return query.strip()
    
    def validate_sparql_injection(self, query: str) -> bool:
        """
        Basic validation to prevent SPARQL injection attacks
        
        Args:
            query: SPARQL query to validate
            
        Returns:
            True if query appears safe
        """
        if not query:
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = [
            r';\s*DROP',
            r';\s*DELETE\s+WHERE\s*\{[^}]*\}',
            r'LOAD\s+<[^>]*>',
            r'CLEAR\s+(GRAPH|DEFAULT|NAMED|ALL)',
            r'CREATE\s+GRAPH',
            r'DROP\s+GRAPH'
        ]
        
        query_upper = query.upper()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                self.logger.warning(f"Potentially dangerous SPARQL pattern detected: {pattern}")
                return False
        
        # Check for balanced braces and parentheses
        if query.count('{') != query.count('}'):
            self.logger.warning("Unbalanced braces in SPARQL query")
            return False
        
        if query.count('(') != query.count(')'):
            self.logger.warning("Unbalanced parentheses in SPARQL query")
            return False
        
        return True
    
    def _get_metadata_predicate(self, key: str) -> Optional[str]:
        """
        Map metadata keys to SPARQL predicate strings
        
        Args:
            key: Metadata key
            
        Returns:
            SPARQL predicate string or None
        """
        predicate_map = {
            'title': 'dcterms:title',
            'creator': 'dcterms:creator',
            'subject': 'dcterms:subject',
            'description': 'dcterms:description',
            'date': 'dcterms:date',
            'type': 'dcterms:type',
            'format': 'dcterms:format',
            'language': 'dcterms:language',
            'publisher': 'dcterms:publisher',
            'contributor': 'dcterms:contributor',
            'rights': 'dcterms:rights',
            'source': 'dcterms:source',
            'relation': 'dcterms:relation',
            'coverage': 'dcterms:coverage',
            # Custom kr: namespace predicates
            'file_path': 'kr:filePath',
            'file_size': 'kr:fileSize',
            'page_count': 'kr:pageCount',
            'processing_status': 'kr:processingStatus'
        }
        
        return predicate_map.get(key)
    
    def get_namespace_info(self) -> Dict[str, str]:
        """
        Get information about configured namespaces
        
        Returns:
            Dictionary mapping namespace prefixes to URIs
        """
        return {
            'kr': str(self.kr_ns),
            'dcterms': str(self.dcterms_ns),
            'foaf': str(self.foaf_ns),
            'skos': str(self.skos_ns),
            'rdf': str(RDF),
            'rdfs': str(RDFS),
            'xsd': str(XSD)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the query builder
        
        Returns:
            Dictionary with statistics
        """
        return {
            'builder_type': 'SPARQLQueryBuilder',
            'rdflib_integration': True,
            'namespaces_configured': len(self.get_namespace_info()),
            'injection_protection': True,
            'uri_validation': True
        }
