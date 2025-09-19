import asyncio
import time
import uuid
from typing import Dict, Any, List
from search.opensearch import OpenSearchProcessor
from search.neptune import NeptuneProcessor
from search.postgres import PostgresProcessor
from search.result_combiner import ResultCombiner
from search.config import get_scoring_config
from models.search_models import SearchResult, SearchResponse, ResultType, search_result_to_dict
import logging

class SearchCoordinator:
    """Coordinates multi-modal search across all data sources"""
    
    def __init__(self):
        # Load configuration
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
        self.logger.info("SearchCoordinator initialized with sophisticated result combination and configuration")
        self.logger.info(f"Configuration: weights={self.config['weights']}, limits={self.config['result_limits']}")

    async def search(self, query: str, filters: Dict[str, Any], 
                    parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-modal search with sophisticated result combination"""
        
        start_time = time.time()
        search_id = str(uuid.uuid4())[:8]
        
        self.logger.info(f"[{search_id}] Starting multi-modal search for query: '{query[:50]}...'")
        
        try:
            # Execute parallel searches with error isolation
            search_tasks = [
                self._safe_keyword_search(query, filters, parameters),
                self._safe_vector_search(query, filters, parameters),
                self._safe_graph_search(query, filters, parameters)
            ]
            
            search_start = time.time()
            keyword_results, vector_results, graph_results = await asyncio.gather(*search_tasks)
            search_duration = time.time() - search_start

            self.logger.info(f"[{search_id}] Search results - Keyword: {len(keyword_results.results)}, "
                           f"Vector: {len(vector_results.results)}, Graph: {len(graph_results.results)} "
                           f"(took {search_duration:.2f}s)")
            
            # Use sophisticated result combination
            combine_start = time.time()
            combined_response = self.result_combiner.combine_results(
                keyword_results, vector_results, graph_results
            )
            combine_duration = time.time() - combine_start
            
            # Enrich with metadata
            enrich_start = time.time()
            enriched_results = await self._enrich_metadata(combined_response.results)
            enrich_duration = time.time() - enrich_start
            
            # Update the response with enriched results
            combined_response.results = enriched_results
            
            # Apply final filtering and pagination
            final_results = self._apply_pagination(combined_response.results, parameters)
            
            # Add comprehensive timing and statistics
            total_duration = time.time() - start_time
            final_results.update({
                'combination_stats': self.result_combiner.get_combination_stats(),
                'search_metadata': combined_response.metadata,
                'performance_metrics': {
                    'search_id': search_id,
                    'total_duration': round(total_duration, 3),
                    'search_duration': round(search_duration, 3),
                    'combination_duration': round(combine_duration, 3),
                    'enrichment_duration': round(enrich_duration, 3),
                    'results_per_second': round(len(combined_response.results) / total_duration, 2)
                }
            })
            
            self.logger.info(f"[{search_id}] Search completed successfully in {total_duration:.2f}s")
            return final_results
            
        except Exception as e:
            import traceback
            self.logger.error(f"[{search_id}] Search failed: {str(e)}")
            self.logger.error(f"[{search_id}] Full stack trace: {traceback.format_exc()}")
            return {
                'results': [],
                'total_results': 0,
                'error': str(e),
                'search_id': search_id,
                'performance_metrics': {
                    'total_duration': round(time.time() - start_time, 3),
                    'status': 'failed'
                }
            }
    
    async def _safe_keyword_search(self, query: str, filters: Dict[str, Any], 
                                  parameters: Dict[str, Any]) -> SearchResponse:
        """Execute keyword search with error isolation"""
        try:
            return await self.opensearch.keyword_search(query, filters, parameters)
        except Exception as e:
            self.logger.error(f"Keyword search failed: {str(e)}")
            return SearchResponse(
                search_type="keyword",
                total_results=0,
                results=[],
                metadata={"error": str(e), "status": "failed"}
            )
    
    async def _safe_vector_search(self, query: str, filters: Dict[str, Any], 
                                 parameters: Dict[str, Any]) -> SearchResponse:
        """Execute vector search with error isolation"""
        try:
            return await self.opensearch.vector_search(query, filters, parameters)
        except Exception as e:
            self.logger.error(f"Vector search failed: {str(e)}")
            return SearchResponse(
                search_type="vector",
                total_results=0,
                results=[],
                metadata={"error": str(e), "status": "failed"}
            )
    
    async def _safe_graph_search(self, query: str, filters: Dict[str, Any], 
                                parameters: Dict[str, Any]) -> SearchResponse:
        """Execute graph search with error isolation"""
        try:
            return await self.neptune.graph_search(query, filters, parameters)
        except Exception as e:
            self.logger.error(f"Graph search failed: {str(e)}")
            return SearchResponse(
                search_type="graph",
                total_results=0,
                results=[],
                metadata={"error": str(e), "status": "failed"}
            )
    
    async def _keyword_search(self, query: str, filters: Dict[str, Any], 
                             parameters: Dict[str, Any]) -> SearchResponse:
        """Execute keyword search via OpenSearch"""
        return await self.opensearch.keyword_search(query, filters, parameters)
    
    async def _vector_search(self, query: str, filters: Dict[str, Any], 
                            parameters: Dict[str, Any]) -> SearchResponse:
        """Execute vector search via OpenSearch"""
        return await self.opensearch.vector_search(query, filters, parameters)
    
    async def _graph_search(self, query: str, filters: Dict[str, Any], 
                           parameters: Dict[str, Any]) -> SearchResponse:
        """Execute graph search via Neptune"""
        return await self.neptune.graph_search(query, filters, parameters)
    
    async def _enrich_metadata(self, results: List[SearchResult]) -> List[SearchResult]:
        """Enrich results with metadata from PostgreSQL"""
        if not results:
            return results
            
        document_ids = [r.document_id for r in results]
        metadata = await self.postgres.get_document_metadata(document_ids)
        
        for result in results:
            doc_id = result.document_id
            if doc_id in metadata:
                # Log title enrichment for debugging
                old_title = result.title
                # Update result with database metadata
                db_metadata = metadata[doc_id]
                result.title = db_metadata.get('title', result.title)
                result.metadata.update(db_metadata)
                
                new_title = result.title
                if new_title and new_title != old_title:
                    self.logger.info(f"Enriched title for {doc_id}: '{new_title[:50]}...'")
        
        return results
    
    def _apply_pagination(self, results: List[SearchResult], 
                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pagination and return formatted results"""
        limit = parameters.get('limit', 20)
        cursor = parameters.get('cursor')
        
        # Simple cursor-based pagination (in production, use more sophisticated approach)
        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except (ValueError, TypeError):
                start_idx = 0
        
        # Apply pagination
        paginated_results = results[start_idx:start_idx + limit]
        
        # Convert SearchResult objects to dictionaries for JSON response
        result_dicts = [search_result_to_dict(result) for result in paginated_results]
        
        # Prepare next cursor
        next_cursor = None
        if start_idx + limit < len(results):
            next_cursor = str(start_idx + limit)
        
        return {
            'results': result_dicts,
            'total_results': len(results),
            'limit': limit,
            'cursor': cursor,
            'next_cursor': next_cursor,
            'has_more': next_cursor is not None
        }
    
    def update_combination_weights(self, keyword: float = None, vector: float = None, graph: float = None):
        """Update result combination weights dynamically"""
        self.result_combiner.update_weights(keyword=keyword, vector=vector, graph=graph)
        self.logger.info("Updated result combination weights")
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get comprehensive search statistics"""
        return {
            'combination_stats': self.result_combiner.get_combination_stats(),
            'normalization_history': getattr(self.result_combiner.score_normalizer, 'get_normalization_history', lambda: {})()
        }
