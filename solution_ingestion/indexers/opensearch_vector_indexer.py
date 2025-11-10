#!/usr/bin/env python3
"""
OpenSearch Vector Indexer for Solution Ingestion
Handles vector indexing of text chunks with embeddings in OpenSearch.
"""

import logging
import json
from typing import List, Dict, Any
from datetime import datetime

from opensearchpy import OpenSearch, RequestsHttpConnection

logger = logging.getLogger(__name__)

class OpenSearchVectorIndexer:
    """Handles OpenSearch vector indexing operations for chunks."""
    
    def __init__(self, env):
        self.env = env
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenSearch client."""
        try:
            # Extract host from endpoint URL
            endpoint = self.env.opensearch_endpoint
            if endpoint.startswith('https://'):
                host = endpoint[8:]  # Remove https://
            else:
                host = endpoint
            
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(self.env.opensearch_username, self.env.opensearch_password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = self.client.info()
            logger.info(f"Connected to OpenSearch for vector indexing: {info.get('cluster_name')}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch vector client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test OpenSearch connection."""
        try:
            info = self.client.info()
            logger.info(f"OpenSearch vector connection successful: {info.get('version', {}).get('number', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"OpenSearch vector connection failed: {e}")
            return False
    
    def get_index_stats(self) -> dict:
        """Get vector index statistics."""
        try:
            stats = self.client.indices.stats(index='chunks_vector')
            doc_count = stats.get('indices', {}).get('chunks_vector', {}).get('total', {}).get('docs', {}).get('count', 0)
            return {'doc_count': doc_count}
        except Exception as e:
            logger.warning(f"Could not get index stats: {e}")
            return {'doc_count': 0}
    
    def index_chunks(self, enriched_chunks: List[Dict[str, Any]]) -> int:
        """Index chunks with embeddings. Returns number of successfully indexed chunks."""
        logger.info(f"Indexing {len(enriched_chunks)} chunks with vectors in OpenSearch")
        
        indexed_count = 0
        for chunk in enriched_chunks:
            try:
                # Prepare chunk body with vector
                body = self._prepare_chunk_vector_body(chunk)
                
                # Index the chunk
                response = self.client.index(
                    index='chunks_vector',
                    id=chunk.get('chunk_id', f"chunk_{indexed_count}"),
                    body=body
                )
                
                if response.get('result') in ['created', 'updated']:
                    indexed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to index chunk {chunk.get('chunk_id', 'unknown')}: {e}")
        
        logger.info(f"Successfully indexed {indexed_count}/{len(enriched_chunks)} chunks with vectors")
        return indexed_count
    
    def search_similar(self, query_text: str, limit: int = 10) -> List[dict]:
        """Search for similar chunks using vector similarity."""
        try:
            # Generate embedding for query text
            from generators.embeddings_generator import EmbeddingsGenerator
            embeddings_gen = EmbeddingsGenerator()
            query_embeddings = embeddings_gen.titan.create_embeddings_batch([query_text])
            query_vector = query_embeddings[0]
            
            # Vector similarity search using knn with correct field name
            search_body = {
                "query": {
                    "knn": {
                        "vector": {
                            "vector": query_vector,
                            "k": limit
                        }
                    }
                },
                "size": limit,
                "_source": ["text", "content_type", "chunk_id", "doc_id", "chunk_metadata"]
            }
            
            response = self.client.search(
                index='chunks_vector',
                body=search_body
            )
            
            results = []
            for hit in response.get('hits', {}).get('hits', []):
                result = hit.get('_source', {})
                result['score'] = hit.get('_score', 0)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def index_chunks_with_vectors(self, enriched_chunks: List[Dict[str, Any]]):
        """Index chunks with embeddings in chunks_vector index."""
        logger.info(f"Indexing {len(enriched_chunks)} chunks with vectors in OpenSearch")
        
        indexed_count = 0
        for chunk in enriched_chunks:
            try:
                # Prepare chunk body with vector
                chunk_body = self._prepare_chunk_vector_body(chunk)
                
                # Index chunk with vector
                response = self.client.index(
                    index='chunks_vector',
                    id=chunk.get('chunk_id'),
                    body=chunk_body
                )
                
                if response.get('result') in ['created', 'updated']:
                    indexed_count += 1
                else:
                    logger.warning(f"Unexpected response for {chunk.get('chunk_id')}: {response}")
                
            except Exception as e:
                logger.error(f"Failed to index chunk {chunk.get('chunk_id')}: {e}")
                continue
        
        logger.info(f"Successfully indexed {indexed_count}/{len(enriched_chunks)} chunks with vectors")
    
    def _prepare_chunk_vector_body(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare chunk body for vector indexing."""
        
        # Base chunk data
        body = {
            'doc_id': chunk.get('doc_id'),
            'chunk_id': chunk.get('chunk_id'),
            'content_type': 'solution',  # Tag as solution chunk
            'text': chunk.get('text', ''),
            'chunk_index': chunk.get('chunk_index', 0),
            'start_char': chunk.get('start_char', 0),
            'end_char': chunk.get('end_char', 0),
            'word_count': chunk.get('word_count', 0),
            'char_count': chunk.get('char_count', 0),
            'created_at': chunk.get('created_at', datetime.utcnow().isoformat()),
            'processing_metadata': {
                'chunk_method': chunk.get('chunk_method', 'sentence_based'),
                'embedding_model': chunk.get('embedding_model'),
                'embedding_dimension': chunk.get('embedding_dimension')
            }
        }
        
        # Add vector if available
        if 'embedding' in chunk and chunk['embedding']:
            body['vector'] = chunk['embedding']  # Use 'vector' field to match mapping
            logger.debug(f"Added {len(chunk['embedding'])}-dimension vector for chunk {chunk.get('chunk_id')}")
        else:
            logger.warning(f"No embedding found for chunk {chunk.get('chunk_id')}")
        
        return body
    
    def create_vector_index_if_not_exists(self):
        """Create chunks_vector index with proper vector mapping if it doesn't exist."""
        index_name = 'chunks_vector'
        
        try:
            if not self.client.indices.exists(index=index_name):
                # Index mapping with vector field
                mapping = {
                    "mappings": {
                        "properties": {
                            "doc_id": {"type": "keyword"},
                            "chunk_id": {"type": "keyword"},
                            "text": {
                                "type": "text",
                                "analyzer": "standard"
                            },
                            "chunk_index": {"type": "integer"},
                            "start_char": {"type": "integer"},
                            "end_char": {"type": "integer"},
                            "word_count": {"type": "integer"},
                            "char_count": {"type": "integer"},
                            "created_at": {"type": "date"},
                            "text_vector": {
                                "type": "knn_vector",
                                "dimension": 1536,
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimilarity",
                                    "engine": "nmslib"
                                }
                            },
                            "processing_metadata": {
                                "type": "object",
                                "properties": {
                                    "chunk_method": {"type": "keyword"},
                                    "embedding_model": {"type": "keyword"},
                                    "embedding_dimension": {"type": "integer"}
                                }
                            }
                        }
                    },
                    "settings": {
                        "index": {
                            "knn": True,
                            "knn.algo_param.ef_search": 100
                        }
                    }
                }
                
                self.client.indices.create(index=index_name, body=mapping)
                logger.info(f"Created {index_name} index with vector mapping")
            else:
                logger.info(f"{index_name} index already exists")
                
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            raise
