import json
import logging
from typing import List, Dict, Tuple, Optional
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

class RelatedDocumentsService:
    """Service for retrieving related Trusted Source Documents using hybrid search"""
    
    def __init__(self, ranking_engine=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.ranking_engine = ranking_engine
        self.logger.info(f"RelatedDocumentsService initialized by ranking engine: {ranking_engine}")
        
        # OpenSearch configuration
        self.opensearch_endpoint = "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
        
        # Initialize OpenSearch client
        self.opensearch_client = self._create_opensearch_client()
        
        # Configuration
        self.MAX_RELATED_DOCS = 5
        self.BM25_TOP_K = 75
        self.VECTOR_TOP_K = 150
        self.RRF_K = 60
        self.MIN_QUERY_LENGTH = 2
        self.logger.info(f"RelatedDocumentsService initialized with MAX_RELATED_DOCS: {self.MAX_RELATED_DOCS}, BM25_TOP_K: {self.BM25_TOP_K}, VECTOR_TOP_K: {self.VECTOR_TOP_K}, RRF_K: {self.RRF_K}, MIN_QUERY_LENGTH: {self.MIN_QUERY_LENGTH}")
        
    def _create_opensearch_client(self):
        """Create OpenSearch client with AWS authentication"""
        try:
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
            
            self.logger.info("Related docs OpenSearch client created successfully")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to create OpenSearch client: {e}")
            return None
        
    def get_related_documents(self, user_query: str, solution_data: dict) -> List[dict]:
        """
        Returns 3-5 related TSDs for a solution in context of user query
        
        Args:
            user_query: Original user search query
            solution_data: Solution object with title, summary, risk_types, countries, solution_types
            
        Returns:
            List of related document objects with relevance scores
        """
        try:
            self.logger.info(f"User query: {user_query}")
            self.logger.info(f"Solution data: {json.dumps(solution_data, indent=2)}")
            self.logger.info(f"Getting related documents for solution: {solution_data.get('document_id', 'unknown')}")
            
            # Validate inputs
            if not user_query or len(user_query.strip()) < self.MIN_QUERY_LENGTH:
                self.logger.info(f"Query too short: '{user_query}'")
                return []
                
            if not self._has_complete_facets(solution_data):
                self.logger.info(f"Solution missing required facets: {solution_data.get('document_id', 'unknown')}")
                return []
            
            # Build queries
            bm25_query = self._build_bm25_query(user_query, solution_data)
            vector_query_text = self._build_vector_query_text(user_query, solution_data)
            
            self.logger.info(f"Executing hybrid search for related docs")
            
            # Execute searches
            bm25_results = self._execute_bm25_search(bm25_query)
            vector_results = self._execute_vector_search(vector_query_text)
            
            self.logger.info(f"BM25 results: {len(bm25_results)}, Vector results: {len(vector_results)}")
            
            # Fuse results using RRF
            fused_results = self._fuse_results(bm25_results, vector_results)
            
            # Convert to response format
            final_results = self._format_results(fused_results[:self.MAX_RELATED_DOCS])
            
            self.logger.info(f"Returning {len(final_results)} related documents")
            return final_results
            
        except Exception as e:
            self.logger.error(f"Related documents retrieval failed: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    def _has_complete_facets(self, solution_data: dict) -> bool:
        """Check if solution has required facets for query construction"""
        required_fields = ['title', 'summary_description', 'risk_types_addressed', 'country_regions_covered', 'solution_types']
        return all(
            solution_data.get(field) and solution_data[field] != [''] 
            for field in required_fields
        )
    
    def _build_bm25_query(self, user_query: str, solution_data: dict) -> str:
        """Construct BM25 query: user_query + solution_summary + facet_context"""
        summary = solution_data.get('summary_description', '')
        risk_types = ', '.join(solution_data.get('risk_types_addressed', []))
        countries = ', '.join(solution_data.get('country_regions_covered', []))
        solution_types = ', '.join(solution_data.get('solution_types', []))
        
        return f"{user_query} Solution summary: {summary} Context: Country: {countries} Risk type: {risk_types} Solution type: {solution_types}"
    
    def _build_vector_query_text(self, user_query: str, solution_data: dict) -> str:
        """Construct vector query text for embedding"""
        summary = solution_data.get('summary_description', '')
        risk_types = ', '.join(solution_data.get('risk_types_addressed', []))
        countries = ', '.join(solution_data.get('country_regions_covered', []))
        solution_types = ', '.join(solution_data.get('solution_types', []))
        
        return f"User query: {user_query}\nSolution summary: {summary}\nContext: Country: {countries}. Risk type: {risk_types}. Solution type: {solution_types}."
    
    def _execute_bm25_search(self, query_text: str) -> List[Tuple[str, int]]:
        """Search documents_keyword index with content_type='trusted_source_document' filter"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": {
                            "multi_match": {
                                "query": query_text,
                                "fields": ["title^3", "content^2", "full_text^1"],
                                "type": "best_fields"
                            }
                        },
                        "filter": {
                            "term": {"content_type": "trusted_source_document"}
                        }
                    }
                },
                "size": self.BM25_TOP_K,
                "_source": ["doc_id"]
            }
            
            response = self.opensearch_client.search(
                index="documents_keyword",
                body=search_body
            )
            
            results = []
            for i, hit in enumerate(response['hits']['hits']):
                doc_id = hit['_source']['doc_id']
                results.append((doc_id, i + 1))  # rank position
                
            return results
            
        except Exception as e:
            self.logger.error(f"BM25 search failed: {e}")
            return []
    
    def _execute_vector_search(self, query_text: str) -> List[Tuple[str, int]]:
        """Search chunks_vector index and aggregate to document level"""
        try:
            # Get query embedding
            query_vector = self._get_query_embedding(query_text)
            if not query_vector:
                return []
            
            search_body = {
                "query": {
                    "bool": {
                        "must": {
                            "knn": {
                                "vector": {
                                    "vector": query_vector,
                                    "k": self.VECTOR_TOP_K
                                }
                            }
                        },
                        "filter": {
                            "term": {"content_type": "trusted_source_document"}
                        }
                    }
                },
                "size": self.VECTOR_TOP_K,
                "_source": ["doc_id"]
            }
            
            response = self.opensearch_client.search(
                index="chunks_vector",
                body=search_body
            )
            
            # Aggregate chunks to documents
            doc_best_rank = {}
            doc_hit_count = {}
            
            for i, hit in enumerate(response['hits']['hits']):
                doc_id = hit['_source']['doc_id']
                rank = i + 1
                
                if doc_id not in doc_best_rank:
                    doc_best_rank[doc_id] = rank
                    doc_hit_count[doc_id] = 1
                else:
                    doc_hit_count[doc_id] += 1
            
            # Sort by best rank, then by hit count
            sorted_docs = sorted(
                doc_best_rank.items(),
                key=lambda x: (x[1], -doc_hit_count[x[0]])
            )
            
            return [(doc_id, rank) for doc_id, rank in sorted_docs]
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    def _get_query_embedding(self, query_text: str) -> Optional[List[float]]:
        """Get embedding for query text using Bedrock Titan"""
        try:
            # Initialize Bedrock client if not exists
            if not hasattr(self, 'bedrock_client'):
                self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            response = self.bedrock_client.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps({"inputText": query_text}),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {e}")
            return None
    
    def _fuse_results(self, bm25_results: List[Tuple[str, int]], 
                     vector_results: List[Tuple[str, int]]) -> List[Tuple[str, float]]:
        """Fuse BM25 and vector results using RRF"""
        if not self.ranking_engine:
            # Simple fallback - just use BM25 results
            return [(doc_id, 1.0 / rank) for doc_id, rank in bm25_results[:self.MAX_RELATED_DOCS]]
        
        # Use existing RRF fusion from ranking engine
        return self.ranking_engine.fuse_rankings(bm25_results, vector_results, k=self.RRF_K)
    
    def _format_results(self, fused_results: List[Tuple[str, float]]) -> List[dict]:
        """Format results for API response"""
        formatted_results = []
        
        self.logger.info(f"Fused results: {json.dumps(fused_results, indent=2)}")
        for doc_id, score in fused_results:
            # Get document metadata from OpenSearch
            doc_data = self._get_document_metadata(doc_id)
            if doc_data:
                self.logger.info(f"Doc data: {json.dumps(doc_data, indent=2)}")
                formatted_results.append({
                    "doc_id": doc_id,
                    "title": doc_data.get('title', 'Unknown Document'),
                    "summary": doc_data.get('summary', ''),
                    "relevance_score": round(score, 3),
                    "source_url": doc_data.get('source_url', ''),
                    "content_type": "trusted_source_document"
                })
        
        self.logger.info(f"Formatted results: {json.dumps(formatted_results, indent=2)}")
        return formatted_results
    
    def _get_document_metadata(self, doc_id: str) -> Optional[dict]:
        """Retrieve document metadata from OpenSearch"""
        try:
            response = self.opensearch_client.search(
                index="documents_keyword",
                body={
                    "query": {"term": {"doc_id": doc_id}},
                    "size": 1,
                    "_source": ["title", "summary", "source_url"]
                }
            )
            
            if response['hits']['hits']:
                return response['hits']['hits'][0]['_source']
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get document metadata for {doc_id}: {e}")
            return None
