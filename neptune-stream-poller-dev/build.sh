#!/bin/bash

# Build script for Neptune Stream Poller with Ontology Filtering
set -e

echo "Building Neptune Stream Poller with Ontology Filtering..."

# Clean previous builds
rm -f neptune-stream-poller-with-filtering.zip
rm -f neptune-streams-layer-with-filtering.zip

# Create function package (just the handler files)
echo "Creating function package..."
zip -r neptune-stream-poller-with-filtering.zip neptune_to_es/ -x "*.pyc" "__pycache__/*"

# Create layer package (all the dependencies and core files)
echo "Creating layer package..."
mkdir -p python
cp -r *.py python/
cp -r aggregator python/ 2>/dev/null || true
cp -r bin python/ 2>/dev/null || true
cp -r cachetools* python/ 2>/dev/null || true
cp -r certifi* python/ 2>/dev/null || true
cp -r chardet* python/ 2>/dev/null || true
cp -r charset_normalizer* python/ 2>/dev/null || true
cp -r idna* python/ 2>/dev/null || true
cp -r isodate* python/ 2>/dev/null || true
cp -r opensearch* python/ 2>/dev/null || true
cp -r packaging* python/ 2>/dev/null || true
cp -r pkg_resources python/ 2>/dev/null || true
cp -r pyparsing* python/ 2>/dev/null || true
cp -r rdflib* python/ 2>/dev/null || true
cp -r requests* python/ 2>/dev/null || true
cp -r retrying* python/ 2>/dev/null || true
cp -r setuptools* python/ 2>/dev/null || true
cp -r six* python/ 2>/dev/null || true
cp -r urllib3* python/ 2>/dev/null || true
cp -r _distutils_hack python/ 2>/dev/null || true
cp *.pth python/ 2>/dev/null || true

zip -r neptune-streams-layer-with-filtering.zip python/

# Clean up
rm -rf python/

echo "Build complete!"
echo "Function package: neptune-stream-poller-with-filtering.zip"
echo "Layer package: neptune-streams-layer-with-filtering.zip"
