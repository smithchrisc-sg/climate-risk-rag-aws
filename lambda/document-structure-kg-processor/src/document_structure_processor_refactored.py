#!/usr/bin/env python3
"""
Document Structure Knowledge Graph Processor - Refactored for RDFLib Graph Building
Processes document structure completion events and generates TTL files using proper RDF graph construction

This Lambda function:
1. Receives SNS messages from text chunker completion (chunks_ready)
2. Generates document structure TTL using RDFLib Graph building with Dublin Core vocabulary
3. Uses Knowledge Graph Layer for consistent URI generation and proper RDF triple management
4. Writes TTL files to S3 for decoupled Neptune loading via kg-integration-worker
5. Updates processing status in PostgreSQL

Refactored to use Knowledge Graph Layer v1.0.0 with RDFLib Graph building approach
"""

import json
import boto3
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# RDFLib imports for proper graph handling
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import from standardized layers
try:
    from utils.DatabaseManager import DatabaseManager
    from utils.KnowledgeGraphManager import KnowledgeGraphManager
    logger.info("Successfully imported from standardized layers")
except ImportError as e:
    logger.error(f"Failed to import from layers: {e}")
    raise

class DocumentStructureKGProcessor:
    """Processes document structure for knowledge graph integration using RDFLib Graph building"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        
        # Initialize managers with standardized layers
        try:
            self.db_manager = DatabaseManager()
            self.kg_manager = KnowledgeGraphManager()
            logger.info("Managers initialized successfully")
        except Exception as e:
            logger.error(f"Manager initialization failed: {e}")
            raise
        
        # S3 configuration
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET')
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.ttl_bucket = os.environ.get('TTL_BUCKET')
        
        # Set up RDFLib namespaces for document structure
        self.kr_ns = self.kg_manager.kr_ns
        self.dcterms_ns = self.kg_manager.dcterms_ns
        self.kr_ontology = URIRef("https://solve.global/ontologies/kr/")
        
        logger.info(f"Initialized with buckets - chunks: {self.chunks_bucket}, text: {self.text_bucket}, ttl: {self.ttl_bucket}")
        logger.info(f"Neptune endpoint: {os.environ.get('NEPTUNE_ENDPOINT')}")
        logger.info("RDFLib graph building enabled for document structure processing")
    
    def lambda_handler(self, event, context):
        """Main Lambda handler for document structure KG processing"""
        
        logger.info(f"Processing document structure KG event: {json.dumps(event)}")
        
        try:
            # Parse SNS message
            if 'Records' in event:
                for record in event['Records']:
                    if record.get('EventSource') == 'aws:sns':
                        message = json.loads(record['Sns']['Message'])
                        return self.process_chunks_ready_message(message)
            else:
                # Direct invocation for testing
                return self.process_chunks_ready_message(event)
                
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            raise
    
    def process_chunks_ready_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process chunks_ready message and generate document structure TTL using RDFLib"""
        
        doc_id = message.get('doc_id')
        data_locations = message.get('data_locations', {})
        processing_metadata = message.get('processing_metadata', {})
        
        if not doc_id:
            raise ValueError("doc_id is required in chunks_ready message")
        
        logger.info(f"Processing document structure KG for document: {doc_id}")
        logger.info(f"Chunks location: {data_locations.get('chunks_location')}")
        
        try:
            # Set processing status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_doc_structure',
                status='in_progress'
            )
            
            # Generate document structure TTL using RDFLib graph building
            ttl_result = self.generate_document_structure_ttl_rdflib(
                doc_id, 
                data_locations=data_locations,
                processing_metadata=processing_metadata
            )
            
            if ttl_result['success']:
                # Write TTL to S3 instead of direct Neptune insertion
                s3_result = self.write_ttl_to_s3(
                    doc_id=doc_id,
                    ttl_content=ttl_result['ttl_content']
                )
                
                if s3_result['success']:
                    # Update processing status to completed
                    self.db_manager.set_processing_status(
                        doc_id=doc_id,
                        stage='kg_doc_structure',
                        status='completed',
                        metadata={
                            'ttl_generated': True,
                            'ttl_s3_location': s3_result['s3_uri'],
                            'ttl_size': ttl_result['ttl_size'],
                            'chunks_count': processing_metadata.get('chunks_created', 0),
                            'chunks_processed': ttl_result['chunks_processed'],
                            'triples_generated': ttl_result['triples_generated'],
                            'sections_processed': ttl_result['sections_processed'],
                            'rdflib_used': True,
                            'processing_completed_at': datetime.utcnow().isoformat() + 'Z'
                        }
                    )
                    
                    logger.info(f"Successfully processed document structure KG for {doc_id}")
                    logger.info(f"TTL written to: {s3_result['s3_uri']}")
                    logger.info(f"Generated {ttl_result['triples_generated']} triples from {ttl_result['sections_processed']} sections")
                    
                    return {
                        'doc_id': doc_id,
                        'status': 'completed',
                        'ttl_location': s3_result['s3_uri'],
                        'ttl_size': ttl_result['ttl_size'],
                        'chunks_processed': ttl_result['chunks_processed'],
                        'triples_generated': ttl_result['triples_generated'],
                        'sections_processed': ttl_result['sections_processed'],
                        'rdflib_used': True
                    }
                else:
                    # S3 write failed
                    self.db_manager.set_processing_status(
                        doc_id=doc_id,
                        stage='kg_doc_structure',
                        status='failed',
                        metadata={
                            'error': s3_result['error'],
                            'failed_at': datetime.utcnow().isoformat() + 'Z'
                        }
                    )
                    
                    logger.error(f"Failed to write TTL to S3 for {doc_id}: {s3_result['error']}")
                    return {
                        'doc_id': doc_id,
                        'status': 'failed',
                        'error': s3_result['error']
                    }
            else:
                # TTL generation failed
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='kg_doc_structure',
                    status='failed',
                    metadata={
                        'error': ttl_result['error'],
                        'failed_at': datetime.utcnow().isoformat() + 'Z'
                    }
                )
                
                logger.error(f"Failed to generate TTL for {doc_id}: {ttl_result['error']}")
                return {
                    'doc_id': doc_id,
                    'status': 'failed',
                    'error': ttl_result['error']
                }
                
        except Exception as e:
            # Update processing status to failed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_doc_structure',
                status='failed',
                metadata={
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat() + 'Z'
                }
            )
            
            logger.error(f"Error processing document structure KG for {doc_id}: {str(e)}")
            raise
    
    def write_ttl_to_s3(self, doc_id: str, ttl_content: str) -> Dict[str, Any]:
        """Write TTL content to S3 for Neptune loading"""
        
        try:
            # S3 key: data-lake/{doc_id}/{doc_id}_document_structure.ttl
            s3_key = f"data-lake/{doc_id}/{doc_id}_document_structure.ttl"
            
            logger.info(f"Writing TTL to S3: s3://{self.ttl_bucket}/{s3_key}")
            
            # Write TTL content to S3
            self.s3_client.put_object(
                Bucket=self.ttl_bucket,
                Key=s3_key,
                Body=ttl_content.encode('utf-8'),
                ContentType='text/turtle',
                Metadata={
                    'doc_id': doc_id,
                    'content_type': 'document_structure',
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'rdflib_generated': 'true'
                }
            )
            
            s3_uri = f"s3://{self.ttl_bucket}/{s3_key}"
            logger.info(f"TTL successfully written to: {s3_uri} ({len(ttl_content)} bytes)")
            
            return {
                'success': True,
                's3_uri': s3_uri,
                'bucket': self.ttl_bucket,
                'key': s3_key,
                'size': len(ttl_content)
            }
            
        except Exception as e:
            logger.error(f"Failed to write TTL to S3: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_document_structure_ttl_rdflib(self, doc_id: str, data_locations: Dict = None, 
                                             processing_metadata: Dict = None) -> Dict[str, Any]:
        """Generate TTL for document structure using RDFLib Graph building"""
        
        try:
            logger.info(f"Generating TTL using RDFLib for document structure: {doc_id}")
            
            # Load document chunks and metadata
            chunks_data = self.load_document_chunks(doc_id, data_locations)
            
            # Create RDFLib graph for document structure
            graph = self.kg_manager.create_graph()
            
            # Build document hierarchy using RDFLib graph operations
            result = self.build_document_hierarchy_rdflib(doc_id, chunks_data, graph)
            
            # Serialize graph to TTL
            ttl_content = graph.serialize(format='turtle')
            if isinstance(ttl_content, bytes):
                ttl_content = ttl_content.decode('utf-8')
            
            logger.info(f"Generated TTL content ({len(ttl_content)} characters) for document: {doc_id}")
            logger.info(f"Graph contains {len(graph)} triples")
            
            return {
                'success': True,
                'ttl_content': ttl_content,
                'ttl_size': len(ttl_content),
                'chunks_processed': result['chunks_processed'],
                'triples_generated': len(graph),
                'sections_processed': result['sections_processed']
            }
            
        except Exception as e:
            logger.error(f"Error generating RDFLib TTL for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_document_chunks(self, doc_id: str, data_locations: Dict = None) -> Dict[str, Any]:
        """Load document chunks from S3"""
        
        try:
            chunks_location = data_locations.get('chunks_location') if data_locations else None
            
            if not chunks_location:
                # Fallback to standard location
                chunks_location = f"s3://{self.chunks_bucket}/data-lake/{doc_id}/"
            
            # Parse S3 location
            if chunks_location.startswith('s3://'):
                bucket_and_prefix = chunks_location[5:]
                bucket, prefix = bucket_and_prefix.split('/', 1)
            else:
                raise ValueError(f"Invalid chunks location format: {chunks_location}")
            
            # List chunk files
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            chunks = []
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json') and not obj['Key'].endswith('metadata.json'):
                    # Load chunk content
                    chunk_response = self.s3_client.get_object(
                        Bucket=bucket,
                        Key=obj['Key']
                    )
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    chunks.append(chunk_data)
            
            logger.info(f"Loaded {len(chunks)} chunks for RDFLib processing")
            
            return {
                'chunks': chunks,
                'chunks_location': chunks_location
            }
            
        except Exception as e:
            logger.error(f"Error loading chunks for {doc_id}: {str(e)}")
            raise
    
    def build_document_hierarchy_rdflib(self, doc_id: str, chunks_data: Dict[str, Any], 
                                       graph: Graph) -> Dict[str, Any]:
        """Build document hierarchy using RDFLib Graph operations instead of string concatenation"""
        
        chunks = chunks_data.get('chunks', [])
        if not chunks:
            logger.warning(f"No chunks found for document: {doc_id}")
            return {
                'chunks_processed': 0,
                'sections_processed': 0
            }
        
        logger.info(f"Building document hierarchy using RDFLib for {len(chunks)} chunks")
        
        # Generate document URI using KG layer
        doc_uri = self.kg_manager.mint_uri(
            unique_id=doc_id,
            namespace=self.kr_ns,
            ontology_concept="Document",
            ontology_uri=self.kr_ontology
        )
        
        # Add document triples using RDFLib
        graph.add((doc_uri, RDF.type, self.kr_ns.Document))
        graph.add((doc_uri, DCTERMS.identifier, Literal(doc_id)))
        graph.add((doc_uri, DCTERMS.created, Literal(datetime.utcnow().isoformat() + 'Z', datatype=XSD.dateTime)))
        
        # Group chunks by section
        sections = {}
        for chunk in chunks:
            section_title = chunk.get('section_title', 'Main Content')
            section_sequence = chunk.get('section_sequence', 1)
            
            if section_title not in sections:
                sections[section_title] = {
                    'sequence': section_sequence,
                    'chunks': []
                }
            sections[section_title]['chunks'].append(chunk)
        
        logger.info(f"Processing {len(sections)} sections for document: {doc_id}")
        
        # Process sections and chunks using RDFLib
        sections_processed = 0
        chunks_processed = 0
        
        for section_title, section_data in sections.items():
            # Generate section URI using KG layer generic mint_uri
            section_id = f"{doc_id}_section_{hash(section_title) % 1000000}"
            section_uri = self.kg_manager.mint_uri(
                unique_id=section_id,
                namespace=self.kr_ns,
                ontology_concept="DocumentSection",
                ontology_uri=self.kr_ontology
            )
            
            section_sequence = section_data['sequence']
            
            # Add section triples using RDFLib
            graph.add((section_uri, RDF.type, self.kr_ns.DocumentSection))
            graph.add((section_uri, DCTERMS.title, Literal(section_title)))
            graph.add((section_uri, self.kr_ns.parentDocument, doc_uri))
            graph.add((section_uri, self.kr_ns.sectionSequence, Literal(section_sequence, datatype=XSD.integer)))
            
            sections_processed += 1
            
            # Process chunks for this section using RDFLib
            for chunk in section_data['chunks']:
                chunk_id = chunk.get('chunk_id')
                if chunk_id:
                    # Generate chunk URI using KG layer
                    chunk_uri = self.kg_manager.mint_uri(
                        unique_id=f"{doc_id}_{chunk_id}",
                        namespace=self.kr_ns,
                        ontology_concept="DocumentChunk",
                        ontology_uri=self.kr_ontology
                    )
                    
                    chunk_sequence = chunk.get('chunk_sequence', 1)
                    
                    # Add chunk triples using RDFLib
                    graph.add((chunk_uri, RDF.type, self.kr_ns.DocumentChunk))
                    graph.add((chunk_uri, DCTERMS.identifier, Literal(chunk_id)))
                    graph.add((chunk_uri, self.kr_ns.parentSection, section_uri))
                    graph.add((chunk_uri, self.kr_ns.parentDocument, doc_uri))
                    graph.add((chunk_uri, self.kr_ns.chunkSequence, Literal(chunk_sequence, datatype=XSD.integer)))
                    
                    # Add content length if available
                    if 'content' in chunk:
                        content_length = len(chunk['content'])
                        graph.add((chunk_uri, self.kr_ns.contentLength, Literal(content_length, datatype=XSD.integer)))
                    
                    # Add chunk text if available (for debugging/analysis)
                    if 'content' in chunk and len(chunk['content']) < 1000:  # Only for small chunks
                        graph.add((chunk_uri, self.kr_ns.hasText, Literal(chunk['content'][:500])))  # Truncate for safety
                    
                    # Add creation timestamp
                    graph.add((chunk_uri, DCTERMS.created, Literal(datetime.utcnow().isoformat() + 'Z', datatype=XSD.dateTime)))
                    
                    chunks_processed += 1
        
        logger.info(f"RDFLib processing complete: {sections_processed} sections, {chunks_processed} chunks")
        logger.info(f"Generated {len(graph)} RDF triples")
        
        return {
            'chunks_processed': chunks_processed,
            'sections_processed': sections_processed
        }
    
    def validate_generated_ttl(self, ttl_content: str) -> Dict[str, Any]:
        """Validate generated TTL using RDFLib parsing"""
        
        try:
            # Use RDFLib to parse and validate the generated TTL
            test_graph = Graph()
            test_graph.parse(data=ttl_content, format='turtle')
            
            validation_result = {
                'valid': True,
                'triples_count': len(test_graph),
                'namespaces_used': len(list(test_graph.namespaces())),
                'validation_method': 'rdflib_parsing'
            }
            
            logger.info(f"TTL validation successful: {validation_result['triples_count']} triples, {validation_result['namespaces_used']} namespaces")
            return validation_result
            
        except Exception as e:
            logger.error(f"TTL validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'validation_method': 'rdflib_parsing'
            }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics for monitoring"""
        
        return {
            'processor_type': 'DocumentStructureKGProcessor',
            'rdflib_enabled': True,
            'kg_layer_version': '1.0.0',
            'namespaces_configured': {
                'kr': str(self.kr_ns),
                'dcterms': str(self.dcterms_ns)
            },
            'buckets_configured': {
                'chunks': self.chunks_bucket,
                'text': self.text_bucket,
                'ttl': self.ttl_bucket
            },
            'graph_building_approach': 'rdflib_native',
            'uri_generation': 'kg_layer_generic_mint_uri'
        }
