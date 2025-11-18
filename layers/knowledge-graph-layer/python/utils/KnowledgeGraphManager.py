#!/usr/bin/env python3
"""
Knowledge Graph Manager - Neptune/SPARQL abstraction layer with RDFLib integration
Provides consistent interface for all knowledge graph operations with proper RDF graph building
"""
import os
import logging
from typing import Dict, List, Any, Optional, Union
import boto3
import requests
from botocore.session import Session
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth
import json
import time

# RDFLib imports for proper graph handling
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

from .SPARQLQueryBuilder import SPARQLQueryBuilder
from .URIManager import URIManager
from .OntologyManager import OntologyManager
from .TripleManager import TripleManager
from .BulkLoadManager import BulkLoadManager
from .kg_exceptions import (
    KGConnectionError, 
    KGQueryError, 
    KGInsertError, 
    KGAuthenticationError,
    KGTimeoutError
)

class KnowledgeGraphManager:
    """
    Centralized manager for all Neptune/Knowledge Graph operations with RDFLib integration
    Provides consistent interface for graph building and Neptune operations
    """
    
    def __init__(self):
        """Initialize KG manager with Neptune connection, RDFLib graph, and utilities"""
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
        
        # Initialize RDFLib graph and namespaces
        self.graph = Graph()
        self._setup_namespaces()
        
        # AWS authentication using botocore (same as working Jupyter approach)
        self.session = Session()
        self.credentials = self.session.get_credentials().get_frozen_credentials()
        
        # Get AWS account ID
        try:
            sts_client = boto3.client('sts')
            self.account_id = sts_client.get_caller_identity()['Account']
        except Exception as e:
            self.logger.warning(f"Could not determine AWS account ID: {e}")
            self.account_id = "861276078413"  # Fallback to known account ID
        
        # Initialize utility managers with dependency injection
        self.query_builder = SPARQLQueryBuilder()
        self.uri_manager = URIManager()
        self.ontology_manager = OntologyManager(
            self  # Pass self as kg_manager for Neptune operations
        )
        self.triple_manager = TripleManager(self)
        self.bulk_load_manager = BulkLoadManager(self)
        
        # Connection settings
        self.timeout = 30
        self.max_retries = 3
        
        # Validate connection
        self._validate_connection()
        
        self.logger.info(f"KnowledgeGraphManager initialized for {self.neptune_endpoint}")
    
    @property
    def auth(self):
        """Return AWS SigV4 auth callable for requests library"""
        class NeptuneSigV4Auth:
            def __init__(self, credentials, region):
                self.credentials = credentials
                self.region = region
            
            def __call__(self, request):
                aws_request = AWSRequest(
                    method=request.method,
                    url=request.url,
                    data=request.body,
                    headers=dict(request.headers)
                )
                SigV4Auth(self.credentials, "neptune-db", self.region).add_auth(aws_request)
                request.headers.update(dict(aws_request.headers.items()))
                return request
        
        return NeptuneSigV4Auth(self.credentials, self.aws_region)
    
    def _setup_namespaces(self):
        """Setup standard namespaces and bind them to the graph"""
        # Define standard namespaces
        self.kr_ns = Namespace("https://solve.global/kr/")
        self.dcterms_ns = Namespace("http://purl.org/dc/terms/")
        self.foaf_ns = Namespace("http://xmlns.com/foaf/0.1/")
        self.skos_ns = Namespace("http://www.w3.org/2004/02/skos/core#")
        
        # Bind namespaces to graph for clean serialization
        self.graph.bind("kr", self.kr_ns)
        self.graph.bind("dcterms", self.dcterms_ns)
        self.graph.bind("foaf", self.foaf_ns)
        self.graph.bind("skos", self.skos_ns)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        
        self.logger.debug("Namespaces bound to RDFLib graph")
    
    def _validate_connection(self):
        """Validate Neptune connection"""
        try:
            test_query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 1"
            self.execute_sparql_query(test_query)
            self.logger.info("Neptune connection validated successfully")
        except Exception as e:
            raise KGConnectionError(f"Neptune connection validation failed: {e}")
    
    # === RDFLib GRAPH OPERATIONS ===
    
    def create_graph(self, named_graph: URIRef = None) -> Graph:
        """Create a new RDFLib graph with standard namespace bindings"""
        graph = Graph()
        
        # Bind standard namespaces
        graph.bind("kr", self.kr_ns)
        graph.bind("dcterms", self.dcterms_ns)
        graph.bind("foaf", self.foaf_ns)
        graph.bind("skos", self.skos_ns)
        graph.bind("rdf", RDF)
        graph.bind("rdfs", RDFS)
        graph.bind("xsd", XSD)
        
        return graph
    
    def add_triple(self, subject: URIRef, predicate: URIRef, obj: Union[URIRef, Literal], 
                   graph: Graph = None, named_graph: URIRef = None):
        """Add a triple to the specified graph or default graph"""
        target_graph = graph if graph is not None else self.graph
        
        if named_graph:
            # For named graphs, we'll handle this in serialization
            # For now, add to the target graph with context
            target_graph.add((subject, predicate, obj))
        else:
            target_graph.add((subject, predicate, obj))
        
        self.logger.debug(f"Added triple: {subject} {predicate} {obj}")
    
    def add_type_triple(self, subject: URIRef, rdf_type: URIRef, graph: Graph = None):
        """Add a type triple (subject rdf:type type)"""
        self.add_triple(subject, RDF.type, rdf_type, graph)
    
    def serialize_graph(self, graph: Graph = None, format: str = 'turtle') -> str:
        """Serialize the graph to specified format"""
        target_graph = graph if graph is not None else self.graph
        
        try:
            serialized = target_graph.serialize(format=format)
            if isinstance(serialized, bytes):
                serialized = serialized.decode('utf-8')
            
            self.logger.debug(f"Serialized graph to {format} format ({len(serialized)} characters)")
            return serialized
            
        except Exception as e:
            self.logger.error(f"Graph serialization failed: {e}")
            raise KGInsertError(f"Failed to serialize graph: {e}")
    
    def clear_graph(self, graph: Graph = None):
        """Clear the specified graph or default graph"""
        target_graph = graph if graph is not None else self.graph
        target_graph.remove((None, None, None))
        self.logger.debug("Graph cleared")
    
    def get_graph_size(self, graph: Graph = None) -> int:
        """Get the number of triples in the graph"""
        target_graph = graph if graph is not None else self.graph
        return len(target_graph)
    
    # === URI MANAGEMENT WITH RDFLIB ===
    
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
        # Sanitize unique_id for URI safety
        safe_id = self._sanitize_uri_component(unique_id)
        
        # Generate URI: namespace + concept + "_" + unique_id
        uri = URIRef(f"{namespace}{ontology_concept}_{safe_id}")
        
        self.logger.debug(f"Minted URI: {uri} for concept {ontology_concept}")
        return uri
    
    def _sanitize_uri_component(self, component: str) -> str:
        """Sanitize string component for safe URI usage"""
        if not component:
            return ""
        
        # Replace problematic characters
        sanitized = component.replace(' ', '_')
        sanitized = sanitized.replace('/', '_')
        sanitized = sanitized.replace('\\', '_')
        sanitized = sanitized.replace('#', '_')
        sanitized = sanitized.replace('?', '_')
        
        return sanitized
    
    # === LEGACY URI METHODS (for backward compatibility) ===
    
    def mint_document_uri(self, doc_id: str) -> URIRef:
        """Generate consistent document URI (legacy method)"""
        return self.mint_uri(doc_id, self.kr_ns, "Document", self.kr_ns)
    
    def mint_chunk_uri(self, doc_id: str, chunk_id: str) -> URIRef:
        """Generate consistent chunk URI (legacy method)"""
        return self.mint_uri(f"{doc_id}_{chunk_id}", self.kr_ns, "DocumentChunk", self.kr_ns)
    
    def mint_concept_mention_uri(self, chunk_id: str, concept_uri: str, position: int) -> URIRef:
        """Generate consistent concept mention URI (legacy method)"""
        unique_id = f"{chunk_id}_{hash(concept_uri)}_{position}"
        return self.mint_uri(unique_id, self.kr_ns, "ConceptMention", self.kr_ns)
    
    # === ONTOLOGY OPERATIONS ===
    
    def get_ontology_concepts(self, concept_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all ontology concepts or filter by type
        
        Args:
            concept_type: Optional filter by concept type ('domain', 'process', etc.)
            
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
    
    # === BULK LOAD OPERATIONS ===
    
    def bulk_load_from_s3(self, 
                         s3_uri: str, 
                         format: str = 'turtle',
                         graph_uri: Optional[str] = None,
                         wait: bool = True,
                         timeout: int = 3600) -> Dict[str, Any]:
        """
        Bulk load RDF data from S3 into Neptune
        
        Args:
            s3_uri: S3 URI of the data file
            format: Data format ('turtle', 'ntriples', 'rdfxml', 'nquads')
            graph_uri: Optional named graph URI
            wait: Whether to wait for completion
            timeout: Maximum time to wait if wait=True
            
        Returns:
            Load result dictionary
        """
        load_id = self.bulk_load_manager.initiate_bulk_load(
            s3_source_uri=s3_uri,
            format=format,
            graph_uri=graph_uri
        )
        
        if wait:
            return self.bulk_load_manager.wait_for_completion(load_id, timeout)
        else:
            return {'load_id': load_id, 'status': 'INITIATED'}
    
    def get_bulk_load_status(self, load_id: str) -> Dict[str, Any]:
        """
        Get status of a bulk load operation
        
        Args:
            load_id: Load ID from bulk_load_from_s3
            
        Returns:
            Load status dictionary
        """
        return self.bulk_load_manager.get_load_status(load_id)
    
    def list_recent_bulk_loads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent bulk load operations
        
        Args:
            limit: Maximum number of loads to return
            
        Returns:
            List of load information dictionaries
        """
        return self.bulk_load_manager.list_recent_loads(limit)
    
    def cancel_bulk_load(self, load_id: str) -> bool:
        """
        Cancel a running bulk load operation
        
        Args:
            load_id: Load ID to cancel
            
        Returns:
            True if cancellation successful
        """
        return self.bulk_load_manager.cancel_load(load_id)
    
    def upload_ttl_to_s3(self, ttl_content: str, s3_key: str, bucket: Optional[str] = None) -> str:
        """
        Upload TTL content to S3 for bulk loading
        
        Args:
            ttl_content: TTL content to upload
            s3_key: S3 key for the file
            bucket: S3 bucket (uses default if not specified)
            
        Returns:
            S3 URI of uploaded file
        """
        import boto3
        import os
        
        # Use default bucket if not specified
        if not bucket:
            bucket = os.environ.get('TTL_BUCKET', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
        
        s3_client = boto3.client('s3')
        
        try:
            # Upload TTL content
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=ttl_content.encode('utf-8'),
                ContentType='text/turtle'
            )
            
            s3_uri = f"s3://{bucket}/{s3_key}"
            self.logger.info(f"Uploaded TTL to S3: {s3_uri}")
            return s3_uri
            
        except Exception as e:
            self.logger.error(f"Failed to upload TTL to S3: {e}")
            raise KGInsertError(f"S3 upload failed: {e}")
    
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
                
                # Always log the query for debugging
                self.logger.info(f"KnowledgeGraphManager: Executing SPARQL query:\n{query}")
                
                # Validate query for basic safety
                if not self.query_builder.validate_sparql_injection(query):
                    raise KGQueryError("Query failed SPARQL injection validation")
                
                # Use botocore signing approach (same as working Jupyter code)
                request_data = {'query': query}
                aws_request = AWSRequest(
                    method="POST", 
                    url=self.sparql_endpoint, 
                    data=request_data
                )
                SigV4Auth(self.credentials, "neptune-db", self.aws_region).add_auth(aws_request)
                
                response = requests.post(
                    self.sparql_endpoint,
                    headers=dict(aws_request.headers.items()),
                    data=request_data,
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
                # Log the exact query that caused the error
                self.logger.error(f"SPARQL query request failed (attempt {attempt + 1}): {e}")
                self.logger.error(f"Failed query was:\n{query}")
                if hasattr(e, 'response') and e.response is not None:
                    self.logger.error(f"Response status: {e.response.status_code}")
                    self.logger.error(f"Response text: {e.response.text}")
                if attempt == self.max_retries - 1:
                    raise KGQueryError(f"SPARQL query failed: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                self.logger.error(f"Error processing SPARQL results: {e}")
                self.logger.error(f"Query that caused error:\n{query}")
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
                
                # Use botocore signing approach (same as working Jupyter code)
                request_data = {'update': update_query}
                aws_request = AWSRequest(
                    method="POST", 
                    url=self.sparql_endpoint, 
                    data=request_data
                )
                SigV4Auth(self.credentials, "neptune-db", self.aws_region).add_auth(aws_request)
                
                response = requests.post(
                    self.sparql_endpoint,
                    headers=dict(aws_request.headers.items()),
                    data=request_data,
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
            'uri_manager_info': self.uri_manager.get_namespace_info() if hasattr(self.uri_manager, 'get_namespace_info') else {}
        }
