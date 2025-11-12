"""
Sophisticated result combination with configurable weighting and confidence levels.
Combines and ranks results from multiple search sources with advanced scoring.
"""

from typing import Dict, List, Any
import logging
from datetime import datetime

from models.search_models import SearchResult, SearchResponse, ResultType
from search.score_normalizer import ScoreNormalizer

class ResultCombiner:
    """
    Combines and normalizes results from multiple search sources with configurable weighting.
    """
    
    def __init__(self, 
                 weight_keyword: float = 0.6,
                 weight_vector: float = 0.4,
                 weight_graph: float = 0.5,
                 max_results: int = 30):
        """
        Initialize result combiner with source weights.
        
        Args:
            weight_keyword: Weight for keyword search results
            weight_vector: Weight for vector search results
            weight_graph: Weight for knowledge graph results
            max_results: Maximum number of results to return
        """
        self.weights = {
            ResultType.KEYWORD: weight_keyword,
            ResultType.VECTOR: weight_vector,
            ResultType.GRAPH: weight_graph
        }
        self.score_normalizer = ScoreNormalizer()
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)

    def combine_results(self,
                       keyword_results: SearchResponse,
                       vector_results: SearchResponse, 
                       graph_results: SearchResponse) -> SearchResponse:
        """Combine results from different search methods."""
        try:
            start_time = datetime.now()
            
            self.logger.info(f"Combining results: {len(keyword_results.results)} keyword, "
                           f"{len(vector_results.results)} vector, {len(graph_results.results)} graph")

            # Normalize scores using sophisticated normalization
            normalized_results = self.score_normalizer.normalize_scores(
                keyword_results=keyword_results,
                vector_results=vector_results,
                graph_results=graph_results
            )

            # Use the merge method that includes deduplication
            merged_response = self.merge_to_single_response(normalized_results)
            scored_results = merged_response.results
            
            # Add confidence levels
            for result in scored_results:
                result.metadata['confidence_level'] = self.get_confidence_level(result.score)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return SearchResponse(
                search_type="combined",
                total_results=len(scored_results),
                results=scored_results,
                metadata={
                    "source_counts": {
                        "keyword": len(keyword_results.results),
                        "vector": len(vector_results.results),
                        "graph": len(graph_results.results)
                    },
                    "source_weights": {
                        "keyword": self.weights[ResultType.KEYWORD],
                        "vector": self.weights[ResultType.VECTOR],
                        "graph": self.weights[ResultType.GRAPH]
                    },
                    "normalization_stats": {
                        "keyword_stats": keyword_results.metadata.get('normalization_stats', {}),
                        "vector_stats": vector_results.metadata.get('normalization_stats', {}),
                        "graph_stats": graph_results.metadata.get('normalization_stats', {})
                    },
                    "timing": {
                        "keyword": keyword_results.metadata.get("took", 0),
                        "vector": vector_results.metadata.get("took", 0),
                        "graph": graph_results.metadata.get("took", 0),
                        "combination_duration": duration
                    },
                    "confidence_distribution": self._calculate_confidence_distribution(scored_results),
                    "score_distribution": self._calculate_score_distribution(scored_results),
                    "normalization_method": "sophisticated_hybrid",
                    "max_results_limit": self.max_results,
                    "combination_method": "weighted_source_combination"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error combining results: {str(e)}")
            return SearchResponse(
                search_type="combined",
                total_results=0,
                results=[],
                metadata={"error": str(e)}
            )

    def _calculate_confidence_distribution(self, results: List[SearchResult]) -> Dict[str, int]:
        """Calculate confidence level distribution for results"""
        if not results:
            return {"high": 0, "medium": 0, "low": 0}
        
        distribution = {"high": 0, "medium": 0, "low": 0}
        
        for result in results:
            score = result.score
            if score >= 0.7:  # High confidence threshold
                distribution["high"] += 1
            elif score >= 0.4:  # Medium confidence threshold
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        
        return distribution

    def _calculate_score_distribution(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Calculate score distribution statistics for final results"""
        if not results:
            return {}
        
        scores = [result.score for result in results]
        scores.sort()
        n = len(scores)
        
        # Calculate basic statistics without numpy
        mean = sum(scores) / n
        variance = sum((x - mean) ** 2 for x in scores) / n
        std = variance ** 0.5
        
        # Calculate percentiles
        def percentile(data, p):
            k = (n - 1) * p / 100
            f = int(k)
            c = k - f
            if f == n - 1:
                return data[f]
            return data[f] * (1 - c) + data[f + 1] * c
        
        return {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "min": round(scores[0], 4),
            "max": round(scores[-1], 4),
            "median": round(percentile(scores, 50), 4),
            "count": n,
            "percentiles": {
                "25th": round(percentile(scores, 25), 4),
                "75th": round(percentile(scores, 75), 4),
                "95th": round(percentile(scores, 95), 4)
            }
        }

    def _score_and_rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Score and rank combined results with source-specific weighting."""
        self.logger.info(f"Scoring and ranking {len(results)} results")
        if not results:
            return []
        
        # Apply source-specific weights to normalized scores
        for result in results:
            weight = self.weights.get(result.source, 0.5)
            original_score = result.score
            weighted_score = result.score * weight
            
            # Update score and add weighting metadata
            result.score = weighted_score
            result.final_score = weighted_score
            
            # Add weighting metadata
            if 'score_metadata' not in result.metadata:
                result.metadata['score_metadata'] = {}
            
            result.metadata['score_metadata'].update({
                'normalized_score': original_score,
                'source_weight': weight,
                'weighted_score': weighted_score,
                'source': result.source.value if result.source else 'unknown'
            })
        
        # Sort by weighted score
        scored_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        # Limit to max results if specified
        if self.max_results and len(scored_results) > self.max_results:
            scored_results = scored_results[:self.max_results]
        
        # Add ranking metadata
        for rank, result in enumerate(scored_results):
            result.metadata['score_metadata']['final_rank'] = rank + 1
        
        return scored_results

    def get_confidence_level(self, score: float) -> str:
        """Convert numerical score to qualitative confidence level."""
        if score >= 0.8:
            return "High"
        elif score >= 0.5:
            return "Medium"
        else:
            return "Low"

    def update_weights(self, keyword: float = None, vector: float = None, graph: float = None):
        """Update source weights dynamically."""
        if keyword is not None:
            self.weights[ResultType.KEYWORD] = keyword
        if vector is not None:
            self.weights[ResultType.VECTOR] = vector
        if graph is not None:
            self.weights[ResultType.GRAPH] = graph
        
        self.logger.info(f"Updated weights: keyword={self.weights[ResultType.KEYWORD]}, "
                        f"vector={self.weights[ResultType.VECTOR]}, "
                        f"graph={self.weights[ResultType.GRAPH]}")

    def get_combination_stats(self) -> Dict[str, Any]:
        """Get statistics about result combination."""
        return {
            'weights': {
                'keyword': self.weights[ResultType.KEYWORD],
                'vector': self.weights[ResultType.VECTOR],
                'graph': self.weights[ResultType.GRAPH]
            },
            'max_results': self.max_results,
            'normalization_config': {
                'log_scale_factor': self.score_normalizer.log_scale_factor,
                'rank_weight': self.score_normalizer.rank_weight,
                'score_weight': self.score_normalizer.score_weight
            }
        }

    def merge_to_single_response(self, normalized_results: Dict[ResultType, SearchResponse]) -> SearchResponse:
        """Merge normalized results into single ranked response."""
        try:
            # Combine all results
            all_results = []
            for response in normalized_results.values():
                all_results.extend(response.results)

            # Deduplicate by document_id and aggregate scores properly
            document_map = {}
            vector_results_count = 0
            keyword_results_count = 0
            
            for result in all_results:
                if result.search_type == "vector":
                    vector_results_count += 1
                elif result.search_type == "keyword":
                    keyword_results_count += 1
                    
                doc_id = result.document_id
                self.logger.info(f"Processing {result.search_type} result with doc_id: {doc_id}")
                
                if doc_id in document_map:
                    existing = document_map[doc_id]
                    
                    self.logger.info(f"Document {doc_id} found in both {existing.search_type} and {result.search_type}")
                    
                    # Aggregate scores by search type instead of just keeping highest
                    if result.search_type == existing.search_type:
                        # Same search type - combine scores from multiple chunks
                        # Use max score to represent the best match for this document
                        if result.score > existing.score:
                            existing.score = result.score
                            existing.content = result.content
                            existing.content_highlights = result.content_highlights
                            existing.title_highlights = result.title_highlights
                        self.logger.info(f"Combined {result.search_type} chunks for {doc_id}: kept score {existing.score}")
                    else:
                        # Different search types - combine scores with weighted average
                        # Convert string search types to ResultType for weight lookup
                        existing_type = ResultType.KEYWORD if existing.search_type == "keyword" else \
                                       ResultType.VECTOR if existing.search_type == "vector" else \
                                       ResultType.GRAPH
                        new_type = ResultType.KEYWORD if result.search_type == "keyword" else \
                                  ResultType.VECTOR if result.search_type == "vector" else \
                                  ResultType.GRAPH
                        
                        existing_weight = self.weights.get(existing_type, 0.5)
                        new_weight = self.weights.get(new_type, 0.5)
                        
                        self.logger.info(f"Combining scores: {existing.search_type}({existing.score}) + {result.search_type}({result.score})")
                        
                        # Weighted combination of scores
                        total_weight = existing_weight + new_weight
                        existing.score = (existing.score * existing_weight + result.score * new_weight) / total_weight
                        
                        # Use content from higher-weighted source
                        if new_weight > existing_weight:
                            existing.content = result.content
                            existing.content_highlights = result.content_highlights
                            existing.title_highlights = result.title_highlights
                    
                    # Merge search types
                    if hasattr(existing, 'search_types'):
                        if result.search_type not in existing.search_types:
                            existing.search_types.append(result.search_type)
                    else:
                        existing.search_types = [existing.search_type, result.search_type]
                    
                    # Update metadata to include both sources
                    if 'sources' not in existing.metadata:
                        existing.metadata['sources'] = [existing.metadata.get('source', existing.search_type)]
                    if result.metadata.get('source', result.search_type) not in existing.metadata['sources']:
                        existing.metadata['sources'].append(result.metadata.get('source', result.search_type))
                else:
                    # First occurrence of this document
                    result.search_types = [result.search_type]
                    if 'sources' not in result.metadata:
                        result.metadata['sources'] = [result.metadata.get('source', result.search_type)]
                    document_map[doc_id] = result
            
            self.logger.info(f"Before deduplication: {keyword_results_count} keyword, {vector_results_count} vector")
            self.logger.info(f"After deduplication: {len(document_map)} unique documents")
            
            # Convert back to list
            all_results = list(document_map.values())

            # Apply source weights and sort
            weighted_results = self._score_and_rank_results(all_results)

            # Add confidence levels
            for result in weighted_results:
                result.metadata['confidence_level'] = self.get_confidence_level(result.score)

            return SearchResponse(
                search_type="combined",
                total_results=len(all_results),
                results=weighted_results,
                metadata={
                    "combination_method": "weighted_merge",
                    "source_weights": {
                        "keyword": self.weights[ResultType.KEYWORD],
                        "vector": self.weights[ResultType.VECTOR],
                        "graph": self.weights[ResultType.GRAPH]
                    },
                    "total_before_ranking": len(all_results),
                    "total_after_ranking": len(weighted_results)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error merging results: {str(e)}")
            return SearchResponse(
                search_type="combined",
                total_results=0,
                results=[],
                metadata={"error": str(e)}
            )

class AdvancedResultCombiner(ResultCombiner):
    """
    Advanced result combiner with additional features like diversity scoring
    and adaptive weighting based on query characteristics.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.diversity_weight = 0.1  # Weight for diversity scoring
        self.adaptive_weighting = True
    
    def _calculate_diversity_score(self, results: List[SearchResult]) -> List[SearchResult]:
        """Calculate diversity scores to promote result variety."""
        if len(results) <= 1:
            return results
        
        # Simple diversity based on content similarity
        for i, result in enumerate(results):
            diversity_score = 1.0  # Start with max diversity
            
            # Compare with previous results
            for j in range(i):
                other_result = results[j]
                # Simple content overlap check
                content_overlap = self._calculate_content_overlap(result.content, other_result.content)
                diversity_score *= (1.0 - content_overlap * 0.5)  # Reduce score for similar content
            
            # Apply diversity adjustment
            original_score = result.score
            adjusted_score = original_score * (1.0 - self.diversity_weight) + diversity_score * self.diversity_weight
            result.score = adjusted_score
            
            # Add diversity metadata
            result.metadata['diversity_score'] = diversity_score
            result.metadata['diversity_adjustment'] = adjusted_score - original_score
        
        return results
    
    def _calculate_content_overlap(self, content1: str, content2: str) -> float:
        """Calculate simple content overlap between two text snippets."""
        if not content1 or not content2:
            return 0.0
        
        # Simple word-based overlap
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _score_and_rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Enhanced scoring with diversity consideration."""
        # Apply base scoring
        scored_results = super()._score_and_rank_results(results)
        
        # Apply diversity scoring
        diverse_results = self._calculate_diversity_score(scored_results)
        
        # Re-sort after diversity adjustment
        final_results = sorted(diverse_results, key=lambda x: x.score, reverse=True)
        
        return final_results

    def _calculate_score_distribution(self, results: List[SearchResult]) -> Dict[str, Any]:
        """Calculate score distribution statistics for final results"""
        if not results:
            return {}
        
        scores = [result.score for result in results]
        scores.sort()
        n = len(scores)
        
        # Calculate basic statistics without numpy
        mean = sum(scores) / n
        variance = sum((x - mean) ** 2 for x in scores) / n
        std = variance ** 0.5
        
        # Calculate percentiles
        def percentile(data, p):
            k = (n - 1) * p / 100
            f = int(k)
            c = k - f
            if f == n - 1:
                return data[f]
            return data[f] * (1 - c) + data[f + 1] * c
        
        return {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "min": round(scores[0], 4),
            "max": round(scores[-1], 4),
            "median": round(percentile(scores, 50), 4),
            "count": n,
            "percentiles": {
                "25th": round(percentile(scores, 25), 4),
                "75th": round(percentile(scores, 75), 4),
                "95th": round(percentile(scores, 95), 4)
            }
        }

    def _calculate_confidence_distribution(self, results: List[SearchResult]) -> Dict[str, int]:
        """Calculate confidence level distribution for results"""
        if not results:
            return {"high": 0, "medium": 0, "low": 0}
        
        distribution = {"high": 0, "medium": 0, "low": 0}
        
        for result in results:
            score = result.score
            if score >= 0.7:  # High confidence threshold
                distribution["high"] += 1
            elif score >= 0.4:  # Medium confidence threshold
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        
        return distribution
