#!/usr/bin/env python3
"""
Keyword Indexer Worker - Entry Point
Clean entry point following gold standard patterns
"""

from src.keyword_indexer_worker import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
