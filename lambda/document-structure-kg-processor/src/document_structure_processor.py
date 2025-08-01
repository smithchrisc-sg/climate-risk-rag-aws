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
        self.sns_client = boto3.client('sns')
        
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
        
        # SNS topic for downstream processing
        self.kg_triples_ready_topic = os.environ.get('KG_TRIPLES_READY_TOPIC_ARN')
        
        # Set up RDFLib namespaces for semantic schema v3.1
        self.sgd_ns = Namespace("http://solve.global/knowledge-commons/document-structure#")
        self.sgm_ns = Namespace("http://solve.global/knowledge-commons/process-metadata#")
        self.sg_ns = Namespace("http://solve.global/knowledge-commons/")
        self.dcterms_ns = DCTERMS
        
        logger.info(f"Initialized with buckets - chunks: {self.chunks_bucket}, text: {self.text_bucket}, ttl: {self.ttl_bucket}")
        logger.info(f"Neptune endpoint: {os.environ.get('NEPTUNE_ENDPOINT')}")
        logger.info("RDFLib graph building enabled for document structure processing")
    
    def _map_section_type_to_semantic_class(self, section_type: str):
        """Map hierarchical chunker section_type to semantic RDF class"""
        mapping = {
            'title': self.sgd_ns.Section,      # Sections with title content
            'header': self.sgd_ns.Heading,     # Section headings
            'paragraph': self.sgd_ns.Paragraph, # Text paragraphs
            'list': self.sgd_ns.List,          # Enumerated content
            'table': self.sgd_ns.Table,        # Tabular data
            'figure': self.sgd_ns.Figure       # Visual content
        }
        return mapping.get(section_type, self.sgd_ns.DocumentElement)
    
    def _get_chunk_uri(self, chunk_id: str) -> URIRef:
        """Generate consistent chunk URI from chunk_id"""
        if '_chunk_' in chunk_id:
            chunk_number = chunk_id.split('_chunk_')[-1]
        else:
            chunk_number = chunk_id
        return URIRef(f"{self.sg_ns}chunk_{chunk_number}")
    
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
                    
                    # Trigger downstream processing if topic configured
                    integration_result = {'success': True, 'message': 'No kg-triples-ready topic configured'}
                    if self.kg_triples_ready_topic:
                        integration_result = self.trigger_kg_integration(doc_id, ttl_result, s3_result)
                        logger.info(f"SNS integration result: {integration_result}")
                    
                    return {
                        'doc_id': doc_id,
                        'status': 'completed',
                        'ttl_location': s3_result['s3_uri'],
                        'ttl_size': ttl_result['ttl_size'],
                        'chunks_processed': ttl_result['chunks_processed'],
                        'triples_generated': ttl_result['triples_generated'],
                        'sections_processed': ttl_result['sections_processed'],
                        'rdflib_used': True,
                        'integration_result': integration_result
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
            
            # Bind namespaces for semantic schema v3.1
            graph.bind("sgd", self.sgd_ns)
            graph.bind("sgm", self.sgm_ns)
            graph.bind("sg", self.sg_ns)
            graph.bind("dcterms", self.dcterms_ns)
            
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
        """Build document hierarchy using semantic schema v3.1 with Dublin Core inheritance"""
        
        chunks = chunks_data.get('chunks', [])
        if not chunks:
            logger.warning(f"No chunks found for document: {doc_id}")
            return {
                'chunks_processed': 0,
                'sections_processed': 0
            }
        
        logger.info(f"Building document hierarchy using semantic schema v3.1 for {len(chunks)} chunks")
        
        # Generate document URI
        doc_uri = URIRef(f"{self.sg_ns}document_{doc_id}")
        
        # Add document triples using semantic schema
        graph.add((doc_uri, RDF.type, self.sgd_ns.Document))
        graph.add((doc_uri, DCTERMS.identifier, Literal(doc_id)))
        graph.add((doc_uri, DCTERMS.created, Literal(datetime.utcnow().isoformat() + 'Z', datatype=XSD.dateTime)))
        
        chunks_processed = 0
        
        # Process individual chunks
        for chunk in chunks:
            chunk_uri = self._process_single_chunk(chunk, doc_uri, graph)
            if chunk_uri:
                chunks_processed += 1
        
        # Process hierarchical relationships after all chunks are created
        self._process_hierarchical_relationships(chunks, graph)
        
        logger.info(f"Semantic schema v3.1 processing complete: {chunks_processed} chunks")
        logger.info(f"Generated {len(graph)} RDF triples")
        
        return {
            'chunks_processed': chunks_processed,
            'sections_processed': chunks_processed
        }
    
    
    def _process_single_chunk(self, chunk_data: Dict, doc_uri: URIRef, graph: Graph) -> Optional[URIRef]:
        """Process single chunk with semantic class assignment and Dublin Core inheritance"""
        
        chunk_id = chunk_data.get('chunk_id')
        if not chunk_id:
            logger.warning("Chunk missing chunk_id, skipping")
            return None
        
        # Generate chunk URI
        chunk_uri = self._get_chunk_uri(chunk_id)
        
        # Get semantic class from section_type
        section_type = chunk_data.get('section_type', 'paragraph')
        semantic_class = self._map_section_type_to_semantic_class(section_type)
        
        # Add semantic triples
        graph.add((chunk_uri, RDF.type, semantic_class))
        
        # Add Dublin Core relationships (explicit assertion for compatibility)
        graph.add((chunk_uri, DCTERMS.isPartOf, doc_uri))
        graph.add((doc_uri, DCTERMS.hasPart, chunk_uri))
        
        # Add document structure relationships (inherit from Dublin Core)
        graph.add((chunk_uri, self.sgd_ns.hasParent, doc_uri))
        graph.add((doc_uri, self.sgd_ns.hasChild, chunk_uri))
        
        # Add content metadata
        if 'text' in chunk_data and len(chunk_data['text']) > 0:
            # Add title for sections, description for others
            if section_type == 'title':
                graph.add((chunk_uri, DCTERMS.title, Literal(chunk_data['text'])))
            else:
                # Truncate long text for RDF storage
                text_preview = chunk_data['text'][:200] + "..." if len(chunk_data['text']) > 200 else chunk_data['text']
                graph.add((chunk_uri, DCTERMS.description, Literal(text_preview)))
        
        # Process split paragraphs
        if chunk_data.get('is_split_paragraph', False):
            self._process_split_paragraph(chunk_data, chunk_uri, graph)
        
        # Add processing metadata (separate namespace)
        self._add_processing_metadata(chunk_data, chunk_uri, graph)
        
        return chunk_uri
    
    def _process_hierarchical_relationships(self, chunks: List[Dict], graph: Graph):
        """Process hierarchical relationships with Dublin Core inheritance and ordered navigation"""
        
        # Group chunks by parent for relationship processing
        parent_groups = {}
        for chunk in chunks:
            parent_id = chunk.get('parent_chunk_id')
            if parent_id:
                if parent_id not in parent_groups:
                    parent_groups[parent_id] = []
                parent_groups[parent_id].append(chunk)
        
        # Process parent-child relationships
        for parent_id, children in parent_groups.items():
            parent_uri = self._get_chunk_uri(parent_id)
            
            # Sort children by chunk_index for document order
            children.sort(key=lambda x: x.get('chunk_index', 0))
            
            # Add parent-child relationships with Dublin Core inheritance
            for child in children:
                child_uri = self._get_chunk_uri(child['chunk_id'])
                
                # Dublin Core relationships (explicit assertion)
                graph.add((parent_uri, DCTERMS.hasPart, child_uri))
                graph.add((child_uri, DCTERMS.isPartOf, parent_uri))
                
                # Document structure relationships (inherit from Dublin Core)
                graph.add((parent_uri, self.sgd_ns.hasChild, child_uri))
                graph.add((child_uri, self.sgd_ns.hasParent, parent_uri))
            
            # Add convenience relationships
            if len(children) > 0:
                first_child_uri = self._get_chunk_uri(children[0]['chunk_id'])
                last_child_uri = self._get_chunk_uri(children[-1]['chunk_id'])
                
                graph.add((parent_uri, self.sgd_ns.firstChild, first_child_uri))
                graph.add((parent_uri, self.sgd_ns.lastChild, last_child_uri))
            
            # Add nextSibling chain for ordered navigation
            for i in range(len(children) - 1):
                current_uri = self._get_chunk_uri(children[i]['chunk_id'])
                next_uri = self._get_chunk_uri(children[i + 1]['chunk_id'])
                graph.add((current_uri, self.sgd_ns.nextSibling, next_uri))
    
    def _process_split_paragraph(self, chunk_data: Dict, chunk_uri: URIRef, graph: Graph):
        """Handle split paragraph relationships"""
        
        if not chunk_data.get('is_split_paragraph', False):
            return
        
        # This chunk is a paragraph part
        graph.add((chunk_uri, RDF.type, self.sgd_ns.ParagraphPart))
        
        # Add part information
        split_part = chunk_data.get('split_part', 1)
        total_splits = chunk_data.get('total_splits', 1)
        
        graph.add((chunk_uri, self.sgd_ns.partNumber, Literal(split_part, datatype=XSD.positiveInteger)))
        graph.add((chunk_uri, self.sgd_ns.totalParts, Literal(total_splits, datatype=XSD.positiveInteger)))
    
    def _add_processing_metadata(self, chunk_data: Dict, chunk_uri: URIRef, graph: Graph):
        """Add processing metadata in sgm: namespace"""
        
        # Original chunker output
        graph.add((chunk_uri, self.sgm_ns.chunkId, Literal(chunk_data.get('chunk_id', ''))))
        graph.add((chunk_uri, self.sgm_ns.chunkIndex, Literal(chunk_data.get('chunk_index', 0), datatype=XSD.nonNegativeInteger)))
        graph.add((chunk_uri, self.sgm_ns.originalSectionType, Literal(chunk_data.get('section_type', ''))))
        
        # Keep hierarchy level for backward compatibility (but mark as deprecated)
        if 'hierarchy_level' in chunk_data:
            graph.add((chunk_uri, self.sgm_ns.originalHierarchyLevel, Literal(chunk_data['hierarchy_level'], datatype=XSD.positiveInteger)))
        
        # Content metrics
        if 'character_count' in chunk_data:
            graph.add((chunk_uri, self.sgm_ns.characterCount, Literal(chunk_data['character_count'], datatype=XSD.nonNegativeInteger)))
        
        # S3 storage location (processing metadata)
        s3_location = f"s3://{self.chunks_bucket}/data-lake/{chunk_data['doc_id']}/{chunk_data['chunk_id']}.json"
        graph.add((chunk_uri, self.sgm_ns.s3Location, URIRef(s3_location)))
        
        # Page and sequence information (processing artifacts)
        if 'page_numbers' in chunk_data and chunk_data['page_numbers']:
            graph.add((chunk_uri, self.sgm_ns.pageNumber, Literal(chunk_data['page_numbers'][0], datatype=XSD.positiveInteger)))
        
        if 'chunk_index' in chunk_data:
            graph.add((chunk_uri, self.sgm_ns.sequenceNumber, Literal(chunk_data['chunk_index'], datatype=XSD.positiveInteger)))
        
        # Chunking strategy
        graph.add((chunk_uri, self.sgm_ns.chunkingStrategy, Literal("layout_based")))
        
        # Processing timestamp
        graph.add((chunk_uri, self.sgm_ns.processingTimestamp, Literal(datetime.utcnow().isoformat() + 'Z', datatype=XSD.dateTime)))
        
        # Content type counts
        for count_type in ['table_count', 'list_count', 'figure_count']:
            if count_type in chunk_data:
                property_name = count_type.replace('_count', 'Count')
                graph.add((chunk_uri, getattr(self.sgm_ns, property_name), Literal(chunk_data[count_type], datatype=XSD.nonNegativeInteger)))
    
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
            'schema_version': '3.1',
            'dublin_core_inheritance': True,
            'rdflib_enabled': True,
            'kg_layer_version': '1.0.0',
            'namespaces_configured': {
                'sgd': str(self.sgd_ns),
                'sgm': str(self.sgm_ns),
                'sg': str(self.sg_ns),
                'dcterms': str(self.dcterms_ns)
            },
            'buckets_configured': {
                'chunks': self.chunks_bucket,
                'text': self.text_bucket,
                'ttl': self.ttl_bucket
            },
            'graph_building_approach': 'semantic_schema_v3.1_dublin_core_inheritance',
            'relationship_strategy': 'hierarchical_with_ordered_navigation'
        }
    
    def trigger_kg_integration(self, doc_id: str, ttl_result: Dict[str, Any], s3_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger downstream processing with KG integration information"""
        
        try:
            message = {
                'doc_id': doc_id,
                'processing_type': 'kg_triples_ready',
                'ttl_location': s3_result['s3_uri'],
                'ttl_size': ttl_result['ttl_size'],
                'triples_generated': ttl_result['triples_generated'],
                'sections_processed': ttl_result['sections_processed'],
                'chunks_processed': ttl_result['chunks_processed'],
                'schema_version': '3.1',
                'processing_method': 'rdflib_graph_building',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            response = self.sns_client.publish(
                TopicArn=self.kg_triples_ready_topic,
                Message=json.dumps(message),
                Subject=f'KG Triples Ready: Document Structure - {doc_id}',
                MessageAttributes={
                    'processing_type': {
                        'DataType': 'String',
                        'StringValue': 'kg_triples_ready'
                    },
                    'doc_id': {
                        'DataType': 'String',
                        'StringValue': doc_id
                    },
                    'schema_version': {
                        'DataType': 'String',
                        'StringValue': '3.1'
                    }
                }
            )
            
            logger.info(f"Published kg-triples-ready message for {doc_id} to {self.kg_triples_ready_topic}")
            logger.info(f"SNS MessageId: {response['MessageId']}")
            
            return {
                'success': True,
                'message_id': response['MessageId'],
                'topic_arn': self.kg_triples_ready_topic
            }
            
        except Exception as e:
            logger.error(f"Failed to publish kg-triples-ready message for {doc_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
