#!/usr/bin/env python3
"""
Document Structure Knowledge Graph Processor - Refactored
Processes document structure completion events and generates TTL for Neptune loading

This Lambda function:
1. Receives SNS messages from text chunker completion (chunks_ready)
2. Generates document structure TTL using Dublin Core vocabulary AND document structure ontology
3. Uses Knowledge Graph Layer for consistent URI generation and triple management
4. Leverages bulk load optimization for large documents
5. Updates processing status in PostgreSQL

Refactored to use Knowledge Graph Layer v1.0.0
"""

import json
import boto3
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

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
    """Processes document structure for knowledge graph integration using KG Layer"""
    
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
        
        # S3 buckets from environment
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        
        # SNS topics for downstream processing
        self.kg_triples_ready_topic = os.environ.get('KG_TRIPLES_READY_TOPIC_ARN')
        
        logger.info(f"Initialized with buckets - chunks: {self.chunks_bucket}, text: {self.text_bucket}")
        logger.info(f"Neptune endpoint: {self.kg_manager.neptune_endpoint}")
        
    def lambda_handler(self, event, context):
        """Main Lambda handler for document structure KG processing"""
        
        try:
            logger.info(f"Processing document structure KG event: {json.dumps(event, default=str)}")
            
            # Parse SNS message
            records = event.get('Records', [])
            results = []
            
            for record in records:
                if record.get('EventSource') == 'aws:sns':
                    # Parse the SNS message
                    sns_message = record['Sns']['Message']
                    message = json.loads(sns_message)
                    result = self.process_chunks_ready_message(message)
                    results.append(result)
                else:
                    logger.warning(f"Unexpected event source: {record.get('EventSource')}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Document structure KG processing completed',
                    'processed_count': len(results),
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error(f"Error in document structure KG processing: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e),
                    'message': 'Document structure KG processing failed'
                })
            }
    
    def process_chunks_ready_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chunks_ready message for document structure KG generation"""
        
        doc_id = None
        try:
            # Validate message format
            if message.get('stage') != 'chunks_ready':
                logger.warning(f"Unexpected message stage: {message.get('stage')}")
                return {
                    'status': 'skipped',
                    'reason': f'Message stage is {message.get("stage")}, expected chunks_ready'
                }
            
            doc_id = message.get('doc_id')
            if not doc_id:
                raise ValueError("Missing doc_id in chunks_ready message")
            
            data_locations = message.get('data_locations', {})
            processing_metadata = message.get('processing_metadata', {})
            
            logger.info(f"Processing document structure KG for document: {doc_id}")
            logger.info(f"Chunks location: {data_locations.get('chunks_location')}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_doc_structure',
                status='in_progress'
            )
            
            # Generate document structure TTL using KG layer
            ttl_result = self.generate_document_structure_ttl(
                doc_id, 
                data_locations=data_locations,
                processing_metadata=processing_metadata
            )
            
            if ttl_result['success']:
                # Use KG layer's optimized insertion (automatically chooses SPARQL vs bulk load)
                insertion_result = self.kg_manager.triple_manager.insert_triples_optimized(
                    ttl_content=ttl_result['ttl_content'],
                    s3_key_prefix=f"document-structure/{doc_id}"
                )
                
                # Trigger downstream processing if topic configured
                integration_result = {'success': True, 'message': 'No kg-triples-ready topic configured'}
                if self.kg_triples_ready_topic:
                    integration_result = self.trigger_kg_integration(doc_id, ttl_result, insertion_result)
                
                # Update processing status to completed
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='kg_doc_structure',
                    status='completed',
                    metadata={
                        'ttl_generated': True,
                        'insertion_method': insertion_result['method'],
                        'records_processed': insertion_result.get('records_loaded', insertion_result.get('estimated_records', 0)),
                        'integration_triggered': integration_result['success'],
                        'chunks_count': processing_metadata.get('chunks_created', 0),
                        'processing_completed_at': datetime.utcnow().isoformat() + 'Z',
                        's3_location': insertion_result.get('s3_uri'),  # Only present for bulk load
                        'ttl_size': ttl_result['ttl_size']
                    }
                )
                
                logger.info(f"Successfully processed document structure KG for {doc_id} using {insertion_result['method']}")
                
                return {
                    'doc_id': doc_id,
                    'status': 'success',
                    'insertion_method': insertion_result['method'],
                    'records_processed': insertion_result.get('records_loaded', insertion_result.get('estimated_records', 0)),
                    'integration_triggered': integration_result['success']
                }
            else:
                # Update status to failed
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='kg_doc_structure',
                    status='failed',
                    metadata={
                        'error': ttl_result['error'],
                        'failed_at': datetime.utcnow().isoformat() + 'Z'
                    }
                )
                
                logger.error(f"TTL generation failed for {doc_id}: {ttl_result['error']}")
                return {
                    'doc_id': doc_id,
                    'status': 'failed',
                    'error': ttl_result['error']
                }
                
        except Exception as e:
            logger.error(f"Error processing chunks_ready message for {doc_id}: {str(e)}")
            
            # Update status to failed
            if doc_id:
                try:
                    self.db_manager.set_processing_status(
                        doc_id=doc_id,
                        stage='kg_doc_structure',
                        status='failed',
                        metadata={
                            'error': str(e),
                            'failed_at': datetime.utcnow().isoformat() + 'Z'
                        }
                    )
                except Exception as db_error:
                    logger.error(f"Failed to update database status: {db_error}")
            
            return {
                'doc_id': doc_id or 'unknown',
                'status': 'error',
                'error': str(e)
            }
    
    def generate_document_structure_ttl(self, doc_id: str, data_locations: Dict = None, processing_metadata: Dict = None) -> Dict[str, Any]:
        """Generate TTL for document structure using Dublin Core AND document structure ontology"""
        
        try:
            logger.info(f"Generating TTL for document structure: {doc_id}")
            
            # Load document chunks and metadata
            chunks_data = self.load_chunks_data(data_locations)
            
            # Generate document URI using KG layer
            doc_uri = self.kg_manager.mint_document_uri(doc_id)
            
            # Get TTL prefixes from KG layer
            prefixes = self.kg_manager.uri_manager.get_prefixes_ttl()
            
            # Add document structure ontology prefix
            prefixes += "\n@prefix ds: <http://solve.global/ontology/document-structure/> ."
            
            # Build document metadata using Dublin Core + document structure ontology
            document_metadata = self.build_document_metadata(doc_id, chunks_data, processing_metadata)
            
            # Insert document metadata using KG layer
            self.kg_manager.insert_document_triples(doc_id, document_metadata)
            
            # Build chunk triples with document structure concepts
            chunk_triples = self.build_chunk_triples(doc_id, chunks_data)
            
            # Combine all TTL content
            ttl_content = prefixes + "\n\n" + chunk_triples
            
            logger.info(f"Generated TTL content ({len(ttl_content)} characters) for document: {doc_id}")
            
            return {
                'success': True,
                'ttl_content': ttl_content,
                'ttl_size': len(ttl_content),
                'chunks_processed': len(chunks_data.get('chunks', []))
            }
            
        except Exception as e:
            logger.error(f"Error generating TTL for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_chunks_data(self, data_locations: Dict = None) -> Dict[str, Any]:
        """Load chunks and metadata from S3"""
        
        try:
            chunks_data = {
                'chunks': [],
                'metadata': {},
                'document_info': {}
            }
            
            chunks_location = data_locations.get('chunks_location', '') if data_locations else ''
            
            if chunks_location and chunks_location.startswith('s3://'):
                # Parse S3 location
                bucket_and_prefix = chunks_location[5:]
                bucket_name = bucket_and_prefix.split('/')[0]
                prefix = '/'.join(bucket_and_prefix.split('/')[1:])
                
                # List all chunk files
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=prefix
                )
                
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('.json'):
                        if key.endswith('metadata.json'):
                            # Load metadata
                            metadata_obj = self.s3_client.get_object(Bucket=bucket_name, Key=key)
                            chunks_data['metadata'] = json.loads(metadata_obj['Body'].read().decode('utf-8'))
                        elif 'chunk_' in key:
                            # Load chunk
                            chunk_obj = self.s3_client.get_object(Bucket=bucket_name, Key=key)
                            chunk_data = json.loads(chunk_obj['Body'].read().decode('utf-8'))
                            chunks_data['chunks'].append(chunk_data)
            
            # Sort chunks by chunk_id for consistent ordering
            chunks_data['chunks'].sort(key=lambda x: x.get('chunk_id', ''))
            
            logger.info(f"Loaded {len(chunks_data['chunks'])} chunks")
            return chunks_data
            
        except Exception as e:
            logger.error(f"Error loading chunks data: {str(e)}")
            return {'chunks': [], 'metadata': {}, 'document_info': {}}
    
    def build_document_metadata(self, doc_id: str, chunks_data: Dict, processing_metadata: Dict = None) -> Dict[str, Any]:
        """Build document metadata using Dublin Core vocabulary"""
        
        metadata = {
            'identifier': doc_id,
            'created': datetime.utcnow().isoformat() + 'Z',
            'modified': datetime.utcnow().isoformat() + 'Z',
            'type': 'Text'
        }
        
        # Add metadata from chunks data
        doc_metadata = chunks_data.get('metadata', {})
        if doc_metadata:
            document_info = doc_metadata.get('document_info', {})
            if document_info.get('title'):
                metadata['title'] = document_info['title']
            if document_info.get('source_url'):
                metadata['source'] = document_info['source_url']
        
        # Add processing metadata
        if processing_metadata:
            chunks_created = processing_metadata.get('chunks_created', 0)
            metadata['extent'] = f"{chunks_created} chunks"
        
        return metadata
    
    def build_chunk_triples(self, doc_id: str, chunks_data: Dict) -> str:
        """Build chunk triples with document structure ontology concepts"""
        
        chunk_triples = []
        doc_uri = self.kg_manager.mint_document_uri(doc_id)
        
        for i, chunk in enumerate(chunks_data.get('chunks', [])):
            chunk_id = chunk.get('chunk_id', f'chunk_{i:03d}')
            chunk_uri = self.kg_manager.mint_chunk_uri(doc_id, chunk_id)
            
            # Basic chunk metadata
            triples = [
                f"<{chunk_uri}> a ds:DocumentChunk ;",
                f"    dcterms:identifier \"{chunk_id}\" ;",
                f"    dcterms:isPartOf <{doc_uri}> ;",
                f"    ds:chunkIndex {i} ;"
            ]
            
            # Add content information
            content = chunk.get('content', '')
            if content:
                # Escape content for TTL
                escaped_content = self.escape_ttl_string(content[:500] + ('...' if len(content) > 500 else ''))
                triples.append(f'    dcterms:abstract "{escaped_content}" ;')
                triples.append(f'    ds:contentLength {len(content)} ;')
            
            # Add document structure concepts
            if chunk.get('section_title'):
                triples.append(f'    ds:sectionTitle "{self.escape_ttl_string(chunk["section_title"])}" ;')
                triples.append(f'    ds:hasStructuralRole ds:SectionContent ;')
            
            if chunk.get('chunk_type'):
                chunk_type = chunk['chunk_type']
                if chunk_type == 'paragraph':
                    triples.append(f'    ds:hasStructuralRole ds:Paragraph ;')
                elif chunk_type == 'heading':
                    triples.append(f'    ds:hasStructuralRole ds:Heading ;')
                elif chunk_type == 'list_item':
                    triples.append(f'    ds:hasStructuralRole ds:ListItem ;')
                else:
                    triples.append(f'    ds:chunkType "{chunk_type}" ;')
            
            # Add position information
            if chunk.get('start_char') is not None:
                triples.append(f'    ds:startPosition {chunk["start_char"]} ;')
            if chunk.get('end_char') is not None:
                triples.append(f'    ds:endPosition {chunk["end_char"]} ;')
            
            # Close chunk description
            triples[-1] = triples[-1].rstrip(' ;') + ' .'
            chunk_triples.extend(triples)
            chunk_triples.append('')  # Add blank line between chunks
        
        return '\n'.join(chunk_triples)
    
    def escape_ttl_string(self, text: str) -> str:
        """Escape string for TTL format"""
        if not text:
            return ""
        
        # Escape quotes and other special characters
        escaped = text.replace('\\', '\\\\')
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace('\n', '\\n')
        escaped = escaped.replace('\r', '\\r')
        escaped = escaped.replace('\t', '\\t')
        
        return escaped
    
    def trigger_kg_integration(self, doc_id: str, ttl_result: Dict[str, Any], insertion_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger downstream processing with KG integration information"""
        
        try:
            message = {
                'doc_id': doc_id,
                'processing_type': 'kg_triples_ready',
                'ttl_location': insertion_result.get('s3_uri'),  # Only present for bulk load
                'insertion_method': insertion_result['method'],
                'records_processed': insertion_result.get('records_loaded', insertion_result.get('estimated_records', 0)),
                'schema_version': '2.0',
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
                    'insertion_method': {
                        'DataType': 'String',
                        'StringValue': insertion_result['method']
                    }
                }
            )
            
            logger.info(f"KG triples ready message sent for {doc_id}: {response['MessageId']}")
            
            return {
                'success': True,
                'message_id': response['MessageId']
            }
            
        except Exception as e:
            logger.error(f"Error triggering KG integration for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
