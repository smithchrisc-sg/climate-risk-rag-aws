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
            # Phase 3: Data Retrieval (NLP results only - entities already mapped to chunks by nlp-worker)
            logger.info(f"Phase 3: Retrieving NLP results for {document_id}")
            nlp_results = self.data_retriever.retrieve_nlp_results(request)
            
            # Phase 5: Ontology Alignment using EntityAlignmentManager (handles TYPE/ontology mapping via env vars)
            logger.info(f"Phase 5: Aligning entities with ontologies for {document_id}")
            
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
            
            # Phase 7: Knowledge Graph Construction (Triple generation)
            logger.info(f"Phase 7: Constructing knowledge graph for {len(successful_alignments)} aligned entities")
            triples = components['triple_manager'].create_triples_from_entities(
                successful_alignments, document_id
            )
            
            # Phase 8: Serialize to TTL and save to Neptune TTL bucket
            logger.info(f"Phase 8: Serializing {len(triples)} triples to TTL")
            ttl_location = self._serialize_triples_to_ttl(
                triples, document_id, request.get('s3_bucket', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
            )
            
            # Phase 9: Trigger kg-triple-loader
            logger.info(f"Phase 9: Triggering kg-triple-loader for {document_id}")
            self.pipeline_integrator.trigger_kg_triple_loader(document_id, ttl_location)
            
            logger.info(f"Successfully processed {document_id}: {len(successful_alignments)} entities aligned, {len(triples)} triples generated")
            
            return {
                'document_id': document_id,
                'status': 'success',
                'entities_processed': len(entities_by_chunk),
                'entities_aligned': len(successful_alignments),
                'triples_generated': len(triples),
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
            entity_dict = {
                'entity': entity.get('Text', ''),
                'type': entity.get('Type', 'OTHER'),
                'score': entity.get('Score', 0.0),
                'chunk_id': entity.get('chunk_id', ''),  # Already mapped by nlp-worker
                'begin_offset': entity.get('BeginOffset', 0),
                'end_offset': entity.get('EndOffset', 0),
                'document_id': document_id
            }
            entities_by_chunk.append(entity_dict)
        
        logger.info(f"Converted {len(entities_by_chunk)} entities from NLP results")
        return entities_by_chunk
    
    def _serialize_triples_to_ttl(self, triples: List[str], document_id: str, ttl_bucket: str) -> str:
        """
        Serialize triples to TTL format and save to S3 Neptune TTL bucket.
        
        Args:
            triples: List of RDF triples
            document_id: Document identifier
            ttl_bucket: S3 bucket for TTL files (Neptune TTL bucket)
            
        Returns:
            S3 location of saved TTL file
        """
        import boto3
        
        # Create TTL content with standard prefixes
        ttl_content = """@prefix kr: <https://solve.global/kr/> .
@prefix gn: <http://www.geonames.org/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

"""
        
        # Add triples
        for triple in triples:
            ttl_content += triple + "\n"
        
        # Save to Neptune TTL bucket with standard path
        s3_key = f"data-lake/{document_id}/entity_triples.ttl"
        
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=ttl_bucket,
            Key=s3_key,
            Body=ttl_content.encode('utf-8'),
            ContentType='text/turtle'
        )
        
        s3_location = f"s3://{ttl_bucket}/{s3_key}"
        logger.info(f"Saved TTL file to: {s3_location}")
        
        return s3_location
