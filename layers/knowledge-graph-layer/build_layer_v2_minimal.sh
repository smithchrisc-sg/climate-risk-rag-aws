#!/bin/bash
# Build script for Knowledge Graph Layer v2.0.0 - Minimal Version for Testing
# CRITICAL: This maintains backward compatibility with existing Lambda functions
# Uses only existing dependencies + basic text processing

set -e

LAYER_NAME="knowledge-graph-layer"
LAYER_VERSION="2.0.0-minimal"
BUILD_DIR="build"
PYTHON_DIR="python"

echo "🔨 Building Knowledge Graph Layer v${LAYER_VERSION} - Minimal Version for Testing"
echo "🛡️  BACKWARD COMPATIBILITY: All existing method signatures preserved"
echo "📦 Using only existing dependencies + basic text processing"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Create build directory
mkdir -p "$BUILD_DIR/$PYTHON_DIR"

echo "📦 Installing existing dependencies only..."
pip3 install rdflib==7.0.0 requests==2.31.0 requests-aws4auth==1.2.3 boto3==1.34.0 botocore==1.34.0 charset-normalizer==3.3.2 -t "$BUILD_DIR/$PYTHON_DIR"

echo "📁 Copying layer code..."
cp -r python/* "$BUILD_DIR/$PYTHON_DIR/"

echo "🔧 Creating minimal implementations for NLP utilities..."
# Create minimal implementations that don't require external dependencies
python3 << 'EOF'
import os

# Create minimal TextNormalizer that uses only standard library
text_normalizer_content = '''#!/usr/bin/env python3
"""
Text Normalizer - Minimal implementation using only standard library
Provides basic text normalization without external dependencies
"""
import logging
import re
import string
from typing import Dict, List, Set, Optional
from collections import defaultdict

class TextNormalizer:
    """
    Minimal text normalization using only standard library
    Provides basic functionality for backward compatibility testing
    """
    
    def __init__(self, download_nltk_data: bool = False):
        """Initialize with minimal configuration"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Basic stopwords (no NLTK required)
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        self.logger.debug("TextNormalizer initialized (minimal version)")
    
    def normalize_entity_text(self, text: str, strategies: List[str] = None) -> Dict[str, str]:
        """Basic text normalization using standard library only"""
        if strategies is None:
            strategies = ['basic']
        
        results = {'original': text}
        
        if 'basic' in strategies:
            results['basic'] = self._basic_normalization(text)
        
        # For other strategies, just return basic normalization
        for strategy in strategies:
            if strategy not in results:
                results[strategy] = results['basic']
        
        return results
    
    def _basic_normalization(self, text: str) -> str:
        """Basic text normalization using standard library"""
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\\s+', ' ', normalized).strip()
        
        # Remove punctuation except hyphens and apostrophes
        normalized = re.sub(r'[^\\w\\s\\'-]', ' ', normalized)
        
        # Clean up extra spaces
        normalized = re.sub(r'\\s+', ' ', normalized).strip()
        
        return normalized
    
    def calculate_text_similarity(self, text1: str, text2: str, method: str = 'basic') -> float:
        """Basic text similarity using word overlap"""
        norm1 = self._basic_normalization(text1)
        norm2 = self._basic_normalization(text2)
        
        if not norm1 or not norm2:
            return 0.0
        
        if norm1 == norm2:
            return 1.0
        
        # Calculate Jaccard similarity on word sets
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def extract_key_terms(self, text: str, min_length: int = 3, max_terms: int = 10) -> List[str]:
        """Extract key terms using basic processing"""
        normalized = self._basic_normalization(text)
        
        tokens = normalized.split()
        
        # Filter tokens
        key_terms = [
            token for token in tokens 
            if (len(token) >= min_length and 
                token not in self.stopwords and
                token.isalpha())
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms[:max_terms]
    
    def get_normalization_stats(self) -> Dict[str, int]:
        """Get basic statistics"""
        return {
            'stopwords': len(self.stopwords),
            'version': 'minimal'
        }
'''

with open('build/python/utils/TextNormalizer.py', 'w') as f:
    f.write(text_normalizer_content)

print("✅ Created minimal TextNormalizer")

# Create minimal ConfidenceScorer
confidence_scorer_content = '''#!/usr/bin/env python3
"""
Confidence Scorer - Minimal implementation for backward compatibility testing
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

@dataclass
class ConfidenceFactors:
    """Minimal confidence factors"""
    text_similarity: float = 0.0
    overall_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'text_similarity': self.text_similarity,
            'overall_confidence': self.overall_confidence
        }

class ConfidenceScorer:
    """Minimal confidence scoring for testing"""
    
    def __init__(self, min_confidence: float = 0.5, track_evidence: bool = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.min_confidence = min_confidence
        self.track_evidence = track_evidence
        
    def calculate_alignment_confidence(self, entity_text: str, concept_label: str, 
                                     concept_metadata: Dict[str, Any], context_text: str = "",
                                     entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[float, ConfidenceFactors]:
        """Basic confidence calculation"""
        # Simple text similarity
        similarity = self._basic_similarity(entity_text, concept_label)
        confidence = similarity
        
        factors = ConfidenceFactors(
            text_similarity=similarity,
            overall_confidence=confidence
        )
        
        return confidence, factors
    
    def _basic_similarity(self, text1: str, text2: str) -> float:
        """Basic similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def get_scorer_stats(self) -> Dict[str, Any]:
        return {
            'min_confidence': self.min_confidence,
            'version': 'minimal'
        }
'''

with open('build/python/utils/ConfidenceScorer.py', 'w') as f:
    f.write(confidence_scorer_content)

print("✅ Created minimal ConfidenceScorer")

# Update __init__.py to only export working components
init_content = '''# Knowledge Graph Layer - Core utilities for Neptune/SPARQL operations with NLP-Ontology Integration
# Version: 2.0.0-minimal - Minimal version for backward compatibility testing
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

# === MINIMAL NLP UTILITIES (FOR TESTING) ===
from .TextNormalizer import TextNormalizer
from .ConfidenceScorer import ConfidenceScorer, ConfidenceFactors

__version__ = "2.0.0-minimal"
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
    
    # === MINIMAL NLP UTILITIES ===
    "TextNormalizer",
    "ConfidenceScorer",
    "ConfidenceFactors"
]

# === BACKWARD COMPATIBILITY GUARANTEE ===
# All existing imports and method signatures remain unchanged
# New functionality is purely additive and does not affect existing code
'''

with open('build/python/utils/__init__.py', 'w') as f:
    f.write(init_content)

print("✅ Updated __init__.py for minimal version")
print("🔧 Minimal implementations created successfully")
EOF

echo "🔍 Validating layer structure..."
echo "   - Checking existing utilities..."
if [ ! -f "$BUILD_DIR/$PYTHON_DIR/utils/KnowledgeGraphManager.py" ]; then
    echo "❌ ERROR: Missing KnowledgeGraphManager.py"
    exit 1
fi

echo "   - Checking minimal NLP utilities..."
if [ ! -f "$BUILD_DIR/$PYTHON_DIR/utils/TextNormalizer.py" ]; then
    echo "❌ ERROR: Missing TextNormalizer.py"
    exit 1
fi

echo "   - Checking __init__.py version..."
if ! grep -q "2.0.0-minimal" "$BUILD_DIR/$PYTHON_DIR/utils/__init__.py"; then
    echo "❌ ERROR: __init__.py not updated to v2.0.0-minimal"
    exit 1
fi

echo "🗜️ Creating layer package..."
cd "$BUILD_DIR"
zip -r "../${LAYER_NAME}-v${LAYER_VERSION}.zip" .
cd ..

echo "🧹 Cleaning build directory..."
rm -rf "$BUILD_DIR"

echo "✅ Layer package created: ${LAYER_NAME}-v${LAYER_VERSION}.zip"
echo "📊 Package size:"
ls -lh "${LAYER_NAME}-v${LAYER_VERSION}.zip"

# Calculate size in MB
SIZE_BYTES=$(stat -f%z "${LAYER_NAME}-v${LAYER_VERSION}.zip" 2>/dev/null || stat -c%s "${LAYER_NAME}-v${LAYER_VERSION}.zip")
SIZE_MB=$((SIZE_BYTES / 1024 / 1024))

echo "📏 Package size: ${SIZE_MB}MB (Lambda layer limit: 250MB unzipped)"

echo ""
echo "🚀 MINIMAL VERSION FOR TESTING:"
echo "   - Contains all existing utilities (unchanged)"
echo "   - Adds minimal TextNormalizer and ConfidenceScorer"
echo "   - No external NLP dependencies"
echo "   - Perfect for testing backward compatibility"
echo ""
echo "🛡️  BACKWARD COMPATIBILITY GUARANTEE:"
echo "   - All existing method signatures unchanged"
echo "   - All existing imports work without modification"
echo "   - document-structure-kg-processor should work unchanged"
echo ""
echo "⚠️  TESTING CHECKLIST:"
echo "   □ Test document-structure-kg-processor with new layer"
echo "   □ Verify URI consistency between old and new functionality"
echo "   □ Test basic import of new utilities"
echo "   □ Validate RDF output compatibility"
echo "   □ Check memory usage and cold start times"
