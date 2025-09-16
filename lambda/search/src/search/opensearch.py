import os
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection

class OpenSearchProcessor:
    """Handles OpenSearch operations for keyword and vector search"""
    
    def __init__(self):
        self.endpoint = os.environ['OPENSEARCH_ENDPOINT']
        self.username = os.environ.get('OPENSEARCH_USERNAME', 'admin')
        self.password = os.environ.get('OPENSEARCH_PASSWORD')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize OpenSearch client
        self.client = self._initialize_client()
    
    def _initialize_client(self) -> Optional[OpenSearch]:
        """Initialize OpenSearch client with basic authentication"""
        try:
            if not self.endpoint:
                print("OPENSEARCH_ENDPOINT environment variable not set")
                return None
                
            if not self.password:
                print("OPENSEARCH_PASSWORD environment variable not set")
                return None
            
            # Extract host from endpoint URL
            host = self.endpoint.replace('https://', '').replace('http://', '')
            
            # Create OpenSearch client with basic auth (same as keyword-indexer)
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
            
            # Test connection
            info = client.info()
            print(f"Connected to OpenSearch cluster: {info.get('cluster_name', 'unknown')}")
            
            return client
            
        except Exception as e:
            print(f"Failed to initialize OpenSearch client: {str(e)}")
            return None
    
    async def keyword_search(self, query: str, filters: Dict[str, Any], 
                           parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute keyword search"""
        
        if not self.client:
            return []
        
        try:
            # Build search query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"],
                        "type": "best_fields"
                    }
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
                results.append({
                    'document_id': hit['_source'].get('doc_id', hit['_id']),
                    'score': hit['_score'],
                    'source': 'opensearch_keyword',
                    'title': hit['_source'].get('title', ''),
                    'content': hit['_source'].get('content', '')[:500]  # Truncate
                })
            
            return results
            
        except Exception as e:
            print(f"OpenSearch keyword search error: {e}")
            return []
    
    async def vector_search(self, query: str, filters: Dict[str, Any], 
                          parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute vector search (placeholder)"""
        
        # Vector search not implemented yet
        return []
