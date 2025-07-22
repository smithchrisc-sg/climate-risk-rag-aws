#!/usr/bin/env python3
"""
Knowledge Graph Integration Worker - Modernized
Handles SPARQL loading of TTL data into Neptune for document structure processing

This Lambda function:
1. Receives SNS messages from document structure KG processor (kg-triples-ready)
2. Downloads TTL files from S3
3. Loads data into Neptune using SPARQL INSERT operations
4. Validates loaded data with SPARQL queries
5. Updates processing status in database

Modernized for standardized deployment process.
"""

import json
import boto3
import os
import sys
import logging
import requests
from requests_aws4auth import AWS4Auth
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

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

class KGIntegrationWorker:
    """Worker for integrating TTL data into Neptune knowledge graph"""
    
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
        
        # Environment configuration
        self.neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT', 
            'solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com')
        self.neptune_port = os.environ.get('NEPTUNE_PORT', '8182')
        self.ttl_bucket = os.environ.get('TTL_BUCKET', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
        
        # AWS credentials for Neptune authentication
        session = boto3.Session()
        credentials = session.get_credentials()
        self.auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            'us-east-1',
            'neptune-db',
            session_token=credentials.token
        )
        
        logger.info(f"Initialized KG worker - Neptune: {self.neptune_endpoint}:{self.neptune_port}")
        logger.info(f"TTL bucket: {self.ttl_bucket}")
    
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
        """Process a kg-triples-ready message"""
        
        try:
            doc_id = message.get('doc_id')
            processing_type = message.get('processing_type', 'document_structure')
            ttl_location = message.get('ttl_location')
            ttl_key = message.get('ttl_key')
            
            if not doc_id:
                raise ValueError("Missing doc_id in kg-triples-ready message")
            
            logger.info(f"Processing KG integration for document: {doc_id}, type: {processing_type}")
            logger.info(f"TTL location: {ttl_location}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_doc_structure',
                status='in_progress',
                metadata={'kg_loading_started': datetime.utcnow().isoformat() + 'Z'}
            )
            
            # Download TTL from S3
            ttl_content = self.download_ttl_from_s3(ttl_location, ttl_key)
            if not ttl_content:
                raise Exception("Failed to download TTL content from S3")
            
            # Load TTL into Neptune
            load_result = self.load_ttl_to_neptune(doc_id, ttl_content, processing_type)
            if not load_result['success']:
                raise Exception(f"Failed to load TTL to Neptune: {load_result['error']}")
            
            # Validate loaded data
            validation_result = self.validate_loaded_data(doc_id, processing_type)
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='kg_doc_structure',
                status='completed',
                metadata={
                    'kg_loading_completed': datetime.utcnow().isoformat() + 'Z',
                    'triples_loaded': load_result.get('triples_count', 0),
                    'operations_count': load_result.get('operations_count', 0),
                    'validation_passed': validation_result.get('success', False),
                    'validation_count': validation_result.get('count', 0)
                }
            )
            
            logger.info(f"Successfully completed KG integration for {doc_id}")
            
            return {
                'doc_id': doc_id,
                'status': 'success',
                'triples_loaded': load_result.get('triples_count', 0),
                'validation_passed': validation_result.get('success', False)
            }
            
        except Exception as e:
            logger.error(f"Error processing kg-triples-ready message for {doc_id}: {str(e)}")
            
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
    
    def download_ttl_from_s3(self, ttl_location: str, ttl_key: str) -> Optional[str]:
        """Download TTL content from S3"""
        try:
            # Use ttl_location if provided, otherwise construct from ttl_key
            if ttl_location and ttl_location.startswith('s3://'):
                # Parse S3 location
                s3_path = ttl_location[5:]  # Remove 's3://'
                bucket, key = s3_path.split('/', 1)
            elif ttl_key:
                bucket = self.ttl_bucket
                key = ttl_key
            else:
                logger.error("No TTL location or key provided")
                return None
            
            logger.info(f"Downloading TTL from s3://{bucket}/{key}")
            
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            ttl_content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Downloaded TTL content ({len(ttl_content)} characters)")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error downloading TTL from S3: {e}")
            return None
    
    def load_ttl_to_neptune(self, doc_id: str, ttl_content: str, processing_type: str) -> Dict[str, Any]:
        """Load TTL content into Neptune using SPARQL INSERT operations"""
        try:
            logger.info(f"Loading TTL to Neptune for document: {doc_id}")
            
            # Split TTL into manageable chunks
            ttl_chunks = self._split_ttl_content(ttl_content)
            logger.info(f"Split TTL into {len(ttl_chunks)} chunks")
            
            total_operations = 0
            total_triples = 0
            
            for i, chunk in enumerate(ttl_chunks):
                logger.info(f"Processing chunk {i+1}/{len(ttl_chunks)}")
                
                # Convert TTL to SPARQL INSERT
                sparql_insert = self._convert_ttl_to_sparql_insert(chunk)
                
                if sparql_insert:
                    # Execute SPARQL INSERT
                    result = self._execute_sparql_update(sparql_insert)
                    
                    if result['success']:
                        total_operations += 1
                        # Estimate triples from chunk
                        total_triples += self._estimate_triples_in_chunk(chunk)
                        logger.info(f"Successfully loaded chunk {i+1}")
                    else:
                        logger.error(f"Failed to execute SPARQL INSERT for chunk {i+1}: {result.get('error')}")
                        return {
                            'success': False,
                            'error': f"SPARQL execution failed on chunk {i+1}: {result.get('error')}"
                        }
            
            logger.info(f"Successfully loaded {total_triples} triples in {total_operations} operations")
            
            return {
                'success': True,
                'triples_count': total_triples,
                'operations_count': total_operations
            }
            
        except Exception as e:
            logger.error(f"Error loading TTL to Neptune: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_loaded_data(self, doc_id: str, processing_type: str) -> Dict[str, Any]:
        """Validate that data was loaded correctly into Neptune"""
        try:
            logger.info(f"Validating loaded data for document: {doc_id}")
            
            # Validation query for document structure
            validation_query = f"""
                PREFIX dc: <http://purl.org/dc/elements/1.1/>
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX cr: <http://climate-risk.org/ontology/>
                
                SELECT (COUNT(*) as ?count) WHERE {{
                    <http://climate-risk.org/documents/{doc_id}> a dcterms:Text ;
                        dc:identifier "{doc_id}" .
                }}
            """
            
            result = self._execute_sparql_query(validation_query)
            
            if result['success']:
                count = self._extract_count_from_sparql_result(result['data'])
                logger.info(f"Validation query returned count: {count}")
                
                return {
                    'success': count > 0,
                    'count': count,
                    'message': f"Found {count} document records for {doc_id}"
                }
            else:
                logger.error(f"Validation query failed: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error')
                }
                
        except Exception as e:
            logger.error(f"Error validating loaded data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _split_ttl_content(self, ttl_content: str) -> List[str]:
        """Split TTL content into manageable chunks"""
        # Split by triple statements (lines ending with .)
        lines = ttl_content.split('\n')
        chunks = []
        current_chunk = []
        prefixes = []
        
        # Extract prefixes
        for line in lines:
            if line.strip().startswith('@prefix'):
                prefixes.append(line)
            else:
                break
        
        # Split content into chunks
        for line in lines:
            if not line.strip().startswith('@prefix'):
                current_chunk.append(line)
                
                # If line ends with '.', it's end of a statement
                if line.strip().endswith('.') and len(current_chunk) > 10:  # Reasonable chunk size
                    # Add prefixes to chunk
                    chunk_content = '\n'.join(prefixes + current_chunk)
                    chunks.append(chunk_content)
                    current_chunk = []
        
        # Add remaining content
        if current_chunk:
            chunk_content = '\n'.join(prefixes + current_chunk)
            chunks.append(chunk_content)
        
        return chunks if chunks else [ttl_content]  # Return original if splitting failed
    
    def _convert_ttl_to_sparql_insert(self, ttl_chunk: str) -> str:
        """Convert TTL chunk to SPARQL INSERT statement"""
        try:
            # Extract prefixes
            prefixes = []
            content_lines = []
            
            for line in ttl_chunk.split('\n'):
                if line.strip().startswith('@prefix'):
                    # Convert TTL prefix to SPARQL prefix
                    sparql_prefix = line.replace('@prefix', 'PREFIX').replace(' .', '')
                    prefixes.append(sparql_prefix)
                elif line.strip() and not line.strip().startswith('#'):
                    content_lines.append(line)
            
            if not content_lines:
                return None
            
            # Build SPARQL INSERT
            sparql_insert = '\n'.join(prefixes) + '\n\n'
            sparql_insert += 'INSERT DATA {\n'
            sparql_insert += '\n'.join(content_lines)
            sparql_insert += '\n}'
            
            return sparql_insert
            
        except Exception as e:
            logger.error(f"Error converting TTL to SPARQL: {e}")
            return None
    
    def _execute_sparql_update(self, sparql_update: str) -> Dict[str, Any]:
        """Execute SPARQL UPDATE operation on Neptune"""
        try:
            sparql_url = f"https://{self.neptune_endpoint}:{self.neptune_port}/sparql"
            
            response = requests.post(
                sparql_url,
                data={'update': sparql_update},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=self.auth,
                timeout=60
            )
            
            if response.status_code == 200:
                return {'success': True}
            else:
                logger.error(f"SPARQL UPDATE failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error executing SPARQL UPDATE: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_sparql_query(self, sparql_query: str) -> Dict[str, Any]:
        """Execute SPARQL SELECT query on Neptune"""
        try:
            sparql_url = f"https://{self.neptune_endpoint}:{self.neptune_port}/sparql"
            
            response = requests.post(
                sparql_url,
                data={'query': sparql_query},
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/sparql-results+json'
                },
                auth=self.auth,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                logger.error(f"SPARQL QUERY failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error executing SPARQL QUERY: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _estimate_triples_in_chunk(self, ttl_chunk: str) -> int:
        """Estimate number of triples in TTL chunk"""
        # Count lines ending with '.' (excluding prefixes)
        lines = ttl_chunk.split('\n')
        triple_count = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.endswith('.') and not stripped.startswith('@prefix'):
                # Count semicolons and commas for multiple predicates/objects
                triple_count += 1 + stripped.count(';') + stripped.count(',')
        
        return max(1, triple_count)  # At least 1 triple per chunk
    
    def _extract_count_from_sparql_result(self, sparql_result: Dict) -> int:
        """Extract count value from SPARQL result"""
        try:
            bindings = sparql_result.get('results', {}).get('bindings', [])
            if bindings:
                count_value = bindings[0].get('count', {}).get('value', '0')
                return int(count_value)
            return 0
        except Exception as e:
            logger.error(f"Error extracting count from SPARQL result: {e}")
            return 0
