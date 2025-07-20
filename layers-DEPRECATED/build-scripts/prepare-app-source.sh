#!/bin/bash
# prepare-app-source.sh - Prepare application source code for layer building

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
APP_SOURCE_DIR="${LAYERS_DIR}/app-source"
POC_SOURCE_DIR="/Volumes/G-RAID Photo 24TB/climate_risk_rag/src"

echo -e "${BLUE}🔧 Preparing Application Source Code for Layers${NC}"
echo -e "${BLUE}===============================================${NC}"

# Create app source directory
rm -rf "$APP_SOURCE_DIR"
mkdir -p "$APP_SOURCE_DIR"

# Function to copy and clean source files
copy_source() {
    local source_path=$1
    local dest_path=$2
    local description=$3
    
    echo -e "${YELLOW}📁 Copying ${description}...${NC}"
    
    if [[ -f "$source_path" ]]; then
        # Copy single file
        mkdir -p "$(dirname "$dest_path")"
        cp "$source_path" "$dest_path"
        echo -e "  ✅ Copied file: $(basename "$source_path")"
    elif [[ -d "$source_path" ]]; then
        # Copy directory
        mkdir -p "$dest_path"
        cp -r "$source_path"/* "$dest_path/"
        echo -e "  ✅ Copied directory: $(basename "$source_path")"
    else
        echo -e "${RED}  ❌ Source not found: ${source_path}${NC}"
        return 1
    fi
    
    # Clean up copied files
    find "$dest_path" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$dest_path" -name "*.pyc" -delete 2>/dev/null || true
    find "$dest_path" -name "*.pyo" -delete 2>/dev/null || true
    find "$dest_path" -name ".DS_Store" -delete 2>/dev/null || true
    
    return 0
}

# Function to create __init__.py files
create_init_files() {
    local dir_path=$1
    find "$dir_path" -type d -exec touch {}/__init__.py \; 2>/dev/null || true
}

# Function to fix imports in copied files
fix_imports() {
    local dir_path=$1
    local description=$2
    
    echo -e "${YELLOW}🔧 Fixing imports in ${description}...${NC}"
    
    # Find all Python files
    find "$dir_path" -name "*.py" -type f | while read -r file; do
        # Replace absolute imports with relative imports
        sed -i.bak 's/from src\./from climate_risk_rag./g' "$file" 2>/dev/null || true
        sed -i.bak 's/import src\./import climate_risk_rag./g' "$file" 2>/dev/null || true
        
        # Remove backup files
        rm -f "${file}.bak" 2>/dev/null || true
    done
    
    echo -e "  ✅ Fixed imports in ${description}"
}

# Copy core utilities
echo -e "${BLUE}Copying Core Utilities...${NC}"

copy_source "${POC_SOURCE_DIR}/utils" "${APP_SOURCE_DIR}/utils" "Core utilities"
copy_source "${POC_SOURCE_DIR}/document_processing/DocumentMetadata.py" "${APP_SOURCE_DIR}/document_processing/DocumentMetadata.py" "Document metadata"

# Copy knowledge graph shared components
echo -e "${BLUE}Copying Knowledge Graph Components...${NC}"

mkdir -p "${APP_SOURCE_DIR}/knowledge_graph"

copy_source "${POC_SOURCE_DIR}/knowledge_graph/OntologyManager.py" "${APP_SOURCE_DIR}/knowledge_graph/OntologyManager.py" "Ontology manager"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/namespaces.py" "${APP_SOURCE_DIR}/knowledge_graph/namespaces.py" "RDF namespaces"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/prefixes.py" "${APP_SOURCE_DIR}/knowledge_graph/prefixes.py" "SPARQL prefixes"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/types.py" "${APP_SOURCE_DIR}/knowledge_graph/types.py" "Shared types"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/ComponentMatcher.py" "${APP_SOURCE_DIR}/knowledge_graph/ComponentMatcher.py" "Component matcher"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/ConfidenceScorer.py" "${APP_SOURCE_DIR}/knowledge_graph/ConfidenceScorer.py" "Confidence scorer"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/TermMatcher.py" "${APP_SOURCE_DIR}/knowledge_graph/TermMatcher.py" "Term matcher"
copy_source "${POC_SOURCE_DIR}/knowledge_graph/UnalignedEntityTracker.py" "${APP_SOURCE_DIR}/knowledge_graph/UnalignedEntityTracker.py" "Unaligned entity tracker"

# Copy RAG system shared components
echo -e "${BLUE}Copying RAG System Components...${NC}"

mkdir -p "${APP_SOURCE_DIR}/rag_system"

copy_source "${POC_SOURCE_DIR}/rag_system/SearchProcessorBase.py" "${APP_SOURCE_DIR}/rag_system/SearchProcessorBase.py" "Search processor base"
copy_source "${POC_SOURCE_DIR}/rag_system/ScoreNormalizer.py" "${APP_SOURCE_DIR}/rag_system/ScoreNormalizer.py" "Score normalizer"
copy_source "${POC_SOURCE_DIR}/rag_system/ResultCombiner.py" "${APP_SOURCE_DIR}/rag_system/ResultCombiner.py" "Result combiner"
copy_source "${POC_SOURCE_DIR}/rag_system/SnippetManager.py" "${APP_SOURCE_DIR}/rag_system/SnippetManager.py" "Snippet manager"
copy_source "${POC_SOURCE_DIR}/rag_system/TemplateManager.py" "${APP_SOURCE_DIR}/rag_system/TemplateManager.py" "Template manager"
copy_source "${POC_SOURCE_DIR}/rag_system/QueryConceptExtractor.py" "${APP_SOURCE_DIR}/rag_system/QueryConceptExtractor.py" "Query concept extractor"

# Create __init__.py files
echo -e "${BLUE}Creating __init__.py files...${NC}"

create_init_files "$APP_SOURCE_DIR"

# Fix imports
echo -e "${BLUE}Fixing Import Statements...${NC}"

fix_imports "${APP_SOURCE_DIR}/utils" "core utilities"
fix_imports "${APP_SOURCE_DIR}/document_processing" "document processing"
fix_imports "${APP_SOURCE_DIR}/knowledge_graph" "knowledge graph components"
fix_imports "${APP_SOURCE_DIR}/rag_system" "RAG system components"

# Create layer manifest
echo -e "${BLUE}Creating Layer Manifest...${NC}"

cat > "${APP_SOURCE_DIR}/layer_manifest.json" << EOF
{
  "layers": {
    "climate-risk-core-layer": {
      "description": "Core application utilities",
      "components": [
        "utils/DocumentIDManager.py",
        "utils/DatabaseManager.py",
        "utils/ProvenanceTracker.py",
        "utils/TextCleaner.py",
        "utils/NERAnalyzer.py",
        "utils/logging_config.py",
        "utils/config.py",
        "document_processing/DocumentMetadata.py"
      ],
      "size_estimate": "15MB",
      "functions_using": [
        "TextExtractor Initiator",
        "TextExtractor Processor", 
        "TextChunker",
        "NERProcessor",
        "EntityExtractor",
        "RelationshipMiner",
        "GraphUpdater",
        "QueryAnalyzer",
        "VectorSearcher",
        "KnowledgeGraphSearcher",
        "ResponseGenerator"
      ]
    },
    "kg-shared-layer": {
      "description": "Knowledge graph shared components",
      "components": [
        "knowledge_graph/OntologyManager.py",
        "knowledge_graph/namespaces.py",
        "knowledge_graph/prefixes.py",
        "knowledge_graph/types.py",
        "knowledge_graph/ComponentMatcher.py",
        "knowledge_graph/ConfidenceScorer.py",
        "knowledge_graph/TermMatcher.py",
        "knowledge_graph/UnalignedEntityTracker.py"
      ],
      "size_estimate": "25MB",
      "functions_using": [
        "EntityExtractor",
        "RelationshipMiner",
        "GraphUpdater",
        "KnowledgeGraphSearcher",
        "NERProcessor",
        "QueryAnalyzer"
      ]
    },
    "rag-shared-layer": {
      "description": "RAG system shared components",
      "components": [
        "rag_system/SearchProcessorBase.py",
        "rag_system/ScoreNormalizer.py",
        "rag_system/ResultCombiner.py",
        "rag_system/SnippetManager.py",
        "rag_system/TemplateManager.py",
        "rag_system/QueryConceptExtractor.py"
      ],
      "size_estimate": "20MB",
      "functions_using": [
        "VectorSearcher",
        "KnowledgeGraphSearcher",
        "QueryAnalyzer",
        "ResponseGenerator"
      ]
    }
  },
  "created": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "source": "${POC_SOURCE_DIR}",
  "destination": "${APP_SOURCE_DIR}"
}
EOF

echo -e "${GREEN}✅ Layer manifest created${NC}"

# Show summary
echo -e "${BLUE}Application Source Preparation Summary:${NC}"
echo -e "${BLUE}=====================================${NC}"

echo -e "📁 Source directories created:"
find "$APP_SOURCE_DIR" -type d | sort | while read -r dir; do
    echo -e "  $(basename "$dir")"
done

echo -e "\n📄 Python files prepared:"
find "$APP_SOURCE_DIR" -name "*.py" | wc -l | xargs echo -e "  Total files:"

echo -e "\n📋 Layer components ready:"
echo -e "  • climate-risk-core-layer: Core utilities"
echo -e "  • kg-shared-layer: Knowledge graph components"
echo -e "  • rag-shared-layer: RAG system components"

echo -e "${GREEN}🎉 Application source preparation completed!${NC}"
echo -e "${BLUE}Next step: Run ./build-all-layers.sh to build all layers${NC}"
