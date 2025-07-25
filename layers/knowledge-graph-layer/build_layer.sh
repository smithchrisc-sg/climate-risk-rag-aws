#!/bin/bash
# Build script for Knowledge Graph Layer
# Version: 1.0.0

set -e

LAYER_NAME="knowledge-graph-layer"
LAYER_VERSION="1.0.1"
BUILD_DIR="build"
PYTHON_DIR="python"

echo "🔨 Building Knowledge Graph Layer v${LAYER_VERSION}"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

# Create build directory
mkdir -p "$BUILD_DIR/$PYTHON_DIR"

echo "📦 Installing dependencies..."
pip3 install -r requirements.txt -t "$BUILD_DIR/$PYTHON_DIR"

echo "📁 Copying layer code..."
cp -r python/* "$BUILD_DIR/$PYTHON_DIR/"

echo "🗜️ Creating layer package..."
cd "$BUILD_DIR"
zip -r "../${LAYER_NAME}-v${LAYER_VERSION}.zip" .
cd ..

echo "🧹 Cleaning build directory..."
rm -rf "$BUILD_DIR"

echo "✅ Layer package created: ${LAYER_NAME}-v${LAYER_VERSION}.zip"
echo "📊 Package size:"
ls -lh "${LAYER_NAME}-v${LAYER_VERSION}.zip"

echo ""
echo "🚀 To deploy this layer:"
echo "1. Upload ${LAYER_NAME}-v${LAYER_VERSION}.zip to AWS Lambda Layers"
echo "2. Update CDK stack to reference new layer version"
echo "3. Deploy Lambda functions with updated layer"
echo ""
echo "⚠️  Remember to test all Lambda functions after layer update!"
