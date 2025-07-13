"""
Vector Embeddings Worker - Updated for Standardized Messaging
Background processing with pluggable embeddings and standardized message handling
"""
import json
import boto3
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import utilities from lambda layer
from utils.DatabaseManager import DatabaseManager
from utils.DocumentIDManager import DocumentIDManager

# Import local embeddings components
from embeddings_interface import EmbeddingsFactory
from opensearch_vector_indexer import OpenSearchVectorIndexer

# Import standardized messaging components
from standardized_messaging import StandardizedMessageParser, StandardizedMessagePublisher

def lambda_handler(event, context):
    """
    Background vector embeddings processing with standardized messaging:
    1. Parse standardized embeddings_ready message
    2. Load chunks from S3
    3. Generate embeddings (pluggable model)
    4. Index in OpenSearch with metadata
    5. Update database status
    6. Publish standardized completion message
    """
    doc_id = None
    
    try:
        # Parse standardized message - handle both SNS and SQS formats
        parser = StandardizedMessageParser()
        
        record = event['Records'][0]
        
        if 'Sns' in record:
            # SNS format (direct SNS trigger)
            message = parser.parse_sns_record(record)
        elif 'body' in record:
            # SQS format (SNS -> SQS -> Lambda)
            body = json.loads(record['body'])
            if 'Message' in body:
                message = json.loads(body['Message'])
                # Validate standardized format
                if not parser.validate_message_format(message):
                    raise ValueError("Invalid standardized message format")
            else:
                message = body
        else:
            # Direct message format
            message = record
            
        # Validate this is an embeddings_ready message
        if message.get('stage') != 'embeddings_ready':
            raise ValueError(f"Expected embeddings_ready message, got: {message.get('stage')}")
            
        doc_id = message['doc_id']
        doc_hash = message['doc_hash']
        
        # Extract data locations from standardized format
        data_locations = message.get('data_locations', {})
        chunks_location = data_locations.get('chunks_folder_url') or data_locations.get('chunks_location')
        text_location = data_locations.get('text_folder_url') or data_locations.get('text_location')
        
        if not chunks_location:
            raise ValueError("chunks_folder_url or chunks_location not found in message data_locations")
        
        # Extract processing metadata
        processing_metadata = message.get('processing_metadata', {})
        chunks_count = processing_metadata.get('chunks_count', 0)
        cost_threshold = processing_metadata.get('cost_threshold', 0.50)
        
        logger.info(f"Processing vector embeddings for document: {doc_id}")
        logger.info(f"Chunks location: {chunks_location}")
        logger.info(f"Expected chunks count: {chunks_count}")
        
        # Initialize managers
        db_manager = DatabaseManager()
        
        # Update status to processing (using get_connection for raw SQL)
        conn = db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                # Create table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vector_embeddings_status (
                        doc_id VARCHAR(255) PRIMARY KEY,
                        status VARCHAR(50) NOT NULL,
                        embeddings_count INTEGER,
                        titan_cost_estimate DECIMAL(10,6),
                        titan_cost_actual DECIMAL(10,6),
                        opensearch_indexed BOOLEAN DEFAULT FALSE,
                        cache_used BOOLEAN DEFAULT FALSE,
                        model_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        error_message TEXT,
                        processing_duration_seconds INTEGER
                    )
                """)
                
                # Add missing columns to document_processing_status if they don't exist
                cursor.execute("""
                    ALTER TABLE document_processing_status 
                    ADD COLUMN IF NOT EXISTS vector_embeddings_status VARCHAR(50) DEFAULT 'PENDING',
                    ADD COLUMN IF NOT EXISTS vector_embeddings_completed_at TIMESTAMP
                """)
                
                # Insert or update status
                cursor.execute("""
                    INSERT INTO vector_embeddings_status (doc_id, status) 
                    VALUES (%s, %s) 
                    ON CONFLICT (doc_id) DO UPDATE SET status = %s
                """, (doc_id, 'PROCESSING', 'PROCESSING'))
                
                conn.commit()
        finally:
            db_manager.return_connection(conn)
        
        # Load chunks from S3 using standardized location format
        chunks = load_chunks_from_s3_standardized(chunks_location)
        logger.info(f"Loaded {len(chunks)} chunks for processing")
        
        # Determine embeddings model based on environment variable
        model_type = os.environ.get('EMBEDDINGS_MODEL_TYPE', 'titan')
        logger.info(f"Using embeddings model: {model_type}")
        
        # Create embeddings instance
        embeddings_model = EmbeddingsFactory.create_embeddings(model_type)
        
        # Estimate cost before processing
        texts = [chunk['text'] for chunk in chunks]
        estimated_cost = embeddings_model.estimate_cost(texts)
        logger.info(f"Estimated cost: ${estimated_cost:.6f}")
        
        # Check cost threshold
        if estimated_cost > cost_threshold:
            logger.warning(f"Estimated cost ${estimated_cost:.6f} exceeds threshold ${cost_threshold:.2f}")
            # Could implement automatic fallback to cheaper model here
        
        # Generate embeddings
        start_time = datetime.now()
        embeddings = embeddings_model.create_embeddings_batch(texts)
        processing_duration = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Generated {len(embeddings)} embeddings in {processing_duration:.2f} seconds")
        
        # Prepare embeddings data for indexing
        embeddings_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            embeddings_data.append({
                'chunk_id': chunk.get('chunk_id', f"{doc_id}_chunk_{i}"),
                'doc_id': doc_id,
                'text': chunk['text'],
                'embedding': embedding,
                'chunk_index': i,
                'metadata': chunk.get('metadata', {})
            })
        
        # Index in OpenSearch
        opensearch_client = get_opensearch_client()
        vector_indexer = OpenSearchVectorIndexer(opensearch_client)
        
        # Ensure vector index exists with correct mapping
        vector_indexer.create_vector_index_mapping(embeddings_model.get_embedding_dimension())
        
        # Index the embeddings
        vector_indexer.index_document_vectors(doc_id, embeddings_data)
        
        # Update database status
        conn = db_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE vector_embeddings_status 
                    SET status = %s, embeddings_count = %s, titan_cost_actual = %s, 
                        opensearch_indexed = %s, completed_at = %s, processing_duration_seconds = %s,
                        model_type = %s
                    WHERE doc_id = %s
                """, ('COMPLETED', len(embeddings), estimated_cost, True, datetime.now(), 
                     int(processing_duration), model_type, doc_id))
                
                # Update document processing status (with error handling for missing columns)
                try:
                    cursor.execute("""
                        UPDATE document_processing_status 
                        SET vector_embeddings_status = %s, vector_embeddings_completed_at = %s
                        WHERE doc_hash = %s
                    """, ('COMPLETED', datetime.now(), doc_id))
                except Exception as col_error:
                    logger.warning(f"Could not update document_processing_status (columns may not exist): {str(col_error)}")
                
                conn.commit()
        finally:
            db_manager.return_connection(conn)
        
        # Publish standardized completion message
        publish_standardized_completion_message(
            doc_id, doc_hash, len(embeddings), estimated_cost, 
            embeddings_model.get_model_info(), processing_duration,
            message.get('document_metadata', {}), chunks_location
        )
        
        logger.info(f"Successfully completed vector embeddings for {doc_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'embeddings_count': len(embeddings),
                'processing_duration': processing_duration,
                'estimated_cost': estimated_cost,
                'model_info': embeddings_model.get_model_info(),
                'status': 'completed',
                'standardized_messaging': True
            })
        }
        
    except Exception as e:
        error_msg = f"Vector embeddings worker error: {str(e)}"
        logger.error(error_msg)
        
        if doc_id:
            try:
                db_manager = DatabaseManager()
                conn = db_manager.get_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE vector_embeddings_status 
                            SET status = %s, error_message = %s 
                            WHERE doc_id = %s
                        """, ('FAILED', str(e), doc_id))
                        conn.commit()
                finally:
                    db_manager.return_connection(conn)
            except Exception as db_error:
                logger.error(f"Failed to update error status: {str(db_error)}")
        
        raise

def load_chunks_from_s3_standardized(chunks_location: str) -> List[Dict[str, Any]]:
    """Load chunks from S3 using standardized location format (s3://bucket/prefix/)"""
    s3_client = boto3.client('s3')
    
    # Parse S3 location
    if not chunks_location.startswith('s3://'):
        raise ValueError(f"Invalid S3 location format: {chunks_location}")
    
    # Remove s3:// prefix and split bucket/prefix
    s3_path = chunks_location[5:]  # Remove 's3://'
    if '/' not in s3_path:
        raise ValueError(f"Invalid S3 path format: {chunks_location}")
    
    bucket = s3_path.split('/')[0]
    prefix = '/'.join(s3_path.split('/')[1:])
    
    # Remove trailing slash if present
    if prefix.endswith('/'):
        prefix = prefix[:-1]
    
    chunks = []
    
    try:
        # List objects with the prefix
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        if 'Contents' not in response:
            raise ValueError(f"No chunks found at {chunks_location}")
        
        # Load each chunk file
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.json') and 'chunk_' in key:
                chunk_response = s3_client.get_object(Bucket=bucket, Key=key)
                chunk_data = json.loads(chunk_response['Body'].read())
                chunks.append(chunk_data)
        
        # Sort by chunk sequence for consistent processing
        chunks.sort(key=lambda x: x.get('chunk_index', 0))
        
        logger.info(f"Successfully loaded {len(chunks)} chunks from {chunks_location}")
        return chunks
        
    except Exception as e:
        logger.error(f"Error loading chunks from S3: {str(e)}")
        raise

def get_opensearch_client():
    """Get OpenSearch client - reuse existing configuration"""
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from aws_requests_auth.aws_auth import AWSRequestsAuth
    
    host = os.environ.get('OPENSEARCH_ENDPOINT', '').replace('https://', '')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    service = 'aoss'  # OpenSearch Serverless
    
    credentials = boto3.Session().get_credentials()
    awsauth = AWSRequestsAuth(
        aws_access_key=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_token=credentials.token,
        aws_region=region,
        aws_service=service,
        aws_host=host
    )
    
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    
    return client

def publish_standardized_completion_message(doc_id: str, doc_hash: str, embeddings_count: int, 
                                          cost: float, model_info: Dict[str, Any], 
                                          processing_duration: float, document_metadata: Dict,
                                          chunks_location: str):
    """Publish standardized completion message to SNS"""
    try:
        publisher = StandardizedMessagePublisher()
        topic_arn = os.environ.get('VECTOR_COMPLETION_TOPIC_ARN')
        
        if not topic_arn:
            logger.warning("No completion topic ARN configured")
            return
        
        # Publish standardized vector embeddings complete message
        completion_message = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": "embeddings_complete",
            "doc_id": doc_id,
            "doc_hash": doc_hash,
            "document_metadata": document_metadata,
            "data_locations": {
                "chunks_location": chunks_location,
                "embeddings_indexed": True,
                "opensearch_endpoint": os.environ.get('OPENSEARCH_ENDPOINT', '')
            },
            "processing_metadata": {
                "embeddings_count": embeddings_count,
                "processing_duration_seconds": processing_duration,
                "processing_cost": cost,
                "model_info": model_info,
                "opensearch_indexed": True
            },
            "integration_flags": {
                "documentid_manager_integration": True,
                "database_tracking_enabled": True,
                "standardized_messaging_enabled": True
            }
        }
        
        sns_client = boto3.client('sns')
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps(completion_message, default=str),
            Subject=f"Vector embeddings completed for {doc_id}"
        )
        
        logger.info(f"Published standardized completion message for {doc_id}: {response['MessageId']}")
        
    except Exception as e:
        logger.error(f"Error publishing completion message: {str(e)}")
        # Don't raise - completion message is not critical
