#!/bin/bash
# Docker-based Lambda Layer Build Script
# This builds dependencies using Amazon Linux to ensure compatibility

set -e

LAYER_NAME="$1"
if [[ -z "$LAYER_NAME" ]]; then
    echo "Usage: $0 <layer-name>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYERS_ROOT="$(dirname "$SCRIPT_DIR")"
LAYER_SOURCE="$LAYERS_ROOT/$LAYER_NAME"
BUILD_DIR="$LAYERS_ROOT/build"

echo "Building $LAYER_NAME using Docker (Amazon Linux)..."

# Create build directory
mkdir -p "$BUILD_DIR"

# Create Dockerfile for building dependencies
cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum update -y && yum install -y gcc postgresql-devel

# Set working directory
WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt -t /build/python --no-deps

# Clean up
RUN find /build -name "*.pyc" -delete && \
    find /build -name "__pycache__" -type d -exec rm -rf {} + || true

CMD ["echo", "Dependencies built successfully"]
EOF

# Copy requirements.txt to build directory
cp "$LAYER_SOURCE/requirements.txt" "$BUILD_DIR/"

# Build dependencies using Docker
echo "Building dependencies with Docker..."
docker build -t lambda-layer-builder "$BUILD_DIR"

# Extract built dependencies
CONTAINER_ID=$(docker create lambda-layer-builder)
docker cp "$CONTAINER_ID:/build/python" "$BUILD_DIR/"
docker rm "$CONTAINER_ID"

# Copy our source code
echo "Copying source code..."
cp -r "$LAYER_SOURCE/python/"* "$BUILD_DIR/python/"

# Create zip file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_FILE="$BUILD_DIR/${LAYER_NAME}_docker_${TIMESTAMP}.zip"

echo "Creating zip file..."
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" python/ > /dev/null

echo "Layer built successfully: $ZIP_FILE"

# Clean up
rm -rf "$BUILD_DIR/python" "$BUILD_DIR/Dockerfile" "$BUILD_DIR/requirements.txt"

echo "Docker-based build complete!"
EOF
