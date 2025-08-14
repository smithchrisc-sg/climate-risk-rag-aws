"""
Simplified Document Processor

Implements the streamlined entity alignment flow:
1. Retrieve NLP results (entities already mapped to chunks)
2. FTS SPARQL alignment for LOCATION entities only
3. Generate triples using aligned URIs
4. Serialize to TTL and trigger kg-triple-loader
"""

import logging
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Simplified document processor focused on LOCATION entity alignment using FTS SPARQL.
    """
    
    def __init__(self, data_retriever, pipeline_integrator):
        self.data_retriever = data_retriever
        self.pipeline_integrator = pipeline_integrator
    
    def process_document_request(self, request: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document through simplified entity alignment flow.
        
        Args:
            request: Document processing request with S3 locations
            components: Initialized layer components
            
        Returns:
            Processing result with status and output locations
        """
        document_id = request['document_id']
        logger.info(f"Processing document: {document_id}")
        
        try:
            # Phase 3: Data Retrieval (NLP results only - chunks mapping already done)
            logger.info(f"Phase 3: Retrieving NLP results for {document_id}")
            nlp_results = self.data_retriever.retrieve_nlp_results(request)
            
            # Filter for LOCATION entities only (as per requirements)
            location_entities = self._filter_location_entities(nlp_results)
            
            if not location_entities:
                logger.info(f"No LOCATION entities found for {document_id}")
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'message': 'No LOCATION entities to process',
                    'entities_processed': 0,
                    'triples_generated': 0
                }
            
            logger.info(f"Found {len(location_entities)} LOCATION entities to process")
            
            # Phase 5: Ontology Alignment using FTS SPARQL (GeoNames only)
            logger.info(f"Phase 5: Aligning LOCATION entities using FTS SPARQL")
            aligned_entities = self._align_location_entities_fts(
                location_entities, components['kg_manager']
            )
            
            # Filter out entities that didn't align
            successful_alignments = [e for e in aligned_entities if e.get('aligned_uri')]
            
            if not successful_alignments:
                logger.warning(f"No entities successfully aligned for {document_id}")
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'message': 'No entities successfully aligned',
                    'entities_processed': len(location_entities),
                    'triples_generated': 0
                }
            
            # Phase 7: KG Construction (Triple generation)
            logger.info(f"Phase 7: Generating triples for {len(successful_alignments)} aligned entities")
            triples = self._generate_triples(
                successful_alignments, document_id, components['uri_manager']
            )
            
            # Phase 8: Serialize to TTL and save to S3
            logger.info(f"Phase 8: Serializing {len(triples)} triples to TTL")
            ttl_location = self._serialize_and_save_ttl(
                triples, document_id, request.get('s3_bucket', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
            )
            
            # Phase 9: Trigger kg-triple-loader
            logger.info(f"Phase 9: Triggering kg-triple-loader for {document_id}")
            self.pipeline_integrator.trigger_kg_triple_loader(document_id, ttl_location)
            
            logger.info(f"Successfully processed {document_id}: {len(successful_alignments)} entities aligned, {len(triples)} triples generated")
            
            return {
                'document_id': document_id,
                'status': 'success',
                'entities_processed': len(location_entities),
                'entities_aligned': len(successful_alignments),
                'triples_generated': len(triples),
                'ttl_location': ttl_location
            }
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {str(e)}")
            raise
    
    def _filter_location_entities(self, nlp_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter NLP results to only include LOCATION entities.
        
        Args:
            nlp_results: NLP results with entities already mapped to chunks
            
        Returns:
            List of LOCATION entities with chunk mappings
        """
        entities = nlp_results.get('entities', [])
        location_entities = []
        
        for entity in entities:
            if entity.get('Type') == 'LOCATION':
                location_entities.append({
                    'text': entity.get('Text', ''),
                    'type': entity.get('Type'),
                    'score': entity.get('Score', 0.0),
                    'chunk_id': entity.get('chunk_id'),  # Already mapped by nlp-worker
                    'begin_offset': entity.get('BeginOffset'),
                    'end_offset': entity.get('EndOffset')
                })
        
        return location_entities
    
    def _align_location_entities_fts(self, entities: List[Dict[str, Any]], kg_manager) -> List[Dict[str, Any]]:
        """
        Align LOCATION entities using FTS SPARQL queries against GeoNames.
        
        Args:
            entities: List of LOCATION entities to align
            kg_manager: KnowledgeGraphManager for SPARQL queries
            
        Returns:
            List of entities with alignment results
        """
        aligned_entities = []
        
        for entity in entities:
            entity_text = entity['text']
            logger.debug(f"Aligning LOCATION entity: {entity_text}")
            
            try:
                # Simple FTS SPARQL query for GeoNames
                sparql_query = f"""
                PREFIX gn: <http://www.geonames.org/ontology#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?entity ?label ?country ?featureClass ?lat ?lon WHERE {{
                    ?entity fts:search "{entity_text}" .
                    ?entity rdfs:label ?label .
                    ?entity gn:countryCode ?country .
                    ?entity gn:featureClass ?featureClass .
                    ?entity gn:lat ?lat .
                    ?entity gn:long ?lon .
                }}
                ORDER BY DESC(fts:score(?entity))
                LIMIT 5
                """
                
                # Execute FTS SPARQL query
                results = kg_manager.execute_sparql_query(sparql_query)
                
                if results and len(results) > 0:
                    # Take the top result (highest FTS score)
                    best_match = results[0]
                    
                    aligned_entity = entity.copy()
                    aligned_entity.update({
                        'aligned_uri': best_match.get('entity'),
                        'aligned_label': best_match.get('label'),
                        'country': best_match.get('country'),
                        'feature_class': best_match.get('featureClass'),
                        'latitude': best_match.get('lat'),
                        'longitude': best_match.get('lon'),
                        'alignment_method': 'fts_sparql',
                        'alignment_score': 1.0  # FTS provides the scoring
                    })
                    
                    aligned_entities.append(aligned_entity)
                    logger.debug(f"Successfully aligned {entity_text} to {best_match.get('entity')}")
                else:
                    logger.debug(f"No alignment found for {entity_text}")
                    aligned_entities.append(entity)  # Keep original without alignment
                    
            except Exception as e:
                logger.warning(f"Failed to align entity {entity_text}: {str(e)}")
                aligned_entities.append(entity)  # Keep original without alignment
        
        return aligned_entities
    
    def _generate_triples(self, aligned_entities: List[Dict[str, Any]], document_id: str, uri_manager) -> List[str]:
        """
        Generate RDF triples for aligned entities.
        
        Args:
            aligned_entities: Entities with alignment information
            document_id: Document identifier
            uri_manager: URI manager for generating chunk URIs
            
        Returns:
            List of RDF triples in N-Triples format
        """
        triples = []
        
        for entity in aligned_entities:
            if not entity.get('aligned_uri'):
                continue
                
            # Generate chunk URI (idempotent)
            chunk_uri = uri_manager.generate_chunk_uri(document_id, entity['chunk_id'])
            
            # Create triple: chunk hasLocation aligned_location_uri
            triple = f"<{chunk_uri}> <https://solve.global/kr/hasLocation> <{entity['aligned_uri']}> ."
            triples.append(triple)
            
            logger.debug(f"Generated triple: {chunk_uri} hasLocation {entity['aligned_uri']}")
        
        return triples
    
    def _serialize_and_save_ttl(self, triples: List[str], document_id: str, ttl_bucket: str) -> str:
        """
        Serialize triples to TTL format and save to S3.
        
        Args:
            triples: List of RDF triples
            document_id: Document identifier
            ttl_bucket: S3 bucket for TTL files
            
        Returns:
            S3 location of saved TTL file
        """
        # Create TTL content with prefixes
        ttl_content = """@prefix kr: <https://solve.global/kr/> .
@prefix gn: <http://www.geonames.org/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

"""
        
        # Add triples (convert N-Triples to TTL format)
        for triple in triples:
            # Simple conversion - could be enhanced
            ttl_content += triple + "\n"
        
        # Save to S3
        s3_key = f"data-lake/{document_id}/entity_triples.ttl"
        
        import boto3
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
