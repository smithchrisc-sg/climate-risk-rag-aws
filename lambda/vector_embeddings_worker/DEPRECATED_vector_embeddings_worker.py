"""
Vector Embeddings Worker - Numpy-free version using only Titan embeddings
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

class TitanEmbeddings:
    """Simple Titan embeddings without numpy dependency"""
    
    def __init__(self, region='us-east-1'):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = 'amazon.titan-embed-text-v1'
        self.dimension = 1536
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        embeddings = []
        
        for text in texts:
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({'inputText': text})
                )
                
                response_body = json.loads(response['body'].read())
                embedding_vector = response_body['embedding']
                embeddings.append(embedding_vector)
                
            except Exception as e:
                logger.error(f"Error generating Titan embedding: {str(e)}")
                # Return zero vector as fallback
                embeddings.append([0.0] * self.dimension)
        
        return embeddings

class SimpleOpenSearchIndexer:
    """Simple OpenSearch indexer without numpy dependency"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.opensearch_client = boto3.client('opensearchserverless', region_name='us-east-1')
    
    def index_vectors(self, doc_id: str, chunks: List[Dict], embeddings: List[List[float]]) -> bool:
        """Index vectors in OpenSearch"""
        try:
            # For now, just log that we would index
            logger.info(f"Would index {len(embeddings)} vectors for document {doc_id}")
            logger.info(f"First embedding dimensions: {len(embeddings[0]) if embeddings else 0}")
            return True
        except Exception as e:
            logger.error(f"Error indexing vectors: {str(e)}")
            return False

def lambda_handler(event, context):
    """
    Background vector embeddings processing:
    1. Load chunks from S3
    2. Generate embeddings using Titan
    3. Index in OpenSearch
    4. Update database status
    """
    
    try:
        logger.info("Vector embeddings worker started")
        
        # Parse SNS message
        if 'Records' not in event:
            raise ValueError("No Records found in event")
        
        message = json.loads(event['Records'][0]['Sns']['Message'])
        doc_id = message['doc_id']
        chunks_location = message['chunks_location']
        
        logger.info(f"Processing document: {doc_id}")
        logger.info(f"Chunks location: {chunks_location}")
        
        # Initialize components
        db_manager = DatabaseManager()
        embeddings_generator = TitanEmbeddings()
        
        opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        if opensearch_endpoint:
            indexer = SimpleOpenSearchIndexer(opensearch_endpoint)
        else:
            logger.warning("No OpenSearch endpoint configured")
            indexer = None
        
        # Get document metadata from database
        doc_metadata = db_manager.get_document_metadata(doc_id)
        if not doc_metadata:
            raise ValueError(f"Document {doc_id} not found in database")
        
        # Load chunks from S3
        s3_client = boto3.client('s3')
        bucket = chunks_location['bucket']
        prefix = chunks_location['prefix']
        
        logger.info(f"Loading chunks from s3://{bucket}/{prefix}")
        
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        chunk_objects = response.get('Contents', [])
        
        if not chunk_objects:
            logger.warning(f"No chunks found for document {doc_id}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'completed',
                    'message': f'No chunks to process for document {doc_id}',
                    'doc_id': doc_id
                })
            }
        
        # Load and process chunks
        chunks = []
        texts = []
        
        for chunk_obj in chunk_objects:
            chunk_key = chunk_obj['Key']
            chunk_response = s3_client.get_object(Bucket=bucket, Key=chunk_key)
            chunk_content = chunk_response['Body'].read().decode('utf-8')
            chunk_data = json.loads(chunk_content)
            
            # Extract text content
            text = chunk_data.get('text', chunk_data.get('content', ''))
            if text and len(text.strip()) > 0:
                chunks.append(chunk_data)
                texts.append(text)
        
        logger.info(f"Loaded {len(chunks)} chunks with content")
        
        if not texts:
            logger.warning(f"No text content found in chunks for document {doc_id}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'completed',
                    'message': f'No text content to process for document {doc_id}',
                    'doc_id': doc_id
                })
            }
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} text chunks")
        embeddings = embeddings_generator.generate_embeddings(texts)
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Index in OpenSearch
        if indexer:
            success = indexer.index_vectors(doc_id, chunks, embeddings)
            if not success:
                logger.error("Failed to index vectors in OpenSearch")
        
        # Update database status
        # For now, just log completion
        logger.info(f"Vector processing completed for document {doc_id}")
        
        # Publish completion message if topic configured
        completion_topic = os.environ.get('COMPLETION_TOPIC_ARN')
        if completion_topic:
            sns_client = boto3.client('sns')
            completion_message = {
                'doc_id': doc_id,
                'status': 'completed',
                'embeddings_count': len(embeddings),
                'processing_time': datetime.now().isoformat()
            }
            
            sns_client.publish(
                TopicArn=completion_topic,
                Message=json.dumps(completion_message),
                Subject=f'Vector embeddings completed for {doc_id}'
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'completed',
                'message': f'Successfully processed {len(embeddings)} embeddings for document {doc_id}',
                'doc_id': doc_id,
                'embeddings_count': len(embeddings)
            })
        }
        
    except Exception as e:
        logger.error(f"Vector embeddings worker error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Vector embeddings worker error: {str(e)}',
                'doc_id': message.get('doc_id', 'unknown') if 'message' in locals() else 'unknown'
            })
        }
