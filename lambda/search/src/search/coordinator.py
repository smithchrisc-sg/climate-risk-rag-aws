import asyncio
from typing import Dict, Any, List
from .opensearch import OpenSearchProcessor
from .neptune import NeptuneProcessor
from .postgres import PostgresProcessor

class SearchCoordinator:
    """Coordinates multi-modal search across all data sources"""
    
    def __init__(self):
        self.opensearch = OpenSearchProcessor()
        self.neptune = NeptuneProcessor()
        self.postgres = PostgresProcessor()
    
    async def search(self, query: str, filters: Dict[str, Any], 
                    parameters: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-modal search"""
        
        # Execute parallel searches
        search_tasks = [
            self._keyword_search(query, filters, parameters),
            self._vector_search(query, filters, parameters),
            self._graph_search(query, filters, parameters)
        ]
        
        keyword_results, vector_results, graph_results = await asyncio.gather(*search_tasks)
        
        # Combine and rank results
        combined_results = self._combine_results(keyword_results, vector_results, graph_results)
        
        # Enrich with metadata
        enriched_results = await self._enrich_metadata(combined_results)
        
        # Apply final filtering and pagination
        final_results = self._apply_pagination(enriched_results, parameters)
        
        return final_results
    
    async def _keyword_search(self, query: str, filters: Dict[str, Any], 
                             parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute keyword search via OpenSearch"""
        return await self.opensearch.keyword_search(query, filters, parameters)
    
    async def _vector_search(self, query: str, filters: Dict[str, Any], 
                            parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute vector search via OpenSearch"""
        return await self.opensearch.vector_search(query, filters, parameters)
    
    async def _graph_search(self, query: str, filters: Dict[str, Any], 
                           parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute graph search via Neptune"""
        return await self.neptune.graph_search(query, filters, parameters)
    
    def _combine_results(self, keyword_results: List[Dict[str, Any]], 
                        vector_results: List[Dict[str, Any]], 
                        graph_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine and normalize scores from different search modalities"""
        
        # Normalize scores to 0-1 range
        all_results = []
        
        for result in keyword_results:
            result['search_type'] = 'keyword'
            result['normalized_score'] = self._normalize_score(result['score'], 'keyword')
            all_results.append(result)
        
        for result in vector_results:
            result['search_type'] = 'vector'
            result['normalized_score'] = self._normalize_score(result['score'], 'vector')
            all_results.append(result)
        
        for result in graph_results:
            result['search_type'] = 'graph'
            result['normalized_score'] = self._normalize_score(result['score'], 'graph')
            all_results.append(result)
        
        # Remove duplicates and combine scores
        unique_results = self._deduplicate_results(all_results)
        
        # Sort by combined score
        unique_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        return unique_results
    
    def _normalize_score(self, score: float, search_type: str) -> float:
        """Normalize scores based on search type"""
        if search_type == 'keyword':
            return min(score / 10.0, 1.0)  # Elasticsearch scores can be high
        elif search_type == 'vector':
            return score  # Cosine similarity already 0-1
        elif search_type == 'graph':
            return min(score / 5.0, 1.0)  # Graph scores typically lower
        return score
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and combine scores"""
        result_map = {}
        
        for result in results:
            doc_id = result['document_id']
            if doc_id not in result_map:
                result_map[doc_id] = result
                result_map[doc_id]['search_types'] = [result['search_type']]
                result_map[doc_id]['final_score'] = result['normalized_score']
            else:
                # Combine scores from multiple search types
                existing = result_map[doc_id]
                existing['search_types'].append(result['search_type'])
                existing['final_score'] = max(existing['final_score'], result['normalized_score'])
        
        return list(result_map.values())
    
    async def _enrich_metadata(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich results with metadata from PostgreSQL"""
        document_ids = [r['document_id'] for r in results]
        metadata = await self.postgres.get_document_metadata(document_ids)
        
        for result in results:
            doc_id = result['document_id']
            if doc_id in metadata:
                result.update(metadata[doc_id])
        
        return results
    
    def _apply_pagination(self, results: List[Dict[str, Any]], 
                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pagination and return formatted results"""
        limit = parameters.get('limit', 20)
        cursor = parameters.get('cursor')
        
        # Simple cursor-based pagination (in production, use more sophisticated approach)
        start_idx = 0
        if cursor:
            try:
                start_idx = int(cursor)
            except ValueError:
                start_idx = 0
        
        end_idx = start_idx + limit
        page_results = results[start_idx:end_idx]
        
        # Generate next cursor
        next_cursor = None
        if end_idx < len(results):
            next_cursor = str(end_idx)
        
        return {
            'results': page_results,
            'pagination': {
                'cursor': cursor,
                'next_cursor': next_cursor,
                'total_results': len(results),
                'returned_results': len(page_results)
            }
        }
