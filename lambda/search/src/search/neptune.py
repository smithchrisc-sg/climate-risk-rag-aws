import os
import json
import requests
import time
from typing import Dict, Any, List
from botocore.session import Session
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth
import logging
from models.search_models import SearchResult, SearchResponse, ResultType

class NeptuneProcessor:
    """Handles Neptune graph operations via SPARQL over HTTPS"""
    
    def __init__(self):
        self.endpoint = os.environ['NEPTUNE_ENDPOINT']
        self.port = os.environ.get('NEPTUNE_PORT', '8182')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Build SPARQL endpoint URL
        self.sparql_endpoint = f"https://{self.endpoint}:{self.port}/sparql"
        
        # Get AWS credentials
        session = Session()
        self.credentials = session.get_credentials()
        
        self.timeout = 30
        self.max_retries = 3
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.info("NeptuneProcessor initialized")
    
    async def graph_search(self, query: str, filters: Dict[str, Any], 
                          parameters: Dict[str, Any]) -> SearchResponse:
        """Execute graph-based search for concept expansion"""
        
        self.logger.info(f"Executing graph-based search for query: {query}")
        
        try:
            # Extract location entities from query
            locations = self._extract_locations(query)
            self.logger.info(f"Extracted locations: {locations}")
            
            if not locations:
                self.logger.info("No location entities found in query")
                sr = SearchResponse(
                    search_type="graph",
                    total_results=0,
                    results=[],
                    metadata={"message": "No location entities found in query"}
                )
                self.logger.info(f"Search response: {sr}")
                return sr
            
            # Find documents related to these locations via graph
            related_documents = await self._find_location_documents(locations, filters)
            self.logger.info(f"Related documents: {related_documents}")
            return self._format_graph_results(related_documents, locations)
            
        except Exception as e:
            self.logger.error(f"Graph search error: {e}")
            return SearchResponse(
                search_type="graph",
                total_results=0,
                results=[],
                metadata={"error": str(e)}
            )
    
    def _extract_locations(self, query: str) -> List[str]:
        """Extract location names from query text"""
        # Simple extraction - look for known patterns
        locations = []
        
        # Check for "North Macedonia" specifically (from Phase 1)
        if "north macedonia" in query.lower():
            locations.append("North Macedonia")
        
        # Add other location extraction logic as needed
        return locations
    
    async def _find_location_documents(self, locations: List[str], 
                                     filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find documents related to locations via SPARQL"""
        
        if not locations:
            return []
        
        # Build SPARQL query to find documents with location entities
        location_filter = " ".join([f'"{loc}"' for loc in locations])
        
        sparql_query = f"""
        PREFIX kr: <https://solve.global/kr/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?document ?chunk ?location ?confidence
        WHERE {{
            ?chunk kr:hasLocation ?locationEntity .
            ?locationEntity rdfs:label ?location .
            ?chunk kr:belongsToDocument ?document .
            ?chunk kr:hasConfidence ?confidence .
            
            FILTER(CONTAINS(LCASE(?location), LCASE("{locations[0]}")))
        }}
        LIMIT 50
        """
        self.logger.info(f"Executing SPARQL query: {sparql_query}")
        try:
            results = self._execute_sparql_query(sparql_query)
            self.logger.info(f"SPARQL query results: {results}")
            
            # Group by document
            document_scores = {}
            for result in results:
                doc_id = result.get('document', '')
                confidence = float(result.get('confidence', 0.5))
                
                if doc_id not in document_scores:
                    document_scores[doc_id] = {
                        'document_id': doc_id,
                        'max_confidence': confidence,
                        'total_confidence': confidence,
                        'chunk_count': 1,
                        'locations': [result.get('location', '')]
                    }
                else:
                    document_scores[doc_id]['max_confidence'] = max(
                        document_scores[doc_id]['max_confidence'], confidence
                    )
                    document_scores[doc_id]['total_confidence'] += confidence
                    document_scores[doc_id]['chunk_count'] += 1
                    if result.get('location') not in document_scores[doc_id]['locations']:
                        document_scores[doc_id]['locations'].append(result.get('location', ''))
            
            self.logger.info(f"Document scores (as dict): {document_scores}")
            self.logger.info(f"Document scores (as list): {list(document_scores.values())}")
            return list(document_scores.values())
            
        except Exception as e:
            self.logger.error(f"SPARQL query error: {e}")
            return []
    
    def _format_graph_results(self, documents: List[Dict[str, Any]], 
                            locations: List[str]) -> SearchResponse:
        """Format graph search results into SearchResponse"""
        
        results = []
        for doc_data in documents:
            # Calculate graph relevance score
            # Use average confidence weighted by chunk count
            avg_confidence = doc_data['total_confidence'] / doc_data['chunk_count']
            chunk_bonus = min(doc_data['chunk_count'] * 0.1, 0.5)  # Bonus for multiple chunks
            graph_score = avg_confidence + chunk_bonus
            
            result = SearchResult(
                document_id=doc_data['document_id'],
                title="",  # Will be enriched later from PostgreSQL
                score=graph_score,
                content="",  # Graph search doesn't provide content directly
                content_highlights=[],
                title_highlights=[],
                source=ResultType.GRAPH,
                search_type="graph",
                metadata={
                    'graph_confidence': avg_confidence,
                    'chunk_count': doc_data['chunk_count'],
                    'max_confidence': doc_data['max_confidence'],
                    'matched_locations': doc_data['locations'],
                    'query_locations': locations
                }
            )
            results.append(result)
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        self.logger.info(f"Formatted graph results: {results}")

        sr = SearchResponse(
            search_type="graph",
            total_results=len(results),
            results=results,
            metadata={
                'query_locations': locations,
                'sparql_endpoint': self.sparql_endpoint,
                'total_documents_found': len(documents)
            }
        )
        self.logger.info(f"Search response: {sr}")
        return sr
    
    def _execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SPARQL query with AWS SigV4 authentication"""
        
        for attempt in range(self.max_retries):
            try:
                # Prepare request
                headers = {
                    'Content-Type': 'application/sparql-query',
                    'Accept': 'application/sparql-results+json'
                }
                
                # Create AWS request for signing
                request = AWSRequest(
                    method='POST',
                    url=self.sparql_endpoint,
                    data=query,
                    headers=headers
                )
                
                # Sign request
                SigV4Auth(self.credentials, 'neptune-db', self.aws_region).add_auth(request)
                
                # Execute request
                response = requests.post(
                    self.sparql_endpoint,
                    data=query,
                    headers=dict(request.headers),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result_data = response.json()
                    self.logger.info(f"SPARQL query results: {result_data}")
                    return self._parse_sparql_results(result_data)
                else:
                    self.logger.warning(f"SPARQL query failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.logger.warning(f"SPARQL query attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return []
    
    def _parse_sparql_results(self, result_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse SPARQL JSON results into list of dictionaries"""
        
        results = []
        self.logger.info(f"Parsing SPARQL query results: {result_data}")
        bindings = result_data.get('results', {}).get('bindings', [])
        self.logger.info(f"Bindings: {bindings}")
        
        for binding in bindings:
            result = {}
            for var, value_data in binding.items():
                result[var] = value_data.get('value', '')
            results.append(result)
        
        return results

    def _execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SPARQL query using signed HTTPS requests"""
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Executing Neptune SPARQL query (attempt {attempt + 1})")
                
                # Use botocore signing (same as KnowledgeGraphManager)
                request_data = {'query': query}
                aws_request = AWSRequest(
                    method="POST", 
                    url=self.sparql_endpoint, 
                    data=request_data
                )
                SigV4Auth(self.credentials, "neptune-db", self.aws_region).add_auth(aws_request)
                
                response = requests.post(
                    self.sparql_endpoint,
                    headers=dict(aws_request.headers.items()),
                    data=request_data,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                
                results = response.json()
                return self._process_sparql_results(results)
                
            except requests.exceptions.Timeout:
                self.logger.error(f"Neptune SPARQL timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise Exception("Neptune SPARQL query timed out")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Neptune SPARQL request failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Neptune SPARQL query failed: {e}")
                time.sleep(2 ** attempt)
    
    def _process_sparql_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process SPARQL JSON results into list of dictionaries"""
        
        if 'results' not in results or 'bindings' not in results['results']:
            return []
        
        processed = []
        for binding in results['results']['bindings']:
            row = {}
            for var, value in binding.items():
                if 'value' in value:
                    row[var] = value['value']
                else:
                    row[var] = str(value)
            processed.append(row)
        
        return processed
    

