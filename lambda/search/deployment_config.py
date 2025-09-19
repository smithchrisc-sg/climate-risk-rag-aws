"""
Deployment configuration for AWS Lambda search function.
Optimizes settings for Lambda environment constraints.
"""

import os

# Lambda-optimized configuration
LAMBDA_CONFIG = {
    "memory_mb": 1024,  # Sufficient for numpy/scipy operations
    "timeout_seconds": 30,  # Match search timeout
    "environment_variables": {
        "PYTHONPATH": "/var/task/src",
        "NUMPY_DISABLE_THREADING": "1",  # Optimize for Lambda
        "SCIPY_DISABLE_THREADING": "1"   # Optimize for Lambda
    },
    "layers": [
        # Consider using AWS Lambda layers for numpy/scipy to reduce package size
        # "arn:aws:lambda:us-east-1:668099181075:layer:AWSLambda-Python39-SciPy1x:107"
    ]
}

# Scoring configuration optimized for Lambda
LAMBDA_SCORING_CONFIG = {
    "weights": {
        "keyword": 0.6,
        "vector": 0.4,
        "graph": 0.5
    },
    "normalization": {
        "log_scale_factor": 1.0,
        "rank_weight": 0.3,
        "min_percentile": 5,
        "max_percentile": 95
    },
    "result_limits": {
        "max_results": 30,
        "max_per_source": 50
    },
    "confidence_thresholds": {
        "high": 0.7,
        "medium": 0.4
    },
    "performance": {
        "search_timeout": 25,  # Leave 5s buffer for Lambda
        "max_retries": 2,      # Reduced for Lambda
        "parallel_search": True
    }
}

def get_lambda_config():
    """Get Lambda deployment configuration"""
    return LAMBDA_CONFIG.copy()

def get_lambda_scoring_config():
    """Get Lambda-optimized scoring configuration"""
    return LAMBDA_SCORING_CONFIG.copy()

def validate_lambda_environment():
    """Validate Lambda environment has required dependencies"""
    try:
        import numpy
        import scipy
        import opensearchpy
        import boto3
        import psycopg2
        return True
    except ImportError as e:
        print(f"Missing dependency for Lambda: {e}")
        return False
