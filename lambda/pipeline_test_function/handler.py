#!/usr/bin/env python3
"""
Pipeline Test Function - Entry Point
Clean entry point following gold standard patterns
"""

from src.pipeline_test_handler import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
