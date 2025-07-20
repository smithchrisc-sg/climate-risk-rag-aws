#!/usr/bin/env python3
"""
Knowledge Graph Integration Worker - Updated with Entity Resolution Support
Handles SPARQL loading of TTL data into Neptune for both document structure and entities

This Lambda function:
1. Receives SNS messages from KG processors and entity resolvers
2. Downloads TTL files from S3 or processes entity resolution results
3. Loads data into Neptune using SPARQL INSERT operations
4. Validates loaded data with SPARQL queries
5. Updates processing status and sends completion notifications

Architecture: Handles both document structure and entity resolution TTL loading
"""

import json
import boto3
import os
import sys
import logging
import urllib3
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add layers to path for shared utilities
sys.path.append('/opt/python')

try:
    # Import from climate-risk-core-utilities layer
    from utils.DatabaseManager import DatabaseManager
    logger.info("Successfully imported shared utilities from layer")
except ImportError as e:
    logger.error(f"Failed to import shared utilities from layer: {e}")
    DatabaseManager = None

# Import entity integration handler
try:
    from entity_integration_handler import EntityIntegrationHandler
    logger.info("Successfully imported entity integration handler")
except ImportError as e:
    logger.error(f"Failed to import entity integration handler: {e}")
    EntityIntegrationHandler = None

