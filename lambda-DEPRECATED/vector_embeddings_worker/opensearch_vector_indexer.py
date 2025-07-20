"""
OpenSearch Vector Indexer - Port from POC with AWS OpenSearch Serverless integration
"""
import json
import logging
import time
from datetime import datetime

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
                        
                        # Vector field for similarity search
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
                        
                        # Metadata fields for enhanced search
                        "metadata": {
                            "properties": {
                                "confidence": {"type": "float"},
                                "structural_quality": {"type": "float"},
                                "section_type": {"type": "keyword"},
                                "language": {"type": "keyword"}
                            }
                        },
                        
                        # Processing metadata
                        "processing": {
                            "properties": {
                                "model_type": {"type": "keyword"},
                                "model_info": {"type": "object"},
                                "indexed_at": {"type": "date"},
                                "embedding_cost": {"type": "float"}
                            }
                        }
                    }
                }
            }
            
            # Create the index
            self.client.indices.create(index=self.index_name, body=mapping)
            logger.info("Created vector index {} with dimension {}".format(self.index_name, embedding_dimension))
            
        except Exception as e:
            logger.error("Error creating vector index mapping: {}".format(str(e)))
            raise
    
    def index_document_vectors(self, doc_id, embeddings_data):
        """Index document vectors with batching and proper timeout handling"""
        logger.info("Indexing {} vectors for document {}".format(len(embeddings_data), doc_id))
        
        # Process in smaller batches to avoid timeouts
        batch_size = 5  # Smaller batches for VECTORSEARCH
        total_indexed = 0
        
        for i in range(0, len(embeddings_data), batch_size):
            batch = embeddings_data[i:i + batch_size]
            bulk_data = []
            
            for emb_data in batch:
                # Calculate metadata scores
                metadata_confidence = self._calculate_metadata_confidence(emb_data.get('metadata', {}))
                structural_quality = self._calculate_structural_quality(emb_data.get('metadata', {}))
                section_type = self._detect_section_type(emb_data['text'], emb_data['chunk_index'])
                
                # Prepare document for indexing
                doc = {
                    "doc_id": doc_id,
                    "chunk_id": emb_data['chunk_id'],
                    "chunk_index": emb_data['chunk_index'],
                    "content": emb_data['text'],
                    "content_vector": emb_data['embedding'].tolist() if hasattr(emb_data['embedding'], 'tolist') else emb_data['embedding'],
                    "metadata": {
                        "confidence": metadata_confidence,
                        "structural_quality": structural_quality,
                        "section_type": section_type,
                        "language": "en"
                    },
                    "processing": {
                        "model_type": "vector_embeddings",
                        "indexed_at": datetime.now().isoformat(),
                        "embedding_cost": 0.0
                    }
                }
                
                # Add to bulk data (no _id for VECTORSEARCH collections)
                bulk_data.append({
                    "index": {
                        "_index": self.index_name
                    }
                })
                bulk_data.append(doc)
            
            # Perform bulk indexing with retry logic
            if bulk_data:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = self.client.bulk(body=bulk_data, timeout='60s', request_timeout=60)
                        
                        # Check for errors
                        if response.get('errors'):
                            errors = [item for item in response['items'] if 'error' in item.get('index', {})]
                            if errors:
                                logger.error("Bulk indexing errors in batch {}: {}".format(i//batch_size + 1, errors[:2]))
                                if attempt == max_retries - 1:
                                    raise Exception("Bulk indexing failed with {} errors after {} retries".format(len(errors), max_retries))
                                continue
                        
                        total_indexed += len(batch)
                        logger.info("Successfully indexed batch {} ({} vectors)".format(i//batch_size + 1, len(batch)))
                        break
                        
                    except Exception as e:
                        logger.warning("Batch {} attempt {} failed: {}".format(i//batch_size + 1, attempt + 1, str(e)))
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(2 ** attempt)  # Exponential backoff
        
        logger.info("Successfully indexed {} total vectors for document {}".format(total_indexed, doc_id))
    
    def search_similar_vectors(self, query_vector, limit=10, metadata_filters=None):
        """Search for similar vectors with optional metadata filtering"""
        try:
            # Build query
            query = {
                "size": limit,
                "query": {
                    "knn": {
                        "content_vector": {
                            "vector": query_vector,
                            "k": limit
                        }
                    }
                }
            }
            
            # Add metadata filters if provided
            if metadata_filters:
                filter_conditions = []
                
                for field, value in metadata_filters.items():
                    if field == 'doc_id':
                        filter_conditions.append({"term": {"doc_id": value}})
                    elif field == 'section_type':
                        filter_conditions.append({"term": {"metadata.section_type": value}})
                    elif field == 'min_confidence':
                        filter_conditions.append({"range": {"metadata.confidence": {"gte": value}}})
                
                if filter_conditions:
                    query["query"] = {
                        "bool": {
                            "must": [query["query"]],
                            "filter": filter_conditions
                        }
                    }
            
            # Execute search
            response = self.client.search(index=self.index_name, body=query)
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    "id": hit['_id'],
                    "score": hit['_score'],
                    "doc_id": hit['_source']['doc_id'],
                    "chunk_id": hit['_source']['chunk_id'],
                    "content": hit['_source']['content'],
                    "metadata": hit['_source']['metadata'],
                    "composite_score": self._calculate_composite_score(
                        hit['_score'],
                        hit['_source']['metadata']['confidence'],
                        hit['_source']['metadata']['structural_quality']
                    )
                }
                results.append(result)
            
            # Sort by composite score
            results.sort(key=lambda x: x['composite_score'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error("Error searching similar vectors: {}".format(str(e)))
            raise
    
    def _calculate_metadata_confidence(self, metadata):
        """Calculate metadata confidence score"""
        # Simple confidence calculation - can be enhanced
        base_confidence = 0.5
        
        # Boost confidence based on available metadata
        if metadata.get('title'):
            base_confidence += 0.1
        if metadata.get('author'):
            base_confidence += 0.1
        if metadata.get('date'):
            base_confidence += 0.1
        if metadata.get('source'):
            base_confidence += 0.1
            
        return min(base_confidence, 1.0)
    
    def _calculate_structural_quality(self, metadata):
        """Calculate structural quality score (ported from POC)"""
        score = 0.5  # Base score
        
        # Boost based on structural elements
        if metadata.get('has_toc'):
            score += 0.1
        if metadata.get('has_references'):
            score += 0.1
        if metadata.get('section_count', 0) > 3:
            score += 0.1
        if metadata.get('figure_count', 0) > 0:
            score += 0.1
            
        return min(score, 1.0)
    
    def _detect_section_type(self, text, chunk_index):
        """Detect section type based on content and position (ported from POC)"""
        text_lower = text.lower()
        
        # Position-based detection
        if chunk_index == 0:
            if any(marker in text_lower for marker in ['abstract', 'summary', 'introduction']):
                return 'introduction'
        
        # Content-based detection
        if 'method' in text_lower or 'methodology' in text_lower:
            return 'methodology'
        elif 'result' in text_lower:
            return 'results'
        elif 'conclusion' in text_lower or 'discussion' in text_lower:
            return 'conclusion'
        elif 'reference' in text_lower or 'bibliography' in text_lower:
            return 'references'
            
        return 'body'
    
    def _calculate_composite_score(self, similarity_score, metadata_confidence, structural_quality, weights=None):
        """Calculate composite score combining similarity and metadata quality (ported from POC)"""
        # Default weights
        w = weights or {
            'similarity': 0.7,
            'metadata': 0.2,
            'structural': 0.1
        }
        
        return (
            similarity_score * w['similarity'] +
            metadata_confidence * w['metadata'] +
            structural_quality * w['structural']
        )
