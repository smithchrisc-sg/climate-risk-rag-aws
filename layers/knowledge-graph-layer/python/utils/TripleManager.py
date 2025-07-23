#!/usr/bin/env python3
"""
Triple Manager - Handles triple insertion and management operations
Provides high-level interface for adding triples to Neptune
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .kg_exceptions import KGInsertError, KGValidationError

class TripleManager:
    """Manages triple insertion and manipulation operations"""
    
    def __init__(self, kg_manager):
        """
        Initialize triple manager
        
        Args:
            kg_manager: KnowledgeGraphManager instance for SPARQL operations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.kg_manager = kg_manager
        self.uri_manager = kg_manager.uri_manager
        self.query_builder = kg_manager.query_builder
        
        # Default graph URIs
        self.document_graph_uri = self.uri_manager.mint_graph_uri('document', 'main')
        self.ontology_graph_uri = self.uri_manager.mint_graph_uri('ontology', 'main')
    
    def insert_document_triples(self, doc_id: str, metadata: Dict[str, Any], graph_uri: Optional[str] = None) -> bool:
        """
        Insert document metadata triples
        
        Args:
            doc_id: Document identifier
            metadata: Document metadata dictionary
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not doc_id:
                raise KGValidationError("Document ID cannot be empty")
            
            doc_uri = self.uri_manager.mint_document_uri(doc_id)
            target_graph = graph_uri or self.document_graph_uri
            
            # Build and execute insert query
            query = self.query_builder.build_insert_document_query(doc_uri, metadata, target_graph)
            
            success = self.kg_manager.execute_sparql_update(query)
            
            if success:
                self.logger.info(f"Successfully inserted document triples for: {doc_id}")
            else:
                self.logger.error(f"Failed to insert document triples for: {doc_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error inserting document triples for {doc_id}: {e}")
            raise KGInsertError(f"Failed to insert document triples: {e}")
    
    def insert_chunk_triples(self, chunk_data: Dict[str, Any], graph_uri: Optional[str] = None) -> bool:
        """
        Insert chunk triples with concept mentions
        
        Args:
            chunk_data: Dictionary containing chunk information and concept mentions
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            doc_id = chunk_data.get('doc_id')
            chunk_id = chunk_data.get('chunk_id')
            
            if not doc_id or not chunk_id:
                raise KGValidationError("Document ID and Chunk ID are required")
            
            doc_uri = self.uri_manager.mint_document_uri(doc_id)
            chunk_uri = self.uri_manager.mint_chunk_uri(doc_id, chunk_id)
            target_graph = graph_uri or self.document_graph_uri
            
            # Build chunk triples
            triples = []
            
            # Basic chunk metadata
            triples.extend([
                f"<{chunk_uri}> a kcc:DocumentChunk",
                f"<{chunk_uri}> dcterms:isPartOf <{doc_uri}>"
            ])
            
            # Add chunk position if available
            if 'position' in chunk_data:
                triples.append(f'<{chunk_uri}> kcc:position {chunk_data["position"]}')
            
            # Add chunk text length if available
            if 'text_length' in chunk_data:
                triples.append(f'<{chunk_uri}> kcc:textLength {chunk_data["text_length"]}')
            
            # Add concept mentions
            mentions = chunk_data.get('concept_mentions', [])
            for mention in mentions:
                concept_uri = mention.get('concept_uri')
                if concept_uri:
                    triples.append(f"<{chunk_uri}> kcc:mentionsConcept <{concept_uri}>")
            
            # Convert to TTL format
            ttl_content = " ;\n    ".join(triples) + " ."
            
            # Insert using bulk insert
            return self.bulk_insert_ttl(ttl_content, target_graph)
            
        except Exception as e:
            self.logger.error(f"Error inserting chunk triples: {e}")
            raise KGInsertError(f"Failed to insert chunk triples: {e}")
    
    def insert_concept_mentions(self, chunk_id: str, mentions: List[Dict[str, Any]], 
                              doc_id: Optional[str] = None, graph_uri: Optional[str] = None) -> bool:
        """
        Insert concept mention triples
        
        Args:
            chunk_id: Chunk identifier
            mentions: List of concept mention dictionaries
            doc_id: Document identifier (extracted from chunk_id if not provided)
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not chunk_id or not mentions:
                raise KGValidationError("Chunk ID and mentions are required")
            
            # Extract doc_id from chunk_id if not provided
            if not doc_id:
                # Assume chunk_id format: doc_id_chunk_N
                doc_id = '_'.join(chunk_id.split('_')[:-2]) if '_chunk_' in chunk_id else chunk_id
            
            chunk_uri = self.uri_manager.mint_chunk_uri(doc_id, chunk_id)
            target_graph = graph_uri or self.document_graph_uri
            
            triples = []
            
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
                mention_uri = self.uri_manager.mint_concept_mention_uri(chunk_id, concept_uri, start_pos)
                
                # Escape text for SPARQL
                escaped_text = self.query_builder.escape_literal(text)
                
                # Build mention triples
                mention_triples = [
                    f"<{chunk_uri}> kcc:hasConceptMention <{mention_uri}>",
                    f"<{mention_uri}> a kcc:ConceptMention",
                    f"<{mention_uri}> kcc:hasConcept <{concept_uri}>",
                    f'<{mention_uri}> kcc:hasText "{escaped_text}"',
                    f"<{mention_uri}> kcc:startPosition {start_pos}",
                    f"<{mention_uri}> kcc:endPosition {end_pos}",
                    f"<{mention_uri}> kcc:confidence {confidence}",
                    f'<{mention_uri}> kcc:source "{source}"'
                ]
                
                if concept_type:
                    mention_triples.append(f'<{mention_uri}> kcc:conceptType "{concept_type}"')
                
                # Add timestamp
                timestamp = datetime.now().isoformat()
                mention_triples.append(f'<{mention_uri}> dcterms:created "{timestamp}"^^xsd:dateTime')
                
                triples.extend(mention_triples)
            
            if not triples:
                self.logger.warning(f"No valid mentions to insert for chunk: {chunk_id}")
                return True
            
            # Convert to TTL format
            ttl_content = " .\n".join(triples) + " ."
            
            # Insert using bulk insert
            success = self.bulk_insert_ttl(ttl_content, target_graph)
            
            if success:
                self.logger.info(f"Successfully inserted {len(mentions)} concept mentions for chunk: {chunk_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error inserting concept mentions for {chunk_id}: {e}")
            raise KGInsertError(f"Failed to insert concept mentions: {e}")
    
    def insert_co_occurrences(self, chunk_id: str, co_occurrences: List[Dict[str, Any]], 
                            doc_id: Optional[str] = None, graph_uri: Optional[str] = None) -> bool:
        """
        Insert co-occurrence relationship triples
        
        Args:
            chunk_id: Chunk identifier
            co_occurrences: List of co-occurrence dictionaries
            doc_id: Document identifier (extracted from chunk_id if not provided)
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not chunk_id or not co_occurrences:
                raise KGValidationError("Chunk ID and co-occurrences are required")
            
            # Extract doc_id from chunk_id if not provided
            if not doc_id:
                doc_id = '_'.join(chunk_id.split('_')[:-2]) if '_chunk_' in chunk_id else chunk_id
            
            chunk_uri = self.uri_manager.mint_chunk_uri(doc_id, chunk_id)
            target_graph = graph_uri or self.document_graph_uri
            
            triples = []
            
            for cooc in co_occurrences:
                concept1_uri = cooc.get('concept1_uri')
                concept2_uri = cooc.get('concept2_uri')
                confidence = cooc.get('confidence', 1.0)
                distance = cooc.get('distance', 0)
                property_uri = cooc.get('property_uri')
                
                if not concept1_uri or not concept2_uri:
                    self.logger.warning(f"Skipping co-occurrence without both concept URIs: {cooc}")
                    continue
                
                # Generate co-occurrence URI
                cooc_uri = self.uri_manager.mint_co_occurrence_uri(chunk_id, concept1_uri, concept2_uri)
                
                # Build co-occurrence triples
                cooc_triples = [
                    f"<{chunk_uri}> kcc:hasCoOccurrence <{cooc_uri}>",
                    f"<{cooc_uri}> a kcc:CoOccurrence",
                    f"<{cooc_uri}> kcc:hasConcept1 <{concept1_uri}>",
                    f"<{cooc_uri}> kcc:hasConcept2 <{concept2_uri}>",
                    f"<{cooc_uri}> kcc:confidence {confidence}",
                    f"<{cooc_uri}> kcc:distance {distance}"
                ]
                
                if property_uri:
                    cooc_triples.append(f"<{cooc_uri}> kcc:hasProperty <{property_uri}>")
                
                # Add timestamp
                timestamp = datetime.now().isoformat()
                cooc_triples.append(f'<{cooc_uri}> dcterms:created "{timestamp}"^^xsd:dateTime')
                
                triples.extend(cooc_triples)
            
            if not triples:
                self.logger.warning(f"No valid co-occurrences to insert for chunk: {chunk_id}")
                return True
            
            # Convert to TTL format
            ttl_content = " .\n".join(triples) + " ."
            
            # Insert using bulk insert
            success = self.bulk_insert_ttl(ttl_content, target_graph)
            
            if success:
                self.logger.info(f"Successfully inserted {len(co_occurrences)} co-occurrences for chunk: {chunk_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error inserting co-occurrences for {chunk_id}: {e}")
            raise KGInsertError(f"Failed to insert co-occurrences: {e}")
    
    def bulk_insert_ttl(self, ttl_content: str, graph_uri: Optional[str] = None) -> bool:
        """
        Bulk insert TTL content
        
        Args:
            ttl_content: TTL content to insert
            graph_uri: Optional named graph URI
            
        Returns:
            True if insertion successful
        """
        try:
            if not ttl_content.strip():
                raise KGValidationError("TTL content cannot be empty")
            
            target_graph = graph_uri or self.document_graph_uri
            
            # Build bulk insert query
            query = self.query_builder.build_bulk_insert_query(ttl_content, target_graph)
            
            # Execute the insert
            success = self.kg_manager.execute_sparql_update(query)
            
            if success:
                self.logger.debug("Successfully executed bulk TTL insert")
            else:
                self.logger.error("Failed to execute bulk TTL insert")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error in bulk TTL insert: {e}")
            raise KGInsertError(f"Failed to bulk insert TTL: {e}")
    
    def bulk_insert_from_s3(self, 
                           s3_uri: str, 
                           format: str = 'turtle',
                           graph_uri: Optional[str] = None,
                           wait: bool = True) -> Dict[str, Any]:
        """
        Bulk insert from S3 using Neptune loader (for very large datasets)
        
        Args:
            s3_uri: S3 URI of the data file
            format: Data format
            graph_uri: Optional named graph URI
            wait: Whether to wait for completion
            
        Returns:
            Load result dictionary
        """
        return self.kg_manager.bulk_load_from_s3(s3_uri, format, graph_uri, wait)
    
    def insert_triples_optimized(self, 
                                ttl_content: str, 
                                graph_uri: Optional[str] = None,
                                s3_key_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Automatically choose optimal insertion method based on content size
        
        Args:
            ttl_content: TTL content to insert
            graph_uri: Optional named graph URI
            s3_key_prefix: S3 key prefix for bulk load (auto-generated if not provided)
            
        Returns:
            Dictionary with insertion result and method used
        """
        try:
            # Check if bulk load should be used
            if self.kg_manager.bulk_load_manager.should_use_bulk_load(ttl_content):
                self.logger.info("Using Neptune bulk load for large dataset")
                
                # Generate S3 key if not provided
                if not s3_key_prefix:
                    import uuid
                    s3_key_prefix = f"bulk-load/{uuid.uuid4().hex}"
                
                s3_key = f"{s3_key_prefix}.ttl"
                
                # Upload to S3
                s3_uri = self.kg_manager.upload_ttl_to_s3(ttl_content, s3_key)
                
                # Perform bulk load
                load_result = self.kg_manager.bulk_load_from_s3(s3_uri, format='turtle', graph_uri=graph_uri)
                
                return {
                    'method': 'bulk_load',
                    'success': load_result.get('status') == 'LOAD_COMPLETED',
                    'load_id': load_result.get('load_id'),
                    'records_loaded': load_result.get('total_records', 0),
                    's3_uri': s3_uri,
                    'details': load_result
                }
            else:
                self.logger.info("Using SPARQL INSERT for small dataset")
                
                # Use regular SPARQL insert
                success = self.bulk_insert_ttl(ttl_content, graph_uri)
                
                # Estimate record count for consistency
                estimated_records = self.kg_manager.bulk_load_manager.estimate_triple_count(ttl_content)
                
                return {
                    'method': 'sparql_insert',
                    'success': success,
                    'estimated_records': estimated_records,
                    'details': {'status': 'COMPLETED' if success else 'FAILED'}
                }
                
        except Exception as e:
            self.logger.error(f"Error in optimized triple insertion: {e}")
            raise KGInsertError(f"Optimized insertion failed: {e}")
    
    def delete_document_triples(self, doc_id: str, graph_uri: Optional[str] = None) -> bool:
        """
        Delete all triples related to a document
        
        Args:
            doc_id: Document identifier
            graph_uri: Optional named graph URI
            
        Returns:
            True if deletion successful
        """
        try:
            if not doc_id:
                raise KGValidationError("Document ID cannot be empty")
            
            doc_uri = self.uri_manager.mint_document_uri(doc_id)
            target_graph = graph_uri or self.document_graph_uri
            
            # Build delete query for document and all related triples
            prefixes = self.uri_manager.get_prefixes_sparql()
            graph_clause = f"GRAPH <{target_graph}>" if target_graph else ""
            
            query = f"""
            {prefixes}
            
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
                        ?chunk kcc:hasConceptMention ?mention .
                        ?mention ?p ?o .
                        BIND(?mention AS ?s)
                    }}
                    UNION
                    {{
                        # Delete co-occurrence triples
                        ?chunk dcterms:isPartOf <{doc_uri}> .
                        ?chunk kcc:hasCoOccurrence ?cooc .
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
        Basic validation of TTL syntax
        
        Args:
            ttl_content: TTL content to validate
            
        Returns:
            True if TTL appears syntactically valid
        """
        try:
            # Basic checks for TTL syntax
            if not ttl_content.strip():
                return False
            
            # Check for balanced angle brackets
            open_brackets = ttl_content.count('<')
            close_brackets = ttl_content.count('>')
            if open_brackets != close_brackets:
                self.logger.warning("Unbalanced angle brackets in TTL content")
                return False
            
            # Check for proper statement termination
            statements = ttl_content.split('.')
            for statement in statements[:-1]:  # Exclude last empty statement after final dot
                if statement.strip() and not any(char in statement for char in ['<', '"', ':']):
                    self.logger.warning(f"Potentially malformed TTL statement: {statement.strip()}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating TTL syntax: {e}")
            return False
