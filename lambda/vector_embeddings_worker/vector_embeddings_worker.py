"""
Vector Embeddings Worker - Background processing with pluggable embeddings
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

def lambda_handler(event, context):
    """
    Background vector embeddings processing:
    1. Load chunks from S3
    2. Generate embeddings (pluggable model)
    3. Index in OpenSearch with metadata
    4. Update database status
    5. Publish completion message
    """
    doc_id = None
    
    try:
        # Parse worker message - handle both SNS and SQS formats
        record = event['Records'][0]
        
        if 'Sns' in record:
            # SNS format (direct SNS trigger)
            message = json.loads(record['Sns']['Message'])
        elif 'body' in record:
            # SQS format (SNS -> SQS -> Lambda)
            body = json.loads(record['body'])
            if 'Message' in body:
                message = json.loads(body['Message'])
            else:
                message = body
        else:
            # Direct message format
            message = record
            
        doc_id = message['doc_id']
        chunks_location = message['chunks_location']
        
        logger.info("Processing vector embeddings for document: {}".format(doc_id))
        
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
        
        # Load chunks from S3
        chunks = load_chunks_from_s3(chunks_location)
        logger.info("Loaded {} chunks for processing".format(len(chunks)))
        
        # Determine embeddings model based on environment variable
        model_type = os.environ.get('EMBEDDINGS_MODEL_TYPE', 'sentence_transformers')
        logger.info("Using embeddings model: {}".format(model_type))
        
        # Create embeddings instance
        embeddings_model = EmbeddingsFactory.create_embeddings(model_type)
        
        # Estimate cost before processing
        texts = [chunk['text'] for chunk in chunks]
        estimated_cost = embeddings_model.estimate_cost(texts)
        logger.info("Estimated cost: ${:.6f}".format(estimated_cost))
        
        # Check cost threshold
        cost_threshold = float(os.environ.get('COST_THRESHOLD_PER_DOC', '0.50'))
        if estimated_cost > cost_threshold:
            logger.warning("Estimated cost ${:.6f} exceeds threshold ${:.2f}".format(estimated_cost, cost_threshold))
            # Could implement automatic fallback to cheaper model here
        
        # Generate embeddings
        start_time = datetime.now()
        embeddings = embeddings_model.create_embeddings_batch(texts)
        processing_duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("Generated {} embeddings in {:.2f} seconds".format(len(embeddings), processing_duration))
        
        # Prepare embeddings data for indexing
        embeddings_data = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            embeddings_data.append({
                'chunk_id': chunk['chunk_id'],
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
                        opensearch_indexed = %s, completed_at = %s, processing_duration_seconds = %s
                    WHERE doc_id = %s
                """, ('COMPLETED', len(embeddings), estimated_cost, True, datetime.now(), 
                     int(processing_duration), doc_id))
                
                # Update document processing status (with error handling for missing columns)
                try:
                    cursor.execute("""
                        UPDATE document_processing_status 
                        SET vector_embeddings_status = %s, vector_embeddings_completed_at = %s
                        WHERE doc_hash = %s
                    """, ('COMPLETED', datetime.now(), doc_id))
                except Exception as col_error:
                    logger.warning("Could not update document_processing_status (columns may not exist): {}".format(str(col_error)))
                
                conn.commit()
        finally:
            db_manager.return_connection(conn)
        
        # Publish completion message
        publish_completion_message(doc_id, len(embeddings), estimated_cost, embeddings_model.get_model_info())
        
        logger.info("Successfully completed vector embeddings for {}".format(doc_id))
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'doc_id': doc_id,
                'embeddings_count': len(embeddings),
                'processing_duration': processing_duration,
                'estimated_cost': estimated_cost,
                'model_info': embeddings_model.get_model_info(),
                'status': 'completed'
            })
        }
        
    except Exception as e:
        error_msg = "Vector embeddings worker error: {}".format(str(e))
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
                logger.error("Failed to update error status: {}".format(str(db_error)))
        
        raise

def load_chunks_from_s3(chunks_location: Dict[str, str]) -> List[Dict[str, Any]]:
    """Load chunks from S3 based on location information"""
    s3_client = boto3.client('s3')
    bucket = chunks_location['bucket']
    prefix = chunks_location['prefix']
    
    chunks = []
    
    try:
        # List objects with the prefix
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        if 'Contents' not in response:
            raise ValueError("No chunks found at s3://{}/{}".format(bucket, prefix))
        
        # Load each chunk file
        for obj in response['Contents']:
            key = obj['Key']
            if key.endswith('.json') and 'chunk_' in key:
                chunk_response = s3_client.get_object(Bucket=bucket, Key=key)
                chunk_data = json.loads(chunk_response['Body'].read())
                chunks.append(chunk_data)
        
        # Sort by chunk sequence for consistent processing
        chunks.sort(key=lambda x: x.get('chunk_index', 0))
        
        return chunks
        
    except Exception as e:
        logger.error("Error loading chunks from S3: {}".format(str(e)))
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

def publish_completion_message(doc_id: str, embeddings_count: int, cost: float, model_info: Dict[str, Any]):
    """Publish completion message to SNS"""
    try:
        sns_client = boto3.client('sns')
        topic_arn = os.environ.get('VECTOR_COMPLETION_TOPIC_ARN')
        
        if not topic_arn:
            logger.warning("No completion topic ARN configured")
            return
        
        message = {
            'doc_id': doc_id,
            'stage': 'embeddings_ready',
            'embeddings_count': embeddings_count,
            'opensearch_indexed': True,
            'processing_cost': cost,
            'model_info': model_info,
            'timestamp': datetime.now().isoformat()
        }
        
        sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps(message),
            Subject='Vector embeddings completed for {doc_id}'
        )
        
        logger.info("Published completion message for {}".format(doc_id))
        
    except Exception as e:
        logger.error("Error publishing completion message: {}".format(str(e)))
        # Don't raise - completion message is not critical
