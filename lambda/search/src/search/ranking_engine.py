import asyncio
import logging
from typing import Dict, List, Any, Optional
from search.opensearch import OpenSearchProcessor

class BasicRankingEngine:
    """Basic ranking engine using OpenSearch keyword search for Phase 2.1"""
    
    def __init__(self):
        self.opensearch = OpenSearchProcessor()
        self.logger = logging.getLogger(__name__)
    
    async def rank_solutions(self, query: str, solution_ids: List[str]) -> List[Dict[str, Any]]:
        """Rank solutions by query relevance using OpenSearch keyword search"""
        
        if not query.strip():
            # No query = no ranking, return in original order
            return [
                {
                    'solution_id': sol_id,
                    'combined_score': 0.0,
                    'content_score': 0.0,
                    'related_documents': []
                }
                for sol_id in solution_ids
            ]
        
        try:
            # Get keyword scores from OpenSearch
            keyword_scores = await self._get_keyword_scores(query, solution_ids)
            
            # Create ranking with scores
            ranking = []
            for sol_id in solution_ids:
                score = keyword_scores.get(sol_id, 0.0)
                ranking.append({
                    'solution_id': sol_id,
                    'combined_score': score,
                    'content_score': score,
                    'related_documents': []  # Phase 2.3 will populate this
                })
            
            # Sort by score (highest first)
            ranking.sort(key=lambda x: x['combined_score'], reverse=True)
            
            self.logger.info(f"Ranked {len(ranking)} solutions, top score: {ranking[0]['combined_score']:.3f}")
            return ranking
            
        except Exception as e:
            self.logger.error(f"Ranking failed: {e}, returning unranked results")
            # Fallback: return unranked
            return [
                {
                    'solution_id': sol_id,
                    'combined_score': 0.0,
                    'content_score': 0.0,
                    'related_documents': []
                }
                for sol_id in solution_ids
            ]
    
    async def _get_keyword_scores(self, query: str, solution_ids: List[str]) -> Dict[str, float]:
        """Get keyword relevance scores from OpenSearch"""
        
        try:
            # Search solutions in OpenSearch documents_keyword index
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"content_type": "solution"}},
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "content^2", "full_text"],
                                    "type": "best_fields"
                                }
                            }
                        ],
                        "filter": [
                            {"terms": {"doc_id": solution_ids}}
                        ]
                    }
                },
                "size": len(solution_ids),
                "_source": ["doc_id"]
            }
            
            if not self.opensearch.client:
                self.logger.warning("OpenSearch client not available, returning zero scores")
                return {}
            
            response = self.opensearch.client.search(
                index="documents_keyword",
                body=search_body
            )
            
            # Extract scores
            scores = {}
            max_score = 0.0
            
            for hit in response['hits']['hits']:
                doc_id = hit['_source']['doc_id']
                raw_score = hit['_score']
                max_score = max(max_score, raw_score)
                scores[doc_id] = raw_score
            
            # Normalize scores to 0-1 range
            if max_score > 0:
                for doc_id in scores:
                    scores[doc_id] = scores[doc_id] / max_score
            
            self.logger.info(f"Retrieved keyword scores for {len(scores)} solutions")
            return scores
            
        except Exception as e:
            self.logger.error(f"Keyword scoring failed: {e}")
            return {}
