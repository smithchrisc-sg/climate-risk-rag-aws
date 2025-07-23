#!/usr/bin/env python3
"""
Knowledge Graph Integration Worker - Refactored
Handles loading of TTL data into Neptune using Knowledge Graph Layer

This Lambda function:
1. Receives SNS messages from document structure KG processor (kg-triples-ready)
2. Uses KG Layer for optimized Neptune operations
3. Handles both SPARQL INSERT and bulk load scenarios
4. Validates loaded data with SPARQL queries
5. Updates processing status in database

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

class KGIntegrationWorker:
    """Worker for integrating TTL data into Neptune knowledge graph using KG Layer"""
    
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
        
        logger.info(f"Initialized KG worker - Neptune: {self.kg_manager.neptune_endpoint}")
    
    def lambda_handler(self, event, context):
        """Main Lambda handler for KG integration processing"""
        
        try:
            logger.info(f"Processing KG integration event: {json.dumps(event, default=str)}")
            
            # Parse SNS message
            records = event.get('Records', [])
            results = []
            
            for record in records:
                if record.get('EventSource') == 'aws:sns':
                    # Parse the SNS message
                    sns_message = record['Sns']['Message']
                    message = json.loads(sns_message)
                    result = self.process_kg_triples_ready_message(message)
                    results.append(result)
                else:
                    logger.warning(f"Unexpected event source: {record.get('EventSource')}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'KG integration processing completed',
                    'processed_count': len(results),
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error(f"Error in KG integration processing: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e),
                    'message': 'KG integration processing failed'
                })
            }
    
    def process_kg_triples_ready_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a kg-triples-ready message using KG Layer"""
        
        doc_id = None
        try:
            doc_id = message.get('doc_id')
            processing_type = message.get('processing_type', 'kg_triples_ready')
            ttl_location = message.get('ttl_location')
            insertion_method = message.get('insertion_method', 'unknown')
            records_processed = message.get('records_processed', 0)
            
            if not doc_id:
                raise ValueError("Missing doc_id in kg-triples-ready message")
            
            logger.info(f"Processing KG integration for document: {doc_id}")
            logger.info(f"Insertion method: {insertion_method}, Records: {records_processed}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_triples_load',
                status='in_progress',
                metadata={
                    'kg_loading_started': datetime.utcnow().isoformat() + 'Z',
                    'insertion_method': insertion_method,
                    'expected_records': records_processed
                }
            )
            
            # Handle different insertion methods
            if insertion_method == 'bulk_load':
                # Data was already loaded via bulk load, just validate
                validation_result = self.validate_bulk_loaded_data(doc_id, ttl_location, records_processed)
                load_result = {
                    'success': True,
                    'method': 'bulk_load',
                    'records_loaded': records_processed,
                    'already_loaded': True
                }
            elif insertion_method == 'sparql_insert':
                # Data was already loaded via SPARQL INSERT, just validate
                validation_result = self.validate_sparql_loaded_data(doc_id, records_processed)
                load_result = {
                    'success': True,
                    'method': 'sparql_insert',
                    'records_loaded': records_processed,
                    'already_loaded': True
                }
            else:
                # Legacy mode - download TTL and load using KG layer optimization
                if ttl_location:
                    ttl_content = self.download_ttl_from_s3(ttl_location)
                    if not ttl_content:
                        raise Exception("Failed to download TTL content from S3")
                    
                    # Use KG layer's optimized insertion
                    load_result = self.kg_manager.triple_manager.insert_triples_optimized(
                        ttl_content=ttl_content,
                        s3_key_prefix=f"kg-integration/{doc_id}"
                    )
                    
                    if not load_result['success']:
                        raise Exception(f"Failed to load TTL using KG layer: {load_result.get('error', 'Unknown error')}")
                    
                    # Validate loaded data
                    validation_result = self.validate_loaded_data(doc_id, load_result)
                else:
                    raise Exception("No TTL location provided and insertion method unknown")
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_triples_load',
                status='completed',
                metadata={
                    'kg_loading_completed': datetime.utcnow().isoformat() + 'Z',
                    'insertion_method': load_result['method'],
                    'records_loaded': load_result.get('records_loaded', load_result.get('estimated_records', 0)),
                    'validation_passed': validation_result.get('success', False),
                    'validation_count': validation_result.get('count', 0),
                    'already_loaded': load_result.get('already_loaded', False),
                    's3_location': load_result.get('s3_uri')
                }
            )
            
            logger.info(f"Successfully completed KG integration for {doc_id} using {load_result['method']}")
            
            return {
                'doc_id': doc_id,
                'status': 'success',
                'insertion_method': load_result['method'],
                'records_loaded': load_result.get('records_loaded', load_result.get('estimated_records', 0)),
                'validation_passed': validation_result.get('success', False),
                'already_loaded': load_result.get('already_loaded', False)
            }
            
        except Exception as e:
            logger.error(f"Error processing kg-triples-ready message for {doc_id}: {str(e)}")
            
            # Update status to failed
            if doc_id:
                try:
                    self.db_manager.set_processing_status(
                        doc_id=doc_id,
                        stage='kg_triples_load',
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
    
    def download_ttl_from_s3(self, ttl_location: str) -> Optional[str]:
        """Download TTL content from S3"""
        try:
            if not ttl_location or not ttl_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 location: {ttl_location}")
            
            # Parse S3 location
            s3_path = ttl_location[5:]  # Remove 's3://'
            bucket_name = s3_path.split('/')[0]
            key = '/'.join(s3_path.split('/')[1:])
            
            logger.info(f"Downloading TTL from s3://{bucket_name}/{key}")
            
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            ttl_content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Downloaded TTL content ({len(ttl_content)} characters)")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error downloading TTL from {ttl_location}: {str(e)}")
            return None
    
    def validate_bulk_loaded_data(self, doc_id: str, ttl_location: str, expected_records: int) -> Dict[str, Any]:
        """Validate data loaded via bulk load"""
        try:
            doc_uri = self.kg_manager.mint_document_uri(doc_id)
            
            # Query for document and its chunks
            query = f"""
            {self.kg_manager.uri_manager.get_prefixes_sparql()}
            
            SELECT (COUNT(*) as ?count)
            WHERE {{
                {{
                    <{doc_uri}> ?p ?o .
                }}
                UNION
                {{
                    ?chunk dcterms:isPartOf <{doc_uri}> .
                    ?chunk ?p ?o .
                }}
            }}
            """
            
            results = self.kg_manager.execute_sparql_query(query)
            actual_count = int(results[0]['count']) if results else 0
            
            # Validation is successful if we have data
            success = actual_count > 0
            
            logger.info(f"Bulk load validation for {doc_id}: {actual_count} triples found")
            
            return {
                'success': success,
                'count': actual_count,
                'expected': expected_records,
                'method': 'bulk_load_validation'
            }
            
        except Exception as e:
            logger.error(f"Error validating bulk loaded data for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    def validate_sparql_loaded_data(self, doc_id: str, expected_records: int) -> Dict[str, Any]:
        """Validate data loaded via SPARQL INSERT"""
        try:
            doc_uri = self.kg_manager.mint_document_uri(doc_id)
            
            # Query for document chunks
            query = f"""
            {self.kg_manager.uri_manager.get_prefixes_sparql()}
            
            SELECT (COUNT(DISTINCT ?chunk) as ?chunkCount) (COUNT(*) as ?tripleCount)
            WHERE {{
                ?chunk dcterms:isPartOf <{doc_uri}> .
                ?chunk ?p ?o .
            }}
            """
            
            results = self.kg_manager.execute_sparql_query(query)
            if results:
                chunk_count = int(results[0]['chunkCount'])
                triple_count = int(results[0]['tripleCount'])
            else:
                chunk_count = 0
                triple_count = 0
            
            # Validation is successful if we have chunks
            success = chunk_count > 0
            
            logger.info(f"SPARQL validation for {doc_id}: {chunk_count} chunks, {triple_count} triples")
            
            return {
                'success': success,
                'count': triple_count,
                'chunk_count': chunk_count,
                'expected': expected_records,
                'method': 'sparql_validation'
            }
            
        except Exception as e:
            logger.error(f"Error validating SPARQL loaded data for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    def validate_loaded_data(self, doc_id: str, load_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data loaded using KG layer optimization"""
        try:
            method = load_result['method']
            
            if method == 'bulk_load':
                return self.validate_bulk_loaded_data(
                    doc_id, 
                    load_result.get('s3_uri', ''), 
                    load_result.get('records_loaded', 0)
                )
            else:
                return self.validate_sparql_loaded_data(
                    doc_id, 
                    load_result.get('estimated_records', 0)
                )
                
        except Exception as e:
            logger.error(f"Error validating loaded data for {doc_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of KG integration worker"""
        try:
            # Use KG layer's health check
            kg_health = self.kg_manager.get_health_status()
            
            return {
                'status': 'healthy' if kg_health['status'] == 'healthy' else 'unhealthy',
                'kg_layer_status': kg_health,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
