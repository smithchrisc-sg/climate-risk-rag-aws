#!/usr/bin/env python3
"""
NLP-KG Integrator - Final integration of NLP results with document structure knowledge graph
Generates RDF triples linking entities/concepts to document chunks with consistent URIs
"""
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
import json

# RDFLib imports for graph building
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

# Import existing KG layer utilities (UNCHANGED)
from .KnowledgeGraphManager import KnowledgeGraphManager
from .kg_exceptions import KGQueryError, KGValidationError

class NLPKGIntegrator:
    """
    Integrates NLP concept mappings with document structure knowledge graph
    Generates consistent RDF triples using existing URI patterns and namespaces
    """
    
    def __init__(self, 
                 kg_manager: KnowledgeGraphManager,
                 s3_bucket: Optional[str] = None,
                 enable_validation: bool = True):
        """
        Initialize NLP-KG integrator with existing KG infrastructure
        
        Args:
            kg_manager: Existing KnowledgeGraphManager instance (UNCHANGED interface)
            s3_bucket: S3 bucket for TTL output (optional)
            enable_validation: Whether to validate generated RDF
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Use existing KG manager (NO CHANGES to existing methods)
        self.kg_manager = kg_manager
        self.uri_manager = kg_manager.uri_manager      # Existing interface
        self.triple_manager = kg_manager.triple_manager # Existing interface
        
        # Configuration
        self.s3_bucket = s3_bucket
        self.enable_validation = enable_validation
        
        # RDF namespaces (using existing patterns)
        self.kr_ns = kg_manager.kr_ns
        self.dcterms_ns = kg_manager.dcterms_ns
        
        # Define NLP-specific predicates
        self.nlp_ns = Namespace("https://solve.global/kr/nlp/")
        
        # Statistics tracking
        self.stats = {
            'concept_mappings_processed': 0,
            'rdf_triples_generated': 0,
            'chunk_links_created': 0,
            'concept_instances_created': 0,
            'validation_errors': 0
        }
        
        self.logger.debug("NLPKGIntegrator initialized")
    
    def integrate_nlp_with_document_structure(self, 
                                            reconciled_mappings: Dict[str, Any],
                                            doc_id: str,
                                            document_structure_ttl_location: Optional[str] = None) -> Dict[str, Any]:
        """
        Main method: Integrate NLP concept mappings with document structure KG
        
        Args:
            reconciled_mappings: Results from ConceptReconciler.reconcile_bidirectional_mappings()
            doc_id: Document identifier
            document_structure_ttl_location: S3 location of existing document structure TTL
        
        Returns:
            Integration results with RDF triples and metadata
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting NLP-KG integration for document {doc_id}")
            
            # Validate input structure
            if not self._validate_reconciled_mappings(reconciled_mappings):
                raise KGValidationError("Invalid reconciled mappings structure")
            
            # Create RDF graph for integration
            integration_graph = self._create_integration_graph()
            
            # Load existing document structure if provided
            if document_structure_ttl_location:
                self._load_existing_document_structure(integration_graph, document_structure_ttl_location)
            
            # Process concept mappings
            concept_mappings = reconciled_mappings.get('reconciled_mappings', [])
            self.stats['concept_mappings_processed'] = len(concept_mappings)
            
            # Generate RDF triples for each mapping
            for mapping in concept_mappings:
                self._generate_mapping_triples(integration_graph, mapping, doc_id)
            
            # Add document-level metadata
            self._add_document_metadata(integration_graph, doc_id, reconciled_mappings)
            
            # Validate generated RDF if enabled
            if self.enable_validation:
                validation_results = self._validate_generated_rdf(integration_graph)
                self.stats['validation_errors'] = len(validation_results.get('errors', []))
            else:
                validation_results = {'status': 'validation_disabled'}
            
            # Serialize to TTL
            ttl_content = self._serialize_to_ttl(integration_graph)
            
            # Upload to S3 if bucket specified
            s3_location = None
            if self.s3_bucket:
                s3_location = self._upload_ttl_to_s3(ttl_content, doc_id)
            
            # Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'integration_status': 'success',
                'doc_id': doc_id,
                'ttl_content': ttl_content,
                's3_location': s3_location,
                'rdf_statistics': {
                    'total_triples': len(integration_graph),
                    'concept_mappings_processed': self.stats['concept_mappings_processed'],
                    'chunk_links_created': self.stats['chunk_links_created'],
                    'concept_instances_created': self.stats['concept_instances_created']
                },
                'validation_results': validation_results,
                'processing_stats': {
                    'processing_time_seconds': processing_time,
                    'triples_per_second': len(integration_graph) / processing_time if processing_time > 0 else 0
                },
                'integration_metadata': {
                    'integration_timestamp': datetime.now().isoformat(),
                    'source_mappings_count': len(concept_mappings),
                    'document_structure_loaded': document_structure_ttl_location is not None
                }
            }
            
            self.stats['rdf_triples_generated'] = len(integration_graph)
            
            self.logger.info(f"NLP-KG integration completed: {len(integration_graph)} triples generated")
            
            return result
            
        except Exception as e:
            self.logger.error(f"NLP-KG integration failed: {e}")
            raise KGQueryError(f"Integration error: {e}")
    
    def _validate_reconciled_mappings(self, reconciled_mappings: Dict[str, Any]) -> bool:
        """Validate reconciled mappings structure"""
        
        if 'reconciled_mappings' not in reconciled_mappings:
            self.logger.error("Missing 'reconciled_mappings' in input")
            return False
        
        # Validate each mapping has required fields
        for mapping in reconciled_mappings['reconciled_mappings']:
            required_fields = ['chunk_id', 'concept_uri', 'text', 'confidence']
            if not all(field in mapping for field in required_fields):
                self.logger.error(f"Missing required fields in mapping: {mapping}")
                return False
        
        return True
    
    def _create_integration_graph(self) -> Graph:
        """Create RDF graph with standard namespace bindings"""
        # Use EXISTING method to create graph with standard namespaces
        graph = self.kg_manager.create_graph()
        
        # Add NLP-specific namespace
        graph.bind("nlp", self.nlp_ns)
        
        return graph
    
    def _load_existing_document_structure(self, graph: Graph, ttl_location: str):
        """Load existing document structure TTL into integration graph"""
        try:
            if ttl_location.startswith('s3://'):
                # Load from S3
                bucket, key = ttl_location.replace('s3://', '').split('/', 1)
                
                response = self.kg_manager.s3_client.get_object(Bucket=bucket, Key=key)
                ttl_content = response['Body'].read().decode('utf-8')
                
                # Parse TTL into graph
                graph.parse(data=ttl_content, format='turtle')
                
                self.logger.debug(f"Loaded {len(graph)} triples from document structure")
            else:
                self.logger.warning(f"Unsupported TTL location format: {ttl_location}")
                
        except Exception as e:
            self.logger.warning(f"Failed to load document structure from {ttl_location}: {e}")
    
    def _generate_mapping_triples(self, graph: Graph, mapping: Dict[str, Any], doc_id: str):
        """Generate RDF triples for a single concept mapping"""
        
        chunk_id = mapping['chunk_id']
        concept_uri = URIRef(mapping['concept_uri'])
        text = mapping['text']
        confidence = mapping['confidence']
        
        # Generate URIs using EXISTING uri_manager methods
        chunk_uri = self._get_chunk_uri(doc_id, chunk_id)
        concept_mention_uri = self._get_concept_mention_uri(chunk_id, mapping['concept_uri'], text)
        
        # Triple 1: Chunk mentions concept
        self._add_triple(graph, chunk_uri, self.nlp_ns.mentionsConcept, concept_uri)
        
        # Triple 2: Create concept mention instance
        self._add_triple(graph, concept_mention_uri, RDF.type, self.nlp_ns.ConceptMention)
        self._add_triple(graph, concept_mention_uri, self.nlp_ns.hasText, Literal(text))
        self._add_triple(graph, concept_mention_uri, self.nlp_ns.hasConcept, concept_uri)
        self._add_triple(graph, concept_mention_uri, self.nlp_ns.hasConfidence, Literal(confidence, datatype=XSD.float))
        self._add_triple(graph, concept_mention_uri, self.nlp_ns.foundInChunk, chunk_uri)
        
        # Triple 3: Link mention to chunk
        self._add_triple(graph, chunk_uri, self.nlp_ns.hasConceptMention, concept_mention_uri)
        
        # Add source method information
        source_method = mapping.get('source_method', 'unknown')
        self._add_triple(graph, concept_mention_uri, self.nlp_ns.detectionMethod, Literal(source_method))
        
        # Add reconciliation information if available
        reconciliation_info = mapping.get('reconciliation_info', {})
        if reconciliation_info.get('type') != 'no_conflict':
            reconciliation_uri = self._create_reconciliation_uri(concept_mention_uri)
            self._add_triple(graph, concept_mention_uri, self.nlp_ns.hasReconciliation, reconciliation_uri)
            self._add_triple(graph, reconciliation_uri, RDF.type, self.nlp_ns.ReconciliationInfo)
            self._add_triple(graph, reconciliation_uri, self.nlp_ns.reconciliationType, 
                           Literal(reconciliation_info.get('type', 'unknown')))
        
        # Add position information if available
        position_info = mapping.get('position_info', {})
        if position_info.get('start_offset') is not None:
            self._add_triple(graph, concept_mention_uri, self.nlp_ns.startOffset, 
                           Literal(position_info['start_offset'], datatype=XSD.integer))
            self._add_triple(graph, concept_mention_uri, self.nlp_ns.endOffset, 
                           Literal(position_info['end_offset'], datatype=XSD.integer))
        
        self.stats['chunk_links_created'] += 1
        self.stats['concept_instances_created'] += 1
    
    def _get_chunk_uri(self, doc_id: str, chunk_id: str) -> URIRef:
        """Get chunk URI using EXISTING uri_manager method"""
        # Use EXISTING method - no changes to interface
        return self.kg_manager.mint_chunk_uri(doc_id, chunk_id)
    
    def _get_concept_mention_uri(self, chunk_id: str, concept_uri: str, text: str) -> URIRef:
        """Get concept mention URI using EXISTING uri_manager method"""
        # Create position hash for uniqueness
        position_hash = hash(text.lower())
        
        # Use EXISTING method - no changes to interface
        return self.kg_manager.mint_concept_mention_uri(chunk_id, concept_uri, position_hash)
    
    def _create_reconciliation_uri(self, concept_mention_uri: URIRef) -> URIRef:
        """Create URI for reconciliation information"""
        unique_id = f"reconciliation_{hash(str(concept_mention_uri))}"
        
        # Use EXISTING mint_uri method
        return self.kg_manager.mint_uri(
            unique_id=unique_id,
            namespace=self.nlp_ns,
            ontology_concept="ReconciliationInfo",
            ontology_uri=self.nlp_ns
        )
    
    def _add_triple(self, graph: Graph, subject: URIRef, predicate: URIRef, obj):
        """Add triple to graph using existing KG manager method"""
        # Use EXISTING method - no changes to interface
        self.kg_manager.add_triple(subject, predicate, obj, graph)
    
    def _add_document_metadata(self, graph: Graph, doc_id: str, reconciled_mappings: Dict[str, Any]):
        """Add document-level NLP processing metadata"""
        
        # Generate document URI using EXISTING method
        doc_uri = self.kg_manager.mint_document_uri(doc_id)
        
        # Add NLP processing metadata
        processing_stats = reconciled_mappings.get('processing_stats', {})
        
        # Create NLP processing instance
        nlp_processing_uri = self._create_nlp_processing_uri(doc_id)
        self._add_triple(graph, nlp_processing_uri, RDF.type, self.nlp_ns.NLPProcessing)
        self._add_triple(graph, nlp_processing_uri, self.nlp_ns.processedDocument, doc_uri)
        self._add_triple(graph, nlp_processing_uri, self.nlp_ns.processingTimestamp, 
                        Literal(datetime.now().isoformat(), datatype=XSD.dateTime))
        
        # Add processing statistics
        if 'final_mappings_output' in processing_stats:
            self._add_triple(graph, nlp_processing_uri, self.nlp_ns.conceptMappingsCount, 
                           Literal(processing_stats['final_mappings_output'], datatype=XSD.integer))
        
        if 'conflicts_resolved' in processing_stats:
            self._add_triple(graph, nlp_processing_uri, self.nlp_ns.conflictsResolved, 
                           Literal(processing_stats['conflicts_resolved'], datatype=XSD.integer))
        
        # Link document to NLP processing
        self._add_triple(graph, doc_uri, self.nlp_ns.hasNLPProcessing, nlp_processing_uri)
    
    def _create_nlp_processing_uri(self, doc_id: str) -> URIRef:
        """Create URI for NLP processing instance"""
        unique_id = f"nlp_processing_{doc_id}_{int(datetime.now().timestamp())}"
        
        # Use EXISTING mint_uri method
        return self.kg_manager.mint_uri(
            unique_id=unique_id,
            namespace=self.nlp_ns,
            ontology_concept="NLPProcessing",
            ontology_uri=self.nlp_ns
        )
    
    def _validate_generated_rdf(self, graph: Graph) -> Dict[str, Any]:
        """Validate generated RDF for consistency and completeness"""
        validation_results = {
            'status': 'valid',
            'errors': [],
            'warnings': [],
            'statistics': {
                'total_triples': len(graph),
                'unique_subjects': len(set(graph.subjects())),
                'unique_predicates': len(set(graph.predicates())),
                'unique_objects': len(set(graph.objects()))
            }
        }
        
        try:
            # Check for required namespaces
            namespaces = dict(graph.namespaces())
            required_namespaces = ['kr', 'nlp', 'dcterms']
            
            for ns in required_namespaces:
                if ns not in namespaces:
                    validation_results['errors'].append(f"Missing required namespace: {ns}")
            
            # Check for orphaned concept mentions
            concept_mentions = list(graph.subjects(RDF.type, self.nlp_ns.ConceptMention))
            for mention in concept_mentions:
                # Check if mention has required properties
                if not list(graph.objects(mention, self.nlp_ns.hasText)):
                    validation_results['errors'].append(f"Concept mention missing text: {mention}")
                
                if not list(graph.objects(mention, self.nlp_ns.hasConcept)):
                    validation_results['errors'].append(f"Concept mention missing concept: {mention}")
                
                if not list(graph.objects(mention, self.nlp_ns.foundInChunk)):
                    validation_results['errors'].append(f"Concept mention missing chunk link: {mention}")
            
            # Set status based on errors
            if validation_results['errors']:
                validation_results['status'] = 'invalid'
            elif validation_results['warnings']:
                validation_results['status'] = 'valid_with_warnings'
            
        except Exception as e:
            validation_results['status'] = 'validation_failed'
            validation_results['errors'].append(f"Validation error: {e}")
        
        return validation_results
    
    def _serialize_to_ttl(self, graph: Graph) -> str:
        """Serialize graph to TTL format using existing KG manager method"""
        # Use EXISTING method - no changes to interface
        return self.kg_manager.serialize_graph(graph, format='turtle')
    
    def _upload_ttl_to_s3(self, ttl_content: str, doc_id: str) -> str:
        """Upload TTL content to S3 using existing KG manager method"""
        
        # Generate S3 key
        s3_key = f"nlp-integration/{doc_id}/nlp_integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ttl"
        
        # Use EXISTING method - no changes to interface
        return self.kg_manager.upload_ttl_to_s3(ttl_content, s3_key, self.s3_bucket)
    
    def get_integrator_statistics(self) -> Dict[str, Any]:
        """Get comprehensive integrator statistics"""
        return {
            'processing_stats': dict(self.stats),
            'configuration': {
                's3_bucket': self.s3_bucket,
                'enable_validation': self.enable_validation
            },
            'namespace_info': {
                'kr_namespace': str(self.kr_ns),
                'nlp_namespace': str(self.nlp_ns),
                'dcterms_namespace': str(self.dcterms_ns)
            }
        }
    
    def generate_sparql_queries_for_nlp_data(self, doc_id: str) -> Dict[str, str]:
        """Generate useful SPARQL queries for accessing NLP-integrated data"""
        
        doc_uri = self.kg_manager.mint_document_uri(doc_id)
        
        queries = {
            'all_concept_mentions': f"""
                PREFIX kr: <{self.kr_ns}>
                PREFIX nlp: <{self.nlp_ns}>
                
                SELECT ?chunk ?concept ?text ?confidence WHERE {{
                    <{doc_uri}> kr:hasChunk ?chunk .
                    ?chunk nlp:hasConceptMention ?mention .
                    ?mention nlp:hasConcept ?concept ;
                             nlp:hasText ?text ;
                             nlp:hasConfidence ?confidence .
                }}
                ORDER BY DESC(?confidence)
            """,
            
            'high_confidence_concepts': f"""
                PREFIX kr: <{self.kr_ns}>
                PREFIX nlp: <{self.nlp_ns}>
                
                SELECT ?concept (COUNT(?mention) as ?frequency) (AVG(?confidence) as ?avg_confidence) WHERE {{
                    <{doc_uri}> kr:hasChunk ?chunk .
                    ?chunk nlp:hasConceptMention ?mention .
                    ?mention nlp:hasConcept ?concept ;
                             nlp:hasConfidence ?confidence .
                    FILTER(?confidence >= 0.8)
                }}
                GROUP BY ?concept
                ORDER BY DESC(?frequency)
            """,
            
            'concept_co_occurrences': f"""
                PREFIX kr: <{self.kr_ns}>
                PREFIX nlp: <{self.nlp_ns}>
                
                SELECT ?concept1 ?concept2 (COUNT(?chunk) as ?co_occurrence_count) WHERE {{
                    <{doc_uri}> kr:hasChunk ?chunk .
                    ?chunk nlp:hasConceptMention ?mention1, ?mention2 .
                    ?mention1 nlp:hasConcept ?concept1 .
                    ?mention2 nlp:hasConcept ?concept2 .
                    FILTER(?concept1 != ?concept2)
                }}
                GROUP BY ?concept1 ?concept2
                HAVING(?co_occurrence_count > 1)
                ORDER BY DESC(?co_occurrence_count)
            """
        }
        
        return queries

# Example usage and testing
if __name__ == "__main__":
    # This would be used in Lambda functions
    kg_manager = KnowledgeGraphManager()
    integrator = NLPKGIntegrator(
        kg_manager, 
        s3_bucket='solve-global-kr-dl-kg-861276078413-us-east-1',
        enable_validation=True
    )
    
    # Mock reconciled mappings (would come from ConceptReconciler)
    reconciled_mappings = {
        'reconciled_mappings': [
            {
                'chunk_id': 'doc123_chunk_0001',
                'concept_uri': 'https://solve.global/ontology/ClimateChange',
                'concept_label': 'Climate Change',
                'text': 'climate change',
                'confidence': 0.89,
                'source_method': 'entity_aligner',
                'reconciliation_info': {'type': 'no_conflict'},
                'position_info': {'start_offset': 10, 'end_offset': 24}
            }
        ],
        'processing_stats': {
            'final_mappings_output': 1,
            'conflicts_resolved': 0
        }
    }
    
    # Integrate with document structure
    result = integrator.integrate_nlp_with_document_structure(
        reconciled_mappings=reconciled_mappings,
        doc_id='doc123'
    )
    
    print(f"Integration result: {json.dumps(result, indent=2)}")
