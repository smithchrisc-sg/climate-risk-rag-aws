#!/usr/bin/env python3
"""
Document Structure Knowledge Graph Processor
Processes document structure completion events and generates TTL for Neptune loading

This Lambda function:
1. Receives SNS messages from text chunker completion
2. Generates document structure TTL using Dublin Core vocabulary
3. Uploads TTL to S3 for Neptune bulk loading
4. Triggers KG integration worker for SPARQL loading
5. Updates processing status in PostgreSQL

Architecture: Designed for extensibility to support future entity processing
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

# Add layers to path for shared utilities
sys.path.append('/opt/python')

try:
    # Import from climate-risk-core-utilities layer (correct path)
    from utils.DatabaseManager import DatabaseManager
    from utils.DocumentIDManager import DocumentIDManager
    logger.info("Successfully imported shared utilities from layer")
except ImportError as e:
    logger.error(f"Failed to import shared utilities from layer: {e}")
    # For local testing, try relative imports from layers directory
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'app-source', 'utils'))
        from DatabaseManager import DatabaseManager
        from DocumentIDManager import DocumentIDManager
        logger.info("Successfully imported utilities from local layers directory")
    except ImportError as e2:
        logger.error(f"Failed to import utilities locally: {e2}")
        # Fallback: create minimal implementations
        DatabaseManager = None
        DocumentIDManager = None

class DocumentStructureKGProcessor:
    """Processes document structure for knowledge graph integration"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        
        # Initialize utilities if available
        if DatabaseManager:
            self.db_manager = DatabaseManager()
        else:
            self.db_manager = None
            logger.warning("DatabaseManager not available")
            
        if DocumentIDManager:
            self.doc_id_manager = DocumentIDManager()
        else:
            self.doc_id_manager = None
            logger.warning("DocumentIDManager not available")
        
        # S3 buckets
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.text_bucket = os.environ.get('TEXT_BUCKET', 'solve-global-kr-dl-text-861276078413-us-east-1')
        self.ttl_bucket = os.environ.get('TTL_BUCKET', 'solve-global-kr-dl-neptune-ttl-861276078413-us-east-1')
        
        # SNS topics for downstream processing
        self.kg_integration_topic = os.environ.get('KG_INTEGRATION_TOPIC_ARN')
        
        # Future: Entity processing topic (architecture ready)
        self.entity_processing_topic = os.environ.get('ENTITY_PROCESSING_TOPIC_ARN')
        
    def lambda_handler(self, event, context):
        """Main Lambda handler for document structure KG processing"""
        
        try:
            logger.info(f"Processing document structure KG event: {json.dumps(event, default=str)}")
            
            # Parse SNS message
            records = event.get('Records', [])
            results = []
            
            for record in records:
                if record.get('EventSource') == 'aws:sns':
                    message = json.loads(record['Sns']['Message'])
                    result = self.process_document_structure(message)
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
    
    def process_document_structure(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document structure completion message"""
        
        document_id = message.get('document_id')
        processing_status = message.get('status', 'unknown')
        
        logger.info(f"Processing document structure for document: {document_id}")
        
        if processing_status != 'completed':
            logger.warning(f"Document {document_id} not in completed status: {processing_status}")
            return {
                'document_id': document_id,
                'status': 'skipped',
                'reason': f'Document status is {processing_status}, not completed'
            }
        
        try:
            # Generate document structure TTL
            ttl_result = self.generate_document_structure_ttl(document_id)
            
            if ttl_result['success']:
                # Trigger KG integration worker
                integration_result = self.trigger_kg_integration(document_id, ttl_result)
                
                # Update processing status
                self.update_processing_status(document_id, 'kg_structure_processing', {
                    'ttl_generated': True,
                    'ttl_s3_location': ttl_result['s3_location'],
                    'integration_triggered': integration_result['success']
                })
                
                return {
                    'document_id': document_id,
                    'status': 'success',
                    'ttl_location': ttl_result['s3_location'],
                    'integration_triggered': integration_result['success']
                }
            else:
                logger.error(f"TTL generation failed for {document_id}: {ttl_result['error']}")
                return {
                    'document_id': document_id,
                    'status': 'failed',
                    'error': ttl_result['error']
                }
                
        except Exception as e:
            logger.error(f"Error processing document structure for {document_id}: {str(e)}")
            return {
                'document_id': document_id,
                'status': 'error',
                'error': str(e)
            }
    
    def generate_document_structure_ttl(self, document_id: str) -> Dict[str, Any]:
        """Generate TTL for document structure using Dublin Core vocabulary"""
        
        try:
            # Import TTL generator (from our updated knowledge graph code)
            from document_ttl_generator import DocumentTTLGenerator
            
            logger.info(f"Generating TTL for document structure: {document_id}")
            
            # Generate TTL using our Dublin Core integrated generator
            generator = DocumentTTLGenerator(document_id)
            ttl_content = generator.generate_ttl_document()
            
            # Upload TTL to S3
            ttl_key = f"documents/{document_id}/document_structure.ttl"
            s3_location = f"s3://{self.ttl_bucket}/{ttl_key}"
            
            self.s3_client.put_object(
                Bucket=self.ttl_bucket,
                Key=ttl_key,
                Body=ttl_content.encode('utf-8'),
                ContentType='text/turtle',
                Metadata={
                    'document_id': document_id,
                    'generated_at': datetime.now().isoformat(),
                    'content_type': 'document_structure',
                    'schema_version': 'dublin_core_v2'
                }
            )
            
            logger.info(f"TTL uploaded to: {s3_location}")
            
            return {
                'success': True,
                's3_location': s3_location,
                'ttl_size': len(ttl_content),
                'ttl_key': ttl_key
            }
            
        except Exception as e:
            logger.error(f"Error generating TTL for {document_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def trigger_kg_integration(self, document_id: str, ttl_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger KG integration worker to load TTL into Neptune"""
        
        try:
            if not self.kg_integration_topic:
                logger.warning("KG integration topic not configured")
                return {'success': False, 'error': 'KG integration topic not configured'}
            
            message = {
                'document_id': document_id,
                'processing_type': 'document_structure',
                'ttl_location': ttl_result['s3_location'],
                'ttl_key': ttl_result['ttl_key'],
                'schema_version': 'dublin_core_v2',
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.sns_client.publish(
                TopicArn=self.kg_integration_topic,
                Message=json.dumps(message),
                Subject=f'KG Integration: Document Structure - {document_id}'
            )
            
            logger.info(f"KG integration triggered for {document_id}: {response['MessageId']}")
            
            return {
                'success': True,
                'message_id': response['MessageId']
            }
            
        except Exception as e:
            logger.error(f"Error triggering KG integration for {document_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_processing_status(self, document_id: str, status: str, metadata: Dict[str, Any]):
        """Update document processing status in PostgreSQL"""
        
        try:
            if self.db_manager:
                # Update processing status with KG structure information
                self.db_manager.update_processing_status(
                    document_id=document_id,
                    processing_stage='kg_structure',
                    status=status,
                    metadata=metadata
                )
                
                logger.info(f"Updated processing status for {document_id}: {status}")
            else:
                logger.warning(f"Database manager not available, cannot update status for {document_id}")
            
        except Exception as e:
            logger.error(f"Error updating processing status for {document_id}: {str(e)}")
    
    # Future: Entity processing methods (architecture ready)
    def process_entity_completion(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Future: Process entity extraction completion messages"""
        # This method will be implemented when we add entity processing
        pass
    
    def generate_entity_ttl(self, document_id: str, entities: List[Dict]) -> Dict[str, Any]:
        """Future: Generate TTL for extracted entities"""
        # This method will be implemented for entity integration
        pass

# Lambda handler function
def lambda_handler(event, context):
    """AWS Lambda entry point"""
    processor = DocumentStructureKGProcessor()
    return processor.lambda_handler(event, context)
