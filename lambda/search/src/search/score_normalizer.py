"""
Sophisticated score normalization with hybrid approach for BM25 scores.
Combines absolute score scaling with rank-based normalization.
"""

import math
from typing import Dict, List
from collections import defaultdict
import logging
from datetime import datetime

from models.search_models import SearchResponse, SearchResult, ResultType
from search.score_stats import ScoreStats, analyze_score_distribution, extract_scores

class ScoreNormalizer:
    """
    Enhanced score normalization with hybrid approach for BM25 scores.
    Combines absolute score scaling with rank-based normalization.
    """
    
    def __init__(self, 
                 log_scale_factor: float = 1.0,
                 rank_weight: float = 0.3,
                 min_percentile: float = 5,
                 max_percentile: float = 95):
        """
        Initialize score normalizer with configurable parameters.
        
        Args:
            log_scale_factor: Factor to control log-scale curve steepness
            rank_weight: Weight given to rank-based component (0-1)
            min_percentile: Percentile to use for minimum score
            max_percentile: Percentile to use for maximum score
        """
        self.log_scale_factor = log_scale_factor
        self.rank_weight = max(0.0, min(1.0, rank_weight))
        self.score_weight = 1.0 - self.rank_weight
        self.min_percentile = min_percentile
        self.max_percentile = max_percentile
        self.logger = logging.getLogger(__name__)
        
        # Initialize statistics tracking
        self.stats_history = defaultdict(list)
        self.normalization_stats = defaultdict(dict)

    def normalize_scores(self, 
                        keyword_results: SearchResponse,    
                        vector_results: SearchResponse,
                        graph_results: SearchResponse) -> Dict[ResultType, SearchResponse]:
        """
        Normalize scores from different search methods.
        
        Args:
            keyword_results: Results with BM25 scores
            vector_results: Results with vector similarity scores
            graph_results: Results with graph relevance scores
            
        Returns:
            Dictionary containing normalized results for each source
        """
        try:
            start_time = datetime.now()
            
            self.logger.debug(f"Normalizing scores for {len(keyword_results.results)} keyword, "
                            f"{len(vector_results.results)} vector, {len(graph_results.results)} graph results")
            
            # Extract original scores
            bm25_scores = extract_scores(keyword_results.results)
            vector_scores = extract_scores(vector_results.results)
            graph_scores = extract_scores(graph_results.results)
            
            # Calculate statistics
            bm25_stats = analyze_score_distribution(bm25_scores)
            vector_stats = analyze_score_distribution(vector_scores)
            graph_stats = analyze_score_distribution(graph_scores)
            
            # Track statistics
            self._update_stats_history(
                bm25_stats=bm25_stats,
                vector_stats=vector_stats,
                graph_stats=graph_stats
            )
            
            # Normalize each source with appropriate method
            normalized_results = {
                ResultType.KEYWORD: self._normalize_bm25_results(keyword_results, bm25_stats),
                ResultType.VECTOR: self._normalize_bounded_results(vector_results, vector_stats),
                ResultType.GRAPH: self._normalize_bounded_results(graph_results, graph_stats)
            }
            
            # Track normalization performance
            duration = (datetime.now() - start_time).total_seconds()
            self._track_normalization_metrics(
                original_stats={
                    'bm25': bm25_stats,
                    'vector': vector_stats,
                    'graph': graph_stats
                },
                duration=duration
            )

            self._log_normalization_stats(bm25_stats, vector_stats, graph_stats)    
            
            return normalized_results
            
        except Exception as e:
            self.logger.error(f"Error in score normalization: {str(e)}")
            raise

    def _normalize_bm25_results(self, 
                              results: SearchResponse, 
                              stats: ScoreStats) -> SearchResponse:
        """
        Apply hybrid normalization to BM25 results.
        
        Args:
            results: SearchResponse with BM25 scores
            stats: Statistics for the score distribution
            
        Returns:
            SearchResponse with normalized scores
        """
        try:
            self.logger.debug(f"Normalizing BM25 results with stats: mean={stats.mean:.3f}, "
                            f"max={stats.max:.3f}, count={stats.count}")
            
            if not results.results:
                return SearchResponse(
                    search_type="keyword",
                    total_results=0,
                    results=[],
                    metadata=results.metadata
                )
            
            # Sort results by original score for rank calculation
            sorted_results = sorted(
                results.results,
                key=lambda x: x.score,
                reverse=True
            )
            
            total_docs = len(sorted_results)
            max_score = stats.max if stats.max > 0 else 1.0
            
            normalized = []
            for rank, result in enumerate(sorted_results):
                original_score = result.score
                
                # Calculate log-scale component
                log_norm = self._calculate_log_component(
                    score=original_score,
                    max_score=max_score
                )
                
                # Calculate rank component
                rank_norm = self._calculate_rank_component(
                    rank=rank,
                    total_docs=total_docs
                )
                
                # Combine components
                final_score = (
                    self.score_weight * log_norm +
                    self.rank_weight * rank_norm
                )
                
                # Create normalized result with metadata
                normalized_result = SearchResult(
                    document_id=result.document_id,
                    title=result.title,
                    score=final_score,
                    content=result.content,
                    content_highlights=result.content_highlights,
                    title_highlights=result.title_highlights,
                    source=result.source,
                    search_type=result.search_type,
                    metadata={
                        **result.metadata,
                        'score_metadata': {
                            'original_score': original_score,
                            'normalized_score': final_score,
                            'log_component': log_norm,
                            'rank_component': rank_norm,
                            'rank_position': rank + 1,
                            'total_documents': total_docs,
                            'normalization_method': 'hybrid_bm25',
                            'normalization_params': {
                                'log_scale_factor': self.log_scale_factor,
                                'rank_weight': self.rank_weight,
                                'score_weight': self.score_weight
                            },
                            'source_stats': {
                                'mean': stats.mean,
                                'std': stats.std,
                                'max': stats.max,
                                'min': stats.min,
                                'median': stats.median,
                                'count': stats.count,
                                'percentile_95': stats.percentile_95,
                                'distribution_type': stats.distribution_type
                            }
                        }
                    }
                )
                normalized.append(normalized_result)
            
            return SearchResponse(
                search_type=results.search_type,
                total_results=len(normalized),
                results=normalized,
                metadata={
                    **results.metadata,
                    'normalization': {
                        'method': 'hybrid_bm25',
                        'log_scale_factor': self.log_scale_factor,
                        'rank_weight': self.rank_weight,
                        'score_weight': self.score_weight,
                        'original_stats': {
                            'mean': stats.mean,
                            'max': stats.max,
                            'count': stats.count
                        }
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error normalizing BM25 results: {str(e)}")
            return results

    def _calculate_log_component(self, score: float, max_score: float) -> float:
        """Calculate log-scale normalization component."""
        if max_score <= 0:
            return 0.0
        return 1.0 - (1.0 / (1.0 + self.log_scale_factor * math.log1p(score / max_score)))

    def _calculate_rank_component(self, rank: int, total_docs: int) -> float:
        """Calculate rank-based normalization component."""
        if total_docs <= 1:
            return 1.0
        return (total_docs - rank) / (total_docs - 1)

    def _normalize_bounded_results(self, 
                                 results: SearchResponse, 
                                 stats: ScoreStats) -> SearchResponse:
        """
        Normalize results that are already bounded (e.g., vector similarities).
        
        Args:
            results: SearchResponse with bounded scores
            stats: Statistics for the score distribution
            
        Returns:
            SearchResponse with normalized scores
        """
        try:
            normalized = []

            for result in results.results:
                original_score = result.score
                
                # Apply mild sigmoid transformation for better alignment
                normalized_score = 1.0 / (1.0 + math.exp(-5.0 * (original_score - 0.5)))
                
                normalized_result = SearchResult(
                    document_id=result.document_id,
                    title=result.title,
                    score=normalized_score,
                    content=result.content,
                    content_highlights=result.content_highlights,
                    title_highlights=result.title_highlights,
                    source=result.source,
                    search_type=result.search_type,
                    metadata={
                        **result.metadata,
                        'score_metadata': {
                            'original_score': original_score,
                            'normalized_score': normalized_score,
                            'normalization_method': 'bounded_sigmoid',
                            'transformation': 'sigmoid_5x',
                            'source_stats': {
                                'mean': stats.mean,
                                'std': stats.std,
                                'max': stats.max,
                                'min': stats.min,
                                'median': stats.median,
                                'count': stats.count,
                                'percentile_95': stats.percentile_95,
                                'distribution_type': stats.distribution_type
                            }
                        }
                    }
                )
                normalized.append(normalized_result)
                
            return SearchResponse(
                search_type=results.search_type,
                total_results=len(normalized),
                results=normalized,
                metadata={
                    **results.metadata,
                    'normalization_applied': 'bounded_sigmoid',
                    'normalization_stats': {
                        'mean': stats.mean,
                        'std': stats.std,
                        'max': stats.max,
                        'min': stats.min,
                        'median': stats.median,
                        'count': stats.count,
                        'percentile_95': stats.percentile_95,
                        'distribution_type': stats.distribution_type
                    },
                    'normalization_params': {
                        'method': 'bounded_sigmoid',
                        'transformation': 'sigmoid_5x',
                        'formula': '1.0 / (1.0 + exp(-5.0 * (score - 0.5)))'
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error normalizing bounded results: {str(e)}")
            return results

    def _update_stats_history(self, bm25_stats: ScoreStats, 
                            vector_stats: ScoreStats, 
                            graph_stats: ScoreStats):
        """Track statistics history for analysis"""
        timestamp = datetime.now()
        
        self.stats_history['bm25'].append({
            'timestamp': timestamp,
            'stats': bm25_stats
        })
        
        self.stats_history['vector'].append({
            'timestamp': timestamp,
            'stats': vector_stats
        })
        
        self.stats_history['graph'].append({
            'timestamp': timestamp,
            'stats': graph_stats
        })
        
        # Keep only recent history (last 100 entries)
        for source in self.stats_history:
            if len(self.stats_history[source]) > 100:
                self.stats_history[source] = self.stats_history[source][-100:]

    def _track_normalization_metrics(self, original_stats: Dict, duration: float):
        """Track normalization performance metrics"""
        self.normalization_stats['last_run'] = {
            'timestamp': datetime.now(),
            'duration_seconds': duration,
            'original_stats': original_stats
        }

    def _log_normalization_stats(self, bm25_stats: ScoreStats, 
                               vector_stats: ScoreStats, 
                               graph_stats: ScoreStats):
        """Log normalization statistics for monitoring"""
        self.logger.info(f"Score normalization completed:")
        self.logger.info(f"  BM25: {bm25_stats.count} scores, "
                        f"range=[{bm25_stats.min:.3f}, {bm25_stats.max:.3f}], "
                        f"mean={bm25_stats.mean:.3f}")
        self.logger.info(f"  Vector: {vector_stats.count} scores, "
                        f"range=[{vector_stats.min:.3f}, {vector_stats.max:.3f}], "
                        f"mean={vector_stats.mean:.3f}")
        self.logger.info(f"  Graph: {graph_stats.count} scores, "
                        f"range=[{graph_stats.min:.3f}, {graph_stats.max:.3f}], "
                        f"mean={graph_stats.mean:.3f}")

    def get_normalization_history(self) -> Dict:
        """Get historical normalization statistics"""
        return {
            'stats_history': dict(self.stats_history),
            'recent_metrics': self.normalization_stats
        }
