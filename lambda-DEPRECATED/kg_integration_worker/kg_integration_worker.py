#!/usr/bin/env python3
"""
Knowledge Graph Integration Worker
Handles SPARQL loading of TTL data into Neptune

This Lambda function:
1. Receives SNS messages from KG processors
2. Downloads TTL files from S3
3. Loads data into Neptune using SPARQL INSERT operations
4. Validates loaded data with SPARQL queries
5. Updates processing status and sends completion notifications

Architecture: Designed to handle both document structure and future entity TTL loading
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
    # Import from climate-risk-core-utilities layer (correct path)
    from utils.DatabaseManager import DatabaseManager
    logger.info("Successfully imported shared utilities from layer")
except ImportError as e:
    logger.error(f"Failed to import shared utilities from layer: {e}")
    # For local testing, try relative imports from layers directory
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'app-source', 'utils'))
        from DatabaseManager import DatabaseManager
        logger.info("Successfully imported utilities from local layers directory")
    except ImportError as e2:
        logger.error(f"Failed to import utilities locally: {e2}")
        # Fallback: create minimal implementations
        DatabaseManager = None

class KGIntegrationWorker:
    """Worker for integrating TTL data into Neptune knowledge graph"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
        # Initialize utilities if available
        if DatabaseManager:
            self.db_manager = DatabaseManager()
        else:
            self.db_manager = None
            logger.warning("DatabaseManager not available")
        
        # Neptune configuration
        self.neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT', 
            'solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com')
        self.sparql_endpoint = f"https://{self.neptune_endpoint}:8182/sparql"
        
        # HTTP client for Neptune SPARQL operations
        self.http = urllib3.PoolManager()
        
        # SNS topics for completion notifications
        self.completion_topic = os.environ.get('KG_COMPLETION_TOPIC_ARN')
        
    def lambda_handler(self, event, context):
        """Main Lambda handler for KG integration"""
        
        try:
            logger.info(f"Processing KG integration event: {json.dumps(event, default=str)}")
            
            # Parse SNS message
            records = event.get('Records', [])
            results = []
            
            for record in records:
                if record.get('EventSource') == 'aws:sns':
                    message = json.loads(record['Sns']['Message'])
                    result = self.process_kg_integration(message)
                    results.append(result)
                else:
                    logger.warning(f"Unexpected event source: {record.get('EventSource')}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'KG integration completed',
                    'processed_count': len(results),
                    'results': results
                })
            }
            
        except Exception as e:
            logger.error(f"Error in KG integration: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': str(e),
                    'message': 'KG integration failed'
                })
            }
    
    def process_kg_integration(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single KG integration message"""
        
        document_id = message.get('document_id')
        processing_type = message.get('processing_type', 'document_structure')
        ttl_location = message.get('ttl_location')
        ttl_key = message.get('ttl_key')
        
        logger.info(f"Processing KG integration for document: {document_id}, type: {processing_type}")
        
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
            load_result = self.load_ttl_to_neptune(document_id, ttl_content, processing_type)
            
            if load_result['success']:
                # Validate loaded data
                validation_result = self.validate_loaded_data(document_id, processing_type)
                
                # Update processing status
                self.update_processing_status(document_id, 'kg_integration_complete', {
                    'processing_type': processing_type,
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success'],
                    'neptune_operations': load_result.get('operations_count', 0)
                })
                
                # Send completion notification
                self.send_completion_notification(document_id, processing_type, {
                    'status': 'success',
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success']
                })
                
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'processing_type': processing_type,
                    'triples_loaded': load_result.get('triples_count', 0),
                    'validation_passed': validation_result['success']
                }
            else:
                logger.error(f"Neptune loading failed for {document_id}: {load_result['error']}")
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': load_result['error']
                }
                
        except Exception as e:
            logger.error(f"Error processing KG integration for {document_id}: {str(e)}")
            return {
                'document_id': document_id,
                'status': 'error',
                'error': str(e)
            }
    
    def download_ttl_from_s3(self, ttl_location: str, ttl_key: str) -> Optional[str]:
        """Download TTL content from S3"""
        
        try:
            # Extract bucket from S3 location
            bucket = ttl_location.replace('s3://', '').split('/')[0]
            
            logger.info(f"Downloading TTL from s3://{bucket}/{ttl_key}")
            
            response = self.s3_client.get_object(Bucket=bucket, Key=ttl_key)
            ttl_content = response['Body'].read().decode('utf-8')
            
            logger.info(f"Downloaded TTL content: {len(ttl_content)} characters")
            return ttl_content
            
        except Exception as e:
            logger.error(f"Error downloading TTL from S3: {str(e)}")
            return None
    
    def load_ttl_to_neptune(self, document_id: str, ttl_content: str, processing_type: str) -> Dict[str, Any]:
        """Load TTL content into Neptune using SPARQL INSERT operations"""
        
        try:
            logger.info(f"Loading TTL to Neptune for document: {document_id}")
            
            # Parse TTL into individual subjects for SPARQL INSERT
            subjects = self.parse_ttl_subjects(ttl_content)
            
            successful_operations = 0
            total_operations = len(subjects)
            
            for i, subject_ttl in enumerate(subjects):
                try:
                    # Create SPARQL INSERT query
                    sparql_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    PREFIX sg: <http://solve.global/knowledge-commons/>
                    PREFIX kr: <http://solve.global/knowledge-commons/schema#>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                    
                    INSERT DATA {{
                        {subject_ttl}
                    }}
                    """
                    
                    # Execute SPARQL INSERT
                    response = self.http.request(
                        'POST',
                        self.sparql_endpoint,
                        body=sparql_query.encode('utf-8'),
                        headers={
                            'Content-Type': 'application/sparql-update',
                            'Accept': 'application/json'
                        }
                    )
                    
                    if response.status == 200:
                        successful_operations += 1
                        logger.debug(f"Successfully loaded subject {i+1}/{total_operations}")
                    else:
                        logger.error(f"SPARQL INSERT failed for subject {i+1}: {response.status} - {response.data}")
                        
                except Exception as e:
                    logger.error(f"Error loading subject {i+1}: {str(e)}")
            
            success_rate = successful_operations / total_operations if total_operations > 0 else 0
            
            logger.info(f"Neptune loading completed: {successful_operations}/{total_operations} operations successful ({success_rate:.1%})")
            
            return {
                'success': success_rate >= 0.9,  # 90% success rate threshold
                'operations_count': total_operations,
                'successful_operations': successful_operations,
                'success_rate': success_rate,
                'triples_count': self.estimate_triples_count(ttl_content)
            }
            
        except Exception as e:
            logger.error(f"Error loading TTL to Neptune: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def parse_ttl_subjects(self, ttl_content: str) -> List[str]:
        """Parse TTL content into individual subjects for SPARQL INSERT"""
        
        lines = ttl_content.split('\n')
        subjects = []
        current_subject = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip prefixes, comments, and empty lines
            if (not stripped or 
                stripped.startswith('@prefix') or 
                stripped.startswith('#') or
                stripped.startswith('=')):
                continue
            
            # Check if this starts a new subject (contains URI and 'a' type declaration)
            if not line.startswith(' ') and not line.startswith('\t') and ('sg:' in line or '<http' in line):
                # Save previous subject
                if current_subject:
                    subjects.append('\n'.join(current_subject))
                    current_subject = []
                
                # Start new subject
                current_subject = [line]
            else:
                # Continuation of current subject
                if current_subject:
                    current_subject.append(line)
        
        # Add final subject
        if current_subject:
            subjects.append('\n'.join(current_subject))
        
        logger.info(f"Parsed TTL into {len(subjects)} subjects")
        return subjects
    
    def estimate_triples_count(self, ttl_content: str) -> int:
        """Estimate number of triples in TTL content"""
        # Simple estimation based on semicolons and periods
        return ttl_content.count(';') + ttl_content.count(' .')
    
    def validate_loaded_data(self, document_id: str, processing_type: str) -> Dict[str, Any]:
        """Validate that data was successfully loaded into Neptune"""
        
        try:
            # Query to check if document exists in Neptune
            validation_query = f"""
            PREFIX sg: <http://solve.global/knowledge-commons/>
            PREFIX kr: <http://solve.global/knowledge-commons/schema#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            
            SELECT ?doc ?title ?chunks WHERE {{
                ?doc a kr:Document ;
                     dcterms:identifier "{document_id}" ;
                     dcterms:title ?title .
                OPTIONAL {{
                    SELECT (COUNT(?chunk) as ?chunks) WHERE {{
                        ?chunk a kr:DocumentChunk ;
                               kr:parentDocument ?doc .
                    }}
                }}
            }}
            """
            
            response = self.http.request(
                'POST',
                self.sparql_endpoint,
                body=validation_query.encode('utf-8'),
                headers={
                    'Content-Type': 'application/sparql-query',
                    'Accept': 'application/json'
                }
            )
            
            if response.status == 200:
                result = json.loads(response.data.decode('utf-8'))
                bindings = result.get('results', {}).get('bindings', [])
                
                if bindings:
                    doc_data = bindings[0]
                    logger.info(f"Validation successful for {document_id}: {doc_data}")
                    return {
                        'success': True,
                        'document_found': True,
                        'title': doc_data.get('title', {}).get('value', ''),
                        'chunks_count': int(doc_data.get('chunks', {}).get('value', 0))
                    }
                else:
                    logger.warning(f"Validation failed: Document {document_id} not found in Neptune")
                    return {
                        'success': False,
                        'document_found': False,
                        'error': 'Document not found in Neptune after loading'
                    }
            else:
                logger.error(f"Validation query failed: {response.status} - {response.data}")
                return {
                    'success': False,
                    'error': f'Validation query failed: {response.status}'
                }
                
        except Exception as e:
            logger.error(f"Error validating loaded data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_processing_status(self, document_id: str, status: str, metadata: Dict[str, Any]):
        """Update document processing status in PostgreSQL"""
        
        try:
            self.db_manager.update_processing_status(
                document_id=document_id,
                processing_stage='kg_integration',
                status=status,
                metadata=metadata
            )
            
            logger.info(f"Updated processing status for {document_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error updating processing status for {document_id}: {str(e)}")
    
    def send_completion_notification(self, document_id: str, processing_type: str, result: Dict[str, Any]):
        """Send completion notification via SNS"""
        
        try:
            if not self.completion_topic:
                logger.info("Completion topic not configured, skipping notification")
                return
            
            message = {
                'document_id': document_id,
                'processing_type': processing_type,
                'processing_stage': 'kg_integration',
                'status': result['status'],
                'timestamp': datetime.now().isoformat(),
                'details': result
            }
            
            self.sns_client.publish(
                TopicArn=self.completion_topic,
                Message=json.dumps(message),
                Subject=f'KG Integration Complete: {document_id}'
            )
            
            logger.info(f"Completion notification sent for {document_id}")
            
        except Exception as e:
            logger.error(f"Error sending completion notification: {str(e)}")

# Lambda handler function
def lambda_handler(event, context):
    """AWS Lambda entry point"""
    worker = KGIntegrationWorker()
    return worker.lambda_handler(event, context)
