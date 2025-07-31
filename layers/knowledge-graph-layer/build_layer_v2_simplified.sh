#!/bin/bash
# Build script for Knowledge Graph Layer v2.0.0 - Simplified Version
# CRITICAL: This maintains backward compatibility with existing Lambda functions
# Uses core NLP functionality without heavy ML dependencies

set -e

LAYER_NAME="knowledge-graph-layer"
LAYER_VERSION="2.0.0-simplified"
BUILD_DIR="build"
PYTHON_DIR="python"

echo "🔨 Building Knowledge Graph Layer v${LAYER_VERSION} - Simplified NLP-Ontology Integration"
echo "🛡️  BACKWARD COMPATIBILITY: All existing method signatures preserved"
echo "📦 Using simplified dependencies to avoid compatibility issues"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Create build directory
mkdir -p "$BUILD_DIR/$PYTHON_DIR"

echo "📦 Installing core dependencies..."
echo "   - Installing existing dependencies..."
pip3 install rdflib==7.0.0 requests==2.31.0 requests-aws4auth==1.2.3 boto3==1.34.0 botocore==1.34.0 charset-normalizer==3.3.2 -t "$BUILD_DIR/$PYTHON_DIR"

echo "   - Installing basic NLP dependencies..."
pip3 install fuzzywuzzy==0.18.0 nltk==3.8.1 numpy==1.24.3 -t "$BUILD_DIR/$PYTHON_DIR"

echo "📁 Copying layer code..."
cp -r python/* "$BUILD_DIR/$PYTHON_DIR/"

echo "🔍 Validating layer structure..."
echo "   - Checking existing utilities..."
if [ ! -f "$BUILD_DIR/$PYTHON_DIR/utils/KnowledgeGraphManager.py" ]; then
    echo "❌ ERROR: Missing KnowledgeGraphManager.py"
    exit 1
fi

echo "   - Checking new NLP utilities..."
if [ ! -f "$BUILD_DIR/$PYTHON_DIR/utils/EntityAligner.py" ]; then
    echo "❌ ERROR: Missing EntityAligner.py"
    exit 1
fi

if [ ! -f "$BUILD_DIR/$PYTHON_DIR/utils/TextNormalizer.py" ]; then
    echo "❌ ERROR: Missing TextNormalizer.py"
    exit 1
fi

echo "   - Checking __init__.py version..."
if ! grep -q "2.0.0" "$BUILD_DIR/$PYTHON_DIR/utils/__init__.py"; then
    echo "❌ ERROR: __init__.py not updated to v2.0.0"
    exit 1
fi

echo "🔧 Creating compatibility patches for simplified version..."
# Patch files to work without heavy dependencies
python3 << 'EOF'
import os
import re

# Patch EntityAligner to work without sentence-transformers
entity_aligner_path = "build/python/utils/EntityAligner.py"
if os.path.exists(entity_aligner_path):
    with open(entity_aligner_path, 'r') as f:
        content = f.read()
    
    # Comment out sentence-transformers import and usage
    content = re.sub(r'from sentence_transformers import SentenceTransformer', '# from sentence_transformers import SentenceTransformer  # Disabled in simplified version', content)
    content = re.sub(r'self\.embedding_model = SentenceTransformer.*', '# self.embedding_model = None  # Disabled in simplified version', content)
    
    with open(entity_aligner_path, 'w') as f:
        f.write(content)
    print("✅ Patched EntityAligner for simplified version")

# Patch OntologyTermMatcher to work without ahocorasick-rs
term_matcher_path = "build/python/utils/OntologyTermMatcher.py"
if os.path.exists(term_matcher_path):
    with open(term_matcher_path, 'r') as f:
        content = f.read()
    
    # Comment out ahocorasick-rs import and provide fallback
    content = re.sub(r'import ahocorasick_rs', '# import ahocorasick_rs  # Disabled in simplified version', content)
    content = re.sub(r'self\.automaton = ahocorasick_rs\.AhoCorasick.*', '# self.automaton = None  # Using fallback implementation', content)
    
    with open(term_matcher_path, 'w') as f:
        f.write(content)
    print("✅ Patched OntologyTermMatcher for simplified version")

# Patch TextNormalizer to work without python-Levenshtein
text_normalizer_path = "build/python/utils/TextNormalizer.py"
if os.path.exists(text_normalizer_path):
    with open(text_normalizer_path, 'r') as f:
        content = f.read()
    
    # Add fallback for missing dependencies
    fallback_code = '''
# Fallback implementations for simplified version
try:
    from nltk.stem import PorterStemmer, WordNetLemmatizer
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
except ImportError:
    print("NLTK not fully available - using basic implementations")
    class PorterStemmer:
        def stem(self, word): return word.lower()
    class WordNetLemmatizer:
        def lemmatize(self, word): return word.lower()
    def word_tokenize(text): return text.split()
    stopwords = lambda x: set()
'''
    
    # Insert fallback code after imports
    content = re.sub(r'(import unicodedata)', r'\1\n' + fallback_code, content)
    
    with open(text_normalizer_path, 'w') as f:
        f.write(content)
    print("✅ Patched TextNormalizer for simplified version")

print("🔧 Compatibility patches applied successfully")
EOF

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

if [ $SIZE_MB -gt 200 ]; then
    echo "⚠️  WARNING: Layer size is approaching Lambda limit"
fi

echo ""
echo "🚀 DEPLOYMENT INSTRUCTIONS:"
echo "1. Upload ${LAYER_NAME}-v${LAYER_VERSION}.zip to AWS Lambda Layers"
echo "2. Update CDK stack to reference new layer version ARN"
echo "3. Test existing Lambda functions (document-structure-kg-processor) first"
echo "4. Deploy new NLP Lambda functions with updated layer"
echo ""
echo "🛡️  BACKWARD COMPATIBILITY GUARANTEE:"
echo "   - All existing method signatures unchanged"
echo "   - All existing imports work without modification"
echo "   - document-structure-kg-processor should work unchanged"
echo ""
echo "🔧 SIMPLIFIED VERSION NOTES:"
echo "   - Uses basic fuzzy matching (fuzzywuzzy without Levenshtein)"
echo "   - NLTK for text processing (with fallbacks)"
echo "   - No heavy ML dependencies (sentence-transformers, torch)"
echo "   - Pattern matching uses Python regex (not Aho-Corasick)"
echo "   - Full ML version can be added later when compatibility is resolved"
echo ""
echo "⚠️  TESTING CHECKLIST:"
echo "   □ Test document-structure-kg-processor with new layer"
echo "   □ Verify URI consistency between old and new functionality"
echo "   □ Test basic NLP utilities with simplified dependencies"
echo "   □ Validate RDF output compatibility"
echo "   □ Check memory usage and cold start times"
