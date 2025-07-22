"""
Vector Embeddings Initiator Lambda Function
Processes chunks_ready messages and initiates vector embedding jobs
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

class VectorEmbeddingsInitiator:
    """
    Vector embeddings initiator with audit-first database design
    Processes chunks_ready messages and delegates to worker
    """
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        
        # Environment configuration
        self.worker_function_name = os.environ.get('VECTOR_WORKER_FUNCTION_NAME', 'vector-embeddings-worker')
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        logger.info("✅ Vector Embeddings Initiator initialized")
        logger.info(f"Worker function: {self.worker_function_name}")
        logger.info(f"Chunks bucket: {self.chunks_bucket}")
    
    def parse_chunks_ready_message(self, message_body: str) -> Dict[str, Any]:
        """Parse standardized chunks_ready message"""
        try:
            message = json.loads(message_body)
            
            # Extract key fields from standardized message
            doc_id = message.get('doc_id')
            stage = message.get('stage')
            data_locations = message.get('data_locations', {})
            processing_metadata = message.get('processing_metadata', {})
            
            if not doc_id:
                raise ValueError("Missing doc_id in message")
            
            if stage != 'chunks_ready':
                raise ValueError(f"Expected stage 'chunks_ready', got '{stage}'")
            
            # Extract S3 locations
            chunks_location = data_locations.get('chunks_location')
            chunk_metadata_location = data_locations.get('chunk_metadata_location')
            
            if not chunks_location:
                raise ValueError("Missing chunks_location in message")
            
            return {
                'doc_id': doc_id,
                'chunks_location': chunks_location,
                'chunk_metadata_location': chunk_metadata_location,
                'processing_metadata': processing_metadata,
                'document_metadata': message.get('document_metadata', {})
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse chunks_ready message: {e}")
            raise
    
    def validate_chunks_exist(self, chunks_location: str) -> Dict[str, Any]:
        """Validate that chunks exist and get basic metadata"""
        try:
            # Parse S3 location
            if not chunks_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 URL format: {chunks_location}")
            
            # Extract bucket and prefix
            s3_parts = chunks_location[5:].split('/', 1)
            bucket = s3_parts[0]
            prefix = s3_parts[1] if len(s3_parts) > 1 else ""
            
            # Handle both directory paths and paths ending with "chunks.json"
            if prefix.endswith('chunks.json'):
                # If path ends with chunks.json, use the directory instead
                prefix = '/'.join(prefix.split('/')[:-1]) + '/'
                logger.info(f"Adjusted chunks path from chunks.json to directory: {prefix}")
            elif not prefix.endswith('/'):
                # Ensure prefix ends with /
                prefix += '/'
            
            logger.info(f"Validating chunks in s3://{bucket}/{prefix}")
            
            # List objects to validate chunks exist
            s3 = boto3.client('s3')
            response = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=1000  # Should be enough for most documents
            )
            
            if 'Contents' not in response:
                raise ValueError(f"No chunks found at {chunks_location}")
            
            # Count chunk files (exclude metadata.json)
            chunk_files = [
                obj for obj in response['Contents'] 
                if obj['Key'].endswith('.json') and not obj['Key'].endswith('metadata.json')
            ]
            
            if not chunk_files:
                raise ValueError(f"No chunk files found at {chunks_location}")
            
            logger.info(f"Found {len(chunk_files)} chunk files")
            
            return {
                'chunks_count': len(chunk_files),
                'total_size': sum(obj['Size'] for obj in chunk_files),
                'bucket': bucket,
                'prefix': prefix
            }
            
        except Exception as e:
            logger.error(f"Failed to validate chunks: {e}")
            raise
    
    def invoke_worker(self, doc_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke vector embeddings worker asynchronously"""
        try:
            # Prepare worker payload
            worker_payload = {
                'doc_id': doc_id,
                'chunks_location': job_data['chunks_location'],
                'chunk_metadata_location': job_data.get('chunk_metadata_location'),
                'processing_metadata': job_data.get('processing_metadata', {}),
                'document_metadata': job_data.get('document_metadata', {}),
                'validation_data': job_data.get('validation_data', {}),
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Invoke worker function asynchronously
            response = self.lambda_client.invoke(
                FunctionName=self.worker_function_name,
                InvocationType='Event',  # Asynchronous invocation
                Payload=json.dumps(worker_payload)
            )
            
            logger.info(f"Invoked worker for {doc_id}: StatusCode {response['StatusCode']}")
            
            return {
                'status_code': response['StatusCode'],
                'invocation_type': 'Event',
                'worker_function': self.worker_function_name
            }
            
        except Exception as e:
            logger.error(f"Failed to invoke worker for {doc_id}: {e}")
            raise
    
    def process_chunks_ready_message(self, message_body: str) -> Dict[str, Any]:
        """Process a single chunks_ready message"""
        try:
            # Parse the standardized message
            parsed_message = self.parse_chunks_ready_message(message_body)
            doc_id = parsed_message['doc_id']
            
            logger.info(f"Processing vector embeddings initiation for doc_id: {doc_id}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='vector_embedding',
                status='in_progress'
            )
            
            # Validate chunks exist
            validation_data = self.validate_chunks_exist(parsed_message['chunks_location'])
            
            # Prepare job data for worker
            job_data = {
                'chunks_location': parsed_message['chunks_location'],
                'chunk_metadata_location': parsed_message.get('chunk_metadata_location'),
                'processing_metadata': parsed_message.get('processing_metadata', {}),
                'document_metadata': parsed_message.get('document_metadata', {}),
                'validation_data': validation_data
            }
            
            # Invoke worker asynchronously
            worker_response = self.invoke_worker(doc_id, job_data)
            
            # Update status to completed (initiator job done)
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='vector_embedding',
                status='completed',
                system_id=self.worker_function_name
            )
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'worker_status': 'invoked',
                'chunks_location': parsed_message['chunks_location'],
                'chunks_count': validation_data['chunks_count'],
                'worker_response': worker_response
            }
            
        except Exception as e:
            # Extract doc_id for error status if possible
            doc_id = 'unknown'
            try:
                parsed = json.loads(message_body)
                doc_id = parsed.get('doc_id', 'unknown')
            except:
                pass
            
            logger.error(f"Error processing chunks_ready message for {doc_id}: {str(e)}")
            
            # Update status to failed if we have a doc_id
            if doc_id != 'unknown':
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='vector_embedding',
                    status='failed',
                    error_message=str(e)
                )
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }

