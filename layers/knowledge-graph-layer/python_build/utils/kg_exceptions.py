#!/usr/bin/env python3
"""
Knowledge Graph Exceptions
Custom exceptions for knowledge graph operations
"""

class KGBaseException(Exception):
    """Base exception for all knowledge graph operations"""
    pass

class KGConnectionError(KGBaseException):
    """Raised when Neptune connection fails"""
    pass

class KGQueryError(KGBaseException):
    """Raised when SPARQL query execution fails"""
    pass

class KGInsertError(KGBaseException):
    """Raised when triple insertion fails"""
    pass

class KGValidationError(KGBaseException):
    """Raised when data validation fails"""
    pass

class KGAuthenticationError(KGBaseException):
    """Raised when Neptune authentication fails"""
    pass

class KGTimeoutError(KGBaseException):
    """Raised when operations timeout"""
    pass

class KGDataFormatError(KGBaseException):
    """Raised when data format is invalid"""
    pass
