"""
Document Processor

Handles processing of individual documents through the NLP-KG pipeline.
"""

import logging
from typing import Dict, List, Any

from .data_retriever import DataRetriever
from .pipeline_integrator import PipelineIntegrator

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes individual documents through the complete NLP-KG pipeline.
    """
    
    def __init__(self):
        """Initialize the document processor with required utilities."""
        self.data_retriever = DataRetriever()
        self.pipeline_integrator = PipelineIntegrator()
    
    def process_document_request(self, request: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single document request through the full NLP-KG pipeline.
        
        Args:
            request: Document processing request with S3 locations
            components: Initialized layer components
            
        Returns:
            Processing result with status and output locations

        Event json looks like this (SNS unwrapped):
        {
            "version": "1.0",
            "timestamp": "2025-08-14T16:29:00.685614Z",
            "source": "climate-risk-rag-system",
            "stage": "nlp_processing_complete",
            "doc_id": "064762102bead7b04a39",
            "data_locations": {
                "entities_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities.json",
                "key_phrases_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases.json",
                "mapped_phrases_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/key_phrases_by_chunk.json",
                "mapped_entities_location": "s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/data-lake/064762102bead7b04a39/entities_by_chunk.json"
            },
            "processing_metadata": {
                "entities_count": 3345,
                "key_phrases_count": 8709,
                "processing_completed": "2025-08-14T16:29:00.685614Z"
            },
            "integration_flags": {
                "database_tracking_enabled": true,
                "knowledge_graph_integration_enabled": true
            }
        }
        """
        document_id = request['doc_id']
        logger.info(f"Processing document: {document_id}")
        
        try:
            # Phase 3: Data Retrieval (NLP results only - entities already mapped to chunks by nlp-worker)
            logger.info(f"Phase 3: Retrieving NLP results for {document_id}")
            nlp_results = self.data_retriever.retrieve_nlp_results(request)
            
            # Phase 4: Ontology Alignment using EntityAlignmentManager (handles TYPE/ontology mapping via env vars)
            logger.info(f"Phase 4: Aligning entities with ontologies for {document_id}")
            
            # Convert NLP results to format expected by EntityAlignmentManager
            entities_by_chunk = self._convert_nlp_results_to_entities(nlp_results, document_id)
            
            if not entities_by_chunk:
                logger.info(f"No entities found for {document_id}")
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'message': 'No entities to process',
                    'entities_processed': 0,
                    'triples_generated': 0
                }
            
            # Use EntityAlignmentManager - it will handle entity type filtering based on env vars
            aligned_entities = components['entity_aligner'].align_entities_to_ontologies(entities_by_chunk)
            
            # Filter out entities that didn't align to any ontology
            successful_alignments = [entity for entity in aligned_entities if entity.get('ontology_alignment')]
            
            if not successful_alignments:
                logger.warning(f"No entities aligned to ontologies for {document_id}")
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'message': 'No alignable entities found',
                    'entities_processed': len(entities_by_chunk),
                    'entities_aligned': 0,
                    'triples_generated': 0
                }
            
            # Phase 5: Knowledge Graph Construction (Triple generation)
            logger.info(f"Phase 5: Constructing knowledge graph for {len(successful_alignments)} aligned entities")
            ttl_content = components['triple_manager'].create_triples_from_entities(
                successful_alignments, document_id
            )
            
            logger.info(f"Phase 5: Received TTL content type: {type(ttl_content)}")
            logger.info(f"Phase 5: Received TTL content length: {len(ttl_content)}")
            logger.info(f"Phase 5: TTL content preview (first 500 chars): {repr(ttl_content[:500])}")
            
            # Phase 6: Write TTL content to S3
            logger.info(f"Phase 6: Writing {len(ttl_content)} characters of TTL content to S3")
            logger.info(f"nlp-kg-processor: document_processor: TTL content: {ttl_content[:500]}")
            ttl_location = self._write_ttl_to_s3(
                ttl_content, document_id, request.get('s3_bucket', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
            )
            
            # Phase 7: Trigger kg-triple-loader
            logger.info(f"Phase 7: Triggering kg-triple-loader for {document_id}")
            self.pipeline_integrator.trigger_kg_triple_loader(document_id, ttl_location)
            
            logger.info(f"Successfully processed {document_id}: {len(successful_alignments)} entities aligned, TTL content generated ({len(ttl_content)} chars)")
            
            return {
                'document_id': document_id,
                'status': 'success',
                'entities_processed': len(entities_by_chunk),
                'entities_aligned': len(successful_alignments),
                'ttl_content_size': len(ttl_content),
                'ttl_location': ttl_location
            }
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {str(e)}")
            raise
    
    def _convert_nlp_results_to_entities(self, nlp_results: Dict[str, Any], document_id: str) -> List[Dict[str, Any]]:
        """
        Convert NLP results to format expected by EntityAlignmentManager.
        
        Args:
            nlp_results: NLP results with entities already mapped to chunks
            document_id: Document identifier
            
        Returns:
            List of entities in format expected by EntityAlignmentManager
        """
        entities = nlp_results.get('entities', [])
        entities_by_chunk = []
        
        for entity in entities:
            # Convert to format expected by EntityAlignmentManager
            # Note: Using actual field names from Comprehend output (lowercase)
            entity_dict = {
                'entity': entity.get('text', ''),                    # Comprehend uses 'text' (lowercase)
                'type': entity.get('type', 'OTHER'),                 # Comprehend uses 'type' (lowercase)
                'score': entity.get('score', 0.0),                   # Comprehend uses 'score' (lowercase)
                'chunk_id': entity.get('chunk_id', ''),              # Already mapped by nlp-worker
                'begin_offset': entity.get('begin_offset', 0),       # Comprehend uses 'begin_offset' (lowercase)
                'end_offset': entity.get('end_offset', 0),           # Comprehend uses 'end_offset' (lowercase)
                'document_id': document_id
            }
            entities_by_chunk.append(entity_dict)
        
        logger.info(f"Converted {len(entities_by_chunk)} entities from NLP results")
        return entities_by_chunk
    
    def _write_ttl_to_s3(self, ttl_content: str, document_id: str, ttl_bucket: str) -> str:
        """
        Write TTL content directly to S3 bucket for kg-triple-loader processing.
        
        Args:
            ttl_content: TTL serialized RDF triples
            document_id: Document identifier
            ttl_bucket: S3 bucket for TTL files (Neptune TTL bucket)
            
        Returns:
            S3 location of saved TTL file
        """
        import boto3
        
        logger.info(f"_write_ttl_to_s3: Received TTL content type: {type(ttl_content)}")
        logger.info(f"_write_ttl_to_s3: Received TTL content length: {len(ttl_content)}")
        logger.info(f"_write_ttl_to_s3: TTL content preview (first 500 chars): {repr(ttl_content[:500])}")
        
        # Save to Neptune TTL bucket with standard path
        s3_key = f"data-lake/{document_id}/entity_triples.ttl"
        
        s3_client = boto3.client('s3')
        
        # Ensure ttl_content is a string and encode properly
        if isinstance(ttl_content, bytes):
            body_content = ttl_content
            logger.info(f"_write_ttl_to_s3: Using bytes content directly")
        else:
            body_content = ttl_content.encode('utf-8')
            logger.info(f"_write_ttl_to_s3: Encoded string to bytes, length: {len(body_content)}")
        
        logger.info(f"_write_ttl_to_s3: Body content type: {type(body_content)}")
        logger.info(f"_write_ttl_to_s3: Body content length: {len(body_content)}")
        
        s3_client.put_object(
            Bucket=ttl_bucket,
            Key=s3_key,
            Body=body_content,
            ContentType='text/turtle'
        )
        
        s3_location = f"s3://{ttl_bucket}/{s3_key}"
        logger.info(f"Saved TTL file to: {s3_location}")
        
        return s3_location
