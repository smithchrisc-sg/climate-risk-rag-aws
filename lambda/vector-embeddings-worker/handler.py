#!/usr/bin/env python3
"""
Vector Embeddings Worker - Entry Point
Clean entry point following gold standard patterns
"""

from src.vector_embeddings_worker import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