def lambda_handler(event, context):
    """Lambda handler for Vector Embeddings Initiator"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        initiator = VectorEmbeddingsInitiator()
        results = []
        
        # Handle SQS events (primary path)
        if 'Records' in event:
            logger.info(f"Found {len(event['Records'])} records in event")
            
            for i, record in enumerate(event['Records']):
                logger.info(f"Processing record {i+1}/{len(event['Records'])}")
                logger.info(f"Record keys: {list(record.keys())}")
                
                # Check for standard SQS event structure
                if record.get('eventSource') == 'aws:sqs':
                    logger.info("Standard SQS event structure detected")
                    try:
                        sqs_body = json.loads(record['body'])
                        if sqs_body.get('Type') == 'Notification':
                            logger.info("Processing SQS-wrapped SNS message (standard structure)")
                            sns_message = sqs_body['Message']
                            logger.info(f"SNS Message content: {sns_message[:200]}...")  # Log first 200 chars
                            result = initiator.process_chunks_ready_message(sns_message)
                            results.append(result)
                        else:
                            logger.warning(f"Unexpected SQS message format: {sqs_body.get('Type')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message: {e}")
                        results.append({'status': 'error', 'error': f'SQS parse error: {e}'})
                
                # Check for non-standard structure but with body field (likely SQS)
                elif 'body' in record:
                    logger.info("Non-standard SQS event structure detected (missing eventSource but has body)")
                    try:
                        sqs_body = json.loads(record['body'])
                        if sqs_body.get('Type') == 'Notification':
                            logger.info("Processing SQS-wrapped SNS message (non-standard structure)")
                            sns_message = sqs_body['Message']
                            logger.info(f"SNS Message content: {sns_message[:200]}...")  # Log first 200 chars
                            result = initiator.process_chunks_ready_message(sns_message)
                            results.append(result)
                        else:
                            logger.warning(f"Unexpected SQS message format: {sqs_body.get('Type')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse SQS message: {e}")
                        results.append({'status': 'error', 'error': f'SQS parse error: {e}'})
                
                # Handle direct SNS invocation
                elif record.get('EventSource') == 'aws:sns' or ('Sns' in record):
                    logger.info("SNS event structure detected")
                    sns_message = record['Sns']['Message']
                    logger.info(f"SNS Message content: {sns_message[:200]}...")  # Log first 200 chars
                    result = initiator.process_chunks_ready_message(sns_message)
                    results.append(result)
                
                else:
                    logger.warning(f"Unexpected record format: {json.dumps(record, default=str)}")
        
        # Handle direct invocation for testing
        elif 'doc_id' in event:
            logger.info("Processing direct invocation")
            # Convert direct event to message format for testing
            test_message = json.dumps(event)
            result = initiator.process_chunks_ready_message(test_message)
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Vector embedding jobs initiated',
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
