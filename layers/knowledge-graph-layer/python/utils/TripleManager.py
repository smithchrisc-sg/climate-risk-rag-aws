#!/usr/bin/env python3
"""
Triple Manager - Handles triple insertion and management operations with RDFLib integration
Provides high-level interface for adding triples to Neptune using proper RDF graph building
"""
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# RDFLib imports for proper graph handling
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

from .kg_exceptions import KGInsertError, KGValidationError

class TripleManager:
    """Manages triple insertion and manipulation operations using RDFLib"""
    
    def __init__(self, kg_manager):
        """
        Initialize triple manager with RDFLib integration
        
        Args:
            kg_manager: KnowledgeGraphManager instance for SPARQL operations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kg_manager = kg_manager
        self.uri_manager = kg_manager.uri_manager
        self.query_builder = kg_manager.query_builder
        
        # Set up namespaces
        self.kr_ns = kg_manager.kr_ns
        self.dcterms_ns = kg_manager.dcterms_ns
        self.foaf_ns = kg_manager.foaf_ns
        self.skos_ns = kg_manager.skos_ns
        
        # Default graph URIs
        self.document_graph_uri = URIRef("https://solve.global/graphs/documents")
        self.ontology_graph_uri = URIRef("https://solve.global/graphs/ontology")
        
        self.logger.debug("TripleManager initialized with RDFLib integration")
    
    def insert_document_triples(self, doc_id: str, metadata: Dict[str, Any], 
                              graph: Graph = None, named_graph: URIRef = None) -> bool:
        """
        Insert document metadata triples using RDFLib Graph
        
        Args:
            doc_id: Document identifier
            metadata: Document metadata dictionary
            graph: Optional RDFLib Graph to add triples to
            named_graph: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not doc_id:
                raise KGValidationError("Document ID cannot be empty")
            
            # Create or use provided graph
            target_graph = graph if graph is not None else self.kg_manager.create_graph()
            
            # Generate document URI using generic mint_uri method
            doc_uri = self.kg_manager.mint_uri(
                unique_id=doc_id,
                namespace=self.kr_ns,
                ontology_concept="Document",
                ontology_uri=self.kr_ns,
                named_graph=named_graph
            )
            
            # Add document type triple
            target_graph.add((doc_uri, RDF.type, self.kr_ns.Document))
            
            # Add document identifier
            target_graph.add((doc_uri, DCTERMS.identifier, Literal(doc_id)))
            
            # Add metadata triples
            for key, value in metadata.items():
                if value is None:
                    continue
                    
                predicate = self._get_metadata_predicate(key)
                if predicate:
                    if isinstance(value, str):
                        target_graph.add((doc_uri, predicate, Literal(value)))
                    elif isinstance(value, (int, float)):
                        target_graph.add((doc_uri, predicate, Literal(value)))
                    elif isinstance(value, bool):
                        target_graph.add((doc_uri, predicate, Literal(value)))
                    elif isinstance(value, datetime):
                        target_graph.add((doc_uri, predicate, Literal(value.isoformat(), datatype=XSD.dateTime)))
                    else:
                        # Convert to string as fallback
                        target_graph.add((doc_uri, predicate, Literal(str(value))))
            
            # Add creation timestamp
            target_graph.add((doc_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
            
            # If no external graph provided, serialize and insert
            if graph is None:
                ttl_content = target_graph.serialize(format='turtle')
                if isinstance(ttl_content, bytes):
                    ttl_content = ttl_content.decode('utf-8')
                
                success = self.bulk_insert_ttl(ttl_content, str(named_graph) if named_graph else None)
                
                if success:
                    self.logger.info(f"Successfully inserted document triples for: {doc_id}")
                else:
                    self.logger.error(f"Failed to insert document triples for: {doc_id}")
                
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting document triples for {doc_id}: {e}")
            raise KGInsertError(f"Failed to insert document triples: {e}")
    
    def insert_chunk_triples(self, chunk_data: Dict[str, Any], 
                           graph: Graph = None, named_graph: URIRef = None) -> bool:
        """
        Insert chunk triples using RDFLib Graph
        
        Args:
            chunk_data: Dictionary containing chunk information
            graph: Optional RDFLib Graph to add triples to
            named_graph: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            doc_id = chunk_data.get('doc_id')
            chunk_id = chunk_data.get('chunk_id')
            
            if not doc_id or not chunk_id:
                raise KGValidationError("Both doc_id and chunk_id are required")
            
            # Create or use provided graph
            target_graph = graph if graph is not None else self.kg_manager.create_graph()
            
            # Generate URIs
            doc_uri = self.kg_manager.mint_uri(
                unique_id=doc_id,
                namespace=self.kr_ns,
                ontology_concept="Document",
                ontology_uri=self.kr_ns,
                named_graph=named_graph
            )
            
            chunk_uri = self.kg_manager.mint_uri(
                unique_id=f"{doc_id}_{chunk_id}",
                namespace=self.kr_ns,
                ontology_concept="DocumentChunk",
                ontology_uri=self.kr_ns,
                named_graph=named_graph
            )
            
            # Add chunk type and relationship triples
            target_graph.add((chunk_uri, RDF.type, self.kr_ns.DocumentChunk))
            target_graph.add((chunk_uri, DCTERMS.isPartOf, doc_uri))
            target_graph.add((chunk_uri, DCTERMS.identifier, Literal(chunk_id)))
            
            # Add chunk content if available
            if 'text' in chunk_data:
                target_graph.add((chunk_uri, self.kr_ns.hasText, Literal(chunk_data['text'])))
            
            # Add chunk metadata
            if 'sequence' in chunk_data:
                target_graph.add((chunk_uri, self.kr_ns.sequence, Literal(chunk_data['sequence'], datatype=XSD.integer)))
            
            if 'start_position' in chunk_data:
                target_graph.add((chunk_uri, self.kr_ns.startPosition, Literal(chunk_data['start_position'], datatype=XSD.integer)))
            
            if 'end_position' in chunk_data:
                target_graph.add((chunk_uri, self.kr_ns.endPosition, Literal(chunk_data['end_position'], datatype=XSD.integer)))
            
            if 'text_length' in chunk_data:
                target_graph.add((chunk_uri, self.kr_ns.textLength, Literal(chunk_data['text_length'], datatype=XSD.integer)))
            
            if 'chunk_type' in chunk_data:
                target_graph.add((chunk_uri, self.kr_ns.chunkType, Literal(chunk_data['chunk_type'])))
            
            # Add concept mentions if available
            mentions = chunk_data.get('concept_mentions', [])
            for mention in mentions:
                concept_uri = mention.get('concept_uri')
                if concept_uri:
                    target_graph.add((chunk_uri, self.kr_ns.mentionsConcept, URIRef(concept_uri)))
            
            # Add creation timestamp
            target_graph.add((chunk_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
            
            # If no external graph provided, serialize and insert
            if graph is None:
                ttl_content = target_graph.serialize(format='turtle')
                if isinstance(ttl_content, bytes):
                    ttl_content = ttl_content.decode('utf-8')
                
                success = self.bulk_insert_ttl(ttl_content, str(named_graph) if named_graph else None)
                
                if success:
                    self.logger.info(f"Successfully inserted chunk triples for: {chunk_id}")
                else:
                    self.logger.error(f"Failed to insert chunk triples for: {chunk_id}")
                
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting chunk triples: {e}")
            raise KGInsertError(f"Failed to insert chunk triples: {e}")
    
    def insert_concept_mentions(self, chunk_id: str, mentions: List[Dict[str, Any]], 
                              doc_id: Optional[str] = None, graph: Graph = None, 
                              named_graph: URIRef = None) -> bool:
        """
        Insert concept mention triples using RDFLib Graph
        
        Args:
            chunk_id: Chunk identifier
            mentions: List of concept mention dictionaries
            doc_id: Document identifier (extracted from chunk_id if not provided)
            graph: Optional RDFLib Graph to add triples to
            named_graph: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not chunk_id or not mentions:
                raise KGValidationError("Chunk ID and mentions are required")
            
            # Extract doc_id from chunk_id if not provided
            if not doc_id:
                doc_id = '_'.join(chunk_id.split('_')[:-2]) if '_chunk_' in chunk_id else chunk_id
            
            # Create or use provided graph
            target_graph = graph if graph is not None else self.kg_manager.create_graph()
            
            # Generate chunk URI
            chunk_uri = self.kg_manager.mint_uri(
                unique_id=f"{doc_id}_{chunk_id}",
                namespace=self.kr_ns,
                ontology_concept="DocumentChunk",
                ontology_uri=self.kr_ns,
                named_graph=named_graph
            )
            
            for mention in mentions:
                concept_uri = mention.get('concept_uri')
                text = mention.get('text', '')
                start_pos = mention.get('start_position', 0)
                end_pos = mention.get('end_position', 0)
                confidence = mention.get('confidence', 1.0)
                concept_type = mention.get('concept_type', '')
                source = mention.get('source', 'unknown')
                
                if not concept_uri:
                    self.logger.warning(f"Skipping mention without concept URI: {mention}")
                    continue
                
                # Generate mention URI
                mention_uri = self.kg_manager.mint_uri(
                    unique_id=f"{chunk_id}_{hash(concept_uri)}_{start_pos}",
                    namespace=self.kr_ns,
                    ontology_concept="ConceptMention",
                    ontology_uri=self.kr_ns,
                    named_graph=named_graph
                )
                
                # Add mention triples
                target_graph.add((chunk_uri, self.kr_ns.hasConceptMention, mention_uri))
                target_graph.add((mention_uri, RDF.type, self.kr_ns.ConceptMention))
                target_graph.add((mention_uri, self.kr_ns.hasConcept, URIRef(concept_uri)))
                target_graph.add((mention_uri, self.kr_ns.hasText, Literal(text)))
                target_graph.add((mention_uri, self.kr_ns.startPosition, Literal(start_pos, datatype=XSD.integer)))
                target_graph.add((mention_uri, self.kr_ns.endPosition, Literal(end_pos, datatype=XSD.integer)))
                target_graph.add((mention_uri, self.kr_ns.confidence, Literal(confidence, datatype=XSD.float)))
                target_graph.add((mention_uri, self.kr_ns.source, Literal(source)))
                
                if concept_type:
                    target_graph.add((mention_uri, self.kr_ns.conceptType, Literal(concept_type)))
                
                # Add timestamp
                target_graph.add((mention_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
            
            # If no external graph provided, serialize and insert
            if graph is None:
                ttl_content = target_graph.serialize(format='turtle')
                if isinstance(ttl_content, bytes):
                    ttl_content = ttl_content.decode('utf-8')
                
                success = self.bulk_insert_ttl(ttl_content, str(named_graph) if named_graph else None)
                
                if success:
                    self.logger.info(f"Successfully inserted {len(mentions)} concept mentions for chunk: {chunk_id}")
                else:
                    self.logger.error(f"Failed to insert concept mentions for chunk: {chunk_id}")
                
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting concept mentions for {chunk_id}: {e}")
            raise KGInsertError(f"Failed to insert concept mentions: {e}")
    
    def insert_co_occurrences(self, chunk_id: str, co_occurrences: List[Dict[str, Any]], 
                            doc_id: Optional[str] = None, graph: Graph = None, 
                            named_graph: URIRef = None) -> bool:
        """
        Insert co-occurrence relationship triples using RDFLib Graph
        
        Args:
            chunk_id: Chunk identifier
            co_occurrences: List of co-occurrence dictionaries
            doc_id: Document identifier (extracted from chunk_id if not provided)
            graph: Optional RDFLib Graph to add triples to
            named_graph: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not chunk_id or not co_occurrences:
                raise KGValidationError("Chunk ID and co-occurrences are required")
            
            # Extract doc_id from chunk_id if not provided
            if not doc_id:
                doc_id = '_'.join(chunk_id.split('_')[:-2]) if '_chunk_' in chunk_id else chunk_id
            
            # Create or use provided graph
            target_graph = graph if graph is not None else self.kg_manager.create_graph()
            
            # Generate chunk URI
            chunk_uri = self.kg_manager.mint_uri(
                unique_id=f"{doc_id}_{chunk_id}",
                namespace=self.kr_ns,
                ontology_concept="DocumentChunk",
                ontology_uri=self.kr_ns,
                named_graph=named_graph
            )
            
            for cooc in co_occurrences:
                concept1_uri = cooc.get('concept1_uri')
                concept2_uri = cooc.get('concept2_uri')
                confidence = cooc.get('confidence', 1.0)
                distance = cooc.get('distance', 0)
                
                if not concept1_uri or not concept2_uri:
                    self.logger.warning(f"Skipping co-occurrence without both concept URIs: {cooc}")
                    continue
                
                # Generate co-occurrence URI
                concept_pair = f"{concept1_uri}|{concept2_uri}"
                pair_hash = hash(concept_pair) % 1000000  # Keep hash manageable
                cooc_uri = self.kg_manager.mint_uri(
                    unique_id=f"{chunk_id}_{pair_hash}",
                    namespace=self.kr_ns,
                    ontology_concept="ConceptCoOccurrence",
                    ontology_uri=self.kr_ns,
                    named_graph=named_graph
                )
                
                # Add co-occurrence triples
                target_graph.add((chunk_uri, self.kr_ns.hasCoOccurrence, cooc_uri))
                target_graph.add((cooc_uri, RDF.type, self.kr_ns.ConceptCoOccurrence))
                target_graph.add((cooc_uri, self.kr_ns.hasConcept1, URIRef(concept1_uri)))
                target_graph.add((cooc_uri, self.kr_ns.hasConcept2, URIRef(concept2_uri)))
                target_graph.add((cooc_uri, self.kr_ns.confidence, Literal(confidence, datatype=XSD.float)))
                target_graph.add((cooc_uri, self.kr_ns.distance, Literal(distance, datatype=XSD.integer)))
                
                # Add timestamp
                target_graph.add((cooc_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
            
            # If no external graph provided, serialize and insert
            if graph is None:
                ttl_content = target_graph.serialize(format='turtle')
                if isinstance(ttl_content, bytes):
                    ttl_content = ttl_content.decode('utf-8')
                
                success = self.bulk_insert_ttl(ttl_content, str(named_graph) if named_graph else None)
                
                if success:
                    self.logger.info(f"Successfully inserted {len(co_occurrences)} co-occurrences for chunk: {chunk_id}")
                else:
                    self.logger.error(f"Failed to insert co-occurrences for chunk: {chunk_id}")
                
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error inserting co-occurrences for {chunk_id}: {e}")
            raise KGInsertError(f"Failed to insert co-occurrences: {e}")
    
    def bulk_insert_ttl(self, ttl_content: str, graph_uri: Optional[str] = None) -> bool:
        """
        Bulk insert TTL content using optimized insertion method
        
        Args:
            ttl_content: TTL content to insert
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            # Use the optimized insertion from TripleManager
            result = self.insert_triples_optimized(ttl_content, graph_uri)
            return result.get('success', False)
            
        except Exception as e:
            self.logger.error(f"Error in bulk TTL insert: {e}")
            raise KGInsertError(f"Failed to bulk insert TTL: {e}")
    
    def insert_triples_optimized(self, ttl_content: str, s3_key_prefix: str = None) -> Dict[str, Any]:
        """
        Insert triples using optimized method (SPARQL vs bulk load)
        
        Args:
            ttl_content: TTL content to insert
            s3_key_prefix: Optional S3 key prefix for bulk load
            
        Returns:
            Dictionary with insertion results
        """
        try:
            # Estimate triple count
            estimated_count = self._estimate_triple_count(ttl_content)
            
            # Use bulk load for large datasets
            if estimated_count >= self.kg_manager.bulk_load_manager.BULK_LOAD_THRESHOLD:
                # Upload to S3 and use bulk load
                s3_key = f"{s3_key_prefix or 'triple-manager'}/bulk-{datetime.now().strftime('%Y%m%d-%H%M%S')}.ttl"
                s3_uri = self.kg_manager.upload_ttl_to_s3(ttl_content, s3_key)
                
                load_result = self.kg_manager.bulk_load_from_s3(s3_uri, wait=True)
                
                return {
                    'success': load_result.get('status') == 'LOAD_COMPLETED',
                    'method': 'bulk_load',
                    'records_loaded': load_result.get('totalRecords', estimated_count),
                    's3_uri': s3_uri,
                    'estimated_records': estimated_count
                }
            else:
                # Use SPARQL INSERT for smaller datasets
                success = self._sparql_insert_ttl(ttl_content)
                
                return {
                    'success': success,
                    'method': 'sparql_insert',
                    'estimated_records': estimated_count
                }
                
        except Exception as e:
            self.logger.error(f"Error in optimized triple insertion: {e}")
            return {
                'success': False,
                'error': str(e),
                'method': 'unknown'
            }
    
    def _estimate_triple_count(self, ttl_content: str) -> int:
        """Estimate number of triples in TTL content"""
        # Simple estimation based on statement terminators
        return ttl_content.count('.') + ttl_content.count(';')
    
    def _sparql_insert_ttl(self, ttl_content: str) -> bool:
        """Insert TTL using SPARQL INSERT"""
        try:
            # Build SPARQL INSERT query
            query = f"""
            INSERT DATA {{
                {ttl_content}
            }}
            """
            
            return self.kg_manager.execute_sparql_update(query)
            
        except Exception as e:
            self.logger.error(f"SPARQL INSERT failed: {e}")
            return False
    
    def _get_metadata_predicate(self, key: str) -> Optional[URIRef]:
        """Map metadata keys to RDF predicates"""
        predicate_map = {
            'title': DCTERMS.title,
            'creator': DCTERMS.creator,
            'subject': DCTERMS.subject,
            'description': DCTERMS.description,
            'date': DCTERMS.date,
            'type': DCTERMS.type,
            'format': DCTERMS.format,
            'language': DCTERMS.language,
            'publisher': DCTERMS.publisher,
            'contributor': DCTERMS.contributor,
            'rights': DCTERMS.rights,
            'source': DCTERMS.source,
            'relation': DCTERMS.relation,
            'coverage': DCTERMS.coverage,
            # Custom kr: namespace predicates
            'file_path': self.kr_ns.filePath,
            'file_size': self.kr_ns.fileSize,
            'page_count': self.kr_ns.pageCount,
            'processing_status': self.kr_ns.processingStatus
        }
        
        return predicate_map.get(key)
    
    def delete_document_triples(self, doc_id: str, named_graph: URIRef = None) -> bool:
        """
        Delete all triples related to a document
        
        Args:
            doc_id: Document identifier
            named_graph: Optional named graph URI
            
        Returns:
            True if deletion successful
        """
        try:
            if not doc_id:
                raise KGValidationError("Document ID cannot be empty")
            
            doc_uri = self.kg_manager.mint_uri(
                unique_id=doc_id,
                namespace=self.kr_ns,
                ontology_concept="Document",
                ontology_uri=self.kr_ns,
                named_graph=named_graph
            )
            
            # Build comprehensive delete query
            graph_clause = f"GRAPH <{named_graph}>" if named_graph else ""
            
            query = f"""
            PREFIX kr: <{self.kr_ns}>
            PREFIX dcterms: <{self.dcterms_ns}>
            
            DELETE {{
                {graph_clause} {{
                    ?s ?p ?o .
                }}
            }}
            WHERE {{
                {graph_clause} {{
                    {{
                        # Delete document triples
                        <{doc_uri}> ?p ?o .
                        BIND(<{doc_uri}> AS ?s)
                    }}
                    UNION
                    {{
                        # Delete chunk triples
                        ?chunk dcterms:isPartOf <{doc_uri}> .
                        ?chunk ?p ?o .
                        BIND(?chunk AS ?s)
                    }}
                    UNION
                    {{
                        # Delete concept mention triples
                        ?chunk dcterms:isPartOf <{doc_uri}> .
                        ?chunk kr:hasConceptMention ?mention .
                        ?mention ?p ?o .
                        BIND(?mention AS ?s)
                    }}
                    UNION
                    {{
                        # Delete co-occurrence triples
                        ?chunk dcterms:isPartOf <{doc_uri}> .
                        ?chunk kr:hasCoOccurrence ?cooc .
                        ?cooc ?p ?o .
                        BIND(?cooc AS ?s)
                    }}
                }}
            }}
            """
            
            success = self.kg_manager.execute_sparql_update(query)
            
            if success:
                self.logger.info(f"Successfully deleted all triples for document: {doc_id}")
            else:
                self.logger.error(f"Failed to delete triples for document: {doc_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting document triples for {doc_id}: {e}")
            raise KGInsertError(f"Failed to delete document triples: {e}")
    
    def validate_ttl_syntax(self, ttl_content: str) -> bool:
        """
        Validate TTL syntax using RDFLib parsing
        
        Args:
            ttl_content: TTL content to validate
            
        Returns:
            True if TTL is syntactically valid
        """
        try:
            if not ttl_content.strip():
                return False
            
            # Use RDFLib to parse and validate TTL
            test_graph = Graph()
            test_graph.parse(data=ttl_content, format='turtle')
            
            self.logger.debug(f"TTL validation successful ({len(test_graph)} triples)")
            return True
            
        except Exception as e:
            self.logger.warning(f"TTL validation failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about triple operations
        
        Returns:
            Dictionary with statistics
        """
        return {
            'manager_type': 'TripleManager',
            'rdflib_integration': True,
            'default_document_graph': str(self.document_graph_uri),
            'default_ontology_graph': str(self.ontology_graph_uri),
            'bulk_load_threshold': self.kg_manager.bulk_load_manager.BULK_LOAD_THRESHOLD,
            'namespaces': {
                'kr': str(self.kr_ns),
                'dcterms': str(self.dcterms_ns),
                'foaf': str(self.foaf_ns),
                'skos': str(self.skos_ns)
            }
        }
