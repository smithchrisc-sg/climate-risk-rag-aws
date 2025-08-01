# Knowledge Graph Layer - Core utilities for Neptune/SPARQL operations with Multi-Ontology Support
# Version: 2.1.0 - Multi-Ontology Integration Extension
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

# === MULTI-ONTOLOGY SUPPORT (NEW) ===
from .MultiOntologyManager import MultiOntologyManager, OntologyConfig, OntologyScope, ConceptMatch

# === NLP-ONTOLOGY UTILITIES ===
from .TextNormalizer import TextNormalizer
from .ConfidenceScorer import ConfidenceScorer, ConfidenceFactors
from .EntityAligner import EntityAligner
from .OntologyTermMatcher import OntologyTermMatcher
from .ConceptReconciler import ConceptReconciler
from .NLPKGIntegrator import NLPKGIntegrator

# === ENHANCED NLP INTEGRATION (NEW) ===
from .EnhancedNLPKGIntegrator import EnhancedNLPKGIntegrator, EntityLinkingResult, DocumentContext

# === SEARCH UTILITIES ===
from .SearchQueryBuilder import SearchQueryBuilder
from .ResultFusionManager import ResultFusionManager
from .ConceptExpander import ConceptExpander

__version__ = "2.1.0"
__multi_ontology_support__ = True

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
    
    # === MULTI-ONTOLOGY SUPPORT ===
    "MultiOntologyManager",
    "OntologyConfig", 
    "OntologyScope",
    "ConceptMatch",
    
    # === NLP-ONTOLOGY UTILITIES ===
    "TextNormalizer",
    "ConfidenceScorer",
    "ConfidenceFactors",
    "EntityAligner",
    "OntologyTermMatcher", 
    "ConceptReconciler",
    "NLPKGIntegrator",
    
    # === ENHANCED NLP INTEGRATION ===
    "EnhancedNLPKGIntegrator",
    "EntityLinkingResult",
    "DocumentContext",
    
    # === SEARCH UTILITIES ===
    "SearchQueryBuilder",
    "ResultFusionManager",
    "ConceptExpander"
]

# === FEATURE DETECTION ===
def has_multi_ontology_support():
    """Check if multi-ontology features are available"""
    return True

def get_supported_ontology_scopes():
    """Get list of supported ontology scopes"""
    return [scope.value for scope in OntologyScope]

# === CONFIGURATION DEFAULTS ===
DEFAULT_MULTI_ONTOLOGY_CONFIG_PATH = "ontology/multi-ontology-config.json"
DEFAULT_SINGLE_ONTOLOGY_FALLBACK = True

# === BACKWARD COMPATIBILITY GUARANTEE ===
# All existing imports and method signatures remain unchanged
# New functionality is purely additive and does not affect existing code
# Legacy aliases for backward compatibility
OntologyManagerLegacy = OntologyManager
NLPKGIntegratorLegacy = NLPKGIntegrator
