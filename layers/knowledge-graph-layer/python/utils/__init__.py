# Knowledge Graph Layer - Core utilities for Neptune/SPARQL operations with NLP-Ontology Integration
# Version: 2.0.0 - NLP-Ontology Integration Extension
# Compatible with: Python 3.11, Neptune, AWS Lambda

# === EXISTING CORE UTILITIES (UNCHANGED) ===
from .KnowledgeGraphManager import KnowledgeGraphManager
from .SPARQLQueryBuilder import SPARQLQueryBuilder
from .URIManager import URIManager
from .OntologyManager import OntologyManager
from .TripleManager import TripleManager
from .BulkLoadManager import BulkLoadManager
from .kg_exceptions import (
    KGConnectionError,
    KGQueryError,
    KGInsertError,
    KGValidationError,
    KGAuthenticationError,
    KGTimeoutError,
    KGDataFormatError
)

# === NEW NLP-ONTOLOGY UTILITIES ===
from .TextNormalizer import TextNormalizer
from .ConfidenceScorer import ConfidenceScorer, ConfidenceFactors
from .EntityAligner import EntityAligner
from .OntologyTermMatcher import OntologyTermMatcher
from .ConceptReconciler import ConceptReconciler
from .NLPKGIntegrator import NLPKGIntegrator

# === FUTURE SEARCH UTILITIES (STUBS) ===
from .SearchQueryBuilder import SearchQueryBuilder
from .ResultFusionManager import ResultFusionManager
from .ConceptExpander import ConceptExpander

__version__ = "2.0.0"
__all__ = [
    # === EXISTING CORE UTILITIES ===
    "KnowledgeGraphManager",
    "SPARQLQueryBuilder", 
    "URIManager",
    "OntologyManager",
    "TripleManager",
    "BulkLoadManager",
    
    # === EXCEPTIONS ===
    "KGConnectionError",
    "KGQueryError", 
    "KGInsertError",
    "KGValidationError",
    "KGAuthenticationError",
    "KGTimeoutError",
    "KGDataFormatError",
    
    # === NEW NLP-ONTOLOGY UTILITIES ===
    "TextNormalizer",
    "ConfidenceScorer",
    "ConfidenceFactors",
    "EntityAligner",
    "OntologyTermMatcher", 
    "ConceptReconciler",
    "NLPKGIntegrator",
    
    # === FUTURE SEARCH UTILITIES ===
    "SearchQueryBuilder",
    "ResultFusionManager",
    "ConceptExpander"
]

# === BACKWARD COMPATIBILITY GUARANTEE ===
# All existing imports and method signatures remain unchanged
# New functionality is purely additive and does not affect existing code
