"""
OpenSearch Vector Indexer - Port from POC with AWS OpenSearch Serverless integration
PRESERVED FROM DEPRECATED VERSION - NO FUNCTIONALITY CHANGES
"""
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any

# Conditional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)

class OpenSearchVectorIndexer:
    def __init__(self, opensearch_client, index_name="climate-risk-vector-index"):
        self.client = opensearch_client
        self.index_name = index_name
        
        logger.info(f"Initialized OpenSearch Vector Indexer for index: {self.index_name}")
        
    def create_vector_index_mapping(self, embedding_dimension=1536):
        """Create or update index mapping with vector fields"""
        try:
            # Check if index exists
            if self.client.indices.exists(index=self.index_name):
                logger.info("Vector index {} already exists".format(self.index_name))
                return
            
            # Enhanced mapping with vector fields
            mapping = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        # Core document fields
                        "doc_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "content": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        
                        # Vector field for semantic search
                        "content_vector": {
                            "type": "knn_vector",
                            "dimension": embedding_dimension,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 24
                                }
                            }
                        },
                        
                        # Metadata fields
                        "character_count": {"type": "integer"},
                        "page_numbers": {"type": "integer"},
                        "section_types": {"type": "keyword"},
                        "hierarchy_levels": {"type": "integer"},
                        "table_count": {"type": "integer"},
                        "list_count": {"type": "integer"},
                        "semantic_context": {"type": "text"},
                        "overlap_with_previous": {"type": "boolean"},
                        "overlap_with_next": {"type": "boolean"},
                        
                        # Embedding metadata
                        "embedding_model": {"type": "keyword"},
                        "embedding_dimension": {"type": "integer"},
                        "embedding_created_at": {"type": "date"},
                        
                        # Document metadata
                        "document_metadata": {
                            "type": "object",
                            "properties": {
                                "original_filename": {"type": "keyword"},
                                "file_size": {"type": "long"},
                                "page_count": {"type": "integer"},
                                "processing_started": {"type": "date"}
                            }
                        },
                        
                        # Indexing metadata
                        "indexed_at": {"type": "date"},
                        "last_updated": {"type": "date"}
                    }
                }
            }
            
            # Create index
            response = self.client.indices.create(
                index=self.index_name,
                body=mapping
            )
            
            logger.info(f"Created vector index {self.index_name}: {response}")
            
        except Exception as e:
            logger.error(f"Error creating vector index mapping: {e}")
            raise
    
    def index_document_vectors(self, doc_id: str, embeddings_data: List[Dict[str, Any]]):
        """Index document vectors with metadata"""
        try:
            logger.info(f"Indexing {len(embeddings_data)} vectors for document {doc_id}")
            
            # Ensure index exists
            self.create_vector_index_mapping()
            
            # Prepare bulk indexing data
            bulk_data = []
            indexed_at = datetime.utcnow().isoformat() + 'Z'
            
            for embedding_item in embeddings_data:
                # Index action - Remove explicit _id for OpenSearch Serverless compatibility
                bulk_data.append({
                    "index": {
                        "_index": self.index_name
                    }
                })
                
                # Document data
                doc_data = {
                    # Core fields
                    "doc_id": doc_id,
                    "chunk_id": embedding_item['chunk_id'],
                    "chunk_index": embedding_item['chunk_index'],
                    "content": embedding_item['text'],
                    "content_vector": embedding_item['embedding'],
                    
                    # Chunk metadata
                    "character_count": embedding_item.get('character_count', 0),
                    "page_numbers": embedding_item.get('page_numbers', []),
                    "section_types": embedding_item.get('section_types', []),
                    "hierarchy_levels": embedding_item.get('hierarchy_levels', []),
                    "table_count": embedding_item.get('table_count', 0),
                    "list_count": embedding_item.get('list_count', 0),
                    "semantic_context": embedding_item.get('semantic_context', ''),
                    "overlap_with_previous": embedding_item.get('overlap_with_previous', False),
                    "overlap_with_next": embedding_item.get('overlap_with_next', False),
                    
                    # Embedding metadata
                    "embedding_model": embedding_item.get('embedding_model', 'unknown'),
                    "embedding_dimension": len(embedding_item['embedding']),
                    "embedding_created_at": embedding_item.get('embedding_created_at', indexed_at),
                    
                    # Document metadata
                    "document_metadata": embedding_item.get('document_metadata', {}),
                    
                    # Indexing metadata
                    "indexed_at": indexed_at,
                    "last_updated": indexed_at
                }
                
                bulk_data.append(doc_data)
            
            # Execute bulk indexing - Remove refresh parameter for OpenSearch Serverless
            response = self.client.bulk(
                body=bulk_data
            )
            
            # Check for errors
            if response.get('errors'):
                error_items = [item for item in response['items'] if 'error' in item.get('index', {})]
                logger.error(f"Bulk indexing errors: {error_items}")
                raise Exception(f"Bulk indexing failed with {len(error_items)} errors")
            
            logger.info(f"Successfully indexed {len(embeddings_data)} vectors for document {doc_id}")
            
            return {
                'indexed_count': len(embeddings_data),
                'took': response.get('took', 0),
                'errors': response.get('errors', False)
            }
            
        except Exception as e:
            logger.error(f"Error indexing document vectors: {e}")
            raise
    
    def delete_document_vectors(self, doc_id: str):
        """Delete all vectors for a document"""
        try:
            # Delete by query
            delete_query = {
                "query": {
                    "term": {
                        "doc_id": doc_id
                    }
                }
            }
            
            response = self.client.delete_by_query(
                index=self.index_name,
                body=delete_query,
                refresh=True
            )
            
            deleted_count = response.get('deleted', 0)
            logger.info(f"Deleted {deleted_count} vectors for document {doc_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting document vectors: {e}")
            raise
    
    def search_similar_vectors(self, query_vector: List[float], size: int = 10, 
                             doc_filter: Dict = None) -> List[Dict]:
        """Search for similar vectors"""
        try:
            # Build search query
            search_body = {
                "size": size,
                "query": {
                    "knn": {
                        "content_vector": {
                            "vector": query_vector,
                            "k": size
                        }
                    }
                },
                "_source": {
                    "excludes": ["content_vector"]  # Exclude vector from results
                }
            }
            
            # Add document filter if provided
            if doc_filter:
                search_body["query"] = {
                    "bool": {
                        "must": [
                            search_body["query"],
                            {"term": doc_filter}
                        ]
                    }
                }
            
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            # Extract results
            hits = response.get('hits', {}).get('hits', [])
            results = []
            
            for hit in hits:
                result = {
                    'chunk_id': hit['_id'],
                    'score': hit['_score'],
                    'source': hit['_source']
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar vectors")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar vectors: {e}")
            raise
