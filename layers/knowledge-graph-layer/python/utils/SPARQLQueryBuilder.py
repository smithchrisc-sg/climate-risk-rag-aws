#!/usr/bin/env python3
"""
SPARQL Query Builder - Consistent SPARQL query construction
Provides reusable query patterns and prevents SPARQL injection
"""
import logging
from typing import List, Dict, Any, Optional, Union
from .URIManager import URIManager
from .kg_exceptions import KGValidationError

class SPARQLQueryBuilder:
    """Builds consistent SPARQL queries for common knowledge graph operations"""
    
    def __init__(self, uri_manager: Optional[URIManager] = None):
        """
        Initialize query builder
        
        Args:
            uri_manager: URIManager instance for consistent URI handling
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.uri_manager = uri_manager or URIManager()
        
        # Common query patterns
        self.prefixes = self.uri_manager.get_prefixes_sparql()
        
    def build_document_concept_query(self, concept_uris: List[str], limit: int = 100) -> str:
        """
        Build query to find documents containing specific concepts
        
        Args:
            concept_uris: List of concept URIs to search for
            limit: Maximum number of results
            
        Returns:
            SPARQL SELECT query
        """
        if not concept_uris:
            raise KGValidationError("Concept URIs list cannot be empty")
        
        # Validate URIs
        for uri in concept_uris:
            if not self.uri_manager.is_valid_uri(uri):
                raise KGValidationError(f"Invalid concept URI: {uri}")
        
        # Build VALUES clause for concepts
        concept_values = " ".join([f"<{uri}>" for uri in concept_uris])
        
        query = f"""
        {self.prefixes}
        
        SELECT DISTINCT ?document ?title ?concept ?conceptText ?confidence
        WHERE {{
            VALUES ?concept {{ {concept_values} }}
            
            ?chunk kcc:mentionsConcept ?concept ;
                   dcterms:isPartOf ?document .
            
            ?document dcterms:title ?title .
            
            ?chunk kcc:hasConceptMention ?mention .
            ?mention kcc:hasConcept ?concept ;
                     kcc:hasText ?conceptText ;
                     kcc:confidence ?confidence .
        }}
        ORDER BY DESC(?confidence)
        LIMIT {limit}
        """
        
        self.logger.debug(f"Built document concept query for {len(concept_uris)} concepts")
        return query.strip()
    
    def build_co_occurrence_query(self, concept_uri: str, limit: int = 50) -> str:
        """
        Build query to find concepts that co-occur with a given concept
        
        Args:
            concept_uri: URI of the concept to find co-occurrences for
            limit: Maximum number of results
            
        Returns:
            SPARQL SELECT query
        """
        if not concept_uri:
            raise KGValidationError("Concept URI cannot be empty")
        
        if not self.uri_manager.is_valid_uri(concept_uri):
            raise KGValidationError(f"Invalid concept URI: {concept_uri}")
        
        query = f"""
        {self.prefixes}
        
        SELECT DISTINCT ?coOccurringConcept ?conceptText ?confidence ?chunkId ?document
        WHERE {{
            ?chunk kcc:hasCoOccurrence ?cooc .
            
            # Find co-occurrences where our concept is concept1
            {{
                ?cooc kcc:hasConcept1 <{concept_uri}> ;
                      kcc:hasConcept2 ?coOccurringConcept ;
                      kcc:confidence ?confidence .
            }}
            UNION
            # Find co-occurrences where our concept is concept2
            {{
                ?cooc kcc:hasConcept2 <{concept_uri}> ;
                      kcc:hasConcept1 ?coOccurringConcept ;
                      kcc:confidence ?confidence .
            }}
            
            # Get additional information about the co-occurring concept
            ?chunk kcc:hasConceptMention ?mention .
            ?mention kcc:hasConcept ?coOccurringConcept ;
                     kcc:hasText ?conceptText .
            
            # Get chunk and document information
            ?chunk dcterms:isPartOf ?document .
            BIND(STRAFTER(STR(?chunk), "chunk/") AS ?chunkId)
        }}
        ORDER BY DESC(?confidence)
        LIMIT {limit}
        """
        
        self.logger.debug(f"Built co-occurrence query for concept: {concept_uri}")
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
        
        doc_uri = self.uri_manager.mint_document_uri(doc_id)
        
        query = f"""
        {self.prefixes}
        
        SELECT ?concept ?conceptText ?conceptType ?confidence ?chunkCount
        WHERE {{
            <{doc_uri}> ^dcterms:isPartOf ?chunk .
            
            ?chunk kcc:hasConceptMention ?mention .
            ?mention kcc:hasConcept ?concept ;
                     kcc:hasText ?conceptText ;
                     kcc:conceptType ?conceptType ;
                     kcc:confidence ?confidence .
            
            # Count chunks containing this concept
            {{
                SELECT ?concept (COUNT(DISTINCT ?chunk) AS ?chunkCount)
                WHERE {{
                    <{doc_uri}> ^dcterms:isPartOf ?chunk .
                    ?chunk kcc:mentionsConcept ?concept .
                }}
                GROUP BY ?concept
            }}
        }}
        ORDER BY DESC(?confidence) DESC(?chunkCount)
        """
        
        self.logger.debug(f"Built document summary query for: {doc_id}")
        return query.strip()
    
    def build_chunk_concept_search(self, concept_uri: str, confidence_threshold: float = 0.5) -> str:
        """
        Build query to search chunks containing a specific concept above confidence threshold
        
        Args:
            concept_uri: Concept URI to search for
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            SPARQL SELECT query
        """
        if not concept_uri:
            raise KGValidationError("Concept URI cannot be empty")
        
        if not self.uri_manager.is_valid_uri(concept_uri):
            raise KGValidationError(f"Invalid concept URI: {concept_uri}")
        
        if not 0 <= confidence_threshold <= 1:
            raise KGValidationError("Confidence threshold must be between 0 and 1")
        
        query = f"""
        {self.prefixes}
        
        SELECT ?chunk ?document ?conceptText ?confidence ?startPosition ?endPosition
        WHERE {{
            ?chunk kcc:mentionsConcept <{concept_uri}> ;
                   dcterms:isPartOf ?document .
            
            ?chunk kcc:hasConceptMention ?mention .
            ?mention kcc:hasConcept <{concept_uri}> ;
                     kcc:hasText ?conceptText ;
                     kcc:confidence ?confidence ;
                     kcc:startPosition ?startPosition ;
                     kcc:endPosition ?endPosition .
            
            FILTER(?confidence >= {confidence_threshold})
        }}
        ORDER BY DESC(?confidence)
        """
        
        self.logger.debug(f"Built chunk concept search for: {concept_uri} (threshold: {confidence_threshold})")
        return query.strip()
    
    def build_ontology_concepts_query(self, concept_type: Optional[str] = None) -> str:
        """
        Build query to retrieve ontology concepts
        
        Args:
            concept_type: Optional filter by concept type ('domain' or 'range')
            
        Returns:
            SPARQL SELECT query
        """
        type_filter = ""
        if concept_type:
            if concept_type not in ['domain', 'range']:
                raise KGValidationError("Concept type must be 'domain' or 'range'")
            type_filter = f'FILTER(?conceptType = "{concept_type}")'
        
        query = f"""
        {self.prefixes}
        
        SELECT DISTINCT ?concept ?label ?conceptType ?description
        WHERE {{
            ?concept a rdfs:Class ;
                     rdfs:label ?label .
            
            OPTIONAL {{ ?concept rdfs:comment ?description }}
            OPTIONAL {{ ?concept kcc:conceptType ?conceptType }}
            
            {type_filter}
        }}
        ORDER BY ?label
        """
        
        self.logger.debug(f"Built ontology concepts query (type: {concept_type})")
        return query.strip()
    
    def build_concept_relationships_query(self, concept_uri: str) -> str:
        """
        Build query to get relationships for a concept
        
        Args:
            concept_uri: Concept URI to get relationships for
            
        Returns:
            SPARQL SELECT query
        """
        if not concept_uri:
            raise KGValidationError("Concept URI cannot be empty")
        
        if not self.uri_manager.is_valid_uri(concept_uri):
            raise KGValidationError(f"Invalid concept URI: {concept_uri}")
        
        query = f"""
        {self.prefixes}
        
        SELECT ?property ?propertyLabel ?relatedConcept ?relatedLabel ?relationshipType
        WHERE {{
            # Find properties where this concept is domain
            {{
                ?property rdfs:domain <{concept_uri}> ;
                         rdfs:label ?propertyLabel ;
                         rdfs:range ?relatedConcept .
                ?relatedConcept rdfs:label ?relatedLabel .
                BIND("domain" AS ?relationshipType)
            }}
            UNION
            # Find properties where this concept is range
            {{
                ?property rdfs:range <{concept_uri}> ;
                         rdfs:label ?propertyLabel ;
                         rdfs:domain ?relatedConcept .
                ?relatedConcept rdfs:label ?relatedLabel .
                BIND("range" AS ?relationshipType)
            }}
        }}
        ORDER BY ?propertyLabel ?relatedLabel
        """
        
        self.logger.debug(f"Built concept relationships query for: {concept_uri}")
        return query.strip()
    
    def build_insert_document_query(self, doc_uri: str, metadata: Dict[str, Any], graph_uri: Optional[str] = None) -> str:
        """
        Build SPARQL INSERT query for document metadata
        
        Args:
            doc_uri: Document URI
            metadata: Document metadata dictionary
            graph_uri: Optional named graph URI
            
        Returns:
            SPARQL INSERT query
        """
        if not doc_uri:
            raise KGValidationError("Document URI cannot be empty")
        
        # Build triples from metadata
        triples = [f"<{doc_uri}> a dcterms:Document"]
        
        # Map common metadata fields to Dublin Core terms
        dc_mappings = {
            'title': 'dcterms:title',
            'creator': 'dcterms:creator',
            'subject': 'dcterms:subject',
            'description': 'dcterms:description',
            'date': 'dcterms:date',
            'type': 'dcterms:type',
            'format': 'dcterms:format',
            'identifier': 'dcterms:identifier'
        }
        
        for key, value in metadata.items():
            if key in dc_mappings and value:
                # Escape quotes in literal values
                escaped_value = str(value).replace('"', '\\"')
                triples.append(f'<{doc_uri}> {dc_mappings[key]} "{escaped_value}"')
        
        triples_str = " ;\n    ".join(triples) + " ."
        
        graph_clause = f"GRAPH <{graph_uri}> {{ " if graph_uri else ""
        graph_close = " }" if graph_uri else ""
        
        query = f"""
        {self.prefixes}
        
        INSERT DATA {{
            {graph_clause}
            {triples_str}
            {graph_close}
        }}
        """
        
        self.logger.debug(f"Built document insert query for: {doc_uri}")
        return query.strip()
    
    def build_bulk_insert_query(self, ttl_content: str, graph_uri: Optional[str] = None) -> str:
        """
        Build SPARQL INSERT query for bulk TTL content
        
        Args:
            ttl_content: TTL content to insert
            graph_uri: Optional named graph URI
            
        Returns:
            SPARQL INSERT query
        """
        if not ttl_content:
            raise KGValidationError("TTL content cannot be empty")
        
        graph_clause = f"GRAPH <{graph_uri}> {{ " if graph_uri else ""
        graph_close = " }" if graph_uri else ""
        
        query = f"""
        {self.prefixes}
        
        INSERT DATA {{
            {graph_clause}
            {ttl_content}
            {graph_close}
        }}
        """
        
        self.logger.debug("Built bulk insert query")
        return query.strip()
    
    def escape_literal(self, value: str) -> str:
        """
        Escape string literal for SPARQL
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string safe for SPARQL
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Escape quotes and other special characters
        escaped = value.replace('\\', '\\\\')  # Escape backslashes first
        escaped = escaped.replace('"', '\\"')   # Escape quotes
        escaped = escaped.replace('\n', '\\n')  # Escape newlines
        escaped = escaped.replace('\r', '\\r')  # Escape carriage returns
        escaped = escaped.replace('\t', '\\t')  # Escape tabs
        
        return escaped
    
    def validate_sparql_injection(self, query: str) -> bool:
        """
        Basic validation to prevent SPARQL injection
        
        Args:
            query: SPARQL query to validate
            
        Returns:
            True if query appears safe
        """
        # Basic checks for suspicious patterns
        suspicious_patterns = [
            'DROP',
            'CLEAR',
            'DELETE WHERE',
            'LOAD',
            'CREATE',
            'COPY',
            'MOVE',
            'ADD'
        ]
        
        query_upper = query.upper()
        for pattern in suspicious_patterns:
            if pattern in query_upper:
                self.logger.warning(f"Potentially dangerous SPARQL pattern detected: {pattern}")
                return False
        
        return True
