#!/usr/bin/env python3
"""
Standardized Messaging Module for Climate Risk RAG System
Provides consistent message formats across all pipeline stages
"""

import json
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class StandardizedMessagePublisher:
    """Handles publishing of standardized messages across the pipeline"""
    
    def __init__(self):
        self.sns = boto3.client('sns')
    
    def publish_text_extraction_complete(self, 
                                       doc_id: str, 
                                       doc_hash: str, 
                                       text_location: str,
                                       structure_location: str,
                                       document_metadata: Dict,
                                       processing_metadata: Dict,
                                       topic_arn: str) -> None:
        """Publish standardized text extraction complete message"""
        
        message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "text_ready",
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "document_metadata": {
                "original_filename": document_metadata.get("original_filename", "unknown.pdf"),
                "file_size": document_metadata.get("file_size", 0),
                "page_count": document_metadata.get("page_count", 0),
                "processing_started": document_metadata.get("processing_started", datetime.utcnow().isoformat() + "Z")
            },
            "data_locations": {
                "text_location": text_location,
                "structure_location": structure_location,
                "base_path": text_location.rsplit('/', 1)[0] + "/"
            },
            "processing_metadata": {
                "total_characters": processing_metadata.get("character_count", 0),
                "blocks_extracted": processing_metadata.get("blocks_extracted", 0),
                "pages_processed": processing_metadata.get("pages_processed", 0),
                "processing_duration_ms": processing_metadata.get("processing_time_ms", 0),
                "cost_estimate": processing_metadata.get("cost_estimate", 0.0),
                "files_created": processing_metadata.get("files_created", [])
            },
            "integration_flags": {
                "documentid_manager_integration": True,
                "selective_migration_used": processing_metadata.get("selective_migration_used", False),
                "database_tracking_enabled": True
            }
        }
        
        try:
            response = self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message, default=str),
                Subject=f"Text extraction complete: {doc_id}",
                MessageAttributes={
                    'stage': {
                        'DataType': 'String',
                        'StringValue': 'text_ready'
                    },
                    'doc_id': {
                        'DataType': 'String',
                        'StringValue': doc_id
                    },
                    'version': {
                        'DataType': 'String',
                        'StringValue': '1.0'
                    }
                }
            )
            
            logger.info(f"Published text extraction complete message for {doc_id}: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Failed to publish text extraction complete message: {e}")
            raise
    
    def publish_chunks_ready(self,
                           doc_id: str,
                           doc_hash: str,
                           chunks_location: str,
                           text_location: str,
                           document_metadata: Dict,
                           processing_metadata: Dict,
                           topic_arn: str) -> None:
        """Publish standardized chunks ready message"""
        
        message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "chunks_ready",
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "document_metadata": document_metadata,
            "data_locations": {
                "text_location": text_location,
                "chunks_location": chunks_location,
                "structure_location": text_location.replace("raw_text.txt", "textract_response.json")
            },
            "processing_metadata": {
                "chunks_count": processing_metadata.get("chunks_count", 0),
                "total_characters": processing_metadata.get("total_characters", 0),
                "processing_duration_ms": processing_metadata.get("processing_duration_ms", 0),
                "cost_estimate": processing_metadata.get("cost_estimate", 0.0)
            },
            "integration_flags": {
                "documentid_manager_integration": True,
                "selective_migration_used": processing_metadata.get("selective_migration_used", False),
                "database_tracking_enabled": True
            }
        }
        
        try:
            response = self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message, default=str),
                Subject=f"Chunks ready: {doc_id}",
                MessageAttributes={
                    'stage': {
                        'DataType': 'String',
                        'StringValue': 'chunks_ready'
                    },
                    'doc_id': {
                        'DataType': 'String',
                        'StringValue': doc_id
                    },
                    'version': {
                        'DataType': 'String',
                        'StringValue': '1.0'
                    }
                }
            )
            
            logger.info(f"Published chunks ready message for {doc_id}: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Failed to publish chunks ready message: {e}")
            raise
    
    def publish_nlp_worker_task(self,
                              doc_id: str,
                              doc_hash: str,
                              chunks_location: str,
                              text_location: str,
                              document_metadata: Dict,
                              nlp_config: Dict,
                              topic_arn: str) -> None:
        """Publish standardized NLP worker task message"""
        
        message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "nlp_ready",
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "document_metadata": document_metadata,
            "data_locations": {
                "text_location": text_location,
                "chunks_location": chunks_location,
                "structure_location": text_location.replace("raw_text.txt", "textract_response.json")
            },
            "processing_metadata": {
                "chunks_count": nlp_config.get("chunks_count", 0),
                "total_characters": nlp_config.get("total_characters", 0)
            },
            "integration_flags": {
                "documentid_manager_integration": True,
                "selective_migration_used": False,
                "database_tracking_enabled": True
            },
            "nlp_config": {
                "provider": nlp_config.get("provider", "comprehend"),
                "processing_type": nlp_config.get("processing_type", "entity_and_phrases"),
                "language": nlp_config.get("language", "auto"),
                "cost_threshold": nlp_config.get("cost_threshold", 0.50)
            }
        }
        
        try:
            response = self.sns.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message, default=str),
                Subject=f"NLP processing: {doc_id}",
                MessageAttributes={
                    'stage': {
                        'DataType': 'String',
                        'StringValue': 'nlp_ready'
                    },
                    'doc_id': {
                        'DataType': 'String',
                        'StringValue': doc_id
                    },
                    'version': {
                        'DataType': 'String',
                        'StringValue': '1.0'
                    }
                }
            )
            
            logger.info(f"Published NLP worker task for {doc_id}: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"Failed to publish NLP worker task: {e}")
            raise

class StandardizedMessageParser:
    """Handles parsing of standardized messages"""
    
    @staticmethod
    def parse_sns_message(event: Dict) -> Dict:
        """Parse SNS message from Lambda event"""
        try:
            # Handle direct SNS invocation
            if 'Records' in event and event['Records']:
                record = event['Records'][0]
                if 'Sns' in record:
                    message = json.loads(record['Sns']['Message'])
                    return message
                elif 'body' in record:
                    # Handle SQS -> SNS message
                    body = json.loads(record['body'])
                    if 'Message' in body:
                        message = json.loads(body['Message'])
                        return message
                    else:
                        return body
            
            raise ValueError("Invalid event format - no SNS message found")
            
        except Exception as e:
            logger.error(f"Failed to parse SNS message: {e}")
            raise
    
    @staticmethod
    def validate_message_format(message: Dict, expected_stage: str = None) -> bool:
        """Validate message follows standardized format"""
        try:
            required_fields = ['version', 'timestamp', 'source', 'stage', 'doc_id', 'doc_hash']
            
            for field in required_fields:
                if field not in message:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            if message['version'] != '1.0':
                logger.error(f"Invalid version: {message['version']}")
                return False
            
            if message['source'] != 'climate-risk-rag-system':
                logger.error(f"Invalid source: {message['source']}")
                return False
            
            if expected_stage and message['stage'] != expected_stage:
                logger.error(f"Expected stage {expected_stage}, got {message['stage']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Message validation error: {e}")
            return False
    
    @staticmethod
    def extract_processing_info(message: Dict) -> Dict:
        """Extract key processing information from standardized message"""
        return {
            'doc_id': message['doc_id'],
            'doc_hash': message['doc_hash'],
            'stage': message['stage'],
            'text_location': message.get('data_locations', {}).get('text_location'),
            'chunks_location': message.get('data_locations', {}).get('chunks_location'),
            'structure_location': message.get('data_locations', {}).get('structure_location'),
            'document_metadata': message.get('document_metadata', {}),
            'processing_metadata': message.get('processing_metadata', {}),
            'integration_flags': message.get('integration_flags', {})
        }

# Utility functions for backward compatibility
def create_legacy_message_adapter(standardized_message: Dict) -> Dict:
    """Convert standardized message to legacy format for backward compatibility"""
    
    if standardized_message['stage'] == 'text_ready':
        return {
            'stage': 'text_ready',
            'doc_id': standardized_message['doc_id'],
            'doc_hash': standardized_message['doc_hash'],
            'full_text_location': standardized_message['data_locations']['text_location'],
            'document_structure_location': standardized_message['data_locations']['structure_location'],
            'documentid_manager_integration': standardized_message['integration_flags']['documentid_manager_integration'],
            'selective_migration_used': standardized_message['integration_flags']['selective_migration_used']
        }
    
    elif standardized_message['stage'] == 'chunks_ready':
        return {
            'doc_id': standardized_message['doc_id'],
            'chunks_location': standardized_message['data_locations']['chunks_location'],
            'chunks_count': standardized_message['processing_metadata']['chunks_count'],
            'full_text_location': standardized_message['data_locations']['text_location']
        }
    
    else:
        return standardized_message

def upgrade_legacy_message(legacy_message: Dict, stage: str) -> Dict:
    """Upgrade legacy message to standardized format"""
    
    base_message = {
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "climate-risk-rag-system",
        "stage": stage,
        "doc_id": legacy_message.get('doc_id', ''),
        "doc_hash": legacy_message.get('doc_hash', ''),
        "document_metadata": {},
        "data_locations": {},
        "processing_metadata": {},
        "integration_flags": {
            "documentid_manager_integration": legacy_message.get('documentid_manager_integration', True),
            "selective_migration_used": legacy_message.get('selective_migration_used', False),
            "database_tracking_enabled": True
        }
    }
    
    if stage == 'text_ready':
        base_message['data_locations'] = {
            'text_location': legacy_message.get('full_text_location', ''),
            'structure_location': legacy_message.get('document_structure_location', '')
        }
    
    elif stage == 'chunks_ready':
        base_message['data_locations'] = {
            'chunks_location': legacy_message.get('chunks_location', ''),
            'text_location': legacy_message.get('full_text_location', '')
        }
        base_message['processing_metadata'] = {
            'chunks_count': legacy_message.get('chunks_count', 0)
        }
    
    return base_message
