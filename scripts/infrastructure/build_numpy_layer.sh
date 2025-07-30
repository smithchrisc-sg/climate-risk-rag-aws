#!/bin/bash

# Build numpy layer for AWS Lambda using Docker
# This ensures the numpy library is compiled for Linux x86_64

set -e

echo "🐳 Building numpy layer for AWS Lambda (Linux x86_64)..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "📁 Working directory: $TEMP_DIR"

# Create the layer structure
mkdir -p "$TEMP_DIR/python"

# Use Docker to install numpy in a Linux environment that matches Lambda
docker run --rm -v "$TEMP_DIR":/var/task --entrypoint="" public.ecr.aws/lambda/python:3.11 /bin/bash -c "
    pip install numpy==1.24.0 -t /var/task/python/
    # Clean up unnecessary files to reduce layer size
    find /var/task/python -name '*.pyc' -delete
    find /var/task/python -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find /var/task/python -name '*.dist-info' -type d -exec rm -rf {} + 2>/dev/null || true
"

# Create the zip file
cd "$TEMP_DIR"
zip -r numpy-layer-linux.zip python/

# Move to project directory
mv numpy-layer-linux.zip /Users/chris/climate-risk-rag-aws/

echo "✅ Layer built successfully: numpy-layer-linux.zip"
echo "📊 Layer size: $(du -h /Users/chris/climate-risk-rag-aws/numpy-layer-linux.zip | cut -f1)"

# Clean up
rm -rf "$TEMP_DIR"

echo "🚀 Ready to deploy with AWS CLI:"
echo "aws lambda publish-layer-version --layer-name numpy-dependencies-linux --zip-file fileb://numpy-layer-linux.zip --compatible-runtimes python3.11 --description 'NumPy compiled for Linux x86_64 Lambda environment'"
