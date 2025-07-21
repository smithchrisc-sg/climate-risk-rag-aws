#!/usr/bin/env python3
"""
Vector Embeddings Initiator - Entry Point
Clean entry point following gold standard patterns
"""

from src.vector_embeddings_initiator import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
