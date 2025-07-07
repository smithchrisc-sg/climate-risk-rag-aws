#!/bin/bash
# build-all-layers.sh - Build all Lambda layers for Climate Risk RAG system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYERS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$LAYERS_DIR")"
BUILD_DIR="${LAYERS_DIR}/built-layers"
REQUIREMENTS_DIR="${LAYERS_DIR}/requirements"
APP_SOURCE_DIR="${LAYERS_DIR}/app-source"

# AWS Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
LAYER_PREFIX="climate-risk-rag"

echo -e "${BLUE}🚀 Building Lambda Layers for Climate Risk RAG System${NC}"
echo -e "${BLUE}=================================================${NC}"

# Create build directory
mkdir -p "$BUILD_DIR"

# Function to build a dependency layer
build_dependency_layer() {
    local layer_name=$1
    local requirements_file=$2
    local description=$3
    
    echo -e "${YELLOW}📦 Building ${layer_name}...${NC}"
    
    local layer_dir="${BUILD_DIR}/${layer_name}"
    local python_dir="${layer_dir}/python"
    
    # Clean and create directories
    rm -rf "$layer_dir"
    mkdir -p "$python_dir"
    
    # Install dependencies
    echo -e "  Installing dependencies from ${requirements_file}..."
    pip install -r "${REQUIREMENTS_DIR}/${requirements_file}" \
        -t "$python_dir" \
        --platform manylinux2014_x86_64 \
        --only-binary=all \
        --upgrade \
        --no-deps || {
        echo -e "${RED}❌ Failed to install dependencies for ${layer_name}${NC}"
        return 1
    }
    
    # Clean up unnecessary files
    find "$python_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -name "*.pyc" -delete 2>/dev/null || true
    find "$python_dir" -name "*.pyo" -delete 2>/dev/null || true
    find "$python_dir" -name ".DS_Store" -delete 2>/dev/null || true
    find "$python_dir" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Create deployment package
    cd "$layer_dir"
    zip -r "../${layer_name}.zip" . -q
    cd - > /dev/null
    
    # Get package size
    local size=$(du -h "${BUILD_DIR}/${layer_name}.zip" | cut -f1)
    echo -e "${GREEN}  ✅ Built ${layer_name} (${size})${NC}"
    
    return 0
}

