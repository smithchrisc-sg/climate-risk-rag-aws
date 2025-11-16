import logging
import json
from typing import Dict, List, Tuple, Any
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

class VectorSearchService:
    """Vector semantic search over solution chunks in OpenSearch"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # OpenSearch configuration
        self.opensearch_endpoint = "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
        self.index_name = "chunks_vector"
        
        # Initialize OpenSearch client
        self.client = self._create_opensearch_client()
        
        # Vector search configuration
        self.max_results = 200
        self.vector_field = "vector"  # Correct field name from index mapping
        
    def _create_opensearch_client(self):
        """Create OpenSearch client with AWS authentication"""
        try:
            # Use AWS credentials for authentication
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                'us-east-1',
                'es',
                session_token=credentials.token
            )
            
            client = OpenSearch(
                hosts=[{'host': self.opensearch_endpoint.replace('https://', ''), 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
            
            self.logger.info("Vector OpenSearch client created successfully")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to create vector OpenSearch client: {e}")
            return None
    
    def search(self, query: str, filters: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Execute vector search and return ranked solution IDs with scores"""
        
        if not self.client:
            self.logger.error("Vector OpenSearch client not available")
            return []
        
        if not query or not query.strip():
            self.logger.warning("Empty query provided to vector search")
            return []
        
        try:
            # Get query embedding
            query_vector = self._get_query_embedding(query)
            if not query_vector:
                self.logger.error("Failed to get query embedding")
                return []
            
            # Build vector search query
            search_query = self._build_vector_query(query_vector, filters)
            
            self.logger.info(f"Executing vector search for: '{query}'")
            self.logger.debug(f"Vector query: {json.dumps(search_query, indent=2)}")
            
            # Execute search
            response = self.client.search(
                index=self.index_name,
                body=search_query
            )
            
            self.logger.info(f"Vector raw response: {json.dumps(response, indent=2)}")
            
            # Extract results
            results = self._extract_results(response)
            
            self.logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for query text using Bedrock Titan"""
        try:
            # Initialize Bedrock client if not exists
            if not hasattr(self, 'bedrock_client'):
                self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            # Prepare request for Titan
            request_body = {
                "inputText": query[:8000]  # Titan input limit
            }
            
            # Call Titan API
            response = self.bedrock_client.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding')
            
            if embedding is None:
                self.logger.error(f"No embedding returned for query: {query}")
                return None
            
            self.logger.info(f"Generated embedding for query: '{query}' (dimension: {len(embedding)})")
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate query embedding: {e}")
            return None
    
    def _build_vector_query(self, query_vector: List[float], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build OpenSearch vector query with KNN search and filters"""
        
        # Build vector search query
        search_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                self.vector_field: {
                                    "vector": query_vector,
                                    "k": self.max_results
                                }
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"content_type": "solution"}}  # Only search solutions
                    ]
                }
            },
            "size": self.max_results,
            "_source": ["doc_id", "title"],  # Only return what we need
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
        
        return search_query
    
    def _extract_results(self, response: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Extract solution IDs and scores from OpenSearch response"""
        
        results = []
        
        if 'hits' not in response or 'hits' not in response['hits']:
            return results
        
        for hit in response['hits']['hits']:
            try:
                doc_id = hit['_source'].get('doc_id')
                score = hit['_score']
                
                if doc_id and score:
                    results.append((doc_id, float(score)))
                    
            except Exception as e:
                self.logger.warning(f"Failed to extract result from hit: {e}")
                continue
        
        return results
    
    def convert_to_ranks(self, scored_results: List[Tuple[str, float]]) -> List[Tuple[str, int]]:
        """Convert vector scores to integer ranks for RRF fusion"""
        
        if not scored_results:
            return []
        
        # Results are already sorted by score (desc), so rank is just position + 1
        ranked_results = []
        for rank, (doc_id, score) in enumerate(scored_results, 1):
            ranked_results.append((doc_id, rank))
        
        return ranked_results
    
    def health_check(self) -> bool:
        """Check if vector OpenSearch is available"""
        
        if not self.client:
            return False
        
        try:
            response = self.client.ping()
            return response
        except Exception as e:
            self.logger.error(f"Vector OpenSearch health check failed: {e}")
            return False
