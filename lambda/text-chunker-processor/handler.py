#!/usr/bin/env python3
"""
Text Chunker Processor - Entry Point
Clean entry point following gold standard patterns
"""

from src.text_chunker_processor import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
