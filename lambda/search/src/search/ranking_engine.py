import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
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
    
    def fuse_rankings(self, bm25_ranks: List[Tuple[str, int]], 
                     vector_ranks: List[Tuple[str, int]], k: int = 60) -> List[Tuple[str, float]]:
        """Fuse BM25 and vector rankings using Reciprocal Rank Fusion (RRF)"""
        
        if not bm25_ranks and not vector_ranks:
            return []
        
        # Create score dictionaries
        bm25_scores = {doc_id: 1.0 / (rank + k) for doc_id, rank in bm25_ranks}
        vector_scores = {doc_id: 1.0 / (rank + k) for doc_id, rank in vector_ranks}
        
        # Get all unique document IDs
        all_doc_ids = set(bm25_scores.keys()) | set(vector_scores.keys())
        
        # Calculate RRF scores
        rrf_scores = []
        for doc_id in all_doc_ids:
            bm25_score = bm25_scores.get(doc_id, 0.0)
            vector_score = vector_scores.get(doc_id, 0.0)
            rrf_score = bm25_score + vector_score
            rrf_scores.append((doc_id, rrf_score))
        
        # Sort by RRF score (highest first)
        rrf_scores.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"RRF fusion: {len(bm25_ranks)} BM25 + {len(vector_ranks)} vector → {len(rrf_scores)} fused")
        return rrf_scores
    
    def normalize_rrf_scores(self, rrf_scores: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """Normalize RRF scores to 0-1 range for consistent API response"""
        
        if not rrf_scores:
            return []
        
        max_score = max(score for _, score in rrf_scores)
        if max_score == 0:
            return [(doc_id, 0.0) for doc_id, _ in rrf_scores]
        
        normalized = [(doc_id, score / max_score) for doc_id, score in rrf_scores]
        return normalized
