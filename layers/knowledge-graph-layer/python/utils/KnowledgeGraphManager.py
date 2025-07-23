#!/usr/bin/env python3
"""
Knowledge Graph Manager - Neptune/SPARQL abstraction layer
Provides consistent interface for all knowledge graph operations
Similar to DatabaseManager but for Neptune/RDF operations
"""
import os
import logging
from typing import Dict, List, Any, Optional, Union
import boto3
import requests
from requests_aws4auth import AWS4Auth
import json
import time

from .SPARQLQueryBuilder import SPARQLQueryBuilder
from .URIManager import URIManager
from .OntologyManager import OntologyManager
from .TripleManager import TripleManager
from .kg_exceptions import (
    KGConnectionError, 
    KGQueryError, 
    KGInsertError, 
    KGAuthenticationError,
    KGTimeoutError
)

class KnowledgeGraphManager:
    """
    Centralized manager for all Neptune/Knowledge Graph operations
    Provides consistent interface similar to DatabaseManager
    """
    
    def __init__(self):
        """Initialize KG manager with Neptune connection and utilities"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Neptune configuration from environment
        self.neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT')
        self.neptune_port = os.environ.get('NEPTUNE_PORT', '8182')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if not self.neptune_endpoint:
            raise ValueError("NEPTUNE_ENDPOINT environment variable required")
        
        # Build endpoint URLs
        self.sparql_endpoint = f"https://{self.neptune_endpoint}:{self.neptune_port}/sparql"
        self.gremlin_endpoint = f"wss://{self.neptune_endpoint}:{self.neptune_port}/gremlin"
        
        # Initialize AWS authentication
        self._setup_auth()
        
        # Initialize utility components
        self.uri_manager = URIManager()
        self.query_builder = SPARQLQueryBuilder(self.uri_manager)
        self.ontology_manager = OntologyManager(self)
        self.triple_manager = TripleManager(self)
        
        # Connection configuration
        self.timeout = int(os.environ.get('NEPTUNE_TIMEOUT', '30'))
        self.max_retries = int(os.environ.get('NEPTUNE_MAX_RETRIES', '3'))
        
        # Connection validation
        self._validate_connection()
        
        self.logger.info(f"KnowledgeGraphManager initialized for {self.neptune_endpoint}")
    
    def _setup_auth(self):
        """Setup AWS4Auth for Neptune access"""
        try:
            credentials = boto3.Session().get_credentials()
            if not credentials:
                raise KGAuthenticationError("Unable to retrieve AWS credentials")
            
            self.auth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.aws_region,
                'neptune-db',
                session_token=credentials.token
            )
            
            self.logger.debug("AWS4Auth configured successfully")
            
        except Exception as e:
            raise KGAuthenticationError(f"Failed to setup Neptune authentication: {e}")
    
    # === ONTOLOGY OPERATIONS ===
    
    def get_ontology_concepts(self, concept_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get ontology concepts, optionally filtered by type
        
        Args:
            concept_type: Optional filter by concept type ('domain' or 'range')
            
        Returns:
            List of concept dictionaries
        """
        return self.ontology_manager.get_concepts(concept_type)
    
    def get_concept_by_uri(self, concept_uri: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific concept
        
        Args:
            concept_uri: URI of the concept
            
        Returns:
            Concept details dictionary or None if not found
        """
        return self.ontology_manager.get_concept_details(concept_uri)
    
    def search_concepts_by_label(self, label: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        Search concepts by label with optional fuzzy matching
        
        Args:
            label: Label text to search for
            fuzzy: Enable fuzzy matching
            
        Returns:
            List of matching concepts
        """
        return self.ontology_manager.search_by_label(label, fuzzy)
    
    def get_concept_relationships(self, concept_uri: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for a concept (domain/range properties)
        
        Args:
            concept_uri: URI of the concept
            
        Returns:
            List of relationship dictionaries
        """
        return self.ontology_manager.get_relationships(concept_uri)
    
    # === URI MANAGEMENT ===
    
    def mint_document_uri(self, doc_id: str) -> str:
        """
        Generate consistent document URI
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Consistent document URI
        """
        return self.uri_manager.mint_document_uri(doc_id)
    
    def mint_chunk_uri(self, doc_id: str, chunk_id: str) -> str:
        """
        Generate consistent chunk URI
        
        Args:
            doc_id: Document identifier
            chunk_id: Chunk identifier
            
        Returns:
            Consistent chunk URI
        """
        return self.uri_manager.mint_chunk_uri(doc_id, chunk_id)
    
    def mint_concept_mention_uri(self, chunk_id: str, concept_uri: str, position: int) -> str:
        """
        Generate consistent concept mention URI
        
        Args:
            chunk_id: Chunk identifier
            concept_uri: Concept URI being mentioned
            position: Position in text
            
        Returns:
            Consistent concept mention URI
        """
        return self.uri_manager.mint_concept_mention_uri(chunk_id, concept_uri, position)
    
    # === TRIPLE OPERATIONS ===
    
    def insert_document_triples(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Insert document metadata triples
        
        Args:
            doc_id: Document identifier
            metadata: Document metadata dictionary
            
        Returns:
            True if insertion successful
        """
        return self.triple_manager.insert_document_triples(doc_id, metadata)
    
    def insert_chunk_triples(self, chunk_data: Dict[str, Any]) -> bool:
        """
        Insert chunk triples with concept mentions
        
        Args:
            chunk_data: Dictionary containing chunk information
            
        Returns:
            True if insertion successful
        """
        return self.triple_manager.insert_chunk_triples(chunk_data)
    
    def insert_concept_mentions(self, chunk_id: str, mentions: List[Dict[str, Any]]) -> bool:
        """
        Insert concept mention triples
        
        Args:
            chunk_id: Chunk identifier
            mentions: List of concept mention dictionaries
            
        Returns:
            True if insertion successful
        """
        return self.triple_manager.insert_concept_mentions(chunk_id, mentions)
    
    def insert_co_occurrences(self, chunk_id: str, co_occurrences: List[Dict[str, Any]]) -> bool:
        """
        Insert co-occurrence relationship triples
        
        Args:
            chunk_id: Chunk identifier
            co_occurrences: List of co-occurrence dictionaries
            
        Returns:
            True if insertion successful
        """
        return self.triple_manager.insert_co_occurrences(chunk_id, co_occurrences)
    
    def bulk_insert_ttl(self, ttl_content: str, graph_uri: Optional[str] = None) -> bool:
        """
        Bulk insert TTL content (for large datasets)
        
        Args:
            ttl_content: TTL content to insert
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        return self.triple_manager.bulk_insert_ttl(ttl_content, graph_uri)
    
    # === QUERY OPERATIONS ===
    
    def find_documents_with_concepts(self, concept_uris: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find documents containing specific concepts
        
        Args:
            concept_uris: List of concept URIs to search for
            limit: Maximum number of results
            
        Returns:
            List of document dictionaries
        """
        query = self.query_builder.build_document_concept_query(concept_uris, limit)
        return self.execute_sparql_query(query)
    
    def find_concept_co_occurrences(self, concept_uri: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find concepts that co-occur with a given concept
        
        Args:
            concept_uri: URI of the concept
            limit: Maximum number of results
            
        Returns:
            List of co-occurrence dictionaries
        """
        query = self.query_builder.build_co_occurrence_query(concept_uri, limit)
        return self.execute_sparql_query(query)
    
    def get_document_concept_summary(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get summary of concepts mentioned in a document
        
        Args:
            doc_id: Document identifier
            
        Returns:
            List of concept summary dictionaries
        """
        query = self.query_builder.build_document_summary_query(doc_id)
        return self.execute_sparql_query(query)
    
    def search_chunks_by_concept(self, concept_uri: str, confidence_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Search chunks containing a specific concept above confidence threshold
        
        Args:
            concept_uri: URI of the concept
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            List of chunk dictionaries
        """
        query = self.query_builder.build_chunk_concept_search(concept_uri, confidence_threshold)
        return self.execute_sparql_query(query)
    
    # === LOW-LEVEL SPARQL OPERATIONS ===
    
    def execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SPARQL SELECT query and return results
        
        Args:
            query: SPARQL SELECT query
            
        Returns:
            List of result dictionaries
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Executing SPARQL query (attempt {attempt + 1})")
                
                # Validate query for basic safety
                if not self.query_builder.validate_sparql_injection(query):
                    raise KGQueryError("Query failed SPARQL injection validation")
                
                response = requests.post(
                    self.sparql_endpoint,
                    data={'query': query},
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'application/sparql-results+json'
                    },
                    auth=self.auth,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                
                results = response.json()
                processed_results = self._process_sparql_results(results)
                
                self.logger.debug(f"SPARQL query executed successfully, returned {len(processed_results)} results")
                return processed_results
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"SPARQL query timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise KGTimeoutError("SPARQL query timed out after all retries")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"SPARQL query request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise KGQueryError(f"SPARQL query failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                self.logger.error(f"Error processing SPARQL results: {e}")
                raise KGQueryError(f"Error processing SPARQL results: {e}")
    
    def execute_sparql_update(self, update_query: str) -> bool:
        """
        Execute SPARQL INSERT/DELETE/UPDATE query
        
        Args:
            update_query: SPARQL update query
            
        Returns:
            True if update successful
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Executing SPARQL update (attempt {attempt + 1})")
                
                # Validate query for basic safety
                if not self.query_builder.validate_sparql_injection(update_query):
                    raise KGInsertError("Update query failed SPARQL injection validation")
                
                response = requests.post(
                    self.sparql_endpoint,
                    data={'update': update_query},
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    auth=self.auth,
                    timeout=self.timeout * 2  # Updates may take longer
                )
                
                response.raise_for_status()
                
                self.logger.debug("SPARQL update executed successfully")
                return True
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"SPARQL update timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise KGTimeoutError("SPARQL update timed out after all retries")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"SPARQL update request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise KGInsertError(f"SPARQL update failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    # === UTILITY METHODS ===
    
    def _validate_connection(self):
        """Validate Neptune connection"""
        try:
            test_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o } LIMIT 1"
            self.execute_sparql_query(test_query)
            self.logger.info("Neptune connection validated successfully")
        except Exception as e:
            raise KGConnectionError(f"Neptune connection validation failed: {e}")
    
    def _process_sparql_results(self, results: Dict) -> List[Dict[str, Any]]:
        """
        Process SPARQL JSON results into Python dictionaries
        
        Args:
            results: Raw SPARQL JSON results
            
        Returns:
            List of processed result dictionaries
        """
        processed = []
        bindings = results.get('results', {}).get('bindings', [])
        
        for binding in bindings:
            row = {}
            for var, value in binding.items():
                if value['type'] == 'uri':
                    row[var] = value['value']
                elif value['type'] == 'literal':
                    row[var] = value['value']
                    # Handle datatype if present
                    if 'datatype' in value:
                        row[f"{var}_datatype"] = value['datatype']
                    # Handle language if present
                    if 'xml:lang' in value:
                        row[f"{var}_lang"] = value['xml:lang']
                else:
                    row[var] = value['value']
            processed.append(row)
        
        return processed
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get connection information for debugging
        
        Returns:
            Dictionary with connection details
        """
        return {
            'neptune_endpoint': self.neptune_endpoint,
            'neptune_port': self.neptune_port,
            'sparql_endpoint': self.sparql_endpoint,
            'aws_region': self.aws_region,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of Neptune connection
        
        Returns:
            Dictionary with health status information
        """
        try:
            start_time = time.time()
            test_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o } LIMIT 1"
            results = self.execute_sparql_query(test_query)
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time_seconds': response_time,
                'triple_count': results[0].get('count', 0) if results else 0,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def clear_all_caches(self):
        """Clear all internal caches"""
        self.ontology_manager.clear_cache()
        self.logger.info("Cleared all KG manager caches")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics from all components
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'ontology_cache': self.ontology_manager.get_cache_stats(),
            'uri_manager_info': self.uri_manager.get_namespace_info()
        }
