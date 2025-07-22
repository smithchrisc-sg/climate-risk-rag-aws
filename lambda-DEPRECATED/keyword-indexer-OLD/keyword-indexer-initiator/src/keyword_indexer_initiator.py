"""
Keyword Indexer Initiator Lambda Function
Processes text extraction completion messages and initiates async keyword indexing
Uses audit-first database design with DatabaseManager
"""

import json
import boto3
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import from locked database core layer - DO NOT CHANGE
from utils.DatabaseManager import DatabaseManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class KeywordIndexerInitiator:
    """Initiates async keyword indexing jobs with audit-first status tracking"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.sns = boto3.client('sns')
        
        # Environment configuration
        self.text_bucket = os.environ.get('TEXT_BUCKET')
        self.worker_function_name = os.environ.get('WORKER_FUNCTION_NAME', 'async-keyword-indexer-worker')
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        logger.info("✅ Keyword Indexer Initiator initialized")
        logger.info(f"Text bucket: {self.text_bucket}")
        logger.info(f"Worker function: {self.worker_function_name}")
    
    def parse_text_ready_message(self, message_body: str) -> Dict[str, Any]:
        """Parse standardized text_ready message"""
        try:
            message = json.loads(message_body)
            
            # Extract key fields from standardized message
            doc_id = message.get('doc_id')
            stage = message.get('stage')
            data_locations = message.get('data_locations', {})
            
            if not doc_id:
                raise ValueError("Missing doc_id in message")
            
            if stage != 'text_ready':
                raise ValueError(f"Expected stage 'text_ready', got '{stage}'")
            
            # Extract S3 locations
            text_location = data_locations.get('text_location')
            structure_location = data_locations.get('structure_location')
            
            if not text_location or not structure_location:
                raise ValueError("Missing required S3 locations in message")
            
            return {
                'doc_id': doc_id,
                'text_location': text_location,
                'structure_location': structure_location,
                'processing_metadata': message.get('processing_metadata', {}),
                'document_metadata': message.get('document_metadata', {})
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse text_ready message: {e}")
            raise
    
    def invoke_keyword_indexer_worker(self, doc_id: str, text_location: str, 
                                    structure_location: str, metadata: Dict) -> str:
        """Invoke keyword indexer worker asynchronously"""
        try:
            # Create worker payload
            worker_payload = {
                'doc_id': doc_id,
                'text_location': text_location,
                'structure_location': structure_location,
                'processing_metadata': metadata.get('processing_metadata', {}),
                'document_metadata': metadata.get('document_metadata', {}),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Invoke worker function asynchronously
            response = self.lambda_client.invoke(
                FunctionName=self.worker_function_name,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(worker_payload)
            )
            
            status_code = response.get('StatusCode', 0)
            if status_code == 202:  # Async invocation success
                logger.info(f"Successfully invoked worker for doc_id: {doc_id}")
                return 'invoked'
            else:
                raise Exception(f"Worker invocation failed with status: {status_code}")
                
        except Exception as e:
            logger.error(f"Failed to invoke worker for {doc_id}: {str(e)}")
            raise
    
    def process_text_ready_message(self, message_body: str) -> Dict[str, Any]:
        """Process a single text_ready message"""
        try:
            # Parse the standardized message
            parsed_message = self.parse_text_ready_message(message_body)
            doc_id = parsed_message['doc_id']
            
            logger.info(f"Processing keyword indexing initiation for doc_id: {doc_id}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_index_initiate',
                status='in_progress'
            )
            
            # Invoke worker asynchronously
            worker_status = self.invoke_keyword_indexer_worker(
                doc_id=doc_id,
                text_location=parsed_message['text_location'],
                structure_location=parsed_message['structure_location'],
                metadata={
                    'processing_metadata': parsed_message['processing_metadata'],
                    'document_metadata': parsed_message['document_metadata']
                }
            )
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='keyword_index_initiate',
                status='completed',
                system_id=self.worker_function_name
            )
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'worker_status': worker_status,
                'text_location': parsed_message['text_location'],
                'structure_location': parsed_message['structure_location']
            }
            
        except Exception as e:
            # Extract doc_id for error status if possible
            doc_id = 'unknown'
            try:
                parsed = json.loads(message_body)
                doc_id = parsed.get('doc_id', 'unknown')
            except:
                pass
            
            logger.error(f"Error processing text_ready message for {doc_id}: {str(e)}")
            
            # Update status to failed if we have a doc_id
            if doc_id != 'unknown':
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='keyword_index_initiate',
                    status='failed',
                    error_message=str(e)
                )
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }

def lambda_handler(event, context):
    """Lambda handler for Keyword Indexer Initiator"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        initiator = KeywordIndexerInitiator()
        results = []
        
        # Handle SNS notifications (text extraction complete messages)
        if 'Records' in event:
            for record in event['Records']:
                if record.get('EventSource') == 'aws:sns':
                    # Parse SNS message
                    sns_message = record['Sns']['Message']
                    
                    logger.info(f"Processing SNS message for keyword indexing")
                    result = initiator.process_text_ready_message(sns_message)
                    results.append(result)
                    
                elif record.get('eventSource') == 'aws:sqs':
                    # Handle SQS-wrapped SNS messages
                    try:
                        sqs_body = json.loads(record['body'])
                        if sqs_body.get('Type') == 'Notification':
                            sns_message = sqs_body['Message']
                            
                            logger.info(f"Processing SQS-wrapped SNS message for keyword indexing")
                            result = initiator.process_text_ready_message(sns_message)
                            results.append(result)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message: {e}")
                        results.append({'status': 'error', 'error': f'SQS parse error: {e}'})
        
        # Handle direct invocation for testing
        elif 'doc_id' in event:
            logger.info("Processing direct invocation")
            # Convert direct event to message format for testing
            test_message = json.dumps(event)
            result = initiator.process_text_ready_message(test_message)
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Keyword indexing jobs initiated',
                'processed_records': len(results),
                'results': results
            }, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
