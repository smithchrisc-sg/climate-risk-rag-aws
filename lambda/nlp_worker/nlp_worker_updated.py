#!/usr/bin/env python3
"""
NLP Worker - STANDARDIZED MESSAGING VERSION
Background processor for NLP analysis with S3 data lake storage and standardized message handling
"""
import json
import boto3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Import standardized messaging
from standardized_messaging import StandardizedMessagePublisher, StandardizedMessageParser

# Import NLP components
from nlp_interface import NLPProcessorFactory
from offset_mapper import OffsetMapper
from s3_data_lake_manager import S3DataLakeManager

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Process NLP analysis with standardized messaging
    
    Event format (standardized):
    {
        'version': '1.0',
        'stage': 'nlp_ready',
        'doc_id': str,
        'doc_hash': str,
        'data_locations': {
            'chunks_location': str,
            'text_location': str
        },
        'nlp_config': {
            'provider': str,
            'processing_type': str,
            'cost_threshold': float
        }
    }
    """
    doc_id = None
    
    try:
        # Initialize standardized message components
        message_parser = StandardizedMessageParser()
        message_publisher = StandardizedMessagePublisher()
        
        # Parse standardized SQS message
        message = message_parser.parse_sns_message(event)
        
        # Validate message format
        if not message_parser.validate_message_format(message, 'nlp_ready'):
            raise ValueError("Invalid message format - expected nlp_ready stage")
        
        # Extract processing information
        processing_info = message_parser.extract_processing_info(message)
        doc_id = processing_info['doc_id']
        doc_hash = processing_info['doc_hash']
        chunks_location = processing_info['chunks_location']
        text_location = processing_info['text_location']
        
        # Extract NLP configuration
        nlp_config = message.get('nlp_config', {})
        nlp_provider = nlp_config.get('provider', 'comprehend')
        processing_type = nlp_config.get('processing_type', 'entity_and_phrases')
        cost_threshold = nlp_config.get('cost_threshold', 0.50)
        
        logger.info(f"Starting NLP processing for document: {doc_id} using {nlp_provider}")
        logger.info(f"Processing type: {processing_type}")
        logger.info(f"Cost threshold: ${cost_threshold}")
        
        # Update status to processing (minimal database tracking)
        db_manager = DatabaseManager()
        update_processing_status(db_manager, doc_id, 'PROCESSING', 'NLP analysis in progress')
        
        # Initialize S3 data lake manager
        ner_results_bucket = os.environ.get('NER_RESULTS_BUCKET', 
                                          'solve-global-kr-ner-results-861276078413-us-east-1')
        s3_manager = S3DataLakeManager(ner_results_bucket)
        
        # Load full text for processing
        full_text = load_full_text_from_s3(text_location)
        if not full_text:
            raise ValueError("Could not load full text for NLP processing")
        
        # Load chunks for offset mapping
        chunks = load_chunks_from_s3(chunks_location)
        if not chunks:
            logger.warning("No chunks found - will process full text only")
        
        # Cost validation
        estimated_cost = estimate_processing_cost(full_text, nlp_provider)
        if estimated_cost > cost_threshold:
            raise ValueError(f"Estimated cost ${estimated_cost:.4f} exceeds threshold ${cost_threshold}")
        
        logger.info(f"Estimated processing cost: ${estimated_cost:.4f}")
        
        # Initialize NLP processor
        nlp_processor = NLPProcessorFactory.create_processor(
            provider=nlp_provider,
            region=os.environ.get('COMPREHEND_REGION', 'us-east-1')
        )
        
        # Process NLP analysis
        processing_start = datetime.utcnow()
        
        if processing_type == 'entity_and_phrases':
            # Extract entities and key phrases
            entities_result = nlp_processor.extract_entities(full_text)
            phrases_result = nlp_processor.extract_key_phrases(full_text)
            
            # Combine results
            nlp_results = {
                'entities': entities_result,
                'key_phrases': phrases_result,
                'processing_metadata': {
                    'provider': nlp_provider,
                    'processing_type': processing_type,
                    'character_count': len(full_text),
                    'processing_time_ms': int((datetime.utcnow() - processing_start).total_seconds() * 1000),
                    'actual_cost': estimated_cost,
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }
        else:
            raise ValueError(f"Unsupported processing type: {processing_type}")
        
        # Map results to chunks if available
        if chunks:
            logger.info("Mapping NLP results to chunks using offset mapping")
            offset_mapper = OffsetMapper()
            
            # Map entities to chunks
            entities_mapped = offset_mapper.map_entities_to_chunks(
                entities_result, chunks, full_text
            )
            
            # Map key phrases to chunks
            phrases_mapped = offset_mapper.map_key_phrases_to_chunks(
                phrases_result, chunks, full_text
            )
            
            nlp_results['entities_mapped_to_chunks'] = entities_mapped
            nlp_results['key_phrases_mapped_to_chunks'] = phrases_mapped
            nlp_results['offset_mapping_report'] = offset_mapper.get_mapping_report()
        
        # Store results in S3 data lake
        storage_results = s3_manager.store_nlp_results(doc_id, nlp_results)
        
        # Update database status
        update_processing_status(db_manager, doc_id, 'COMPLETED', 
                               f'NLP processing completed successfully. Cost: ${estimated_cost:.4f}')
        
        # Publish completion notification (standardized format)
        publish_nlp_completion(message_publisher, doc_id, doc_hash, storage_results, nlp_results)
        
        logger.info(f"Successfully completed NLP processing for document: {doc_id}")
        logger.info(f"Entities found: {len(entities_result)}")
        logger.info(f"Key phrases found: {len(phrases_result)}")
        logger.info(f"Actual cost: ${estimated_cost:.4f}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'NLP processing completed successfully',
                'doc_id': doc_id,
                'results_summary': {
                    'entities_count': len(entities_result),
                    'key_phrases_count': len(phrases_result),
                    'chunks_mapped': len(chunks) if chunks else 0,
                    'processing_time_ms': nlp_results['processing_metadata']['processing_time_ms'],
                    'actual_cost': estimated_cost
                },
                'storage_locations': storage_results,
                'standardized_messaging': True
            })
        }
        
    except Exception as e:
        logger.error(f"NLP processing failed for document {doc_id}: {e}")
        
        # Update status to failed
        if doc_id:
            try:
                db_manager = DatabaseManager()
                update_processing_status(db_manager, doc_id, 'FAILED', str(e))
            except:
                pass  # Don't fail on error tracking failure
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'doc_id': doc_id,
                'standardized_messaging': True
            })
        }

def load_full_text_from_s3(text_location: str) -> str:
    """Load full text from S3 location"""
    
    try:
        s3 = boto3.client('s3')
        
        # Parse S3 location
        if text_location.startswith('s3://'):
            s3_path = text_location[5:]
            bucket, key = s3_path.split('/', 1)
        else:
            raise ValueError(f"Invalid S3 location format: {text_location}")
        
        logger.info(f"Loading full text from s3://{bucket}/{key}")
        
        # Get object from S3
        response = s3.get_object(Bucket=bucket, Key=key)
        text_content = response['Body'].read().decode('utf-8')
        
        logger.info(f"Successfully loaded {len(text_content)} characters")
        return text_content
        
    except Exception as e:
        logger.error(f"Error loading full text from S3: {e}")
        return ""

def load_chunks_from_s3(chunks_location: str) -> List[Dict]:
    """Load chunks from S3 location"""
    
    try:
        s3 = boto3.client('s3')
        
        # Parse S3 location
        if chunks_location.startswith('s3://'):
            s3_path = chunks_location[5:]
            bucket, key_prefix = s3_path.split('/', 1)
        else:
            raise ValueError(f"Invalid S3 location format: {chunks_location}")
        
        # Remove trailing slash
        if key_prefix.endswith('/'):
            key_prefix = key_prefix[:-1]
        
        logger.info(f"Loading chunks from s3://{bucket}/{key_prefix}/")
        
        # List chunk files
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=f"{key_prefix}/",
            Delimiter='/'
        )
        
        chunks = []
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.json') and 'chunk_' in obj['Key']:
                # Load individual chunk
                chunk_response = s3.get_object(Bucket=bucket, Key=obj['Key'])
                chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                chunks.append(chunk_data)
        
        # Sort chunks by index
        chunks.sort(key=lambda x: x.get('chunk_index', 0))
        
        logger.info(f"Successfully loaded {len(chunks)} chunks")
        return chunks
        
    except Exception as e:
        logger.error(f"Error loading chunks from S3: {e}")
        return []

def estimate_processing_cost(text: str, provider: str) -> float:
    """Estimate processing cost based on text length and provider"""
    
    character_count = len(text)
    
    if provider == 'comprehend':
        # Amazon Comprehend pricing: $0.0001 per 100 characters for entities + key phrases
        # So $0.0002 per 100 characters for both
        cost_per_100_chars = 0.0002
        estimated_cost = (character_count / 100.0) * cost_per_100_chars
        return round(estimated_cost, 4)
    
    return 0.0

def update_processing_status(db_manager: DatabaseManager, doc_id: str, status: str, message: str):
    """Update NLP processing status in database"""
    
    try:
        conn = db_manager.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO nlp_processing_status (doc_id, status, message, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    message = EXCLUDED.message,
                    updated_at = EXCLUDED.updated_at
            """, (doc_id, status, message, datetime.utcnow()))
            
            conn.commit()
            logger.info(f"Updated NLP status: {doc_id} -> {status}")
            
    except Exception as e:
        logger.error(f"Error updating processing status: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def publish_nlp_completion(message_publisher: StandardizedMessagePublisher, 
                         doc_id: str, doc_hash: str, storage_results: Dict, nlp_results: Dict):
    """Publish standardized NLP completion message"""
    
    try:
        completion_topic_arn = os.environ.get('NLP_COMPLETION_TOPIC_ARN',
                                            'arn:aws:sns:us-east-1:861276078413:nlp-processing-complete')
        
        # Create standardized completion message
        completion_message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "nlp_complete",
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "data_locations": {
                "nlp_results_location": storage_results.get('base_location', ''),
                "entities_location": storage_results.get('entities_file', ''),
                "key_phrases_location": storage_results.get('key_phrases_file', ''),
                "chunk_mappings_location": storage_results.get('chunk_mappings_file', '')
            },
            "processing_metadata": nlp_results.get('processing_metadata', {}),
            "results_summary": {
                "entities_count": len(nlp_results.get('entities', [])),
                "key_phrases_count": len(nlp_results.get('key_phrases', [])),
                "chunks_mapped": len(nlp_results.get('entities_mapped_to_chunks', [])) > 0
            },
            "integration_flags": {
                "documentid_manager_integration": True,
                "database_tracking_enabled": True,
                "s3_data_lake_storage": True
            }
        }
        
        sns = boto3.client('sns')
        response = sns.publish(
            TopicArn=completion_topic_arn,
            Message=json.dumps(completion_message, default=str),
            Subject=f"NLP processing complete: {doc_id}",
            MessageAttributes={
                'stage': {
                    'DataType': 'String',
                    'StringValue': 'nlp_complete'
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
        
        logger.info(f"Published NLP completion message for {doc_id}: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Failed to publish NLP completion message: {e}")
        # Don't raise - this shouldn't fail the main processing
