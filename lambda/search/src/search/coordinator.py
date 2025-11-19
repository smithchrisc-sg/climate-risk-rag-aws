import asyncio
import time
import logging
import json
import base64
import uuid
from typing import Dict, Any, List

# Import new solution search components
from search.solution_searcher import SolutionSearcher
from search.query_processor import QueryProcessor
from search.bm25_search_service import BM25SearchService
from search.vector_search_service import VectorSearchService
from search.related_documents_service import RelatedDocumentsService
from utilities.response_formatter import SolutionResponseFormatter

# Phase 2.1: S3 Session Cache and Basic Ranking
from search.session_manager import SearchSessionManager, SessionNotFoundError, SessionExpiredError
from search.ranking_engine import BasicRankingEngine

# Keep existing imports for Phase 2 (trusted documents)
from search.opensearch import OpenSearchProcessor
from search.neptune import NeptuneProcessor
from search.postgres import PostgresProcessor
from search.result_combiner import ResultCombiner
from search.config import get_scoring_config
from models.search_models import SearchResult, SearchResponse, ResultType, search_result_to_dict

class SearchCoordinator:
    """Coordinates search - Phase 1: Solutions via KG, Phase 2: S3 Session Cache + Ranking"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Phase 1: Solution search components
        self.logger.info("SearchCoordinator: About to create SolutionSearcher")

        try:
            self.solution_searcher = SolutionSearcher()
            self.logger.info("SearchCoordinator: SolutionSearcher created successfully")
        except Exception as e:
            self.logger.error(f"SearchCoordinator: FAILED to create SolutionSearcher: {e}")
            import traceback
            self.logger.error(f"SearchCoordinator: Full traceback: {traceback.format_exc()}")
            # Create a dummy searcher that returns empty results
            self.solution_searcher = None
        
        # Phase 2.1: Session cache and ranking
        self.session_manager = SearchSessionManager()
        self.ranking_engine = BasicRankingEngine()
        
        # Phase 1.1: Query processing and search services
        self.query_processor = QueryProcessor()
        self.bm25_search_service = BM25SearchService()
        self.vector_search_service = VectorSearchService()
        
        # Related documents service
        self.logger.info("Initializing RelatedDocumentsService")
        self.related_docs_service = RelatedDocumentsService(
            ranking_engine=self.ranking_engine
        )
        self.logger.info("RelatedDocumentsService initialized successfully")
        
        self.response_formatter = SolutionResponseFormatter()
        self.logger.info("SearchCoordinator: SolutionResponseFormatter created successfully")
        
        # Phase 2: Multi-modal search components (for future use)
        self.config = get_scoring_config()
        self.opensearch = OpenSearchProcessor()
        self.neptune = NeptuneProcessor()
        self.postgres = PostgresProcessor()
        self.result_combiner = ResultCombiner(
            weight_keyword=self.config["weights"]["keyword"],
            weight_vector=self.config["weights"]["vector"],
            weight_graph=self.config["weights"]["graph"],
            max_results=self.config["result_limits"]["max_results"]
        )
        
    async def search(self, query: str, filters: Dict[str, Any], 
                    parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search with S3 session cache and basic ranking"""
        
        start_time = time.time()
        
        self.logger.info(f"Starting search for query: '{query}'")
        self.logger.info(f"Filters: {filters}")
        self.logger.info(f"Parameters: {parameters}")
        
        try:
            # Extract pagination parameters
            cursor = parameters.get('cursor')
            max_results = parameters.get('max_results', 20)
            
            if cursor:
                # Handle cursor-based pagination using session cache
                return await self._handle_cursor_search(cursor, parameters, start_time)
            else:
                # Handle new search with ranking and session creation
                return await self._handle_new_search(query, filters, parameters, start_time)
                
        except Exception as e:
            import traceback
            self.logger.error(f"Search failed: {str(e)}")
            self.logger.error(f"Full stack trace: {traceback.format_exc()}")
            
            return {
                'status': 'error',
                'query_id': f"search_{int(time.time())}",
                'execution_time_ms': int((time.time() - start_time) * 1000),
                'total_results': 0,
                'returned_results': 0,
                'results': {'solutions': [], 'pagination': {}},
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            }
    
    async def _handle_new_search(self, query: str, filters: Dict[str, Any], 
                               parameters: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle new search - route between filter-only and hybrid search"""
        
        max_results = parameters.get('max_results', 20)
        
        # Process and validate query
        processed_query = self.query_processor.preprocess_query(query)
        search_strategy = self.query_processor.should_use_hybrid_search(processed_query)
        
        if search_strategy == "filter_only":
            self.logger.info("Using filter-only search (no query or query too short)")
            return await self._handle_filter_only_search(filters, parameters, start_time)
        elif search_strategy == "hybrid_full":
            self.logger.info(f"Using full hybrid search (BM25 + Vector) for query: '{processed_query}'")
            return await self._handle_hybrid_search(processed_query, filters, parameters, start_time)
        else:
            # Future: handle hybrid_bm25, hybrid_vector strategies
            self.logger.info(f"Using hybrid search for query: '{processed_query}'")
            return await self._handle_hybrid_search(processed_query, filters, parameters, start_time)
    
    async def _handle_filter_only_search(self, filters: Dict[str, Any], 
                                       parameters: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle filter-only search using existing logic"""
        
        max_results = parameters.get('max_results', 20)
        
        # Step 1: Get solution IDs from Neptune filters
        self.logger.info("Filter-only search: Getting solution IDs from Neptune")
        if self.solution_searcher is None:
            solution_ids = []
        else:
            try:
                solution_ids, _ = self.solution_searcher.get_filtered_solution_ids(filters)
                self.logger.info(f"Found {len(solution_ids)} solution IDs")
            except Exception as e:
                self.logger.error(f"Neptune filter query failed: {e}")
                solution_ids = []
        
        if not solution_ids:
            return self._create_empty_response("", filters, parameters, start_time)
        
        # Step 2: Create session with Neptune order (no ranking)
        session_id = await self.session_manager.create_session_lightweight(
            query="",
            filters=filters,
            solution_ids=solution_ids,
            page_size=max_results
        )
        
        # Step 3: Serve first page
        return await self._serve_page_from_session(
            session_id, page=1, parameters=parameters, start_time=start_time
        )
    
    async def _handle_hybrid_search(self, query: str, filters: Dict[str, Any], 
                                  parameters: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Handle hybrid search with BM25 keyword search"""
        
        max_results = parameters.get('max_results', 20)
        
        self.logger.info(f"Starting hybrid search for query: '{query}'")
        
        try:
            # Step 1: Get KG-filtered solution universe
            self.logger.info("Getting KG-filtered solution universe")
            if self.solution_searcher is None:
                kg_solution_ids, kg_doc_ids = [], []
            else:
                try:
                    kg_solution_ids, kg_doc_ids = self.solution_searcher.get_filtered_solution_ids(filters)
                    self.logger.info(f"KG filters returned {len(kg_solution_ids)} solutions")
                except Exception as e:
                    self.logger.error(f"KG filter query failed: {e}")
                    kg_solution_ids, kg_doc_ids = [], []
            
            if not kg_solution_ids:
                return self._create_empty_response(query, filters, parameters, start_time)
            
            # Step 2: Execute BM25 search
            self.logger.info("Executing BM25 keyword search")
            bm25_results = self.bm25_search_service.search(query, filters)
            
            if not bm25_results:
                self.logger.warning("BM25 search returned no results, falling back to filter-only")
                return await self._handle_filter_only_search(filters, parameters, start_time)
            
            # Step 3: Execute Vector search
            self.logger.info("Executing vector semantic search")
            vector_results = self.vector_search_service.search(query, filters)
            
            if not vector_results:
                self.logger.warning("Vector search returned no results, using BM25-only")
            
            # Step 4: Convert scores to ranks
            bm25_ranks = self.bm25_search_service.convert_to_ranks(bm25_results)
            vector_ranks = self.vector_search_service.convert_to_ranks(vector_results)
            self.logger.info(f"BM25: {len(bm25_ranks)} ranked, Vector: {len(vector_ranks)} ranked")
            
            # Step 5: Intersect search results with KG-filtered universe
            kg_doc_id_set = set(kg_doc_ids)
            
            # Intersect BM25 results
            bm25_intersected = [
                (sol_id, rank) for sol_id, rank in bm25_ranks 
                if sol_id in kg_doc_id_set
            ]
            
            # Intersect Vector results
            vector_intersected = [
                (sol_id, rank) for sol_id, rank in vector_ranks 
                if sol_id in kg_doc_id_set
            ]
            
            self.logger.info(f"Intersections - BM25: {len(bm25_intersected)}, Vector: {len(vector_intersected)}, KG: {len(kg_doc_ids)}")
            
            if not bm25_intersected and not vector_intersected:
                self.logger.warning("No intersection between search results and KG, falling back to filter-only")
                return await self._handle_filter_only_search(filters, parameters, start_time)
            
            # Step 6: Fuse rankings using RRF
            rrf_scores = self.ranking_engine.fuse_rankings(bm25_intersected, vector_intersected)
            normalized_scores = self.ranking_engine.normalize_rrf_scores(rrf_scores)
            
            # Step 7: Convert doc_ids back to URIs and maintain RRF ranking
            doc_id_to_uri = dict(zip(kg_doc_ids, kg_solution_ids))
            
            ordered_solution_ids = [
                doc_id_to_uri[doc_id] for doc_id, score in normalized_scores 
                if doc_id in doc_id_to_uri
            ]
            
            # Store RRF scores for relevance scoring
            rrf_score_map = dict(normalized_scores)
            
            self.logger.info(f"Final RRF hybrid results: {len(ordered_solution_ids)} solutions")
            
            # Step 8: Create session with RRF-ranked solution IDs
            session_id = await self.session_manager.create_session_lightweight(
                query=query,
                filters=filters,
                solution_ids=ordered_solution_ids,
                page_size=max_results,
                metadata={'rrf_scores': rrf_score_map}  # Store scores for relevance
            )
            
            # Step 7: Serve first page
            return await self._serve_page_from_session(
                session_id, page=1, parameters=parameters, start_time=start_time
            )
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            self.logger.info("Falling back to filter-only search")
            return await self._handle_filter_only_search(filters, parameters, start_time)
    
    async def _handle_cursor_search(self, cursor: str, parameters: Dict[str, Any], 
                                  start_time: float) -> Dict[str, Any]:
        """Handle cursor-based pagination using session cache"""
        
        # Decode cursor
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
            session_id = cursor_data['query_id'].replace('search_', '')
            target_page = cursor_data['page']
            self.logger.info(f"Cursor navigation: session={session_id}, page={target_page}")
        except Exception as e:
            self.logger.error(f"Failed to decode cursor: {e}")
            raise ValueError("Invalid cursor format")
        
        # Serve page from session
        try:
            return await self._serve_page_from_session(
                session_id, target_page, parameters, start_time
            )
        except (SessionNotFoundError, SessionExpiredError) as e:
            self.logger.warning(f"Session issue: {e}")
            return {
                'status': 'error',
                'query_id': f"search_{session_id}",
                'execution_time_ms': int((time.time() - start_time) * 1000),
                'error': {
                    'code': 'SESSION_EXPIRED',
                    'message': 'Search session expired, please start a new search'
                }
            }
    
    async def _serve_page_from_session(self, session_id: str, page: int, 
                                     parameters: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Serve page by fetching content for solutions on that page"""
        
        try:
            # Load session data
            session_data = await self.session_manager.load_session_lightweight(session_id)
            self.logger.info(f"Session data keys: {list(session_data.keys())}")
            self.logger.info(f"Session query field: '{session_data.get('query', 'NOT_FOUND')}'")
            
            # Get solution IDs for this page
            page_data = self.session_manager.get_page_solution_ids(
                session_data, page, parameters.get('max_results')
            )
            
            solution_ids = page_data['solution_ids']
            page_info = page_data['page_info']
            
            self.logger.info(f"Fetching content for {len(solution_ids)} solutions on page {page}")
            
            # Fetch full solution content for this page only
            page_solutions = []
            if self.solution_searcher:
                total_results = page_info['total_results']
                # Get RRF scores from session metadata if available
                rrf_scores = session_data.get('metadata', {}).get('rrf_scores', {})
                user_query = session_data.get('query', '')
                self.logger.info(f"User query from session: '{user_query}'")
                
                for idx, sol_id in enumerate(solution_ids): # sol_id is the URI of the solution 
                    try:
                        # Fetch individual solution content by solution URI
                        solution_content = self.solution_searcher.get_solution_content(sol_id)
                        if solution_content:
                            # Extract doc_id from URI for RRF score lookup
                            doc_id = sol_id.split('Document_')[1] if 'Document_' in sol_id else None
                            
                            # Use RRF score if available, otherwise fall back to position-based
                            if doc_id and doc_id in rrf_scores:
                                relevance_score = rrf_scores[doc_id]
                            else:
                                # Fallback to position-based scoring
                                start_position = (page - 1) * parameters.get('max_results', 20)
                                position = start_position + idx + 1  # 1-based position
                                relevance_score = 1.0 - (position / total_results) if total_results > 0 else 1.0
                            
                            solution_content['relevance_score'] = round(relevance_score, 4)
                            
                            # Add related documents if solution has complete facets
                            self.logger.info(f"Attempting to get related documents for solution: {solution_content.get('solution_id', sol_id)}")
                            try:
                                related_docs = self.related_docs_service.get_related_documents(
                                    user_query=user_query,
                                    solution_data=solution_content
                                )
                                solution_content['related_documents'] = related_docs
                                self.logger.info(f"Added {len(related_docs)} related documents")
                            except Exception as e:
                                self.logger.error(f"Related docs failed for {solution_content.get('solution_id', sol_id)}: {e}")
                                solution_content['related_documents'] = []
                            
                            page_solutions.append(solution_content)
                    except Exception as e:
                        self.logger.error(f"Failed to fetch solution {sol_id}: {e}")
                        # Continue with other solutions
            
            # Build pagination cursors
            next_cursor = None
            if page_info['has_next']:
                next_cursor = base64.b64encode(
                    json.dumps({
                        'query_id': f"search_{session_id}",
                        'page': page + 1
                    }).encode('utf-8')
                ).decode('utf-8')
            
            # Build response
            execution_time = time.time() - start_time
            
            return {
                'status': 'success',
                'query_id': f"search_{session_id}",
                'execution_time_ms': int(execution_time * 1000),
                'total_results': page_info['total_results'],
                'returned_results': len(page_solutions),
                'results': {
                    'solutions': page_solutions,
                    'pagination': {
                        'current_page': page_info['current_page'],
                        'total_pages': page_info['total_pages'],
                        'total_results': page_info['total_results'],
                        'page_size': page_info['page_size'],
                        'next_cursor': next_cursor
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to serve page {page} from session {session_id}: {e}")
            raise
    
    
    async def _get_solution_data(self, solution_id: str) -> Dict[str, Any]:
        """Get full solution data using existing S3 assembly logic"""
        
        if self.solution_searcher is None:
            return self._create_placeholder_solution(solution_id)
        
        try:
            # Use existing solution searcher to get individual solution
            # We'll search for this specific solution by doc_id
            solutions = self.solution_searcher.search_solutions(
                filters={},  # No filters, we want this specific solution
                query="",    # No query for individual lookup
                max_results=1,
                offset=0,
                doc_id_filter=solution_id  # Add this parameter to filter by doc_id
            )
            
            if solutions and len(solutions) > 0:
                return self._convert_solution_format(solutions[0])
            else:
                self.logger.warning(f"No solution data found for {solution_id}")
                return self._create_placeholder_solution(solution_id)
                
        except Exception as e:
            self.logger.error(f"Failed to get solution data for {solution_id}: {e}")
            return self._create_placeholder_solution(solution_id)
    
    def _convert_solution_format(self, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert solution_searcher format to API v2 format"""
        
        # Extract data from the complex solution_searcher format
        doc_id = solution_data.get('doc_id', '')
        kg_data = solution_data.get('kg_data', {})
        content = solution_data.get('content', {})
        
        # Build API v2 format solution
        return {
            'document_id': doc_id,
            'content_type': 'solution',
            'solution_name': kg_data.get('title', content.get('chunk_metadata', {}).get('solution_name', '')),
            'title': kg_data.get('title', content.get('chunk_metadata', {}).get('solution_name', '')),
            'relevance_score': solution_data.get('relevance_score', 0.0),
            'publication_date': None,  # TODO: Extract from metadata if available
            'country_regions_covered': [],  # TODO: Extract from spatial data
            'risk_types_addressed': [kg_data.get('riskType', '')],
            'solution_categories': [],  # TODO: Map from solution types
            'solution_types': kg_data.get('solutionType', '').split(',') if kg_data.get('solutionType') else [],
            'implemented': 'unknown',
            'ppp_involvement': 'unknown',
            'summary_description': content.get('assembled_description', ''),
            'key_highlights': [],
            'source': '',  # TODO: Extract from metadata
            'related_documents': [],
            'snippets': [
                {
                    'text': content.get('assembled_description', '')[:200] + '...',
                    'page_number': 1,
                    'section': 'Description'
                }
            ],
            'metadata': {
                'document_type': 'solution',
                'categories': [],
                'regions': [],
                'publication_year': None,
                'source': '',
                'processing_timestamp': content.get('chunk_metadata', {}).get('processing_timestamp', '')
            }
        }
    
    def _create_placeholder_solution(self, solution_id: str) -> Dict[str, Any]:
        """Create placeholder solution when real data unavailable"""
        
        return {
            'document_id': solution_id,
            'content_type': 'solution',
            'solution_name': f'Solution {solution_id}',
            'title': f'Solution {solution_id}',
            'relevance_score': 0.0,
            'publication_date': None,
            'country_regions_covered': [],
            'risk_types_addressed': [],
            'solution_categories': [],
            'solution_types': [],
            'implemented': 'unknown',
            'ppp_involvement': 'unknown',
            'summary_description': 'Solution data temporarily unavailable',
            'key_highlights': [],
            'source': '',
            'related_documents': [],
            'snippets': [],
            'metadata': {
                'document_type': 'solution',
                'categories': [],
                'regions': [],
                'publication_year': None,
                'source': 'session_cache_placeholder',
                'processing_timestamp': ''
            }
        }
    
    def _create_empty_response(self, query: str, filters: Dict[str, Any], 
                             parameters: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Create response for empty results"""
        
        execution_time = time.time() - start_time
        query_id = f"search_{str(uuid.uuid4())}"
        
        pagination = {
            'current_page': 1,
            'total_pages': 0,
            'total_results': 0,
            'page_size': parameters.get('max_results', 20),
            'has_next': False,
            'has_previous': False,
            'next_cursor': None
        }
        
        return self.response_formatter.format_solution_results(
            [],
            {'query': query, 'filters': filters, 'parameters': parameters},
            execution_time,
            pagination
        )
    
    async def get_repository_metadata(self, metadata_type: str) -> Dict[str, Any]:
        """Get repository metadata (last update or solution count)"""
        try:
            if metadata_type == "last-update":
                return {
                    'status': 'success',
                    'last_update': "2025-11-10T08:00:00Z",
                    'update_type': "solution_ingestion",
                    'documents_updated': 568
                }
            elif metadata_type == "solution-count":
                return {
                    'status': 'success',
                    'total_solutions': 568,
                    'total_trusted_documents': 0,  # Phase 2
                    'total_documents': 568,
                    'last_counted': "2025-11-10T08:00:00Z",
                    'breakdown': {
                        'solutions_by_category': {
                            'risk_reduction': 200,  # Estimated
                            'insurance_penetration': 200,  # Estimated
                            'risk_financing': 168   # Estimated
                        },
                        'trusted_documents_by_type': {
                            'supporting_studies': 0,  # Phase 2
                            'policy_frameworks': 0,  # Phase 2
                            'research_papers': 0     # Phase 2
                        }
                    }
                }
            else:
                return {
                    'status': 'error',
                    'error': {
                        'code': 'INVALID_REQUEST',
                        'message': 'Invalid metadata type'
                    }
                }
        except Exception as e:
            self.logger.error(f"Repository metadata request failed: {str(e)}")
            return {
                'status': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            }

    # Phase 2 methods (for future trusted document search)
    async def search_trusted_documents(self, query: str, solution_context: List[Dict], 
                                     filters: Dict[str, Any], parameters: Dict[str, Any]) -> List[Dict]:
        """Phase 2: Multi-modal search for trusted source documents (future implementation)"""
        
        # This will use the existing multi-modal search logic
        # when Phase 2 is implemented
        
        self.logger.info("Phase 2 trusted document search not yet implemented")
        return []
