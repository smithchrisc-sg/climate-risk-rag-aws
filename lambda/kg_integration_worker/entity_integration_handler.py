#!/usr/bin/env python3
"""
Entity Integration Handler
Extends KG Integration Worker to handle entity resolution TTL files
"""

import json
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EntityIntegrationHandler:
    """Handles entity-specific KG integration operations"""
    
    def __init__(self, neptune_endpoint: str, s3_client, sns_client):
        self.neptune_endpoint = neptune_endpoint
        self.s3_client = s3_client
        self.sns_client = sns_client
        
        # Entity-specific SPARQL templates
        self.entity_validation_queries = {
            'PERSON': """
                SELECT (COUNT(*) as ?count) WHERE {
                    ?person a foaf:Person ;
                            foaf:name ?name ;
                            kr:extractedFrom ?source .
                    FILTER(CONTAINS(STR(?source), "{document_id}"))
                }
            """,
            'ORGANIZATION': """
                SELECT (COUNT(*) as ?count) WHERE {
                    ?org a foaf:Organization ;
                         foaf:name ?name ;
                         kr:extractedFrom ?source .
                    FILTER(CONTAINS(STR(?source), "{document_id}"))
                }
            """,
            'LOCATION': """
                SELECT (COUNT(*) as ?count) WHERE {
                    ?location a schema:Place ;
                              schema:name ?name ;
                              kr:extractedFrom ?source .
                    FILTER(CONTAINS(STR(?source), "{document_id}"))
                }
            """
        }
    
    def process_entity_integration(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process entity resolution integration message"""
        
        document_id = message.get('document_id')
        storage_location = message.get('storage_location')
        entity_types = message.get('entity_types', [])
        entity_count = message.get('entity_count', 0)
        
        logger.info(f"Processing entity integration for document: {document_id}")
        logger.info(f"Entity types: {entity_types}, count: {entity_count}")
        
        try:
            # Download entity resolution results from S3
            entity_data = self._download_entity_results(storage_location)
            
            if not entity_data:
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': 'Failed to download entity resolution results'
                }
            
            # Generate TTL from entity data
            ttl_content = self._generate_entity_ttl(entity_data)
            
            if not ttl_content:
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': 'Failed to generate entity TTL'
                }
            
            # Load entity TTL into Neptune
            load_result = self._load_entity_ttl_to_neptune(document_id, ttl_content)
            
            if load_result['success']:
                # Validate loaded entities
                validation_result = self._validate_loaded_entities(document_id, entity_types)
                
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'processing_type': 'entity_resolution',
                    'entities_loaded': load_result.get('entities_count', 0),
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success'],
                    'entity_types': entity_types
                }
            else:
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': load_result.get('error', 'Unknown error loading entities')
                }
                
        except Exception as e:
            logger.error(f"Error processing entity integration: {e}")
            return {
                'document_id': document_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _download_entity_results(self, storage_location: str) -> Optional[Dict[str, Any]]:
        """Download entity resolution results from S3"""
        try:
            if not storage_location.startswith('s3://'):
                logger.error(f"Invalid S3 location: {storage_location}")
                return None
            
            # Parse S3 location
            s3_path = storage_location[5:]  # Remove 's3://'
            bucket, key = s3_path.split('/', 1)
            
            logger.info(f"Downloading entity results from s3://{bucket}/{key}")
            
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            entity_data = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"Downloaded entity data with {len(entity_data.get('resolved_entities', []))} entities")
            return entity_data
            
        except Exception as e:
            logger.error(f"Error downloading entity results: {e}")
            return None
    
    def _generate_entity_ttl(self, entity_data: Dict[str, Any]) -> Optional[str]:
        """Generate TTL content from entity resolution data"""
        try:
            # Import the RDF builder (would need to be available in the Lambda)
            from rdf_entity_builder import RDFEntityBuilder
            
            builder = RDFEntityBuilder()
            resolved_entities = entity_data.get('resolved_entities', [])
            doc_id = entity_data.get('doc_id', 'unknown')
            
            if not resolved_entities:
                logger.warning("No resolved entities found in data")
                return None
            
            # Build TTL content
            ttl_content = builder.build_entity_ttl(resolved_entities, doc_id)
            
            logger.info(f"Generated TTL content with {len(resolved_entities)} entities")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error generating entity TTL: {e}")
            return None
    
    def _load_entity_ttl_to_neptune(self, document_id: str, ttl_content: str) -> Dict[str, Any]:
        """Load entity TTL content into Neptune using SPARQL"""
        try:
            # Split TTL into manageable chunks for SPARQL INSERT operations
            ttl_chunks = self._split_ttl_for_sparql(ttl_content)
            
            total_operations = 0
            total_triples = 0
            entities_loaded = 0
            
            for chunk in ttl_chunks:
                # Convert TTL chunk to SPARQL INSERT
                sparql_insert = self._convert_ttl_to_sparql_insert(chunk)
                
                if sparql_insert:
                    # Execute SPARQL INSERT
                    result = self._execute_sparql_update(sparql_insert)
                    
                    if result['success']:
                        total_operations += 1
                        # Estimate triples and entities from chunk
                        chunk_stats = self._estimate_chunk_stats(chunk)
                        total_triples += chunk_stats['triples']
                        entities_loaded += chunk_stats['entities']
                    else:
                        logger.error(f"Failed to execute SPARQL INSERT: {result.get('error')}")
                        return {
                            'success': False,
                            'error': f"SPARQL execution failed: {result.get('error')}"
                        }
            
            logger.info(f"Successfully loaded {entities_loaded} entities ({total_triples} triples) in {total_operations} operations")
            
            return {
                'success': True,
                'entities_count': entities_loaded,
                'triples_count': total_triples,
                'operations_count': total_operations
            }
            
        except Exception as e:
            logger.error(f"Error loading entity TTL to Neptune: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _split_ttl_for_sparql(self, ttl_content: str) -> List[str]:
        """Split TTL content into chunks suitable for SPARQL INSERT operations"""
        # Simple splitting by entity blocks (separated by empty lines)
        chunks = []
        current_chunk = []
        prefixes = []
        
        lines = ttl_content.split('\n')
        
        # Extract prefixes first
        for line in lines:
            if line.strip().startswith('@prefix'):
                prefixes.append(line)
            else:
                break
        
        # Process entity blocks
        in_entity = False
        for line in lines:
            if line.strip().startswith('@prefix'):
                continue
            
            if line.strip() and not line.startswith('#'):
                current_chunk.append(line)
                in_entity = True
            elif line.strip().startswith('#') or not line.strip():
                if in_entity and current_chunk:
                    # End of entity block
                    chunk_content = '\n'.join(prefixes + [''] + current_chunk)
                    chunks.append(chunk_content)
                    current_chunk = []
                    in_entity = False
                elif line.strip().startswith('#'):
                    current_chunk.append(line)
        
        # Add final chunk if exists
        if current_chunk:
            chunk_content = '\n'.join(prefixes + [''] + current_chunk)
            chunks.append(chunk_content)
        
        logger.info(f"Split TTL into {len(chunks)} chunks for SPARQL processing")
        return chunks
    
    def _convert_ttl_to_sparql_insert(self, ttl_chunk: str) -> Optional[str]:
        """Convert TTL chunk to SPARQL INSERT DATA statement"""
        try:
            # Extract prefixes
            prefixes = []
            data_lines = []
            
            for line in ttl_chunk.split('\n'):
                if line.strip().startswith('@prefix'):
                    # Convert @prefix to PREFIX for SPARQL
                    prefix_line = line.replace('@prefix', 'PREFIX').rstrip(' .')
                    prefixes.append(prefix_line)
                elif line.strip() and not line.startswith('#'):
                    data_lines.append(line)
            
            if not data_lines:
                return None
            
            # Build SPARQL INSERT DATA statement
            sparql_parts = prefixes + ['', 'INSERT DATA {'] + data_lines + ['}']
            sparql_insert = '\n'.join(sparql_parts)
            
            return sparql_insert
            
        except Exception as e:
            logger.error(f"Error converting TTL to SPARQL: {e}")
            return None
    
    def _execute_sparql_update(self, sparql_query: str) -> Dict[str, Any]:
        """Execute SPARQL UPDATE query against Neptune"""
        try:
            import urllib3
            import urllib.parse
            
            # Neptune SPARQL endpoint
            sparql_endpoint = f"https://{self.neptune_endpoint}:8182/sparql"
            
            # Prepare request
            headers = {
                'Content-Type': 'application/sparql-update',
                'Accept': 'application/json'
            }
            
            http = urllib3.PoolManager()
            
            # Execute SPARQL UPDATE
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
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"Error executing SPARQL UPDATE: {e}")
            return {'success': False, 'error': str(e)}
    
    def _estimate_chunk_stats(self, ttl_chunk: str) -> Dict[str, int]:
        """Estimate number of triples and entities in TTL chunk"""
        lines = ttl_chunk.split('\n')
        
        triple_count = 0
        entity_count = 0
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('@prefix'):
                if line.endswith('.') or line.endswith(';'):
                    triple_count += 1
                if ' a ' in line:  # RDF type declaration
                    entity_count += 1
        
        return {
            'triples': triple_count,
            'entities': max(1, entity_count)  # At least 1 entity per chunk
        }
    
    def _validate_loaded_entities(self, document_id: str, entity_types: List[str]) -> Dict[str, Any]:
        """Validate that entities were loaded correctly into Neptune"""
        try:
            validation_results = {}
            total_entities_found = 0
            
            for entity_type in entity_types:
                if entity_type in self.entity_validation_queries:
                    query = self.entity_validation_queries[entity_type].format(document_id=document_id)
                    result = self._execute_sparql_query(query)
                    
                    if result['success']:
                        count = self._extract_count_from_sparql_result(result['data'])
                        validation_results[entity_type] = count
                        total_entities_found += count
                    else:
                        validation_results[entity_type] = 0
                        logger.warning(f"Failed to validate {entity_type} entities: {result.get('error')}")
            
            success = total_entities_found > 0
            
            logger.info(f"Entity validation results: {validation_results} (total: {total_entities_found})")
            
            return {
                'success': success,
                'entity_counts': validation_results,
                'total_entities': total_entities_found
            }
            
        except Exception as e:
            logger.error(f"Error validating loaded entities: {e}")
            return {
                'success': False,
                'error': str(e),
                'entity_counts': {},
                'total_entities': 0
            }
    
    def _execute_sparql_query(self, sparql_query: str) -> Dict[str, Any]:
        """Execute SPARQL SELECT query against Neptune"""
        try:
            import urllib3
            import urllib.parse
            
            # Neptune SPARQL endpoint
            sparql_endpoint = f"https://{self.neptune_endpoint}:8182/sparql"
            
            # Prepare request
            params = {'query': sparql_query}
            headers = {'Accept': 'application/json'}
            
            http = urllib3.PoolManager()
            
            # Execute SPARQL SELECT
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
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"Error executing SPARQL SELECT: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_count_from_sparql_result(self, sparql_result: Dict[str, Any]) -> int:
        """Extract count value from SPARQL SELECT result"""
        try:
            bindings = sparql_result.get('results', {}).get('bindings', [])
            if bindings and 'count' in bindings[0]:
                return int(bindings[0]['count']['value'])
            return 0
        except:
            return 0
