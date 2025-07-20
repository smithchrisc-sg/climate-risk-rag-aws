"""
NLP Worker - Background processor for NLP analysis with S3 data lake storage
Processes full document text and maps results to chunks using offset mapping
"""
import json
import boto3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Import NLP components
from nlp_interface import NLPProcessorFactory
from offset_mapper import OffsetMapper
from s3_data_lake_manager import S3DataLakeManager

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Process NLP analysis for full document with chunk mapping and S3 storage
    
    Event format (from SQS):
    {
        'doc_id': str,
        'chunks_location': dict,
        'full_text_location': dict,
        'nlp_provider': str,
        'processing_type': str
    }
    """
    doc_id = None
    
    try:
        # Parse SQS message
        message = json.loads(event['Records'][0]['body'])
        sns_message = json.loads(message['Message'])
        
        doc_id = sns_message['doc_id']
        chunks_location = sns_message['chunks_location']
        full_text_location = sns_message.get('full_text_location')
        nlp_provider = sns_message.get('nlp_provider', 'comprehend')
        processing_type = sns_message.get('processing_type', 'entity_and_phrases')
        
        logger.info(f"Starting NLP processing for document: {doc_id} using {nlp_provider}")
        
        # Update status to processing (minimal database tracking)
        update_nlp_status_minimal(doc_id, 'PROCESSING', nlp_provider)
        
        # Load full document text and chunks from S3
        full_text = load_full_text_from_s3(full_text_location)
        chunks = load_chunks_from_s3(chunks_location)
        
        if not full_text:
            raise ValueError(f"Could not load full text for document {doc_id}")
        
        if not chunks:
            raise ValueError(f"Could not load chunks for document {doc_id}")
        
        logger.info(f"Loaded {len(full_text)} characters and {len(chunks)} chunks for {doc_id}")
        
        # Get NLP processor based on provider
        nlp_processor = NLPProcessorFactory.create_processor(nlp_provider)
        
        # Process full document text
        start_time = datetime.now()
        nlp_results = nlp_processor.process_document(doc_id, full_text)
        processing_duration = (datetime.now() - start_time).total_seconds()
        
        nlp_results['processing_duration'] = processing_duration
        
        logger.info(f"NLP processing completed in {processing_duration:.2f}s, "
                   f"found {len(nlp_results['entities'])} entities, "
                   f"{len(nlp_results['key_phrases'])} key phrases")
        
        # Map entities and phrases to chunks using offsets
        offset_mapper = OffsetMapper(full_text, chunks)
        mapped_results = offset_mapper.map_to_chunks(nlp_results)
        
        # Log mapping quality
        mapping_report = offset_mapper.get_mapping_quality_report()
        logger.info(f"Offset mapping quality: {mapping_report['mapping_success_rate']:.2%} chunks mapped")
        
        # Store complete results in S3 Data Lake (PRIMARY STORAGE)
        s3_manager = S3DataLakeManager()
        s3_location = s3_manager.store_complete_nlp_results(doc_id, mapped_results)
        
        # Store minimal tracking info in database (NO CONTENT DUPLICATION)
        entities_count = len([m for m in mapped_results['chunk_mappings'] if m['type'] == 'entity'])
        phrases_count = len([m for m in mapped_results['chunk_mappings'] if m['type'] == 'key_phrase'])
        
        store_nlp_status_only(doc_id, {
            'status': 'COMPLETED',
            'entities_count': entities_count,
            'key_phrases_count': phrases_count,
            'processing_cost': mapped_results['processing_cost'],
            's3_results_location': s3_location,  # Reference to data lake
            'processing_duration': processing_duration,
            'nlp_provider': nlp_provider
        })
        
        # Index in OpenSearch for search capabilities (optional)
        try:
            index_nlp_results_in_opensearch(doc_id, mapped_results)
        except Exception as e:
            logger.warning(f"OpenSearch indexing failed for {doc_id}: {str(e)}")
            # Don't fail the entire process for OpenSearch issues
        
        # Publish completion message
        publish_completion_message(doc_id, {
            'status': 'COMPLETED',
            's3_location': s3_location,
            'entities_count': entities_count,
            'key_phrases_count': phrases_count,
            'processing_cost': mapped_results['processing_cost'],
            'processing_duration': processing_duration,
            'provider': nlp_provider
        })
        
        logger.info(f"Successfully completed NLP processing for {doc_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'status': 'completed',
                'entities_count': entities_count,
                'key_phrases_count': phrases_count,
                'processing_cost': mapped_results['processing_cost'],
                'processing_duration': processing_duration,
                's3_location': s3_location
            })
        }
        
    except Exception as e:
        error_msg = f"NLP worker error for {doc_id}: {str(e)}"
        logger.error(error_msg)
        
        # Update status to failed
        if doc_id:
            update_nlp_status_minimal(doc_id, 'FAILED', error_msg=str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'doc_id': doc_id
            })
        }

def load_full_text_from_s3(full_text_location: Dict[str, str]) -> Optional[str]:
    """Load full document text from S3"""
    
    if not full_text_location:
        logger.warning("No full text location provided")
        return None
    
    try:
        s3_client = boto3.client('s3')
        bucket = full_text_location['bucket']
        key = full_text_location['key']
        
        logger.info(f"Loading full text from s3://{bucket}/{key}")
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        full_text = response['Body'].read().decode('utf-8')
        
        logger.info(f"Loaded {len(full_text)} characters from S3")
        return full_text
        
    except Exception as e:
        logger.error(f"Error loading full text from S3: {str(e)}")
        return None

def load_chunks_from_s3(chunks_location: Dict[str, str]) -> List[Dict[str, Any]]:
    """Load document chunks from S3"""
    
    try:
        s3_client = boto3.client('s3')
        bucket = chunks_location['bucket']
        prefix = chunks_location['prefix']
        
        logger.info(f"Loading chunks from s3://{bucket}/{prefix}")
        
        # List chunk files
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            logger.warning(f"No chunk files found at s3://{bucket}/{prefix}")
            return []
        
        chunks = []
        
        # Load each chunk file
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):
                try:
                    chunk_response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    chunks.append(chunk_data)
                except Exception as e:
                    logger.warning(f"Error loading chunk {obj['Key']}: {str(e)}")
                    continue
        
        # Sort chunks by index
        chunks.sort(key=lambda x: x.get('chunk_index', 0))
        
        logger.info(f"Loaded {len(chunks)} chunks from S3")
        return chunks
        
    except Exception as e:
        logger.error(f"Error loading chunks from S3: {str(e)}")
        return []

def update_nlp_status_minimal(doc_id: str, status: str, provider: str = None, error_msg: str = None):
    """Update NLP processing status in database (minimal tracking only)"""
    
    try:
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        try:
            with conn.cursor() as cursor:
                # Create table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS nlp_processing_status (
                        doc_id VARCHAR(255) PRIMARY KEY,
                        status VARCHAR(50) NOT NULL,
                        processing_type VARCHAR(50) DEFAULT 'entity_and_phrases',
                        nlp_provider VARCHAR(50) DEFAULT 'comprehend',
                        entities_count INTEGER,
                        key_phrases_count INTEGER,
                        comprehend_cost_estimate DECIMAL(10,6),
                        comprehend_cost_actual DECIMAL(10,6),
                        s3_results_location VARCHAR(500),
                        opensearch_indexed BOOLEAN DEFAULT FALSE,
                        cache_used BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        error_message TEXT,
                        processing_duration_seconds INTEGER
                    );
                """)
                
                if status == 'PROCESSING':
                    cursor.execute(
                        """INSERT INTO nlp_processing_status (doc_id, status, nlp_provider, created_at) 
                           VALUES (%s, %s, %s, %s) 
                           ON CONFLICT (doc_id) DO UPDATE SET 
                               status = EXCLUDED.status, 
                               nlp_provider = EXCLUDED.nlp_provider,
                               created_at = EXCLUDED.created_at""",
                        (doc_id, status, provider or 'comprehend', datetime.now())
                    )
                elif status == 'FAILED':
                    cursor.execute(
                        """INSERT INTO nlp_processing_status (doc_id, status, error_message) 
                           VALUES (%s, %s, %s) 
                           ON CONFLICT (doc_id) DO UPDATE SET 
                               status = EXCLUDED.status, 
                               error_message = EXCLUDED.error_message""",
                        (doc_id, status, error_msg)
                    )
                
                conn.commit()
                
        finally:
            db_manager.return_connection(conn)
            
    except Exception as e:
        logger.error(f"Error updating NLP status for {doc_id}: {str(e)}")

