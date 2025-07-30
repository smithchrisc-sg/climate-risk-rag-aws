#!/bin/bash
# Simple AWS Lambda Layer Build Script
# Usage: ./build-layer-simple.sh <layer-name> [--deploy] [--profile <profile>]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="default"
REGION="us-east-1"
DEPLOY=false

# Script directory and layers root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYERS_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$LAYERS_ROOT/build"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
Simple AWS Lambda Layer Build Script

USAGE:
    $0 <layer-name> [OPTIONS]

OPTIONS:
    --deploy           Deploy the layer to AWS after building
    --profile PROFILE  AWS profile to use (default: default)
    --help            Show this help message

EXAMPLES:
    $0 database-core-layer
    $0 database-core-layer --deploy --profile solve-global
EOF
}

# Parse arguments
if [[ $# -eq 0 ]]; then
    show_usage
    exit 1
fi

LAYER_NAME="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --deploy)
            DEPLOY=true
            shift
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate layer exists
LAYER_SOURCE="$LAYERS_ROOT/$LAYER_NAME"
if [[ ! -d "$LAYER_SOURCE" ]]; then
    print_error "Layer directory not found: $LAYER_SOURCE"
    exit 1
fi

if [[ ! -d "$LAYER_SOURCE/python" ]]; then
    print_error "Layer must contain a 'python' directory: $LAYER_SOURCE/python"
    exit 1
fi

print_info "Building layer: $LAYER_NAME"
print_info "Source: $LAYER_SOURCE"

# Create build directory
mkdir -p "$BUILD_DIR"
LAYER_BUILD_DIR="$BUILD_DIR/$LAYER_NAME"

# Clean previous build
print_info "Cleaning previous build..."
rm -rf "$LAYER_BUILD_DIR"
rm -f "$BUILD_DIR/${LAYER_NAME}"*.zip

# Copy source to build directory
print_info "Copying source files..."
mkdir -p "$LAYER_BUILD_DIR"
cp -r "$LAYER_SOURCE/python" "$LAYER_BUILD_DIR/"

# Install dependencies if requirements.txt exists
if [[ -f "$LAYER_SOURCE/requirements.txt" ]]; then
    print_info "Installing dependencies from requirements.txt..."
    
    # Check for pip3 first, then pip
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        print_warning "Neither pip nor pip3 found, skipping dependency installation"
        PIP_CMD=""
    fi
    
    if [[ -n "$PIP_CMD" ]]; then
        # Use pre-built Linux wheels for Lambda compatibility
        $PIP_CMD install \
            -r "$LAYER_SOURCE/requirements.txt" \
            -t "$LAYER_BUILD_DIR/python" \
            --platform linux_x86_64 \
            --implementation cp \
            --python-version 3.11 \
            --only-binary=:all: \
            --upgrade \
            --no-deps
        print_success "Dependencies installed using $PIP_CMD with Linux wheels"
    fi
else
    print_info "No requirements.txt found, skipping dependency installation"
fi

# Clean Python cache files
print_info "Cleaning Python cache files..."
find "$LAYER_BUILD_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$LAYER_BUILD_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$LAYER_BUILD_DIR" -name "*.pyo" -delete 2>/dev/null || true
find "$LAYER_BUILD_DIR" -name ".DS_Store" -delete 2>/dev/null || true
find "$LAYER_BUILD_DIR" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Create zip file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_FILE="$BUILD_DIR/${LAYER_NAME}_${TIMESTAMP}.zip"

print_info "Creating zip file: $ZIP_FILE"
cd "$LAYER_BUILD_DIR"
zip -r "$ZIP_FILE" python/ -x \
    "python/__pycache__/*" \
    "python/*/__pycache__/*" \
    "python/*/*/__pycache__/*" \
    "*.pyc" \
    "*.pyo" \
    ".DS_Store" > /dev/null

# Create latest symlink
LATEST_LINK="$BUILD_DIR/${LAYER_NAME}_latest.zip"
rm -f "$LATEST_LINK"
ln -s "$(basename "$ZIP_FILE")" "$LATEST_LINK"

print_success "Layer built successfully: $ZIP_FILE"

# Verify contents
print_info "Verifying zip contents..."
if [[ "$LAYER_NAME" == "database-core-layer" ]]; then
    if unzip -l "$ZIP_FILE" | grep -q "python/utils/DatabaseManager.py"; then
        # Extract and check for required method
        TEMP_DIR=$(mktemp -d)
        unzip -q "$ZIP_FILE" -d "$TEMP_DIR"
        
        if grep -q "def set_processing_status" "$TEMP_DIR/python/utils/DatabaseManager.py"; then
            print_success "DatabaseManager.py contains set_processing_status method"
        else
            print_error "DatabaseManager.py missing set_processing_status method"
            rm -rf "$TEMP_DIR"
            exit 1
        fi
        
        rm -rf "$TEMP_DIR"
    else
        print_error "DatabaseManager.py not found in zip file"
        exit 1
    fi
fi

print_success "Zip contents verified"

# Deploy if requested
if [[ "$DEPLOY" == "true" ]]; then
    print_info "Deploying layer to AWS..."
    
    # Check for required tools
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is required for deployment"
        exit 1
    fi
    
    # Deploy layer
    DESCRIPTION="Built on $(date '+%Y-%m-%d %H:%M:%S') from $(basename "$ZIP_FILE")"
    
    RESULT=$(aws lambda publish-layer-version \
        --layer-name "$LAYER_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --compatible-runtimes python3.11 \
        --description "$DESCRIPTION" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query '{Version:Version,LayerVersionArn:LayerVersionArn}' \
        --output json)
    
    VERSION=$(echo "$RESULT" | jq -r '.Version')
    ARN=$(echo "$RESULT" | jq -r '.LayerVersionArn')
    
    print_success "Layer deployed successfully!"
    print_success "Version: $VERSION"
    print_success "ARN: $ARN"
    
    # Save deployment info
    echo "$RESULT" > "$BUILD_DIR/${LAYER_NAME}_deployment.json"
fi

print_success "Build process completed successfully!"
