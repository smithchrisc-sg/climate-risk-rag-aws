#!/usr/bin/env python3
"""
Keyword Indexer Initiator - Entry Point
Clean entry point following gold standard patterns
"""

from src.keyword_indexer_initiator import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
