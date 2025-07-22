#!/usr/bin/env python3
"""
Document Structure Knowledge Graph Processor
Processes document structure completion events and generates TTL for Neptune loading

This Lambda function:
1. Receives SNS messages from text chunker completion (chunks_ready)
2. Generates document structure TTL using Dublin Core vocabulary
3. Uploads TTL to S3 for Neptune bulk loading
4. Updates processing status in PostgreSQL

Modernized for standardized deployment process.
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

# Import from standardized database layer
try:
    from utils.DatabaseManager import DatabaseManager
    logger.info("Successfully imported DatabaseManager from standardized layer")
except ImportError as e:
    logger.error(f"Failed to import DatabaseManager from layer: {e}")
    raise

class DocumentStructureKGProcessor:
    """Processes document structure for knowledge graph integration"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
        # Initialize database manager with standardized layer
        try:
            self.db_manager = DatabaseManager()
            logger.info("DatabaseManager initialized successfully")
        except Exception as e:
            logger.error(f"DatabaseManager initialization failed: {e}")
            raise
        
        # S3 buckets from environment
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        self.ttl_bucket = os.environ.get('TTL_BUCKET', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
        
        # Neptune configuration
        self.neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT', 'solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com')
        self.neptune_port = os.environ.get('NEPTUNE_PORT', '8182')
        
        # SNS topics for downstream processing
        self.kg_triples_ready_topic = os.environ.get('KG_TRIPLES_READY_TOPIC_ARN')
        
        logger.info(f"Initialized with buckets - chunks: {self.chunks_bucket}, text: {self.text_bucket}, ttl: {self.ttl_bucket}")
        logger.info(f"Neptune endpoint: {self.neptune_endpoint}:{self.neptune_port}")
        
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
            
            # Generate document structure TTL
            ttl_result = self.generate_document_structure_ttl(
                doc_id, 
                data_locations=data_locations,
                processing_metadata=processing_metadata
            )
            
            if ttl_result['success']:
                # Trigger KG integration if topic configured
                integration_result = {'success': True, 'message': 'No kg-triples-ready topic configured'}
                if self.kg_triples_ready_topic:
                    integration_result = self.trigger_kg_integration(doc_id, ttl_result)
                
                # Update processing status to completed
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='kg_doc_structure',
                    status='completed',
                    metadata={
                        'ttl_generated': True,
                        'ttl_s3_location': ttl_result['s3_location'],
                        'integration_triggered': integration_result['success'],
                        'chunks_count': processing_metadata.get('chunks_created', 0),
                        'processing_completed_at': datetime.utcnow().isoformat() + 'Z'
                    }
                )
                
                logger.info(f"Successfully processed document structure KG for {doc_id}")
                
                return {
                    'doc_id': doc_id,
                    'status': 'success',
                    'ttl_location': ttl_result['s3_location'],
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
            if 'doc_id' in locals():
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
                'doc_id': doc_id if 'doc_id' in locals() else 'unknown',
                'status': 'error',
                'error': str(e)
            }
    
    def generate_document_structure_ttl(self, doc_id: str, data_locations: Dict = None, processing_metadata: Dict = None) -> Dict[str, Any]:
        """Generate TTL for document structure using Dublin Core vocabulary"""
        
        try:
            logger.info(f"Generating TTL for document structure: {doc_id}")
            
            # Import TTL generator
            from document_ttl_generator import DocumentTTLGenerator
            
            # Prepare metadata for TTL generation
            enhanced_metadata = {
                'data_locations': data_locations or {},
                'processing_metadata': processing_metadata or {},
                'generation_timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Generate TTL using Dublin Core vocabulary
            generator = DocumentTTLGenerator(doc_id, enhanced_metadata)
            ttl_content = generator.generate_document_structure_ttl()
            
            # Upload TTL to S3
            ttl_key = f"documents/{doc_id}/document_structure.ttl"
            s3_location = f"s3://{self.ttl_bucket}/{ttl_key}"
            
            self.s3_client.put_object(
                Bucket=self.ttl_bucket,
                Key=ttl_key,
                Body=ttl_content.encode('utf-8'),
                ContentType='text/turtle',
                Metadata={
                    'document_id': doc_id,
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'content_type': 'document_structure',
                    'schema_version': 'dublin_core_v2'
                }
            )
            
            logger.info(f"TTL uploaded to: {s3_location} ({len(ttl_content)} bytes)")
            
            return {
                'success': True,
                's3_location': s3_location,
                'ttl_size': len(ttl_content),
                'ttl_key': ttl_key
            }
            
        except Exception as e:
            logger.error(f"Error generating TTL for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def trigger_kg_integration(self, doc_id: str, ttl_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger KG integration worker to load TTL into Neptune"""
        
        try:
            message = {
                'doc_id': doc_id,
                'processing_type': 'document_structure',
                'ttl_location': ttl_result['s3_location'],
                'ttl_key': ttl_result['ttl_key'],
                'schema_version': 'dublin_core_v2',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            response = self.sns_client.publish(
                TopicArn=self.kg_triples_ready_topic,
                Message=json.dumps(message),
                Subject=f'KG Triples Ready: Document Structure - {doc_id}',
                MessageAttributes={
                    'processing_type': {
                        'DataType': 'String',
                        'StringValue': 'document_structure'
                    },
                    'doc_id': {
                        'DataType': 'String', 
                        'StringValue': doc_id
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
