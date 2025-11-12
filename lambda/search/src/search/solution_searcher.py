import boto3
import json
import logging
from typing import Dict, List, Any
import sys
import os

# Import from knowledge graph layer - use utils path like working Lambda functions
from utils.KnowledgeGraphManager import KnowledgeGraphManager


class SolutionSearcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.kg_manager = KnowledgeGraphManager()
        self.s3_client = boto3.client('s3')
        self.chunks_bucket = 'solve-global-kr-dl-chunks-861276078413-us-east-1'
        
        # Filter mappings from UI values to KG URIs
        self.filter_mappings = {
            'solution_category': {
                'natural-catastrophe': 'sg:RiskType_natural_catastrophe',
                'cyber': 'sg:RiskType_cyber',
                'health': 'sg:RiskType_health',
                'retirement': 'sg:RiskType_retirement',
                'mortality': 'sg:RiskType_mortality'
            },
            'risk_type': {
                'pandemic': 'sg:RiskType_pandemic',
                'cyber-attack': 'sg:RiskType_cyber_attack',
                'natural-disaster': 'sg:RiskType_natural_disaster',
                'climate-change': 'sg:RiskType_climate_change',
                'economic-crisis': 'sg:RiskType_economic_crisis'
            },
            'solution_type': {
                'prevention': 'sg:SolutionType_prevention',
                'mitigation': 'sg:SolutionType_mitigation',
                'response': 'sg:SolutionType_response',
                'recovery': 'sg:SolutionType_recovery',
                'risk-financing': 'sg:SolutionType_risk_financing',
                'preparedness': 'sg:SolutionType_preparedness'
            }
        }
        self.logger.info(f"SolutionSearcher initialized with filter mappings: {self.filter_mappings}")
        self.logger.info(f"Knowledge Graph Manager initialized: {self.kg_manager}")
        self.logger.info(f"S3 client initialized: {self.s3_client}")
        self.logger.info(f"Chunks bucket: {self.chunks_bucket}")
        
    def search_solutions(self, filters: Dict[str, Any], query: str) -> List[Dict]:
        """Search solutions using KG filters + S3 content"""
        
        print("=== SOLUTION_SEARCHER: METHOD CALLED ===")
        self.logger.info("=== SOLUTION_SEARCHER: METHOD CALLED ===")
        
        try:
            self.logger.info(f"Searching solutions with filters: {filters}, query: {query}")
            
            # 1. Build and execute SPARQL query
            sparql_query = self._build_solution_sparql(filters)
            self.logger.info(f"Executing SPARQL query: {sparql_query}")
            
            kg_results = self.kg_manager.execute_sparql_query(sparql_query)
            self.logger.info(f"KG returned {len(kg_results)} results")
            if kg_results:
                self.logger.info(f"Sample KG result: {kg_results[0] if kg_results else 'None'}")
            
            # 2. Process KG results and retrieve S3 content
            # Group results by doc_id to handle multiple chunks per solution
            solutions_by_doc_id = {}
            for result in kg_results:
                doc_id = result.get('doc_id')
                if not doc_id:
                    continue
                    
                if doc_id not in solutions_by_doc_id:
                    solutions_by_doc_id[doc_id] = {
                        'doc_id': doc_id,
                        'title': result.get('title', ''),
                        'riskType': result.get('riskType', ''),
                        'solutionType': result.get('solutionType', ''),
                        'chunk_numbers': []
                    }
                
                # Parse and add chunk numbers from this result
                desc_chunks_prefixed = result.get('descChunksPrefixed', '')
                if desc_chunks_prefixed:
                    for prefixed_chunk in desc_chunks_prefixed.split(','):
                        if '|' in prefixed_chunk:
                            try:
                                chunk_num_str = prefixed_chunk.split('|')[0]
                                chunk_num = int(chunk_num_str)
                                if chunk_num not in solutions_by_doc_id[doc_id]['chunk_numbers']:
                                    solutions_by_doc_id[doc_id]['chunk_numbers'].append(chunk_num)
                            except ValueError:
                                continue
            
            self.logger.info(f"Grouped into {len(solutions_by_doc_id)} unique solutions")
            
            # Process each unique solution
            solutions = []
            for doc_id, solution_data in solutions_by_doc_id.items():
                try:
                    solution_data['chunk_numbers'].sort()  # Ensure proper order
                    solution = self._process_solution_result(solution_data)
                    if solution:
                        solutions.append(solution)
                except Exception as e:
                    self.logger.warning(f"Failed to process solution {doc_id}: {e}")
                    continue
            
            self.logger.info(f"Processed {len(solutions)} solutions with content")
            
            # 3. Rank by search query relevance
            if query and solutions:
                solutions = self._rank_by_relevance(solutions, query)
            
            return solutions
            
        except Exception as e:
            self.logger.error(f"CRITICAL ERROR in search_solutions: {str(e)}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return []  # Return empty list on error
    
    def _build_solution_sparql(self, filters: Dict[str, Any]) -> str:
        """Build SPARQL query from UI filters"""
        
        # Working query structure that navigates document ontology properly
        base_query = """
        PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
        PREFIX sg:  <http://solve.global/knowledge-commons/>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?solution ?doc_id ?title ?riskType ?solutionType
               (GROUP_CONCAT(?prefixed; SEPARATOR=",") AS ?descChunksPrefixed)
        WHERE {{
          {{
            SELECT ?solution ?doc_id ?title ?riskType ?solutionType
                   (CONCAT(?last4, "|", STR(?chunk)) AS ?prefixed)
            WHERE {{
              ?solution a sgd:Solution ;
                        dcterms:identifier ?doc_id ;
                        sg:riskType ?riskType ;
                        sg:solutionType ?solutionType ;
                        dcterms:title ?title ;
                        sgd:hasChild ?descSection .
              ?descSection dcterms:title ?t .
              FILTER(LCASE(STR(?t)) = "description")

              ?descSection sgd:firstChild ?c1 .
              ?c1 (sgd:nextSibling)* ?chunk .
              ?chunk sgd:hasParent ?descSection .

              BIND(STR(?chunk) AS ?s)
              BIND(STRLEN(?s) AS ?L)
              BIND(SUBSTR(?s, ?L - 3, 4) AS ?last4)
              FILTER(REGEX(?last4, "^[0-9]{{4}}$"))
              
              # Dynamic filter conditions
              {filter_conditions}
            }}
            ORDER BY ?last4
          }}
        }}
        GROUP BY ?solution ?doc_id ?title ?riskType ?solutionType
        ORDER BY ?solution
        LIMIT 50
        """
        
        # Build filter conditions
        filter_conditions = self._build_filter_conditions(filters)
        
        final_query = base_query.format(filter_conditions=filter_conditions)
        
        self.logger.info("=== FULL SPARQL QUERY ===")
        self.logger.info(final_query)
        self.logger.info("=== END SPARQL QUERY ===")
        
        return final_query
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> str:
        """Convert UI filters to SPARQL filter conditions"""
        conditions = []
        
        self.logger.info(f"Building filter conditions from: {filters}")
        
        # Solution category filter
        if 'solution_category' in filters and filters['solution_category']:
            category_value = filters['solution_category'][0]  # Take first value
            uri = self.filter_mappings['solution_category'].get(category_value)
            self.logger.info(f"Solution category: {category_value} -> {uri}")
            if uri:
                conditions.append(f"FILTER(?riskType = {uri})")
            else:
                self.logger.warning(f"No mapping found for solution_category: {category_value}")
        
        # Risk type filter
        if 'risk_type' in filters and filters['risk_type']:
            risk_value = filters['risk_type'][0]  # Take first value
            uri = self.filter_mappings['risk_type'].get(risk_value)
            self.logger.info(f"Risk type: {risk_value} -> {uri}")
            if uri:
                conditions.append(f"FILTER(?riskType = {uri})")
            else:
                self.logger.warning(f"No mapping found for risk_type: {risk_value}")
        
        # Solution type filter
        if 'solution_type' in filters and filters['solution_type']:
            solution_value = filters['solution_type'][0]  # Take first value
            uri = self.filter_mappings['solution_type'].get(solution_value)
            self.logger.info(f"Solution type: {solution_value} -> {uri}")
            if uri:
                conditions.append(f"FILTER(?solutionType = {uri})")
            else:
                self.logger.warning(f"No mapping found for solution_type: {solution_value}")
        
        self.logger.info(f"Generated {len(conditions)} filter conditions: {conditions}")
        
        # If no conditions, return empty string
        result = '\n            '.join(conditions) if conditions else ""
        self.logger.info(f"Final filter conditions string: '{result}'")
        return result
    
    def _process_solution_result(self, solution_data: Dict) -> Dict:
        """Process grouped solution data and retrieve S3 content"""
        
        doc_id = solution_data.get('doc_id')
        chunk_numbers = solution_data.get('chunk_numbers', [])
        
        if not doc_id or not chunk_numbers:
            self.logger.warning(f"Missing doc_id or chunk_numbers in solution data: {solution_data}")
            return None
        
        # Retrieve S3 content for all chunks
        content = self._get_solution_content(doc_id, chunk_numbers)
        if not content:
            return None
        
        return {
            'doc_id': doc_id,
            'kg_data': solution_data,
            'content': content,
            'relevance_score': 0.0  # Will be set by ranking
        }
    
    def _get_solution_content(self, doc_id: str, chunk_numbers: List[int]) -> Dict:
        """Retrieve solution content from S3 chunks"""
        
        chunks = []
        metadata = {}
        
        for chunk_num in sorted(chunk_numbers):
            s3_key = f"data-lake/{doc_id}/{doc_id}_chunk_{chunk_num:04d}.json"
            
            try:
                response = self.s3_client.get_object(Bucket=self.chunks_bucket, Key=s3_key)
                chunk_data = json.loads(response['Body'].read())
                
                chunks.append({
                    'number': chunk_num,
                    'text': chunk_data['text'],
                    'metadata': chunk_data['metadata']
                })
                
                # Store metadata from first chunk
                if not metadata:
                    metadata = chunk_data['metadata']
                    
            except Exception as e:
                self.logger.warning(f"Failed to retrieve chunk {s3_key}: {e}")
                continue
        
        if not chunks:
            self.logger.warning(f"No chunks retrieved for solution {doc_id}")
            return None
        
        # Assemble description maintaining paragraph structure
        assembled_description = '\n\n'.join([chunk['text'] for chunk in chunks])
        
        return {
            'assembled_description': assembled_description,
            'chunk_metadata': metadata,
            'chunks': chunks
        }
    
    def _rank_by_relevance(self, solutions: List[Dict], query: str) -> List[Dict]:
        """Rank solutions by relevance to search query"""
        
        # Simple relevance scoring based on query term matches
        query_terms = query.lower().split()
        
        for solution in solutions:
            score = 0.0
            content = solution['content']
            
            # Check solution name
            solution_name = content['chunk_metadata'].get('solution_name', '').lower()
            for term in query_terms:
                if term in solution_name:
                    score += 2.0  # Higher weight for name matches
            
            # Check description content
            description = content['assembled_description'].lower()
            for term in query_terms:
                score += description.count(term) * 0.5
            
            # Check risk type and solution type
            risk_type = content['chunk_metadata'].get('type_of_risk', '').lower()
            solution_type = content['chunk_metadata'].get('type_of_solution', '').lower()
            
            for term in query_terms:
                if term in risk_type:
                    score += 1.0
                if term in solution_type:
                    score += 1.0
            
            # Normalize score (0.0 to 1.0)
            solution['relevance_score'] = min(score / 10.0, 1.0)
        
        # Sort by relevance score (highest first)
        return sorted(solutions, key=lambda x: x['relevance_score'], reverse=True)
