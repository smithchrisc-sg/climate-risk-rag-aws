"""
Climate Risk RAG System - Core Utilities
AWS-optimized shared utilities for Lambda layers
"""

from .DatabaseManager import DatabaseManager
from .DocumentIDManager import DocumentIDManager

try:
    from .ProvenanceTracker import ProvenanceTracker
    from .TextCleaner import TextCleaner
    from .NERAnalyzer import NERAnalyzer
except ImportError:
    # These will be added in subsequent phases
    pass

__all__ = [
    'DatabaseManager',
    'DocumentIDManager',
    'ProvenanceTracker',
    'TextCleaner', 
    'NERAnalyzer'
]

__version__ = '1.0.0'
