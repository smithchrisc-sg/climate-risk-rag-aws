import boto3
import json
import logging
from typing import Dict, List, Any
import sys
import os
from datetime import datetime

# Import from knowledge graph layer - use utils path like working Lambda functions
from utils.KnowledgeGraphManager import KnowledgeGraphManager
from utils.DatabaseManager import DatabaseManager


class SolutionSearcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.kg_manager = KnowledgeGraphManager()
        self.db_manager = DatabaseManager()
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
    def get_filtered_solution_ids(self, filters: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Get solution IDs from Neptune filters - returns (uris, doc_ids)"""
        
        self.logger.info("=== GET_FILTERED_SOLUTION_IDS: METHOD CALLED ===")
        self.logger.info(f"Filters: {filters}")
        
        try:
            # Build SPARQL query for solution IDs only
            sparql_query = self._build_solution_ids_query(filters)
            self.logger.info(f"SPARQL query: {sparql_query}")
            
            # Execute query
            results = self.kg_manager.execute_sparql_query(sparql_query)
            self.logger.info(f"Raw SPARQL results: {results}")
            
            # Extract solution IDs
            solution_uris = []
            doc_ids = []
            if results:
                for result in results:
                    solution_uris.append(result['solution'])
                    doc_ids.append(result['doc_id'])
            else:
                self.logger.warning(f"No results found for query: {sparql_query}")
                return [], []
            
            self.logger.info(f"Extracted {len(solution_uris)} solution IDs")
            return solution_uris, doc_ids
            
        except Exception as e:
            self.logger.error(f"Failed to get solution IDs: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return [], []
    
    def _build_solution_ids_query(self, filters: Dict[str, Any]) -> str:
        """Build SPARQL query to get only solution IDs (no content)"""
        
        # Base query - just get solution URIs
        query_parts = [
            "PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>",
            "PREFIX sg: <http://solve.global/knowledge-commons/>",
            "PREFIX dcterms: <http://purl.org/dc/terms/>",
            "PREFIX gn: <http://www.geonames.org/ontology#>",
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>",
            "",
            "SELECT DISTINCT ?solution ?doc_id WHERE {",
            "  ?solution a sgd:Solution .",
            "  ?solution dcterms:identifier ?doc_id ."
        ]
        
        # Add filter conditions (reuse existing logic but simplified)
        filter_conditions = []
        
        # Solution category (risk types)
        if 'solution_category' in filters and filters['solution_category']:
            categories = filters['solution_category'] if isinstance(filters['solution_category'], list) else [filters['solution_category']]
            mapped_categories = [self.filter_mappings['solution_category'].get(cat) for cat in categories if cat in self.filter_mappings['solution_category']]
            if mapped_categories:
                category_uris = ', '.join([f"{uri}" for uri in mapped_categories])
                filter_conditions.append(f"  ?solution sg:riskType ?risk_type .")
                filter_conditions.append(f"  FILTER(?risk_type IN ({category_uris}))")
        
        # Solution type
        if 'solution_type' in filters and filters['solution_type']:
            types = filters['solution_type'] if isinstance(filters['solution_type'], list) else [filters['solution_type']]
            mapped_types = [self.filter_mappings['solution_type'].get(t) for t in types if t in self.filter_mappings['solution_type']]
            if mapped_types:
                type_uris = ', '.join([f"{uri}" for uri in mapped_types])
                filter_conditions.append(f"  ?solution sg:solutionType ?sol_type .")
                filter_conditions.append(f"  FILTER(?sol_type IN ({type_uris}))")
        
        # Countries
        if 'countries' in filters and filters['countries']:
            countries = filters['countries'] if isinstance(filters['countries'], list) else [filters['countries']]
            mapped_countries = [self.country_mappings.get(c) for c in countries if c in self.country_mappings]
            if mapped_countries:
                country_uris = ', '.join([f"{uri}" for uri in mapped_countries])
                filter_conditions.append(f"  ?solution dcterms:spatial ?country .")
                filter_conditions.append(f"  FILTER(?country IN ({country_uris}))")
        # Regions
        elif 'region' in filters and filters['region']:
            region = filters['region'] if isinstance(filters['region'], list) else [filters['region']]
            mapped_region = [self.filter_mappings['region'].get(r) for r in region if r in self.filter_mappings['region']]
            if mapped_region: # only one region is supported at a time
                region_uri = f"{mapped_region[0]}"
                filter_conditions.append(f"  ?solution dcterms:spatial ?country .")
                filter_conditions.append(f"{region_uri} sg:hasMember ?country .")  
        
        # Add all filter conditions
        query_parts.extend(filter_conditions)
        query_parts.append("}")

        full_query = '\n'.join(query_parts)

        return full_query
    
    def _get_ppp_involvement(self, doc_id: str) -> str:
        """Check if solution has both public/international and private organization involvement"""
        try:
            sparql_query = f"""
            PREFIX sg: <http://solve.global/knowledge-commons/>
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT ?solution 
                   (COUNT(DISTINCT ?publicIntlOrg) as ?publicIntlCount)
                   (COUNT(DISTINCT ?privateOrg) as ?privateCount)
            WHERE {{
                ?solution a sgd:Solution .
                ?solution dcterms:identifier "{doc_id}" .
                OPTIONAL {{ 
                    ?solution sg:associatedOrganization ?org .
                    ?org a ?orgType .
                    FILTER(?orgType = sg:PublicOrganization || ?orgType = sg:InternationalOrganization)
                    BIND(?org as ?publicIntlOrg)
                }}
                OPTIONAL {{ 
                    ?solution sg:associatedOrganization ?org .
                    ?org a sg:PrivateOrganization .
                    BIND(?org as ?privateOrg)
                }}
            }}
            GROUP BY ?solution
            """
            
            results = self.kg_manager.execute_sparql_query(sparql_query)
            if results and len(results) > 0:
                result = results[0]
                public_intl_count = int(result.get('publicIntlCount', 0))
                private_count = int(result.get('privateCount', 0))
                return "yes" if public_intl_count > 0 and private_count > 0 else "no"
            
            return "no"
        except Exception as e:
            self.logger.error(f"Error checking PPP involvement for {doc_id}: {e}")
            return "unknown"
        
    def get_solution_content(self, solution_uri: str) -> Dict[str, Any]:
        """Fetch full content for a single solution by doc_id"""
        
        self.logger.info(f"Fetching content for solution: {solution_uri}")
        
        try:
            # Get solution metadata from Neptune with enhanced lookups
            sparql_query = f"""
            PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
            PREFIX sg: <http://solve.global/knowledge-commons/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX gno: <http://www.geonames.org/ontology#>
            
            SELECT ?solution ?title ?riskType ?solutionType ?doc_id ?prefixed 
                   ?country_name ?risk_type_label ?solution_type_label ?implementation_date ?created_date ?highlightsPrefixed WHERE {{
                ?solution a sgd:Solution .
                ?solution dcterms:identifier ?doc_id .  
                FILTER(STR(?solution) = "{solution_uri}")
                OPTIONAL {{ ?solution dcterms:title ?title }}
                OPTIONAL {{ ?solution sg:riskType ?riskType }}
                OPTIONAL {{ ?solution sg:solutionType ?solutionType }}
                
                # Country names from GeoNames
                OPTIONAL {{
                  ?solution dcterms:spatial ?geo .
                  FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/"))
                  GRAPH <http://www.geonames.org/ontology/data> {{
                    ?geo gno:name ?country_name
                  }}
                }}
                
                # Risk type labels
                OPTIONAL {{ 
                  ?solution sg:riskType ?riskType .
                  ?riskType rdfs:label ?risk_type_label 
                }}
                
                # Solution type labels
                OPTIONAL {{ 
                  ?solution sg:solutionType ?solutionType .
                  ?solutionType rdfs:label ?solution_type_label 
                }}
                
                # Implementation date
                OPTIONAL {{ 
                  ?solution sg:implementationYear ?implementation_date 
                }}
                
                # Created date
                OPTIONAL {{ 
                  ?solution dcterms:created ?created_date 
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
                
                # Key highlights chunks
                OPTIONAL {{
                    ?solution sgd:hasChild ?highlightsSection .
                    ?highlightsSection dcterms:title ?ht .
                    FILTER(LCASE(STR(?ht)) = "key highlights")

                    ?highlightsSection sgd:firstChild ?hc1 .
                    ?hc1 (sgd:nextSibling)* ?highlightChunk .
                    ?highlightChunk sgd:hasParent ?highlightsSection .

                    BIND(STR(?highlightChunk) AS ?hs)
                    BIND(STRLEN(?hs) AS ?hL)
                    BIND(SUBSTR(?hs, ?hL - 3, 4) AS ?hLast4)
                    FILTER(REGEX(?hLast4, "^[0-9]{{4}}$"))
                    
                    BIND(CONCAT(?hLast4, "|", STR(?highlightChunk)) AS ?highlightsPrefixed)
                }}
            }}
            """
            
            kg_results = self.kg_manager.execute_sparql_query(sparql_query)
            self.logger.info(f"Raw SPARQL results for solution content: {kg_results}")

            kg_data = {}
            doc_id = ''
            content_data = {}
            # Extract KG metadata with enhanced data
            if kg_results:
                chunk_numbers = []
                country_names = []
                risk_type_labels = []
                solution_type_labels = []
                
                if len(kg_results) >= 1:
                    # Collect all unique values from results
                    for result in kg_results:
                        # Country names
                        if result.get('country_name') and result['country_name'] not in country_names:
                            country_names.append(result['country_name'])
                        
                        # Risk type labels
                        if result.get('risk_type_label') and result['risk_type_label'] not in risk_type_labels:
                            risk_type_labels.append(result['risk_type_label'])
                        
                        # Solution type labels
                        if result.get('solution_type_label') and result['solution_type_label'] not in solution_type_labels:
                            solution_type_labels.append(result['solution_type_label'])
                        
                        # Chunk numbers
                        if result.get('prefixed'):
                            chunk_num = int(result.get('prefixed').split('|')[0])
                            if chunk_num not in chunk_numbers:
                                chunk_numbers.append(chunk_num)

                    # Separate highlights processing
                    highlights_chunk_numbers = []
                    for result in kg_results:
                        if result.get('highlightsPrefixed'):
                            highlight_chunk_num = int(result.get('highlightsPrefixed').split('|')[0])
                            if highlight_chunk_num not in highlights_chunk_numbers:
                                highlights_chunk_numbers.append(highlight_chunk_num)
                        
                        # Highlights chunk numbers
                        if result.get('highlightsPrefixed'):
                            highlight_chunk_num = int(result.get('highlightsPrefixed').split('|')[0])
                            if highlight_chunk_num not in chunk_numbers:  # Add to same list for now
                                chunk_numbers.append(highlight_chunk_num)

                    # Get most recent implementation date
                    implementation_dates = [result.get('implementation_date') for result in kg_results if result.get('implementation_date')]
                    most_recent_date = max(implementation_dates) if implementation_dates else None

                    # Get created date
                    created_dates = [result.get('created_date') for result in kg_results if result.get('created_date')]
                    created_date = max(created_dates) if created_dates else None

                    kg_data = {
                        'title': kg_results[0].get('title', ''),
                        'riskType': kg_results[0].get('riskType', ''),
                        'solutionType': kg_results[0].get('solutionType', ''),
                        'country_names': country_names,
                        'risk_type_labels': risk_type_labels,
                        'solution_type_labels': solution_type_labels,
                        'implementation_date': most_recent_date,
                        'created_date': created_date
                    }
                    doc_id = kg_results[0].get('doc_id', '')
                    content_data = self._get_solution_content(doc_id, chunk_numbers) if chunk_numbers else {}
                    key_highlights = self._get_key_highlights_content(doc_id, highlights_chunk_numbers) if highlights_chunk_numbers else []
            else:
                self.logger.warning(f"No results found for solution URI: {solution_uri}")
                return None
            
            # Combine data
            solution_data = {
                'doc_id': doc_id,
                'kg_data': kg_data,
                'content': content_data,
                'key_highlights': key_highlights
            }
            
            # Convert to API format
            return self._convert_solution_to_api_format(solution_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get solution content for {doc_id}: {e}")
            return None
    
    def _convert_solution_to_api_format(self, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert solution data to API v2 format"""
        
        try:
            doc_id = solution_data.get('doc_id', '')
            kg_data = solution_data.get('kg_data', {})
            content = solution_data.get('content', {})
            
            title = kg_data.get('title', '') or content.get('chunk_metadata', {}).get('solution_name', '')
            description = content.get('assembled_description', '')
            key_highlights = solution_data.get('key_highlights', [])
            
            # Use enhanced data from SPARQL queries
            country_names = kg_data.get('country_names', [])
            risk_type_labels = kg_data.get('risk_type_labels', [])
            solution_type_labels = kg_data.get('solution_type_labels', [])
            
            # Fallback: if labels are empty, extract from URIs
            if not risk_type_labels and kg_data.get('riskType'):
                risk_uri = kg_data.get('riskType', '')
                if 'RiskType_' in risk_uri:
                    label = risk_uri.split('RiskType_')[1].replace('_', ' ').title()
                    risk_type_labels = [label]
            
            if not solution_type_labels and kg_data.get('solutionType'):
                solution_uri = kg_data.get('solutionType', '')
                if 'SolutionType_' in solution_uri:
                    label = solution_uri.split('SolutionType_')[1].replace('_', ' ').title()
                    solution_type_labels = [label]
            
            # Extract publication year from implementation date
            publication_year = None
            if kg_data.get('implementation_date'):
                try:
                    date_str = str(kg_data.get('implementation_date'))
                    if len(date_str) >= 4:
                        publication_year = int(date_str[:4])
                except:
                    publication_year = None
            
            # Determine implementation status from publication date
            implementation_date = kg_data.get('implementation_date')
            implemented = False
            if implementation_date:
                try:
                    # Handle both string and integer years
                    if isinstance(implementation_date, str):
                        impl_year = int(implementation_date.split('-')[0])  # Extract year from date string
                    else:
                        impl_year = int(implementation_date)
                    implemented = impl_year <= datetime.now().year
                except (ValueError, TypeError):
                    implemented = False
            
            # Determine PPP involvement
            ppp_involvement = self._get_ppp_involvement(doc_id)
            
            # Get last update date from knowledge graph
            last_update_date = None
            if kg_data.get('created_date'):
                try:
                    created_date = kg_data.get('created_date')
                    if hasattr(created_date, 'isoformat'):
                        last_update_date = created_date.isoformat()
                    elif isinstance(created_date, str):
                        # Handle DD/MM/YYYY format and convert to ISO8601
                        if '/' in created_date:
                            # Parse DD/MM/YYYY format
                            date_part = created_date.replace('Z', '').strip()
                            try:
                                dt = datetime.strptime(date_part, '%d/%m/%Y')
                                last_update_date = dt.date().isoformat()  # YYYY-MM-DD format
                            except ValueError:
                                last_update_date = str(created_date)
                        else:
                            last_update_date = str(created_date)
                    else:
                        last_update_date = str(created_date)
                except Exception as e:
                    self.logger.warning(f"Failed to format created date for {doc_id}: {e}")
            
            return {
                'document_id': doc_id,
                'content_type': 'solution',
                'solution_name': title,
                'title': title,
                'relevance_score': 1.0,
                'publication_date': implementation_date,
                'country_regions_covered': country_names,
                'risk_types_addressed': risk_type_labels,
                'solution_categories': [],
                'solution_types': solution_type_labels,
                'implemented': implemented,
                'ppp_involvement': ppp_involvement,
                'last_update_date': last_update_date,
                'summary_description': description,
                'key_highlights': key_highlights,
                'source': content.get('chunk_metadata', {}).get('source_url', '') if content else '',
                'related_documents': [],
                'snippets': [
                    {
                        'text': description[:200] + '...' if description and len(description) > 200 else description,
                        'page_number': 1,
                        'section': 'Description'
                    }
                ] if description else [],
                'metadata': {
                    'document_type': 'solution',
                    'categories': risk_type_labels,  # Use risk type labels as categories
                    'regions': country_names,  # Use country names as regions
                    'publication_year': publication_year,
                    'source': content.get('chunk_metadata', {}).get('source_url', '') if content else '',
                    'processing_timestamp': content.get('chunk_metadata', {}).get('processing_timestamp', '') if content else ''
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to format solution {solution_data.get('doc_id', 'unknown')}: {e}")
            return {
                'document_id': solution_data.get('doc_id', 'unknown'),
                'content_type': 'solution',
                'solution_name': 'Solution formatting error',
                'title': 'Solution formatting error',
                'relevance_score': 0.0,
                'summary_description': 'Error formatting solution data',
                'metadata': {'source': 'error_fallback'}
            }
        
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
                    # Parse enhanced data from SPARQL results
                    country_names = result.get('country_names', '').split(',') if result.get('country_names') else []
                    risk_type_labels = result.get('risk_type_labels', '').split(',') if result.get('risk_type_labels') else []
                    solution_type_labels = result.get('solution_type_labels', '').split(',') if result.get('solution_type_labels') else []
                    
                    # Clean up empty strings
                    country_names = [name.strip() for name in country_names if name.strip()]
                    risk_type_labels = [label.strip() for label in risk_type_labels if label.strip()]
                    solution_type_labels = [label.strip() for label in solution_type_labels if label.strip()]
                    
                    solutions_by_doc_id[doc_id] = {
                        'doc_id': doc_id,
                        'title': result.get('title', ''),
                        'riskType': result.get('riskType', ''),
                        'solutionType': result.get('solutionTypes', ''),  # Now contains concatenated types
                        'country_names': country_names,
                        'risk_type_labels': risk_type_labels,
                        'solution_type_labels': solution_type_labels,
                        'chunk_numbers': [],
                        'highlights_chunk_numbers': []
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
                
                # Parse highlights chunks
                highlights_chunks_prefixed = result.get('highlightsChunksPrefixed', '')
                if highlights_chunks_prefixed and highlights_chunks_prefixed.strip():
                    for prefixed_chunk in highlights_chunks_prefixed.split(','):
                        if '|' in prefixed_chunk:
                            try:
                                chunk_num_str = prefixed_chunk.split('|')[0]
                                chunk_num = int(chunk_num_str)
                                if chunk_num not in solutions_by_doc_id[doc_id]['highlights_chunk_numbers']:
                                    solutions_by_doc_id[doc_id]['highlights_chunk_numbers'].append(chunk_num)
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
        
        # Enhanced query to include country names and type labels
        base_query = """
        PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
        PREFIX sg:  <http://solve.global/knowledge-commons/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX gno: <http://www.geonames.org/ontology#>

        SELECT ?solution ?doc_id ?title ?riskType ?solutionTypes
               (GROUP_CONCAT(?prefixed; SEPARATOR=",") AS ?descChunksPrefixed)
               (GROUP_CONCAT(?highlightsPrefixed; SEPARATOR=",") AS ?highlightsChunksPrefixed)
               (GROUP_CONCAT(DISTINCT ?country_name; SEPARATOR=",") AS ?country_names)
               (GROUP_CONCAT(DISTINCT ?risk_type_label; SEPARATOR=",") AS ?risk_type_labels)
               (GROUP_CONCAT(DISTINCT ?solution_type_label; SEPARATOR=",") AS ?solution_type_labels)
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
          
          # Country names from GeoNames
          OPTIONAL {{
            ?solution dcterms:spatial ?geo .
            FILTER(STRSTARTS(STR(?geo), "https://sws.geonames.org/"))
            GRAPH <http://www.geonames.org/ontology/data> {{
              ?geo gno:name ?country_name
            }}
          }}
          
          # Risk type labels
          OPTIONAL {{ 
            ?solution sg:riskType ?riskType .
            ?riskType rdfs:label ?risk_type_label 
          }}
          
          # Solution type labels
          OPTIONAL {{ 
            ?solution sg:solutionType ?st .
            ?st rdfs:label ?solution_type_label 
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
          
          # Key highlights chunks
          OPTIONAL {{
            ?solution sgd:hasChild ?highlightsSection .
            ?highlightsSection dcterms:title ?ht .
            FILTER(LCASE(STR(?ht)) = "key highlights")

            ?highlightsSection sgd:firstChild ?hc1 .
            ?hc1 (sgd:nextSibling)* ?highlightChunk .
            ?highlightChunk sgd:hasParent ?highlightsSection .

            BIND(STR(?highlightChunk) AS ?hs)
            BIND(STRLEN(?hs) AS ?hL)
            BIND(SUBSTR(?hs, ?hL - 3, 4) AS ?hLast4)
            FILTER(REGEX(?hLast4, "^[0-9]{{4}}$"))
            
            BIND(CONCAT(?hLast4, "|", STR(?highlightChunk)) AS ?highlightsPrefixed)
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
        highlights_chunk_numbers = solution_data.get('highlights_chunk_numbers', [])
        
        if not doc_id or not chunk_numbers:
            self.logger.warning(f"Missing doc_id or chunk_numbers in solution data: {solution_data}")
            return None
        
        # Retrieve S3 content for all chunks
        content = self._get_solution_content(doc_id, chunk_numbers)
        if not content:
            return None
        
        # Get key highlights
        key_highlights = self._get_key_highlights_content(doc_id, highlights_chunk_numbers) if highlights_chunk_numbers else []
        
        return {
            'doc_id': doc_id,
            'kg_data': solution_data,
            'content': content,
            'key_highlights': key_highlights,
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
    
    def _get_key_highlights_content(self, doc_id: str, chunk_numbers: List[int]) -> List[str]:
        """Retrieve key highlights content from S3 chunks as separate strings"""
        
        highlights = []
        
        for chunk_num in sorted(chunk_numbers):
            s3_key = f"data-lake/{doc_id}/{doc_id}_chunk_{chunk_num:04d}.json"
            
            try:
                response = self.s3_client.get_object(Bucket=self.chunks_bucket, Key=s3_key)
                chunk_data = json.loads(response['Body'].read())
                
                highlight_text = chunk_data['text'].strip()
                if highlight_text:
                    highlights.append(highlight_text)
                    
            except Exception as e:
                self.logger.warning(f"Failed to retrieve highlight chunk {s3_key}: {e}")
                continue
        
        return highlights
    
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
