import asyncio
import time
import logging
import json
import base64
import uuid
from typing import Dict, Any, List

# Import new solution search components
from search.solution_searcher import SolutionSearcher
from utilities.response_formatter import SolutionResponseFormatter

# Keep existing imports for Phase 2 (trusted documents)
from search.opensearch import OpenSearchProcessor
from search.neptune import NeptuneProcessor
from search.postgres import PostgresProcessor
from search.result_combiner import ResultCombiner
from search.config import get_scoring_config
from models.search_models import SearchResult, SearchResponse, ResultType, search_result_to_dict

class SearchCoordinator:
    """Coordinates search - Phase 1: Solutions via KG, Phase 2: Trusted docs via multi-modal"""
    
    def __init__(self):
        # Phase 1: Solution search components
        logging.info("SearchCoordinator: About to create SolutionSearcher")
        try:
            self.solution_searcher = SolutionSearcher()
            logging.info("SearchCoordinator: SolutionSearcher created successfully")
        except Exception as e:
            logging.error(f"SearchCoordinator: FAILED to create SolutionSearcher: {e}")
            import traceback
            logging.error(f"SearchCoordinator: Full traceback: {traceback.format_exc()}")
            # Create a dummy searcher that returns empty results
            self.solution_searcher = None
            
        self.response_formatter = SolutionResponseFormatter()
        logging.info("SearchCoordinator: SolutionResponseFormatter created successfully")
        
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
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def search(self, query: str, filters: Dict[str, Any], 
                    parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search with cursor-based pagination"""
        
        start_time = time.time()
        
        self.logger.info(f"Starting search for query: '{query}'")
        self.logger.info(f"Filters: {filters}")
        self.logger.info(f"Parameters: {parameters}")
        
        try:
            # Extract pagination parameters
            cursor = parameters.get('cursor')
            max_results = parameters.get('max_results', 20)
            
            # Determine page and query_id
            if cursor:
                # Decode cursor to get page and query_id
                try:
                    cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
                    page = cursor_data.get('page', 1)
                    query_id = cursor_data.get('query_id')
                    self.logger.info(f"Cursor decoded: page={page}, query_id={query_id}")
                except Exception as e:
                    self.logger.error(f"Failed to decode cursor: {e}")
                    # Treat as new search
                    page = 1
                    query_id = None
            else:
                # New search
                page = 1
                query_id = f"search_{str(uuid.uuid4())}"
                self.logger.info(f"New search, generated query_id: {query_id}")
            
            # Calculate offset for existing Neptune pagination
            offset = (page - 1) * max_results
            
            # Execute search using existing logic
            self.logger.info("SearchCoordinator: About to call solution_searcher.search_solutions")
            if self.solution_searcher is None:
                self.logger.error("SearchCoordinator: solution_searcher is None - returning empty results")
                solutions = []
                total_count = 0
            else:
                self.logger.info(f"Pagination: page={page}, max_results={max_results}, offset={offset}")
                
                # Get total count first for debugging
                try:
                    total_count = self.solution_searcher.count_solutions(filters)
                    self.logger.info(f"Total count query returned: {total_count}")
                except Exception as e:
                    self.logger.error(f"Count query failed: {e}")
                    total_count = 0
                
                # Get paginated solutions
                try:
                    solutions = self.solution_searcher.search_solutions(filters, query, max_results, offset)
                    self.logger.info(f"Search query returned: {len(solutions)} solutions")
                except Exception as e:
                    self.logger.error(f"Search query failed: {e}")
                    solutions = []
                    total_count = 0
                
            self.logger.info(f"SearchCoordinator: solution_searcher returned {len(solutions)} solutions, total: {total_count}")
            
            # Build pagination metadata
            total_pages = (total_count + max_results - 1) // max_results if total_count > 0 else 1
            
            # Generate next cursor if there are more pages
            next_cursor = None
            if page < total_pages:
                next_cursor_data = {'query_id': query_id, 'page': page + 1}
                next_cursor = base64.b64encode(json.dumps(next_cursor_data).encode('utf-8')).decode('utf-8')
            
            pagination = {
                'current_page': page,
                'total_pages': total_pages,
                'total_results': total_count,
                'page_size': max_results,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'next_cursor': next_cursor
            }
            
            # Format response using API v2 format
            execution_time = time.time() - start_time
            
            response = self.response_formatter.format_solution_results(
                solutions, 
                {'query': query, 'filters': filters, 'parameters': parameters}, 
                execution_time,
                pagination
            )
            
            # Add query_id to response
            response['query_id'] = query_id
            
            self.logger.info(f"Search completed in {execution_time:.2f}s")
            return response
            
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
                'results': {'solutions': []},
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            }
    
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
