#!/bin/bash
# AWS Lambda Layer Build Script

set -e

LAYERS_DIR="$(dirname "$0")/.."
BUILD_DIR="$LAYERS_DIR/build"

echo "🏗️ Building AWS Lambda Layers"
echo "=============================="

# Clean build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Build database-core-layer
echo ""
echo "📋 Building database-core-layer..."
LAYER_NAME="database-core-layer"
LAYER_SOURCE="$LAYERS_DIR/$LAYER_NAME"
LAYER_BUILD="$BUILD_DIR/$LAYER_NAME"

mkdir -p "$LAYER_BUILD"
cp -r "$LAYER_SOURCE/python" "$LAYER_BUILD/"

# Create layer zip
cd "$LAYER_BUILD"
zip -r "../$LAYER_NAME.zip" python/
echo "✅ $LAYER_NAME.zip created"

echo ""
echo "🎉 Layer built successfully!"
echo "📁 Build artifacts in: $BUILD_DIR"