class KGIntegrationWorker:
    """Worker for integrating TTL data into Neptune knowledge graph"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
        # Environment configuration
        self.neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT', 
            'solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com')
        self.ttl_bucket = os.environ.get('TTL_BUCKET', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
        self.kg_completion_topic_arn = os.environ.get('KG_COMPLETION_TOPIC_ARN')
        
        # Database manager for status tracking
        try:
            self.db_manager = DatabaseManager() if DatabaseManager else None
        except Exception as e:
            logger.warning(f"DatabaseManager not available: {e}")
            self.db_manager = None
        
        # Initialize entity integration handler
        if EntityIntegrationHandler:
            self.entity_handler = EntityIntegrationHandler(
                self.neptune_endpoint, 
                self.s3_client, 
                self.sns_client
            )
        else:
            self.entity_handler = None
            logger.warning("Entity integration handler not available")
    
    def process_kg_integration(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single KG integration message"""
        
        document_id = message.get('document_id')
        processing_type = message.get('processing_type', 'document_structure')
        
        logger.info(f"Processing KG integration for document: {document_id}, type: {processing_type}")
        
        try:
            # Route to appropriate handler based on processing type
            if processing_type == 'entity_resolution':
                return self._process_entity_resolution(message)
            else:
                return self._process_document_structure(message)
                
        except Exception as e:
            logger.error(f"Error in KG integration processing: {e}")
            return {
                'document_id': document_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _process_entity_resolution(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process entity resolution integration"""
        
        if not self.entity_handler:
            return {
                'document_id': message.get('document_id'),
                'status': 'failed',
                'error': 'Entity integration handler not available'
            }
        
        try:
            # Use entity handler for processing
            result = self.entity_handler.process_entity_integration(message)
            
            # Update processing status
            if result['status'] == 'success':
                self.update_processing_status(
                    result['document_id'], 
                    'entity_kg_integration_complete', 
                    {
                        'processing_type': 'entity_resolution',
                        'entities_loaded': result.get('entities_loaded', 0),
                        'triples_loaded': result.get('triples_loaded', 0),
                        'validation_passed': result.get('validation_passed', False),
                        'entity_types': result.get('entity_types', [])
                    }
                )
                
                # Send completion notification
                self.send_completion_notification(
                    result['document_id'], 
                    'entity_resolution', 
                    result
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing entity resolution: {e}")
            return {
                'document_id': message.get('document_id'),
                'status': 'failed',
                'error': str(e)
            }
    
    def _process_document_structure(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process document structure integration (existing functionality)"""
        
        document_id = message.get('document_id')
        ttl_location = message.get('ttl_location')
        ttl_key = message.get('ttl_key')
        
        try:
            # Download TTL from S3
            ttl_content = self.download_ttl_from_s3(ttl_location, ttl_key)
            
            if not ttl_content:
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': 'Failed to download TTL content'
                }
            
            # Load TTL into Neptune
            load_result = self.load_ttl_to_neptune(document_id, ttl_content, 'document_structure')
            
            if load_result['success']:
                # Validate loaded data
                validation_result = self.validate_loaded_data(document_id, 'document_structure')
                
                # Update processing status
                self.update_processing_status(document_id, 'kg_integration_complete', {
                    'processing_type': 'document_structure',
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success'],
                    'neptune_operations': load_result.get('operations_count', 0)
                })
                
                # Send completion notification
                self.send_completion_notification(document_id, 'document_structure', {
                    'status': 'success',
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success']
                })
                
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'processing_type': 'document_structure',
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success']
                }
            else:
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': load_result.get('error', 'Unknown error loading TTL')
                }
                
        except Exception as e:
            logger.error(f"Error processing document structure: {e}")
            return {
                'document_id': document_id,
                'status': 'failed',
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
    
    def load_ttl_to_neptune(self, document_id: str, ttl_content: str, processing_type: str) -> Dict[str, Any]:
        """Load TTL content into Neptune using SPARQL INSERT operations"""
        try:
            # Split TTL into manageable chunks
            ttl_chunks = self._split_ttl_content(ttl_content)
            
            total_operations = 0
            total_triples = 0
            
            for chunk in ttl_chunks:
                # Convert TTL to SPARQL INSERT
                sparql_insert = self._convert_ttl_to_sparql_insert(chunk)
                
                if sparql_insert:
                    # Execute SPARQL INSERT
                    result = self._execute_sparql_update(sparql_insert)
                    
                    if result['success']:
                        total_operations += 1
                        # Estimate triples from chunk
                        total_triples += self._estimate_triples_in_chunk(chunk)
                    else:
                        logger.error(f"Failed to execute SPARQL INSERT: {result.get('error')}")
                        return {
                            'success': False,
                            'error': f"SPARQL execution failed: {result.get('error')}"
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
    
    def validate_loaded_data(self, document_id: str, processing_type: str) -> Dict[str, Any]:
        """Validate that data was loaded correctly into Neptune"""
        try:
            # Different validation queries based on processing type
            if processing_type == 'document_structure':
                validation_query = f"""
                    SELECT (COUNT(*) as ?count) WHERE {{
                        ?doc a foaf:Document ;
                             dcterms:identifier "{document_id}" .
                    }}
                """
            else:
                # Generic validation
                validation_query = f"""
                    SELECT (COUNT(*) as ?count) WHERE {{
                        ?s ?p ?o .
                        FILTER(CONTAINS(STR(?s), "{document_id}") || CONTAINS(STR(?o), "{document_id}"))
                    }}
                """
            
            result = self._execute_sparql_query(validation_query)
            
            if result['success']:
                count = self._extract_count_from_result(result['data'])
                success = count > 0
                
                logger.info(f"Validation query returned count: {count}")
                
                return {
                    'success': success,
                    'count': count
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
    
    def update_processing_status(self, document_id: str, status: str, metadata: Dict[str, Any]):
        """Update processing status in database"""
        if not self.db_manager:
            logger.warning("Database manager not available for status update")
            return
        
        try:
            # Update processing status with metadata
            logger.info(f"Updated processing status for {document_id}: {status}")
            # Implementation would depend on your database schema
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
    
    def send_completion_notification(self, document_id: str, processing_type: str, result: Dict[str, Any]):
        """Send completion notification via SNS"""
        if not self.kg_completion_topic_arn:
            logger.warning("KG completion topic ARN not configured")
            return
        
        try:
            message = {
                'document_id': document_id,
                'processing_type': processing_type,
                'status': result.get('status', 'unknown'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'details': result
            }
            
            response = self.sns_client.publish(
                TopicArn=self.kg_completion_topic_arn,
                Message=json.dumps(message),
                Subject=f"KG Integration Complete: {document_id}"
            )
            
            logger.info(f"Sent completion notification: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Error sending completion notification: {e}")
    
    # Helper methods for SPARQL operations
    def _split_ttl_content(self, ttl_content: str) -> List[str]:
        """Split TTL content into manageable chunks"""
        # Simple implementation - split by empty lines
        chunks = []
        current_chunk = []
        prefixes = []
        
        lines = ttl_content.split('\n')
        
        # Extract prefixes
        for line in lines:
            if line.strip().startswith('@prefix'):
                prefixes.append(line)
        
        # Split content into chunks
        for line in lines:
            if line.strip().startswith('@prefix'):
                continue
            
            if line.strip():
                current_chunk.append(line)
            else:
                if current_chunk:
                    chunk_content = '\n'.join(prefixes + [''] + current_chunk)
                    chunks.append(chunk_content)
                    current_chunk = []
        
        # Add final chunk
        if current_chunk:
            chunk_content = '\n'.join(prefixes + [''] + current_chunk)
            chunks.append(chunk_content)
        
        return chunks if chunks else [ttl_content]
    
    def _convert_ttl_to_sparql_insert(self, ttl_chunk: str) -> Optional[str]:
        """Convert TTL chunk to SPARQL INSERT DATA statement"""
        try:
            # Extract prefixes and convert to SPARQL format
            prefixes = []
            data_lines = []
            
            for line in ttl_chunk.split('\n'):
                if line.strip().startswith('@prefix'):
                    prefix_line = line.replace('@prefix', 'PREFIX').rstrip(' .')
                    prefixes.append(prefix_line)
                elif line.strip() and not line.startswith('#'):
                    data_lines.append(line)
            
            if not data_lines:
                return None
            
            # Build SPARQL INSERT DATA statement
            sparql_parts = prefixes + ['', 'INSERT DATA {'] + data_lines + ['}']
            return '\n'.join(sparql_parts)
            
        except Exception as e:
            logger.error(f"Error converting TTL to SPARQL: {e}")
            return None
    
    def _execute_sparql_update(self, sparql_query: str) -> Dict[str, Any]:
        """Execute SPARQL UPDATE query against Neptune"""
        try:
            sparql_endpoint = f"https://{self.neptune_endpoint}:8182/sparql"
            
            headers = {
                'Content-Type': 'application/sparql-update',
                'Accept': 'application/json'
            }
            
            http = urllib3.PoolManager()
            
            response = http.request(
                'POST',
                sparql_endpoint,
                body=sparql_query.encode('utf-8'),
                headers=headers,
                timeout=30.0
            )
            
            if response.status == 200:
                return {'success': True}
            else:
                error_msg = f"SPARQL UPDATE failed with status {response.status}: {response.data.decode('utf-8')}"
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_sparql_query(self, sparql_query: str) -> Dict[str, Any]:
        """Execute SPARQL SELECT query against Neptune"""
        try:
            import urllib.parse
            
            sparql_endpoint = f"https://{self.neptune_endpoint}:8182/sparql"
            
            params = {'query': sparql_query}
            headers = {'Accept': 'application/json'}
            
            http = urllib3.PoolManager()
            
            response = http.request(
                'GET',
                sparql_endpoint,
                fields=params,
                headers=headers,
                timeout=30.0
            )
            
            if response.status == 200:
                data = json.loads(response.data.decode('utf-8'))
                return {'success': True, 'data': data}
            else:
                error_msg = f"SPARQL SELECT failed with status {response.status}: {response.data.decode('utf-8')}"
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _estimate_triples_in_chunk(self, ttl_chunk: str) -> int:
        """Estimate number of triples in TTL chunk"""
        lines = ttl_chunk.split('\n')
        triple_count = 0
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('@prefix'):
                if line.endswith('.') or line.endswith(';'):
                    triple_count += 1
        
        return max(1, triple_count)
    
    def _extract_count_from_result(self, sparql_result: Dict[str, Any]) -> int:
        """Extract count value from SPARQL SELECT result"""
        try:
            bindings = sparql_result.get('results', {}).get('bindings', [])
            if bindings and 'count' in bindings[0]:
                return int(bindings[0]['count']['value'])
            return 0
        except:
            return 0

def lambda_handler(event, context):
    """Lambda handler for KG integration"""
    try:
        logger.info(f"KG integration triggered with event: {json.dumps(event, default=str)}")
        
        worker = KGIntegrationWorker()
        results = []
        
        # Process SNS records
        for record in event.get('Records', []):
            if record.get('EventSource') == 'aws:sns':
                try:
                    message = json.loads(record['Sns']['Message'])
                    result = worker.process_kg_integration(message)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing record: {e}")
                    results.append({
                        'status': 'failed',
                        'error': str(e)
                    })
        
        # Return summary
        successful = sum(1 for r in results if r.get('status') == 'success')
        failed = len(results) - successful
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'KG integration completed',
                'processed_count': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"KG integration failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'KG integration failed'
            })
        }