# Function to build an application layer
build_app_layer() {
    local layer_name=$1
    local source_paths=$2
    local description=$3
    
    echo -e "${YELLOW}📦 Building ${layer_name}...${NC}"
    
    local layer_dir="${BUILD_DIR}/${layer_name}"
    local python_dir="${layer_dir}/python"
    local app_dir="${python_dir}/climate_risk_rag"
    
    # Clean and create directories
    rm -rf "$layer_dir"
    mkdir -p "$app_dir"
    
    # Copy application source files
    echo -e "  Copying application source files..."
    IFS=',' read -ra PATHS <<< "$source_paths"
    for source_path in "${PATHS[@]}"; do
        source_path=$(echo "$source_path" | xargs) # trim whitespace
        full_source_path="${APP_SOURCE_DIR}/${source_path}"
        
        if [[ -f "$full_source_path" ]]; then
            # Copy individual file
            cp "$full_source_path" "$app_dir/"
        elif [[ -d "$full_source_path" ]]; then
            # Copy directory contents
            cp -r "$full_source_path"/* "$app_dir/"
        else
            echo -e "${YELLOW}  ⚠️  Source not found: ${full_source_path}${NC}"
        fi
    done
    
    # Clean up unnecessary files
    find "$python_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$python_dir" -name "*.pyc" -delete 2>/dev/null || true
    find "$python_dir" -name "*.pyo" -delete 2>/dev/null || true
    find "$python_dir" -name ".DS_Store" -delete 2>/dev/null || true
    
    # Create __init__.py files
    find "$python_dir" -type d -exec touch {}/__init__.py \; 2>/dev/null || true
    
    # Create deployment package
    cd "$layer_dir"
    zip -r "../${layer_name}.zip" . -q
    cd - > /dev/null
    
    # Get package size
    local size=$(du -h "${BUILD_DIR}/${layer_name}.zip" | cut -f1)
    echo -e "${GREEN}  ✅ Built ${layer_name} (${size})${NC}"
    
    return 0
}

# Function to deploy layer to AWS
deploy_layer() {
    local layer_name=$1
    local description=$2
    
    echo -e "${YELLOW}🚀 Deploying ${layer_name} to AWS...${NC}"
    
    local zip_file="${BUILD_DIR}/${layer_name}.zip"
    local full_layer_name="${LAYER_PREFIX}-${layer_name}"
    
    if [[ ! -f "$zip_file" ]]; then
        echo -e "${RED}❌ Zip file not found: ${zip_file}${NC}"
        return 1
    fi
    
    # Deploy to AWS
    local version_output
    version_output=$(aws lambda publish-layer-version \
        --layer-name "$full_layer_name" \
        --zip-file "fileb://${zip_file}" \
        --compatible-runtimes python3.11 \
        --description "$description" \
        --region "$AWS_REGION" \
        --output json 2>/dev/null) || {
        echo -e "${RED}❌ Failed to deploy ${layer_name}${NC}"
        return 1
    }
    
    local version=$(echo "$version_output" | jq -r '.Version')
    local arn=$(echo "$version_output" | jq -r '.LayerVersionArn')
    
    echo -e "${GREEN}  ✅ Deployed ${layer_name} version ${version}${NC}"
    echo -e "     ARN: ${arn}"
    
    return 0
}

# Build dependency layers
echo -e "${BLUE}Building Dependency Layers...${NC}"

build_dependency_layer "aws-core-layer" "aws-core.txt" "AWS SDK and core utilities"
build_dependency_layer "data-processing-layer" "data-processing.txt" "NumPy, Pandas, SciPy for data processing"
build_dependency_layer "database-layer" "database.txt" "Database connectivity (PostgreSQL, OpenSearch, Redis)"
build_dependency_layer "nlp-core-layer" "nlp-core.txt" "Core NLP libraries without models"
build_dependency_layer "pytorch-layer" "pytorch.txt" "PyTorch framework for ML inference"
build_dependency_layer "knowledge-graph-layer" "knowledge-graph.txt" "RDF, SPARQL, and ontology processing"
build_dependency_layer "web-template-layer" "web-template.txt" "Web scraping and templating"
build_dependency_layer "nlp-models-layer" "nlp-models.txt" "Pre-trained NLP models and specialized tools"

# Build application layers
echo -e "${BLUE}Building Application Layers...${NC}"

build_app_layer "climate-risk-core-layer" "utils,document_processing/DocumentMetadata.py" "Core application utilities"
build_app_layer "kg-shared-layer" "knowledge_graph/OntologyManager.py,knowledge_graph/namespaces.py,knowledge_graph/prefixes.py,knowledge_graph/types.py,knowledge_graph/ComponentMatcher.py,knowledge_graph/ConfidenceScorer.py,knowledge_graph/TermMatcher.py,knowledge_graph/UnalignedEntityTracker.py" "Knowledge graph shared components"
build_app_layer "rag-shared-layer" "rag_system/SearchProcessorBase.py,rag_system/ScoreNormalizer.py,rag_system/ResultCombiner.py,rag_system/SnippetManager.py,rag_system/TemplateManager.py,rag_system/QueryConceptExtractor.py" "RAG system shared components"

echo -e "${BLUE}Build Summary:${NC}"
echo -e "${BLUE}=============${NC}"

# Show build summary
total_size=0
layer_count=0

for zip_file in "${BUILD_DIR}"/*.zip; do
    if [[ -f "$zip_file" ]]; then
        layer_name=$(basename "$zip_file" .zip)
        size_bytes=$(stat -f%z "$zip_file" 2>/dev/null || stat -c%s "$zip_file" 2>/dev/null || echo "0")
        size_mb=$((size_bytes / 1024 / 1024))
        total_size=$((total_size + size_mb))
        layer_count=$((layer_count + 1))
        
        printf "  %-30s %5d MB\n" "$layer_name" "$size_mb"
    fi
done

echo -e "${BLUE}=============${NC}"
printf "  %-30s %5d MB\n" "Total Size:" "$total_size"
printf "  %-30s %5d layers\n" "Total Layers:" "$layer_count"

# Deploy layers if requested
if [[ "${1:-}" == "--deploy" ]]; then
    echo -e "${BLUE}Deploying Layers to AWS...${NC}"
    echo -e "${BLUE}=========================${NC}"
    
    # Check AWS CLI configuration
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        echo -e "${RED}❌ AWS CLI not configured or no valid credentials${NC}"
        exit 1
    fi
    
    # Deploy dependency layers
    deploy_layer "aws-core-layer" "AWS SDK and core utilities"
    deploy_layer "data-processing-layer" "NumPy, Pandas, SciPy for data processing"
    deploy_layer "database-layer" "Database connectivity (PostgreSQL, OpenSearch, Redis)"
    deploy_layer "nlp-core-layer" "Core NLP libraries without models"
    deploy_layer "pytorch-layer" "PyTorch framework for ML inference"
    deploy_layer "knowledge-graph-layer" "RDF, SPARQL, and ontology processing"
    deploy_layer "web-template-layer" "Web scraping and templating"
    deploy_layer "nlp-models-layer" "Pre-trained NLP models and specialized tools"
    
    # Deploy application layers
    deploy_layer "climate-risk-core-layer" "Core application utilities"
    deploy_layer "kg-shared-layer" "Knowledge graph shared components"
    deploy_layer "rag-shared-layer" "RAG system shared components"
    
    echo -e "${GREEN}🎉 All layers deployed successfully!${NC}"
fi

echo -e "${GREEN}🎉 Layer build completed successfully!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Deploy layers: ./build-all-layers.sh --deploy"
echo -e "  2. Deploy infrastructure: cd ../infrastructure && cdk deploy"
echo -e "  3. Test layers: ../tests/test-all-layers.sh"
