#!/bin/bash
# AWS Lambda Layer Build Script - Best Practices
# Usage: ./build-layer.sh <layer-name> [options]
# Example: ./build-layer.sh database-core-layer --deploy --profile solve-global

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
FORCE=false
COMPATIBLE_RUNTIMES="python3.11"
DESCRIPTION=""

# Script directory and layers root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYERS_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$LAYERS_ROOT/build"

# Function to print colored output
print_status() {
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

# Function to show usage
show_usage() {
    cat << EOF
AWS Lambda Layer Build Script

USAGE:
    $0 <layer-name> [OPTIONS]

ARGUMENTS:
    layer-name          Name of the layer directory to build

OPTIONS:
    --deploy           Deploy the layer to AWS after building
    --profile PROFILE  AWS profile to use (default: default)
    --region REGION    AWS region (default: us-east-1)
    --force           Force rebuild even if layer exists
    --runtime RUNTIME  Compatible runtime (default: python3.11)
    --description DESC Layer description for AWS
    --help            Show this help message

EXAMPLES:
    # Build layer only
    $0 database-core-layer
    
    # Build and deploy with custom profile
    $0 database-core-layer --deploy --profile solve-global
    
    # Build with custom description
    $0 database-core-layer --description "Database utilities v2.1"

LAYER STRUCTURE:
    layers/
    ├── <layer-name>/
    │   ├── python/          # Python code and dependencies
    │   │   ├── utils/       # Your modules
    │   │   └── ...
    │   └── requirements.txt # Optional: dependencies to install
    └── scripts/
        └── build-layer.sh   # This script

EOF
}

# Function to validate layer structure
validate_layer_structure() {
    local layer_path="$1"
    
    if [[ ! -d "$layer_path" ]]; then
        print_error "Layer directory not found: $layer_path"
        return 1
    fi
    
    if [[ ! -d "$layer_path/python" ]]; then
        print_error "Layer must contain a 'python' directory: $layer_path/python"
        return 1
    fi
    
    print_success "Layer structure validated"
    return 0
}

# Function to clean build artifacts
clean_build() {
    local layer_name="$1"
    local layer_build_dir="$BUILD_DIR/$layer_name"
    
    print_status "Cleaning previous build artifacts..."
    
    # Remove build directory
    if [[ -d "$layer_build_dir" ]]; then
        rm -rf "$layer_build_dir"
    fi
    
    # Remove old zip files
    find "$BUILD_DIR" -name "${layer_name}*.zip" -delete 2>/dev/null || true
    
    print_success "Build artifacts cleaned"
}

# Function to prepare build environment
prepare_build() {
    local layer_name="$1"
    local layer_source="$2"
    local layer_build_dir="$BUILD_DIR/$layer_name"
    
    print_status "Preparing build environment..."
    
    # Create build directory
    mkdir -p "$layer_build_dir"
    
    # Copy python directory
    cp -r "$layer_source/python" "$layer_build_dir/"
    
    # Clean Python cache files
    find "$layer_build_dir" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$layer_build_dir" -name "*.pyc" -delete 2>/dev/null || true
    find "$layer_build_dir" -name "*.pyo" -delete 2>/dev/null || true
    find "$layer_build_dir" -name ".DS_Store" -delete 2>/dev/null || true
    
    print_success "Build environment prepared"
}

# Function to install dependencies
install_dependencies() {
    local layer_source="$1"
    local layer_build_dir="$2"
    
    local requirements_file="$layer_source/requirements.txt"
    
    if [[ -f "$requirements_file" ]]; then
        print_status "Installing dependencies from requirements.txt..."
        
        # Check if pip is available
        if ! command -v pip &> /dev/null; then
            print_warning "pip not found, skipping dependency installation"
            return 0
        fi
        
        pip install -r "$requirements_file" -t "$layer_build_dir/python" --no-deps --upgrade
        
        # Clean up pip artifacts
        find "$layer_build_dir" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$layer_build_dir" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        
        print_success "Dependencies installed"
    else
        print_status "No requirements.txt found, skipping dependency installation"
    fi
}

# Function to create layer zip
create_layer_zip() {
    local layer_name="$1"
    local layer_build_dir="$BUILD_DIR/$layer_name"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local zip_file="$BUILD_DIR/${layer_name}_${timestamp}.zip"
    
    print_status "Creating layer zip file..."
    
    cd "$layer_build_dir"
    zip -r "$zip_file" python/ -x \
        "python/__pycache__/*" \
        "python/*/__pycache__/*" \
        "python/*/*/__pycache__/*" \
        "*.pyc" \
        "*.pyo" \
        ".DS_Store"
    
    # Create a symlink to latest
    local latest_link="$BUILD_DIR/${layer_name}_latest.zip"
    rm -f "$latest_link"
    ln -s "$(basename "$zip_file")" "$latest_link"
    
    echo "$zip_file"
}

# Function to verify zip contents
verify_zip_contents() {
    local zip_file="$1"
    local layer_name="$2"
    
    print_status "Verifying zip contents..."
    
    # Check if zip file exists
    if [[ ! -f "$zip_file" ]]; then
        print_error "Zip file not found: $zip_file"
        return 1
    fi
    
    # List contents (first 20 lines)
    print_status "Zip file contents (first 20 lines):"
    unzip -l "$zip_file" 2>/dev/null | head -20
    
    # Check for common issues
    if unzip -l "$zip_file" 2>/dev/null | grep -q "__pycache__"; then
        print_warning "Found __pycache__ directories in zip file"
    fi
    
    if unzip -l "$zip_file" 2>/dev/null | grep -q "\.pyc"; then
        print_warning "Found .pyc files in zip file"
    fi
    
    # Verify key files exist for database-core-layer
    if [[ "$layer_name" == "database-core-layer" ]]; then
        if ! unzip -l "$zip_file" 2>/dev/null | grep -q "python/utils/DatabaseManager.py"; then
            print_error "DatabaseManager.py not found in zip file"
            return 1
        fi
        
        # Extract and verify DatabaseManager has required methods
        local temp_dir=$(mktemp -d)
        if unzip -q "$zip_file" -d "$temp_dir" 2>/dev/null; then
            if [[ -f "$temp_dir/python/utils/DatabaseManager.py" ]]; then
                if grep -q "def set_processing_status" "$temp_dir/python/utils/DatabaseManager.py"; then
                    print_success "DatabaseManager.py contains set_processing_status method"
                else
                    print_error "DatabaseManager.py missing set_processing_status method"
                    rm -rf "$temp_dir"
                    return 1
                fi
            else
                print_error "DatabaseManager.py not found after extraction"
                rm -rf "$temp_dir"
                return 1
            fi
        else
            print_error "Failed to extract zip file for verification"
            rm -rf "$temp_dir"
            return 1
        fi
        
        rm -rf "$temp_dir"
    fi
    
    print_success "Zip contents verified"
    return 0
}

# Function to deploy layer to AWS
deploy_layer() {
    local layer_name="$1"
    local zip_file="$2"
    local aws_layer_name="$3"
    
    print_status "Deploying layer to AWS..."
    
    # Build description
    local deploy_description="$DESCRIPTION"
    if [[ -z "$deploy_description" ]]; then
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        deploy_description="Built on $timestamp from $(basename "$zip_file")"
    fi
    
    # Deploy layer
    local result=$(aws lambda publish-layer-version \
        --layer-name "$aws_layer_name" \
        --zip-file "fileb://$zip_file" \
        --compatible-runtimes "$COMPATIBLE_RUNTIMES" \
        --description "$deploy_description" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query '{Version:Version,LayerVersionArn:LayerVersionArn}' \
        --output json)
    
    local version=$(echo "$result" | jq -r '.Version')
    local arn=$(echo "$result" | jq -r '.LayerVersionArn')
    
    print_success "Layer deployed successfully!"
    print_success "Version: $version"
    print_success "ARN: $arn"
    
    # Save deployment info
    local deploy_info="$BUILD_DIR/${layer_name}_deployment.json"
    echo "$result" > "$deploy_info"
    
    echo "$arn"
}

# Function to build layer
build_layer() {
    local layer_name="$1"
    local layer_source="$LAYERS_ROOT/$layer_name"
    local layer_build_dir="$BUILD_DIR/$layer_name"
    
    print_status "Building layer: $layer_name"
    print_status "Source: $layer_source"
    print_status "Build dir: $layer_build_dir"
    
    # Validate structure
    validate_layer_structure "$layer_source" || return 1
    
    # Clean previous builds
    clean_build "$layer_name"
    
    # Prepare build environment
    prepare_build "$layer_name" "$layer_source" "$layer_build_dir"
    
    # Install dependencies if needed
    install_dependencies "$layer_source" "$layer_build_dir"
    
    # Create zip file
    local zip_file=$(create_layer_zip "$layer_name")
    
    # Verify contents
    verify_zip_contents "$zip_file" "$layer_name" || return 1
    
    print_success "Layer built successfully: $zip_file"
    
    # Deploy if requested
    if [[ "$DEPLOY" == "true" ]]; then
        local aws_layer_name="$layer_name"
        deploy_layer "$layer_name" "$zip_file" "$aws_layer_name"
    fi
    
    return 0
}

# Parse command line arguments
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
        --region)
            REGION="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --runtime)
            COMPATIBLE_RUNTIMES="$2"
            shift 2
            ;;
        --description)
            DESCRIPTION="$2"
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

# Validate required tools
if [[ "$DEPLOY" == "true" ]]; then
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is required for deployment"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq is required for deployment"
        exit 1
    fi
fi

# Create build directory
mkdir -p "$BUILD_DIR"

# Main execution
print_status "Starting layer build process..."
print_status "Layer: $LAYER_NAME"
print_status "Deploy: $DEPLOY"
print_status "Profile: $PROFILE"
print_status "Region: $REGION"

if build_layer "$LAYER_NAME"; then
    print_success "Build process completed successfully!"
else
    print_error "Build process failed!"
    exit 1
fi
