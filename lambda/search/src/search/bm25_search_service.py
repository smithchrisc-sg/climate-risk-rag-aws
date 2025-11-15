import logging
import json
from typing import Dict, List, Tuple, Any
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

class BM25SearchService:
    """BM25 keyword search over solution pseudo-documents in OpenSearch"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # OpenSearch configuration
        self.opensearch_endpoint = "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
        self.index_name = "documents_keyword"
        
        # Initialize OpenSearch client
        self.client = self._create_opensearch_client()
        
        # BM25 configuration
        self.max_results = 200
        self.field_boosts = {
            "title": 3.0,
            "content": 2.0, 
            "full_text": 1.0
        }
        
        # Filter mappings (same as solution_searcher)
        self.filter_mappings = {
            'solution_category': {
                'natural-catastrophe': 'Natural Catastrophe',
                'cyber': 'Cyber',
                'health': 'Health',
                'retirement': 'Retirement',
                'mortality': 'Mortality'
            },
            'solution_type': {
                'risk-reduction': 'Risk Reduction',
                'risk-financing': 'Risk Financing',
                'increase-penetration': 'Increase Penetration',
                'raising-awareness': 'Raising Awareness',
                'leveraging-technology': 'Leveraging Technology',
                'regulation': 'Regulation'
            },
            'countries': {
                'thailand': 'Thailand',
                'singapore': 'Singapore',
                'malaysia': 'Malaysia',
                'indonesia': 'Indonesia',
                'philippines': 'Philippines',
                'vietnam': 'Vietnam',
                'myanmar': 'Myanmar',
                'cambodia': 'Cambodia',
                'laos': 'Laos',
                'brunei': 'Brunei'
            }
        }
    
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
            
            self.logger.info("OpenSearch client created successfully")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to create OpenSearch client: {e}")
            return None
    
    def search(self, query: str, filters: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Execute BM25 search and return ranked solution IDs with scores"""
        
        if not self.client:
            self.logger.error("OpenSearch client not available")
            return []
        
        if not query or not query.strip():
            self.logger.warning("Empty query provided to BM25 search")
            return []
        
        try:
            # Build OpenSearch query
            search_query = self._build_search_query(query, filters)
            
            self.logger.info(f"Executing BM25 search for: '{query}'")
            self.logger.debug(f"OpenSearch query: {json.dumps(search_query, indent=2)}")
            
            # Execute search
            response = self.client.search(
                index=self.index_name,
                body=search_query
            )
            
            self.logger.info(f"BM25 raw response: {json.dumps(response, indent=2)}")
            
            # Extract results
            results = self._extract_results(response)
            
            self.logger.info(f"BM25 search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"BM25 search failed: {e}")
            return []
    
    def _build_search_query(self, query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build OpenSearch query with BM25 scoring and filters"""
        
        # Build multi-match query with field boosting
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        f"title^{self.field_boosts['title']}",
                        f"content^{self.field_boosts['content']}",
                        f"full_text^{self.field_boosts['full_text']}"
                    ],
                    "type": "best_fields",
                    "operator": "or"
                }
            }
        ]
        
        # Build filter clauses
        filter_clauses = [
            {"term": {"content_type": "solution"}}  # Only search solutions
        ]
        
        # Add KG filters
        opensearch_filters = self._build_opensearch_filters(filters)
        filter_clauses.extend(opensearch_filters)
        
        # Construct full query
        search_query = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "size": self.max_results,
            "_source": ["doc_id", "title"],  # Only return what we need
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
        
        return search_query
    
    def _build_opensearch_filters(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert KG filters to OpenSearch filter clauses"""
        
        opensearch_filters = []
        
        # Solution category (risk types)
        if 'solution_category' in filters and filters['solution_category']:
            categories = filters['solution_category'] if isinstance(filters['solution_category'], list) else [filters['solution_category']]
            mapped_categories = [self.filter_mappings['solution_category'].get(cat, cat) for cat in categories]
            opensearch_filters.append({
                "terms": {"risk_types": mapped_categories}
            })
        
        # Solution types
        if 'solution_type' in filters and filters['solution_type']:
            types = filters['solution_type'] if isinstance(filters['solution_type'], list) else [filters['solution_type']]
            mapped_types = [self.filter_mappings['solution_type'].get(t, t) for t in types]
            opensearch_filters.append({
                "terms": {"solution_types": mapped_types}
            })
        
        # Countries
        if 'countries' in filters and filters['countries']:
            countries = filters['countries'] if isinstance(filters['countries'], list) else [filters['countries']]
            mapped_countries = [self.filter_mappings['countries'].get(c, c.title()) for c in countries]
            opensearch_filters.append({
                "terms": {"countries": mapped_countries}
            })
        
        # Regions (ASEAN, ASEAN+3) - would need region-to-countries mapping
        if 'region' in filters and filters['region']:
            # For now, skip region filters in BM25 - let Neptune handle them
            self.logger.info(f"Region filter {filters['region']} not implemented in BM25, will be handled by Neptune intersection")
        
        return opensearch_filters
    
    def _extract_results(self, response: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Extract solution IDs and scores from OpenSearch response"""
        
        results = []
        
        if 'hits' not in response or 'hits' not in response['hits']:
            return results
        
        for hit in response['hits']['hits']:
            try:
                solution_id = hit['_source'].get('doc_id')
                score = hit['_score']
                
                if solution_id and score:
                    results.append((solution_id, float(score)))
                    
            except Exception as e:
                self.logger.warning(f"Failed to extract result from hit: {e}")
                continue
        
        return results
    
    def convert_to_ranks(self, scored_results: List[Tuple[str, float]]) -> List[Tuple[str, int]]:
        """Convert BM25 scores to integer ranks for RRF fusion"""
        
        if not scored_results:
            return []
        
        # Results are already sorted by score (desc), so rank is just position + 1
        ranked_results = []
        for rank, (solution_id, score) in enumerate(scored_results, 1):
            ranked_results.append((solution_id, rank))
        
        return ranked_results
    
    def health_check(self) -> bool:
        """Check if OpenSearch is available"""
        
        if not self.client:
            return False
        
        try:
            response = self.client.ping()
            return response
        except Exception as e:
            self.logger.error(f"OpenSearch health check failed: {e}")
            return False
