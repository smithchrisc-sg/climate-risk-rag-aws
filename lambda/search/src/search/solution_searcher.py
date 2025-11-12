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
        
        # Filter mappings from UI values to KG URIs (based on actual ontology)
        self.filter_mappings = {
            'solution_category': {
                # Frontend sends these as solution_category but they map to risk types
                'natural-catastrophe': 'sg:RiskType_natural_catastrophe',
                'cyber': 'sg:RiskType_cyber',
                'health': 'sg:RiskType_health',
                'retirement': 'sg:RiskType_retirement',
                'mortality': 'sg:RiskType_mortality'
            },
            'solution_type': {
                # Updated to match new frontend options and actual ontology
                'risk-reduction': 'sg:SolutionType_risk_reduction',
                'risk-financing': 'sg:SolutionType_risk_financing',
                'increase-penetration': 'sg:SolutionType_increase_penetration',
                'raising-awareness': 'sg:SolutionType_raising_awareness',
                'leveraging-technology': 'sg:SolutionType_leveraging_technology',
                'regulation': 'sg:SolutionType_regulation'
            },
            'region': {
                # Regional organizations (need to be added to Neptune)
                'asean': 'sg:RegionalOrg_asean',
                'asean-plus-3': 'sg:RegionalOrg_asean_plus_3'
            }
        }
        
        # Country name to GeoNames ID mapping (using correct namespace)
        self.country_mappings = {
            'brunei': '<http://www.geonames.org/ontology#1820814>',
            'cambodia': '<http://www.geonames.org/ontology#1831722>', 
            'indonesia': '<http://www.geonames.org/ontology#1643084>',
            'laos': '<http://www.geonames.org/ontology#1655842>',
            'malaysia': '<http://www.geonames.org/ontology#1733045>',
            'myanmar': '<http://www.geonames.org/ontology#1327865>',
            'philippines': '<http://www.geonames.org/ontology#1694008>',
            'singapore': '<http://www.geonames.org/ontology#1880251>',
            'thailand': '<http://www.geonames.org/ontology#1605651>',
            'vietnam': '<http://www.geonames.org/ontology#1562822>',
            # ASEAN+3 additional
            'china': '<http://www.geonames.org/ontology#1814991>',
            'japan': '<http://www.geonames.org/ontology#1861060>',
            'south-korea': '<http://www.geonames.org/ontology#1835841>',
            # Other Asia/Oceania
            'australia': '<http://www.geonames.org/ontology#2077456>',
            'new-zealand': '<http://www.geonames.org/ontology#2186224>',
            'papua-new-guinea': '<http://www.geonames.org/ontology#2088628>',
            'fiji': '<http://www.geonames.org/ontology#2205218>',
            'timor-leste': '<http://www.geonames.org/ontology#1966436>',
            'india': '<http://www.geonames.org/ontology#1269750>',
            'bangladesh': '<http://www.geonames.org/ontology#1210997>',
            'pakistan': '<http://www.geonames.org/ontology#1168579>',
            'nepal': '<http://www.geonames.org/ontology#1282988>',
            'sri-lanka': '<http://www.geonames.org/ontology#1227603>'
        }
        
        # Country name variations for literal matching
        self.country_literals = {
            'australia': ['Australia', 'Australia (Victoria)'],
            'singapore': ['Singapore'],
            'thailand': ['Thailand'],
            'malaysia': ['Malaysia'],
            'philippines': ['Philippines'],
            'indonesia': ['Indonesia'],
            'vietnam': ['Vietnam'],
            'cambodia': ['Cambodia'],
            'laos': ['Laos PDR', 'Laos'],
            'china': ['China'],
            'japan': ['Japan'],
            'south-korea': ['South Korea'],
            'new-zealand': ['New Zealand']
        }
        self.logger.info(f"SolutionSearcher initialized with filter mappings: {self.filter_mappings}")
        self.logger.info(f"Knowledge Graph Manager initialized: {self.kg_manager}")
        self.logger.info(f"S3 client initialized: {self.s3_client}")
        self.logger.info(f"Chunks bucket: {self.chunks_bucket}")
        
    def search_solutions(self, filters: Dict[str, Any], query: str, max_results: int = 20, offset: int = 0) -> List[Dict]:
        """Search solutions using KG filters + S3 content"""
        
        print("=== SOLUTION_SEARCHER: METHOD CALLED ===")
        self.logger.info("=== SOLUTION_SEARCHER: METHOD CALLED ===")
        
        try:
            self.logger.info(f"Searching solutions with filters: {filters}, query: {query}, max_results: {max_results}, offset: {offset}")
            
            # 1. Build and execute SPARQL query
            sparql_query = self._build_solution_sparql(filters, max_results, offset)
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
                        'solutionType': result.get('solutionTypes', ''),  # Now contains concatenated types
                        'chunk_numbers': []
                    }
                
                # Parse and add chunk numbers from this result (if any)
                desc_chunks_prefixed = result.get('descChunksPrefixed', '')
                if desc_chunks_prefixed and desc_chunks_prefixed.strip():
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
                    else:
                        # Even if no S3 content, include the solution with basic info
                        self.logger.warning(f"No S3 content for solution {doc_id}, including with basic info")
                        solutions.append({
                            'doc_id': doc_id,
                            'kg_data': solution_data,
                            'content': {
                                'assembled_description': f"Solution: {solution_data.get('title', 'No title available')}",
                                'chunk_metadata': {
                                    'solution_name': solution_data.get('title', ''),
                                    'type_of_risk': solution_data.get('riskType', ''),
                                    'type_of_solution': solution_data.get('solutionType', '')
                                },
                                'chunks': []
                            },
                            'relevance_score': 0.0
                        })
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
    
    def _build_solution_sparql(self, filters: Dict[str, Any], max_results: int = 20, offset: int = 0) -> str:
        """Build SPARQL query from UI filters"""
        
        # Fixed query to handle multiple solutionTypes per solution
        base_query = """
        PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
        PREFIX sg:  <http://solve.global/knowledge-commons/>
        PREFIX dcterms: <http://purl.org/dc/terms/>

        SELECT ?solution ?doc_id ?title ?riskType ?solutionTypes
               (GROUP_CONCAT(?prefixed; SEPARATOR=",") AS ?descChunksPrefixed)
        WHERE {{
          # First get unique solutions with aggregated solutionTypes
          {{
            SELECT ?solution ?doc_id ?title ?riskType 
                   (GROUP_CONCAT(DISTINCT ?solutionType; SEPARATOR=",") AS ?solutionTypes)
            WHERE {{
              ?solution a sgd:Solution ;
                        dcterms:identifier ?doc_id ;
                        sg:riskType ?riskType ;
                        sg:solutionType ?solutionType ;
                        dcterms:title ?title .
              
              # Dynamic filter conditions for solution selection
              {filter_conditions}
            }}
            GROUP BY ?solution ?doc_id ?title ?riskType
            ORDER BY ?solution
            LIMIT {max_results}
            OFFSET {offset}
          }}
          
          # Then optionally get chunks for these solutions
          OPTIONAL {{
            ?solution sgd:hasChild ?descSection .
            ?descSection dcterms:title ?t .
            FILTER(LCASE(STR(?t)) = "description")

            ?descSection sgd:firstChild ?c1 .
            ?c1 (sgd:nextSibling)* ?chunk .
            ?chunk sgd:hasParent ?descSection .

            BIND(STR(?chunk) AS ?s)
            BIND(STRLEN(?s) AS ?L)
            BIND(SUBSTR(?s, ?L - 3, 4) AS ?last4)
            FILTER(REGEX(?last4, "^[0-9]{{4}}$"))
            
            BIND(CONCAT(?last4, "|", STR(?chunk)) AS ?prefixed)
          }}
        }}
        GROUP BY ?solution ?doc_id ?title ?riskType ?solutionTypes
        ORDER BY ?solution
        """
        
        # Build filter conditions
        filter_conditions = self._build_filter_conditions(filters)
        
        final_query = base_query.format(filter_conditions=filter_conditions, max_results=max_results, offset=offset)
        
        self.logger.info("=== FULL SPARQL QUERY ===")
        self.logger.info(final_query)
        self.logger.info("=== END SPARQL QUERY ===")
        
        return final_query
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> str:
        """Convert UI filters to SPARQL filter conditions"""
        conditions = []
        
        self.logger.info(f"Building filter conditions from: {filters}")
        
        # Solution category filter (maps to riskType)
        if 'solution_category' in filters and filters['solution_category']:
            category_values = filters['solution_category']
            if len(category_values) == 1:
                uri = self.filter_mappings['solution_category'].get(category_values[0])
                if uri:
                    conditions.append(f"FILTER(?riskType = {uri})")
                    self.logger.info(f"Solution category filter: {category_values[0]} -> {uri}")
            elif len(category_values) > 1:
                uris = [self.filter_mappings['solution_category'].get(val) for val in category_values if self.filter_mappings['solution_category'].get(val)]
                if uris:
                    uri_list = ', '.join(uris)
                    conditions.append(f"FILTER(?riskType IN ({uri_list}))")
                    self.logger.info(f"Solution category filter (multiple): {category_values} -> {uris}")
        
        # Solution type filter  
        if 'solution_type' in filters and filters['solution_type']:
            solution_values = filters['solution_type']
            if len(solution_values) == 1:
                uri = self.filter_mappings['solution_type'].get(solution_values[0])
                if uri:
                    conditions.append(f"FILTER(?solutionType = {uri})")
                    self.logger.info(f"Solution type filter: {solution_values[0]} -> {uri}")
            elif len(solution_values) > 1:
                uris = [self.filter_mappings['solution_type'].get(val) for val in solution_values if self.filter_mappings['solution_type'].get(val)]
                if uris:
                    uri_list = ', '.join(uris)
                    conditions.append(f"FILTER(?solutionType IN ({uri_list}))")
                    self.logger.info(f"Solution type filter (multiple): {solution_values} -> {uris}")
        
        # Location filters (region OR countries, mutually exclusive)
        location_conditions = self._build_location_conditions(filters)
        if location_conditions:
            conditions.extend(location_conditions)
        
        self.logger.info(f"Generated {len(conditions)} filter conditions: {conditions}")
        
        result = '\n              '.join(conditions) if conditions else ""
        self.logger.info(f"Final filter conditions string: '{result}'")
        return result
    
    def _build_location_conditions(self, filters: Dict[str, Any]) -> List[str]:
        """Build location-specific filter conditions"""
        conditions = []
        
        # Regional filter (ASEAN, ASEAN+3)
        if 'region' in filters and filters['region']:
            region_values = filters['region']
            if len(region_values) == 1:
                region_uri = self.filter_mappings['region'].get(region_values[0])
                if region_uri:
                    # Add spatial property and regional membership check
                    conditions.append(f"?solution dcterms:spatial ?country .")
                    conditions.append(f"{region_uri} sg:hasMember ?country .")
                    self.logger.info(f"Region filter: {region_values[0]} -> {region_uri}")
        
        # Country list filter
        elif 'countries' in filters and filters['countries']:
            country_values = filters['countries']
            country_uris = [self.country_mappings.get(country) for country in country_values if self.country_mappings.get(country)]
            if country_uris:
                conditions.append(f"?solution dcterms:spatial ?country .")
                if len(country_uris) == 1:
                    conditions.append(f"FILTER(?country = {country_uris[0]})")
                else:
                    uri_list = ', '.join(country_uris)
                    conditions.append(f"FILTER(?country IN ({uri_list}))")
                self.logger.info(f"Country filter: {country_values} -> {country_uris}")
        
        return conditions
    
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
    
    def count_solutions(self, filters: Dict[str, Any]) -> int:
        """Count total solutions matching filters for pagination"""
        
        # Check if we have location filters that need special handling
        has_location_filters = 'region' in filters or 'countries' in filters
        
        if has_location_filters:
            # Use same structure as main query for location filters
            count_query = """
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            PREFIX sg:  <http://solve.global/knowledge-commons/>
            PREFIX dcterms: <http://purl.org/dc/terms/>

            SELECT (COUNT(DISTINCT ?solution) AS ?total)
            WHERE {{
              ?solution a sgd:Solution ;
                        dcterms:identifier ?doc_id ;
                        sg:riskType ?riskType ;
                        sg:solutionType ?solutionType ;
                        dcterms:title ?title .
              
              # Location filter conditions need spatial property
              {filter_conditions}
            }}
            """
        else:
            # Simple count for non-location filters
            count_query = """
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            PREFIX sg:  <http://solve.global/knowledge-commons/>
            PREFIX dcterms: <http://purl.org/dc/terms/>

            SELECT (COUNT(DISTINCT ?solution) AS ?total)
            WHERE {{
              ?solution a sgd:Solution ;
                        dcterms:identifier ?doc_id ;
                        sg:riskType ?riskType ;
                        sg:solutionType ?solutionType ;
                        dcterms:title ?title .
              
              # Non-location filter conditions
              {filter_conditions}
            }}
            """
        
        # Build filter conditions - reuse the same logic as main query
        filter_conditions = self._build_filter_conditions(filters)
        final_query = count_query.format(filter_conditions=filter_conditions)
        
        self.logger.info(f"Count query: {final_query}")
        
        try:
            results = self.kg_manager.execute_sparql_query(final_query)
            if results and len(results) > 0:
                total = int(results[0].get('total', 0))
                self.logger.info(f"Total solutions matching filters: {total}")
                return total
            return 0
        except Exception as e:
            self.logger.error(f"Error counting solutions: {e}")
            return 0
    
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
