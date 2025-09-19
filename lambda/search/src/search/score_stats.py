"""
Score statistics analysis for sophisticated score normalization.
Analyzes score distributions to enable adaptive normalization strategies.
"""

import math
from dataclasses import dataclass
from typing import List, Optional
import logging

@dataclass
class ScoreStats:
    """Statistics for a set of scores."""
    mean: float
    std: float
    min: float
    max: float
    median: float
    count: int
    percentile_95: float
    distribution_type: str  # 'normal', 'log_normal', or 'power_law'

def analyze_score_distribution(scores: List[float]) -> ScoreStats:
    """
    Analyze score distribution and detect distribution type.
    
    Args:
        scores: List of numerical scores
        
    Returns:
        ScoreStats object with distribution analysis
    """
    logger = logging.getLogger(__name__)
    
    if not scores:
        return ScoreStats(
            mean=0.0, std=0.0, min=0.0, max=0.0, median=0.0,
            count=0, percentile_95=0.0, distribution_type='empty'
        )
    
    # Sort scores for calculations
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    
    # Basic statistics
    mean_val = sum(scores) / n
    variance = sum((x - mean_val) ** 2 for x in scores) / n
    std_val = variance ** 0.5
    min_val = sorted_scores[0]
    max_val = sorted_scores[-1]
    
    # Calculate median
    if n % 2 == 0:
        median_val = (sorted_scores[n//2 - 1] + sorted_scores[n//2]) / 2
    else:
        median_val = sorted_scores[n//2]
    
    # Calculate 95th percentile
    percentile_95_idx = int(0.95 * (n - 1))
    percentile_95_val = sorted_scores[percentile_95_idx]
    
    count_val = n
    
    # Simple distribution type detection
    distribution_type = _detect_distribution_type(sorted_scores)
    
    logger.debug(f"Score distribution analysis: mean={mean_val:.3f}, std={std_val:.3f}, "
                f"range=[{min_val:.3f}, {max_val:.3f}], type={distribution_type}")
    
    return ScoreStats(
        mean=mean_val,
        std=std_val,
        min=min_val,
        max=max_val,
        median=median_val,
        count=count_val,
        percentile_95=percentile_95_val,
        distribution_type=distribution_type
    )

def _detect_distribution_type(scores: List[float]) -> str:
    """
    Simple distribution type detection without scipy.
    
    Args:
        scores: Sorted list of scores
        
    Returns:
        Distribution type string
    """
    if len(scores) < 3:
        return "insufficient_data"
    
    # Simple heuristics for distribution detection
    mean_val = sum(scores) / len(scores)
    
    # Check if all positive (could be log-normal)
    if all(s > 0 for s in scores):
        # Simple coefficient of variation check
        variance = sum((x - mean_val) ** 2 for x in scores) / len(scores)
        std_val = variance ** 0.5
        cv = std_val / mean_val if mean_val > 0 else 0
        
        if cv > 1.0:  # High variability suggests log-normal
            return "log_normal"
    
    # Check for power law (large range)
    if scores[-1] > scores[0] * 10:  # Large range suggests power law
        return "power_law"
    
    # Default to normal
    return "normal"

def extract_scores(results: List) -> List[float]:
    """
    Extract scores from search results.
    
    Args:
        results: List of SearchResult objects or dictionaries
        
    Returns:
        List of numerical scores
    """
    scores = []
    
    for result in results:
        if hasattr(result, 'score'):
            # SearchResult object
            scores.append(float(result.score))
        elif isinstance(result, dict) and 'score' in result:
            # Dictionary format
            scores.append(float(result['score']))
    
    return scores

def calculate_percentile_bounds(scores: List[float], 
                              min_percentile: float = 5.0,
                              max_percentile: float = 95.0) -> tuple:
    """
    Calculate percentile-based bounds for score normalization.
    
    Args:
        scores: List of scores
        min_percentile: Lower percentile bound
        max_percentile: Upper percentile bound
        
    Returns:
        Tuple of (min_bound, max_bound)
    """
    if not scores:
        return (0.0, 1.0)
    
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    
    # Calculate percentiles
    def percentile(data, p):
        k = (n - 1) * p / 100
        f = int(k)
        c = k - f
        if f == n - 1:
            return data[f]
        return data[f] * (1 - c) + data[f + 1] * c
    
    min_bound = percentile(sorted_scores, min_percentile)
    max_bound = percentile(sorted_scores, max_percentile)
    
    return (min_bound, max_bound)

def is_score_outlier(score: float, stats: ScoreStats, 
                    z_threshold: float = 3.0) -> bool:
    """
    Determine if a score is an outlier based on z-score.
    
    Args:
        score: Score to test
        stats: Score statistics
        z_threshold: Z-score threshold for outlier detection
        
    Returns:
        True if score is an outlier
    """
    if stats.std == 0:
        return False
    
    z_score = abs(score - stats.mean) / stats.std
    return z_score > z_threshold
