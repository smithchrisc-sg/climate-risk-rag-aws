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
        """
        document_id = request['document_id']
        logger.info(f"Processing document: {document_id}")
        
        try:
            # Phase 3: Data Retrieval
            logger.info(f"Phase 3: Retrieving data for {document_id}")
            nlp_results = self.data_retriever.retrieve_nlp_results(request)
            chunks_data = self.data_retriever.retrieve_chunks_data(request)
            
            # Phase 4: Entity-Chunk Mapping
            logger.info(f"Phase 4: Mapping entities to chunks for {document_id}")
            entity_chunk_mappings = components['nlp_kg_integrator'].map_entities_to_chunks(
                nlp_results, chunks_data
            )
            
            # Phase 5: Ontology Alignment (before URI generation for efficiency)
            logger.info(f"Phase 5: Aligning entities with ontologies for {document_id}")
            aligned_entities = components['entity_aligner'].align_entities_to_ontologies(
                entity_chunk_mappings,
                components['climate_ontology'],
                components['geonames_ontology']
            )
            
            # Filter out entities that didn't align to any ontology
            aligned_entities = [entity for entity in aligned_entities if entity.get('ontology_alignment')]
            
            if not aligned_entities:
                logger.warning(f"No entities aligned to ontologies for {document_id}")
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'message': 'No alignable entities found',
                    'entities_processed': 0,
                    'triples_generated': 0
                }
            
            # Phase 6: URI Generation
            logger.info(f"Phase 6: Generating URIs for {len(aligned_entities)} aligned entities")
            entities_with_uris = components['uri_manager'].generate_uris_for_entities(
                aligned_entities, document_id
            )
            
            # Phase 7: Knowledge Graph Construction
            logger.info(f"Phase 7: Constructing knowledge graph for {document_id}")
            triples = components['triple_manager'].create_triples_from_entities(
                entities_with_uris, document_id
            )
            
            # Phase 8: Data Persistence and Pipeline Integration
            logger.info(f"Phase 8: Persisting {len(triples)} triples for {document_id}")
            output_location = self.pipeline_integrator.persist_knowledge_graph_data(
                document_id, triples, request['s3_bucket']
            )
            
            # Trigger next stage of pipeline (kg-triple-loader)
            self.pipeline_integrator.trigger_kg_triple_loader(document_id, output_location)
            
            logger.info(f"Successfully processed {document_id}: {len(aligned_entities)} entities, {len(triples)} triples")
            
            return {
                'document_id': document_id,
                'status': 'success',
                'entities_processed': len(aligned_entities),
                'triples_generated': len(triples),
                'output_location': output_location
            }
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {str(e)}")
            raise
