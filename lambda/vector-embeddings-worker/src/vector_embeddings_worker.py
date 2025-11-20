"""
Vector Embeddings Worker Lambda Function
Updated for AWS Managed OpenSearch with basic authentication
Processes vector embedding jobs with Bedrock Titan and OpenSearch integration
Uses audit-first database design with DatabaseManager
"""

import json
import boto3
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import from locked database core layer - DO NOT CHANGE
from utils.DatabaseManager import DatabaseManager

# Import embedding components - PRESERVED FUNCTIONALITY
from embeddings_interface import EmbeddingsFactory
from opensearch_vector_indexer import OpenSearchVectorIndexer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class VectorEmbeddingsWorker:
    """
    Vector embeddings worker for AWS Managed OpenSearch
    Uses basic authentication and chunks_vector index for dual indexing strategy
    """
    
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.sns = boto3.client('sns')
        
        # Environment configuration
        self.chunks_bucket = os.environ.get('CHUNKS_BUCKET', 'solve-global-kr-dl-chunks-861276078413-us-east-1')
        self.embeddings_bucket = os.environ.get('EMBEDDINGS_BUCKET', 'solve-global-kr-dl-embeddings-861276078413-us-east-1')
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.opensearch_username = os.environ.get('OPENSEARCH_USERNAME', 'admin')
        self.opensearch_password = os.environ.get('OPENSEARCH_PASSWORD')
        self.bedrock_region = os.environ.get('BEDROCK_REGION', 'us-east-1')
        self.completion_topic_arn = os.environ.get('COMPLETION_TOPIC_ARN')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Index names for dual indexing strategy
        self.chunks_index = 'chunks_vector'  # For vector search with document linkage
        
        # Initialize DatabaseManager - LOCKED LAYER
        self.db_manager = DatabaseManager()
        
        # Initialize embeddings generator - PRESERVED FUNCTIONALITY
        self.embeddings_generator = EmbeddingsFactory.create_embeddings(
            model_type="titan",
            bedrock_client=boto3.client('bedrock-runtime', region_name=self.bedrock_region)
        )
        
        # Initialize OpenSearch client and indexer
        self.opensearch_client = self._initialize_opensearch_client()
        self.vector_indexer = None
        if self.opensearch_client:
            # Create chunks index for vector search
            self._create_chunks_index_mapping()
            self.vector_indexer = OpenSearchVectorIndexer(
                opensearch_client=self.opensearch_client,
                index_name=self.chunks_index
            )
        
        logger.info("✅ Managed OpenSearch Vector Embeddings Worker initialized")
        logger.info(f"Chunks bucket: {self.chunks_bucket}")
        logger.info(f"Embeddings bucket: {self.embeddings_bucket}")
        logger.info(f"OpenSearch endpoint: {self.opensearch_endpoint}")
        logger.info(f"Chunks index: {self.chunks_index}")
        logger.info(f"Bedrock region: {self.bedrock_region}")
        logger.info(f"Embedding model: {self.embeddings_generator.model_id}")
        logger.info(f"Embedding dimension: {self.embeddings_generator.dimension}")
    
    def _initialize_opensearch_client(self) -> Optional[OpenSearch]:
        """Initialize OpenSearch client with basic authentication for managed domain"""
        try:
            if not self.opensearch_endpoint:
                logger.error("OPENSEARCH_ENDPOINT environment variable not set")
                return None
                
            if not self.opensearch_password:
                logger.error("OPENSEARCH_PASSWORD environment variable not set")
                return None
            
            # Extract host from endpoint URL
            host = self.opensearch_endpoint.replace('https://', '').replace('http://', '')
            
            # Create OpenSearch client with basic auth for managed domain
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(self.opensearch_username, self.opensearch_password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = client.info()
            logger.info(f"Connected to OpenSearch cluster: {info.get('cluster_name', 'unknown')}")
            logger.info(f"OpenSearch version: {info.get('version', {}).get('number', 'unknown')}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            return None
    
    def _create_chunks_index_mapping(self):
        """Create the chunks index with proper mapping for vector search"""
        try:
            # Check if index exists
            if self.opensearch_client.indices.exists(index=self.chunks_index):
                logger.info(f"Index {self.chunks_index} already exists")
                return
            
            # Create index mapping optimized for chunk-level vector search
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {
                            "type": "keyword"
                        },
                        "doc_id": {
                            "type": "keyword"
                        },
                        "chunk_index": {
                            "type": "integer"
                        },
                        "text": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "vector": {
                            "type": "knn_vector",
                            "dimension": 1536,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2"
                            }
                        },
                        "chunk_metadata": {
                            "properties": {
                                "character_count": {"type": "integer"},
                                "page_numbers": {"type": "integer"},
                                "section_type": {"type": "keyword"},
                                "hierarchy_level": {"type": "integer"},
                                "parent_chunk_id": {"type": "keyword"},
                                "child_chunk_ids": {"type": "keyword"},
                                "sibling_chunk_ids": {"type": "keyword"},
                                "table_count": {"type": "integer"},
                                "list_count": {"type": "integer"},
                                "figure_count": {"type": "integer"},
                                "is_split_paragraph": {"type": "boolean"},
                                "split_part": {"type": "integer"},
                                "total_splits": {"type": "integer"},
                                "semantic_context": {"type": "text"}
                            }
                        },
                        "embedding_metadata": {
                            "properties": {
                                "model": {"type": "keyword"},
                                "dimension": {"type": "integer"},
                                "created_at": {"type": "date"}
                            }
                        },
                        "timestamp": {
                            "type": "date"
                        }
                    }
                }
            }
            
            # Create the index
            response = self.opensearch_client.indices.create(
                index=self.chunks_index,
                body=mapping
            )
            
            logger.info(f"Created chunks index {self.chunks_index}: {response}")
            
        except Exception as e:
            logger.error(f"Failed to create chunks index mapping: {str(e)}")
            raise
    
    def load_chunks_from_s3(self, chunks_location: str) -> List[Dict[str, Any]]:
        """Load all chunks for a document from S3"""
        try:
            # Parse S3 location
            if not chunks_location.startswith('s3://'):
                raise ValueError(f"Invalid S3 URL format: {chunks_location}")
            
            # Extract bucket and prefix
            s3_parts = chunks_location[5:].split('/', 1)
            bucket = s3_parts[0]
            prefix = s3_parts[1] if len(s3_parts) > 1 else ""
            
            # Ensure prefix ends with /
            if prefix and not prefix.endswith('/'):
                prefix += '/'
            
            logger.info(f"Loading chunks from s3://{bucket}/{prefix}")
            
            # List all chunk files
            response = self.s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=1000
            )
            
            if 'Contents' not in response:
                raise ValueError(f"No chunks found at {chunks_location}")
            
            # Filter chunk files (exclude metadata.json)
            chunk_files = [
                obj for obj in response['Contents'] 
                if obj['Key'].endswith('.json') and not obj['Key'].endswith('metadata.json')
            ]
            
            if not chunk_files:
                raise ValueError(f"No chunk files found at {chunks_location}")
            
            # Load all chunks
            chunks = []
            for chunk_file in chunk_files:
                try:
                    # Download chunk file
                    chunk_response = self.s3.get_object(Bucket=bucket, Key=chunk_file['Key'])
                    chunk_data = json.loads(chunk_response['Body'].read().decode('utf-8'))
                    chunks.append(chunk_data)
                    
                except Exception as e:
                    logger.error(f"Failed to load chunk {chunk_file['Key']}: {e}")
                    continue
            
            # Sort chunks by chunk_index
            chunks.sort(key=lambda x: x.get('chunk_index', 0))
            
            logger.info(f"Loaded {len(chunks)} chunks from S3")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to load chunks from S3: {e}")
            raise
    
    def determine_document_type(self, doc_id: str) -> str:
        """Determine document type based on doc_id prefix"""
        return 'solution' if doc_id.startswith('sol_') else 'trusted_source_document'
    
    def generate_embeddings_for_chunks(self, chunks: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
        """Generate embeddings for all chunks using Titan"""
        try:
            logger.info(f"Generating embeddings for {len(chunks)} chunks using {self.embeddings_generator.model_id}")
            
            # Extract texts from chunks
            texts = [chunk['text'] for chunk in chunks]
            
            # Generate embeddings in batch
            embeddings = self.embeddings_generator.create_embeddings_batch(texts)
            
            if len(embeddings) != len(chunks):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")
            
            # Combine chunks with embeddings for vector index
            embeddings_data = []
            embedding_created_at = datetime.utcnow().isoformat() + 'Z'
            content_type = self.determine_document_type(doc_id)
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                embedding_item = {
                    # Core identifiers for linking to documents
                    'chunk_id': chunk['chunk_id'],
                    'doc_id': doc_id,  # Key for linking to document index
                    'content_type': content_type,
                    'chunk_index': chunk['chunk_index'],
                    'text': chunk['text'],
                    'vector': embedding,  # Vector for k-NN search
                    
                    # Chunk metadata for filtering/boosting
                    'chunk_metadata': {
                        'character_count': chunk.get('character_count', 0),
                        'page_numbers': chunk.get('page_numbers', []),
                        'section_type': chunk.get('section_type', 'unknown'),
                        'hierarchy_level': chunk.get('hierarchy_level', 0),
                        'parent_chunk_id': chunk.get('parent_chunk_id', None),
                        'child_chunk_ids': chunk.get('child_chunk_ids', []),
                        'sibling_chunk_ids': chunk.get('sibling_chunk_ids', []),
                        'table_count': chunk.get('table_count', 0),
                        'list_count': chunk.get('list_count', 0),
                        'figure_count': chunk.get('figure_count', 0),
                        'is_split_paragraph': chunk.get('is_split_paragraph', False),
                        'split_part': chunk.get('split_part', 0),
                        'total_splits': chunk.get('total_splits', 1),
                        'semantic_context': chunk.get('semantic_context', ''),
                        'overlap_with_previous': chunk.get('overlap_with_previous', False),
                        'overlap_with_next': chunk.get('overlap_with_next', False)
                    },
                    
                    # Embedding metadata
                    'embedding_metadata': {
                        'model': self.embeddings_generator.model_id,
                        'dimension': self.embeddings_generator.dimension,
                        'created_at': embedding_created_at
                    },
                    
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                embeddings_data.append(embedding_item)
            
            logger.info(f"Generated {len(embeddings_data)} embeddings successfully")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    def save_embeddings_to_s3(self, doc_id: str, embeddings_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Save embeddings to S3 for backup/reprocessing"""
        try:
            # Create S3 paths
            embeddings_prefix = f"data-lake/{doc_id}/"
            
            # Save individual embeddings
            embedding_locations = []
            for embedding_item in embeddings_data:
                embedding_key = f"{embeddings_prefix}{embedding_item['chunk_id']}_embedding.json"
                
                # Upload embedding
                self.s3.put_object(
                    Bucket=self.embeddings_bucket,
                    Key=embedding_key,
                    Body=json.dumps(embedding_item, indent=2),
                    ContentType='application/json'
                )
                
                embedding_locations.append(f"s3://{self.embeddings_bucket}/{embedding_key}")
            
            # Create and upload metadata
            metadata = {
                'doc_id': doc_id,
                'total_embeddings': len(embeddings_data),
                'embedding_model': self.embeddings_generator.model_id,
                'embedding_dimension': self.embeddings_generator.dimension,
                'embedding_locations': embedding_locations,
                'created_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            metadata_key = f"{embeddings_prefix}metadata.json"
            self.s3.put_object(
                Bucket=self.embeddings_bucket,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            
            logger.info(f"Saved {len(embeddings_data)} embeddings to S3")
            
            return {
                'embeddings_location': f"s3://{self.embeddings_bucket}/{embeddings_prefix}",
                'embeddings_metadata_location': f"s3://{self.embeddings_bucket}/{metadata_key}"
            }
            
        except Exception as e:
            logger.error(f"Failed to save embeddings to S3: {e}")
            raise
    
    def index_vectors_in_opensearch(self, doc_id: str, embeddings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Index vectors in OpenSearch chunks index"""
        try:
            logger.info(f"Indexing {len(embeddings_data)} vectors in OpenSearch chunks index")
            
            # Index each chunk with its vector
            indexed_count = 0
            failed_count = 0
            
            for embedding_item in embeddings_data:
                try:
                    # Index chunk with vector in chunks_vector index
                    result = self.opensearch_client.index(
                        index=self.chunks_index,
                        id=embedding_item['chunk_id'],
                        body=embedding_item
                    )
                    
                    if result.get('result') in ['created', 'updated']:
                        indexed_count += 1
                    else:
                        logger.warning(f"Unexpected result for chunk {embedding_item['chunk_id']}: {result}")
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to index chunk {embedding_item['chunk_id']}: {e}")
                    failed_count += 1
                    continue
            
            # Refresh index to make documents searchable
            self.opensearch_client.indices.refresh(index=self.chunks_index)
            
            indexing_result = {
                'total_chunks': len(embeddings_data),
                'indexed_successfully': indexed_count,
                'failed': failed_count,
                'index_name': self.chunks_index
            }
            
            logger.info(f"Vector indexing complete: {indexing_result}")
            return indexing_result
            
        except Exception as e:
            logger.error(f"Failed to index vectors in OpenSearch: {e}")
            raise
    
    def publish_completion_message(self, doc_id: str, s3_locations: Dict[str, str], 
                                 embeddings_count: int, processing_metadata: Dict) -> None:
        """Publish vector_embeddings_ready completion message"""
        try:
            # Create standardized completion message
            message = {
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "source": "climate-risk-rag-system",
                "stage": "vector_embeddings_ready",
                "doc_id": doc_id,
                "data_locations": {
                    "embeddings_location": s3_locations['embeddings_location'],
                    "embeddings_metadata_location": s3_locations['embeddings_metadata_location'],
                    "vector_index_name": self.chunks_index
                },
                "processing_metadata": {
                    "vectors_created": embeddings_count,
                    "embedding_model": self.embeddings_generator.model_id,
                    "vector_dimension": self.embeddings_generator.dimension,
                    "chunks_processed": processing_metadata.get('chunks_processed', 0),
                    "processing_completed": datetime.utcnow().isoformat() + "Z"
                },
                "integration_flags": {
                    "database_tracking_enabled": True,
                    "audit_first_design": True,
                    "bedrock_titan_embeddings": True,
                    "managed_opensearch_vector_indexing": True
                }
            }
            
            # Publish to SNS (if topic configured)
            if self.completion_topic_arn:
                response = self.sns.publish(
                    TopicArn=self.completion_topic_arn,
                    Message=json.dumps(message, default=str),
                    Subject=f"Vector embeddings complete: {doc_id}",
                    MessageAttributes={
                        'stage': {
                            'DataType': 'String',
                            'StringValue': 'vector_embeddings_ready'
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
                
                logger.info(f"Published vector_embeddings_ready message for {doc_id}: {response['MessageId']}")
            else:
                logger.info(f"No completion topic configured, skipping message publication for {doc_id}")
                
        except Exception as e:
            logger.error(f"Failed to publish completion message for {doc_id}: {e}")
            # Don't raise - this is not critical for the embedding process
    
    def process_vector_embedding_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a vector embedding job"""
        try:
            doc_id = job_data['doc_id']
            
            logger.info(f"Processing vector embeddings for doc_id: {doc_id}")
            
            # Update status to in_progress
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='vector_indexing',
                status='in_progress'
            )
            
            # Load chunks from S3
            chunks = self.load_chunks_from_s3(job_data['chunks_location'])
            
            # Generate embeddings using Bedrock Titan
            embeddings_data = self.generate_embeddings_for_chunks(chunks, doc_id)
            
            # Save embeddings to S3
            s3_locations = self.save_embeddings_to_s3(doc_id, embeddings_data)
            
            # Index vectors in OpenSearch chunks index
            indexing_result = self.index_vectors_in_opensearch(doc_id, embeddings_data)
            
            # Publish completion message
            processing_metadata = {
                'chunks_processed': len(chunks),
                'validation_data': job_data.get('validation_data', {})
            }
            
            self.publish_completion_message(
                doc_id=doc_id,
                s3_locations=s3_locations,
                embeddings_count=len(embeddings_data),
                processing_metadata=processing_metadata
            )
            
            # Update status to completed
            self.db_manager.set_processing_status(
                doc_id=doc_id,
                stage='vector_indexing',
                status='completed'
            )
            
            return {
                'status': 'success',
                'doc_id': doc_id,
                'vectors_created': len(embeddings_data),
                'embeddings_location': s3_locations['embeddings_location'],
                'vector_index_name': self.chunks_index,
                'indexing_result': indexing_result
            }
            
        except Exception as e:
            doc_id = job_data.get('doc_id', 'unknown')
            
            logger.error(f"Error processing vector embedding job for {doc_id}: {str(e)}")
            
            # Update status to failed if we have a doc_id
            if doc_id != 'unknown':
                self.db_manager.set_processing_status(
                    doc_id=doc_id,
                    stage='vector_indexing',
                    status='failed',
                    error_message=str(e)
                )
            
            return {
                'status': 'error',
                'doc_id': doc_id,
                'error': str(e)
            }

def lambda_handler(event, context):
    """Lambda handler for Vector Embeddings Worker"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        worker = VectorEmbeddingsWorker()
        
        # Process the job data directly (invoked by initiator)
        result = worker.process_vector_embedding_job(event)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Vector embedding job processed',
                'result': result
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
