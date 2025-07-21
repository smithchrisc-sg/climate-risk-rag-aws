#!/usr/bin/env python3
"""
Text Extractor Initiator - Entry Point
Clean entry point following gold standard patterns
"""

from src.text_extractor_initiator import lambda_handler

# Export the handler for Lambda runtime
__all__ = ['lambda_handler']
