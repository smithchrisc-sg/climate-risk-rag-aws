import os
import json
import requests
import time
from typing import Dict, Any, List
from botocore.session import Session
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth

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
    
    async def graph_search(self, query: str, filters: Dict[str, Any], 
                          parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute graph-based search for concept expansion"""
        
        try:
            # Extract location entities from query
            locations = self._extract_locations(query)
            
            if not locations:
                return []
            
            # Find documents related to these locations via graph
            related_documents = await self._find_location_documents(locations, filters)
            
            return self._format_graph_results(related_documents, locations)
            
        except Exception as e:
            print(f"Graph search error: {e}")
            return []
    
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
        
        try:
            results = self._execute_sparql_query(sparql_query)
            
            # Group by document
            document_scores = {}
            for result in results:
                doc_id = result.get('document', '')
                confidence = float(result.get('confidence', 0.5))
                
                if doc_id:
                    if doc_id in document_scores:
                        document_scores[doc_id] = max(document_scores[doc_id], confidence)
                    else:
                        document_scores[doc_id] = confidence
            
            # Convert to result format
            documents = []
            for doc_id, score in document_scores.items():
                documents.append({
                    'document_id': doc_id,
                    'score': score,
                    'source': 'neptune_graph'
                })
            
            return documents
            
        except Exception as e:
            print(f"SPARQL query error: {e}")
            return []
    
    def _execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SPARQL query using signed HTTPS requests"""
        
        for attempt in range(self.max_retries):
            try:
                print(f"Executing Neptune SPARQL query (attempt {attempt + 1})")
                
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
                print(f"Neptune SPARQL timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise Exception("Neptune SPARQL query timed out")
                time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                print(f"Neptune SPARQL request failed (attempt {attempt + 1}): {e}")
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
    
    def _format_graph_results(self, documents: List[Dict[str, Any]], 
                            locations: List[str]) -> List[Dict[str, Any]]:
        """Format graph search results"""
        
        for doc in documents:
            doc['matched_concepts'] = locations
            doc['search_method'] = 'graph_location_search'
            doc['result_type'] = 'graph'
        
        return documents
