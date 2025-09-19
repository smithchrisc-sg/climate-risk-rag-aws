import os
import json
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
import logging
from models.search_models import SearchResult, SearchResponse, ResultType


class OpenSearchProcessor:
    """Handles OpenSearch operations for keyword and vector search"""
    
    def __init__(self):
        self.endpoint = os.environ['OPENSEARCH_ENDPOINT']
        self.username = os.environ.get('OPENSEARCH_USERNAME', 'admin')
        self.password = os.environ.get('OPENSEARCH_PASSWORD')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.info("OpenSearchProcessor initialized")
        # Initialize OpenSearch client
        self.client = self._initialize_client()
    
    def _initialize_client(self) -> Optional[OpenSearch]:
        """Initialize OpenSearch client with basic authentication"""
        try:
            if not self.endpoint or not self.password:
                return None
            
            # Extract host from endpoint URL
            host = self.endpoint.replace('https://', '').replace('http://', '')
            
            # Create OpenSearch client with basic auth
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(self.username, self.password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenSearch client: {str(e)}")
            return None
    
    async def keyword_search(self, query: str, filters: Dict[str, Any], 
                           parameters: Dict[str, Any]) -> SearchResponse:
        """Execute keyword search"""
        self.logger.info(f"Executing keyword search for query: {query}")
        if not self.client:
            return SearchResponse(
                search_type="keyword",
                total_results=0,
                results=[],
                metadata={"error": "OpenSearch client not initialized"}
            )
        
        try:
            # Build search query with highlights
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"],
                        "type": "best_fields"
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {},
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                },
                "size": parameters.get('limit', 20)
            }
            
            # Execute search
            response = self.client.search(
                index="documents_keyword",
                body=search_body
            )
            
            # Format results
            results = []
            for hit in response['hits']['hits']:
                self.logger.info(f"Hit: {hit}")
                # Extract highlights
                highlights = hit.get('highlight', {})
                content_highlights = highlights.get('content', [])
                title_highlights = highlights.get('title', [])
                
                result = SearchResult(
                    document_id=hit['_source'].get('doc_id', hit['_id']),
                    title=hit['_source'].get('title', ''),
                    score=hit['_score'],
                    content=hit['_source'].get('content', '')[:500],
                    content_highlights=content_highlights,
                    title_highlights=title_highlights,
                    source=ResultType.KEYWORD,
                    search_type="keyword",
                    metadata={
                        'opensearch_score': hit['_score'],
                        'index': 'documents_keyword'
                    }
                )
                results.append(result)
            
            return SearchResponse(
                search_type="keyword",
                total_results=response['hits']['total']['value'],
                results=results,
                metadata={
                    'took': response.get('took', 0),
                    'timed_out': response.get('timed_out', False),
                    'max_score': response['hits'].get('max_score', 0)
                }
            )
            
        except Exception as e:
            self.logger.error(f"OpenSearch keyword search error: {e}")
            return SearchResponse(
                search_type="keyword",
                total_results=0,
                results=[],
                metadata={"error": str(e)}
            )
    
    async def vector_search(self, query: str, filters: Dict[str, Any], 
                          parameters: Dict[str, Any]) -> SearchResponse:
        """Execute vector search using Titan embeddings"""

        self.logger.info(f"Executing vector search for query: {query}")

        if not self.client:
            return SearchResponse(
                search_type="vector",
                total_results=0,
                results=[],
                metadata={"error": "OpenSearch client not initialized"}
            )
        
        try:
            # Generate embedding for the query using Titan
            import boto3
            import json
            
            bedrock_client = boto3.client('bedrock-runtime')
            
            # Create embedding for search query
            embedding_request = {
                "inputText": query
            }
            
            response = bedrock_client.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps(embedding_request),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            query_embedding = response_body['embedding']
            
            # Build vector search query
            search_body = {
                "query": {
                    "knn": {
                        "vector": {
                            "vector": query_embedding,
                            "k": parameters.get('limit', 20)
                        }
                    }
                },
                "size": parameters.get('limit', 20)
            }
            
            # Execute search
            search_response = self.client.search(
                index="chunks_vector",
                body=search_body
            )
            
            # Format results
            results = []
            for hit in search_response['hits']['hits']:
                result = SearchResult(
                    document_id=hit['_source'].get('doc_id', hit['_id']),
                    title=hit['_source'].get('title', ''),
                    score=hit['_score'],
                    content=hit['_source'].get('content', '')[:500],
                    content_highlights=[],  # Vector search doesn't provide highlights
                    title_highlights=[],
                    source=ResultType.VECTOR,
                    search_type="vector",
                    metadata={
                        'opensearch_score': hit['_score'],
                        'index': 'chunks_vector',
                        'similarity_score': hit['_score']
                    }
                )
                results.append(result)
            
            return SearchResponse(
                search_type="vector",
                total_results=search_response['hits']['total']['value'],
                results=results,
                metadata={
                    'took': search_response.get('took', 0),
                    'timed_out': search_response.get('timed_out', False),
                    'max_score': search_response['hits'].get('max_score', 0),
                    'embedding_model': 'amazon.titan-embed-text-v1'
                }
            )
            
        except Exception as e:
            self.logger.error(f"OpenSearch vector search error: {e}")
            return SearchResponse(
                search_type="vector",
                total_results=0,
                results=[],
                metadata={"error": str(e)}
            )