def store_nlp_status_only(doc_id: str, status_info: Dict[str, Any]):
    """Store only processing status and metadata - NO content duplication"""
    
    try:
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO nlp_processing_status 
                    (doc_id, status, entities_count, key_phrases_count, 
                     comprehend_cost_actual, s3_results_location, 
                     processing_duration_seconds, nlp_provider, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        entities_count = EXCLUDED.entities_count,
                        key_phrases_count = EXCLUDED.key_phrases_count,
                        comprehend_cost_actual = EXCLUDED.comprehend_cost_actual,
                        s3_results_location = EXCLUDED.s3_results_location,
                        processing_duration_seconds = EXCLUDED.processing_duration_seconds,
                        nlp_provider = EXCLUDED.nlp_provider,
                        completed_at = EXCLUDED.completed_at
                """, (
                    doc_id, status_info['status'], status_info['entities_count'],
                    status_info['key_phrases_count'], status_info['processing_cost'],
                    status_info['s3_results_location'], int(status_info['processing_duration']),
                    status_info['nlp_provider'], datetime.now()
                ))
                conn.commit()
                
        finally:
            db_manager.return_connection(conn)
            
    except Exception as e:
        logger.error(f"Error storing NLP status for {doc_id}: {str(e)}")

def index_nlp_results_in_opensearch(doc_id: str, mapped_results: Dict[str, Any]):
    """Index NLP results in OpenSearch for search capabilities"""
    
    # This is optional and can be implemented later
    # For now, just log that it would happen
    logger.info(f"OpenSearch indexing would happen here for {doc_id}")
    pass

def publish_completion_message(doc_id: str, completion_info: Dict[str, Any]):
    """Publish NLP completion message to SNS"""
    
    try:
        sns_client = boto3.client('sns')
        completion_topic_arn = os.environ.get('NLP_COMPLETION_TOPIC_ARN')
        
        if not completion_topic_arn:
            logger.warning("NLP_COMPLETION_TOPIC_ARN not set, skipping completion message")
            return
        
        message = {
            'doc_id': doc_id,
            'stage': 'nlp_processing_complete',
            'status': completion_info['status'],
            's3_location': completion_info['s3_location'],
            'entities_count': completion_info['entities_count'],
            'key_phrases_count': completion_info['key_phrases_count'],
            'processing_cost': completion_info['processing_cost'],
            'processing_duration': completion_info['processing_duration'],
            'provider': completion_info['provider'],
            'timestamp': datetime.now().isoformat()
        }
        
        sns_client.publish(
            TopicArn=completion_topic_arn,
            Message=json.dumps(message),
            Subject=f'NLP processing completed for {doc_id}'
        )
        
        logger.info(f"Published NLP completion message for {doc_id}")
        
    except Exception as e:
        logger.error(f"Error publishing completion message for {doc_id}: {str(e)}")
        # Don't fail the entire process for messaging issues
