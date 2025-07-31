#!/bin/bash
# Build script for Knowledge Graph Layer v2.0.0 - NLP-Ontology Integration Extension
# CRITICAL: This maintains backward compatibility with existing Lambda functions

set -e

LAYER_NAME="knowledge-graph-layer"
LAYER_VERSION="2.0.0"
BUILD_DIR="build"
PYTHON_DIR="python"

echo "🔨 Building Knowledge Graph Layer v${LAYER_VERSION} - NLP-Ontology Integration"
echo "🛡️  BACKWARD COMPATIBILITY: All existing method signatures preserved"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Create build directory
mkdir -p "$BUILD_DIR/$PYTHON_DIR"

echo "📦 Installing dependencies (including new NLP libraries)..."
echo "   - Installing existing dependencies..."
pip3 install rdflib==7.0.0 requests==2.31.0 requests-aws4auth==1.2.3 boto3==1.34.0 botocore==1.34.0 charset-normalizer==3.3.2 -t "$BUILD_DIR/$PYTHON_DIR"

echo "   - Installing NLP processing dependencies..."
pip3 install fuzzywuzzy==0.18.0 python-Levenshtein==0.21.1 nltk==3.8.1 -t "$BUILD_DIR/$PYTHON_DIR"

echo "   - Installing semantic similarity dependencies..."
pip3 install sentence-transformers==2.2.2 numpy==1.24.3 scipy==1.10.1 scikit-learn==1.3.0 -t "$BUILD_DIR/$PYTHON_DIR"

echo "   - Installing pattern matching dependencies..."
pip3 install ahocorasick-rs==0.20.0 -t "$BUILD_DIR/$PYTHON_DIR"

echo "   - Installing PyTorch (CPU-only for Lambda)..."
pip3 install torch==2.0.1+cpu torchvision==0.15.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu -t "$BUILD_DIR/$PYTHON_DIR"

echo "   - Installing additional ML dependencies..."
pip3 install tokenizers==0.13.3 transformers==4.30.2 pandas==2.0.3 -t "$BUILD_DIR/$PYTHON_DIR"

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

if [ ! -f "$BUILD_DIR/$PYTHON_DIR/utils/OntologyTermMatcher.py" ]; then
    echo "❌ ERROR: Missing OntologyTermMatcher.py"
    exit 1
fi

echo "   - Checking __init__.py version..."
if ! grep -q "2.0.0" "$BUILD_DIR/$PYTHON_DIR/utils/__init__.py"; then
    echo "❌ ERROR: __init__.py not updated to v2.0.0"
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
echo "🔧 NEW FUNCTIONALITY AVAILABLE:"
echo "   - EntityAligner: Comprehend entities → ontology concepts"
echo "   - OntologyTermMatcher: Ontology concepts → text mentions"
echo "   - ConceptReconciler: Bidirectional result merging"
echo "   - NLPKGIntegrator: Final RDF integration"
echo "   - TextNormalizer: Advanced text processing"
echo "   - ConfidenceScorer: Multi-factor confidence calculation"
echo ""
echo "⚠️  TESTING CHECKLIST:"
echo "   □ Test document-structure-kg-processor with new layer"
echo "   □ Verify URI consistency between old and new functionality"
echo "   □ Test new NLP Lambda functions"
echo "   □ Validate RDF output compatibility"
echo "   □ Check memory usage and cold start times"
