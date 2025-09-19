"""
Configuration settings for the sophisticated search system.
"""

import os

# Default configuration
SCORING_CONFIG = {
    "weights": {
        "keyword": 0.6,
        "vector": 0.4,
        "graph": 0.5
    },
    "normalization": {
        "log_scale_factor": 1.0,
        "rank_weight": 0.3,
        "min_percentile": 1,  # Lowered from 5
        "max_percentile": 99  # Lowered from 95
    },
    "result_limits": {
        "max_results": 50,    # Increased from 30
        "max_per_source": 100 # Increased from 50
    },
    "confidence_thresholds": {
        "high": 0.3,   # Lowered from 0.7
        "medium": 0.1  # Lowered from 0.4
    },
    "performance": {
        "search_timeout": 30,
        "max_retries": 3,
        "parallel_search": True
    }
}

# Lambda-optimized configuration
LAMBDA_SCORING_CONFIG = {
    "weights": {
        "keyword": 0.6,
        "vector": 0.4,
        "graph": 0.5
    },
    "normalization": {
        "log_scale_factor": 1.0,
        "rank_weight": 0.3,
        "min_percentile": 1,  # Lowered from 5
        "max_percentile": 99  # Lowered from 95
    },
    "result_limits": {
        "max_results": 50,    # Increased from 30
        "max_per_source": 100 # Increased from 50
    },
    "confidence_thresholds": {
        "high": 0.3,   # Lowered from 0.7
        "medium": 0.1  # Lowered from 0.4
    },
    "performance": {
        "search_timeout": 25,  # Leave buffer for Lambda
        "max_retries": 2,      # Reduced for Lambda
        "parallel_search": True
    }
}

def is_lambda_environment():
    """Detect if running in AWS Lambda"""
    return os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None

def get_scoring_config():
    """Get current scoring configuration based on environment"""
    if is_lambda_environment():
        return LAMBDA_SCORING_CONFIG.copy()
    return SCORING_CONFIG.copy()

def update_scoring_config(updates: dict):
    """Update scoring configuration"""
    def deep_update(base_dict, update_dict):
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    config = LAMBDA_SCORING_CONFIG if is_lambda_environment() else SCORING_CONFIG
    deep_update(config, updates)
