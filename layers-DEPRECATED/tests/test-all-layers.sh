#!/bin/bash
# test-all-layers.sh - Test all Lambda layers for compatibility and functionality

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

# AWS Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
LAYER_PREFIX="climate-risk-rag"
TEST_FUNCTION_PREFIX="test-layer"

echo -e "${BLUE}🧪 Testing Lambda Layers for Climate Risk RAG System${NC}"
echo -e "${BLUE}===================================================${NC}"

# Function to create a test Lambda function
create_test_function() {
    local layer_name=$1
    local layer_arn=$2
    local test_code=$3
    
    local function_name="${TEST_FUNCTION_PREFIX}-${layer_name}"
    
    echo -e "${YELLOW}Creating test function for ${layer_name}...${NC}"
    
    # Create test function code
    cat > "/tmp/${function_name}.py" << EOF
import json
import sys
import importlib.util

def lambda_handler(event, context):
    """Test function for layer: ${layer_name}"""
    
    results = {
        'layer_name': '${layer_name}',
        'test_results': [],
        'python_path': sys.path,
        'success': True,
        'errors': []
    }
    
    # Test imports based on layer type
    test_imports = event.get('test_imports', [])
    
    for import_test in test_imports:
        try:
            module_name = import_test['module']
            test_name = import_test.get('name', module_name)
            
            # Try to import the module
            if '.' in module_name:
                # Handle from X import Y
                parts = module_name.split('.')
                if len(parts) == 2:
                    exec(f"from {parts[0]} import {parts[1]}")
                else:
                    exec(f"import {module_name}")
            else:
                exec(f"import {module_name}")
            
            results['test_results'].append({
                'test': test_name,
                'status': 'PASS',
                'message': f'Successfully imported {module_name}'
            })
            
        except Exception as e:
            results['test_results'].append({
                'test': test_name,
                'status': 'FAIL',
                'message': f'Failed to import {module_name}: {str(e)}'
            })
            results['success'] = False
            results['errors'].append(str(e))
    
    # Additional functionality tests
    if event.get('run_functionality_tests', False):
        try:
            # Run layer-specific functionality tests
            if '${layer_name}' == 'aws-core-layer':
                import boto3
                client = boto3.client('sts')
                results['test_results'].append({
                    'test': 'boto3_functionality',
                    'status': 'PASS',
                    'message': 'boto3 client creation successful'
                })
            
            elif '${layer_name}' == 'data-processing-layer':
                import numpy as np
                import pandas as pd
                arr = np.array([1, 2, 3])
                df = pd.DataFrame({'test': [1, 2, 3]})
                results['test_results'].append({
                    'test': 'numpy_pandas_functionality',
                    'status': 'PASS',
                    'message': f'NumPy array: {arr.shape}, Pandas DataFrame: {df.shape}'
                })
            
            elif '${layer_name}' == 'nlp-core-layer':
                from transformers import AutoTokenizer
                results['test_results'].append({
                    'test': 'transformers_functionality',
                    'status': 'PASS',
                    'message': 'Transformers library loaded successfully'
                })
                
        except Exception as e:
            results['test_results'].append({
                'test': 'functionality_test',
                'status': 'FAIL',
                'message': f'Functionality test failed: {str(e)}'
            })
            results['success'] = False
            results['errors'].append(str(e))
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }
EOF
    
    # Create deployment package
    cd /tmp
    zip -q "${function_name}.zip" "${function_name}.py"
    
    # Create or update the function
    if aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" > /dev/null 2>&1; then
        # Update existing function
        aws lambda update-function-code \
            --function-name "$function_name" \
            --zip-file "fileb://${function_name}.zip" \
            --region "$AWS_REGION" > /dev/null
    else
        # Create new function
        aws lambda create-function \
            --function-name "$function_name" \
            --runtime python3.11 \
            --role "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role" \
            --handler "${function_name}.lambda_handler" \
            --zip-file "fileb://${function_name}.zip" \
            --timeout 30 \
            --memory-size 256 \
            --layers "$layer_arn" \
            --region "$AWS_REGION" > /dev/null
    fi
    
    # Clean up
    rm -f "${function_name}.py" "${function_name}.zip"
    
    echo "$function_name"
}

# Function to test a layer
test_layer() {
    local layer_name=$1
    local test_imports=$2
    local run_functionality_tests=${3:-false}
    
    echo -e "${YELLOW}🧪 Testing layer: ${layer_name}${NC}"
    
    # Get layer ARN
    local full_layer_name="${LAYER_PREFIX}-${layer_name}"
    local layer_arn
    
    layer_arn=$(aws lambda list-layer-versions \
        --layer-name "$full_layer_name" \
        --region "$AWS_REGION" \
        --query 'LayerVersions[0].LayerVersionArn' \
        --output text 2>/dev/null)
    
    if [[ "$layer_arn" == "None" ]] || [[ -z "$layer_arn" ]]; then
        echo -e "${RED}  ❌ Layer not found: ${full_layer_name}${NC}"
        return 1
    fi
    
    echo -e "  Layer ARN: ${layer_arn}"
    
    # Create test function
    local test_function
    test_function=$(create_test_function "$layer_name" "$layer_arn" "")
    
    # Wait for function to be ready
    sleep 5
    
    # Prepare test payload
    local test_payload
    test_payload=$(cat << EOF
{
    "test_imports": ${test_imports},
    "run_functionality_tests": ${run_functionality_tests}
}
EOF
)
    
    # Invoke test function
    echo -e "  Invoking test function..."
    local response
    response=$(aws lambda invoke \
        --function-name "$test_function" \
        --payload "$test_payload" \
        --region "$AWS_REGION" \
        /tmp/test-response.json 2>/dev/null)
    
    # Parse results
    if [[ -f "/tmp/test-response.json" ]]; then
        local test_results
        test_results=$(cat /tmp/test-response.json | jq -r '.body' | jq .)
        
        local success
        success=$(echo "$test_results" | jq -r '.success')
        
        if [[ "$success" == "true" ]]; then
            echo -e "${GREEN}  ✅ Layer test passed${NC}"
            
            # Show test details
            echo "$test_results" | jq -r '.test_results[] | "    • \(.test): \(.status) - \(.message)"'
        else
            echo -e "${RED}  ❌ Layer test failed${NC}"
            
            # Show errors
            echo "$test_results" | jq -r '.errors[]' | while read -r error; do
                echo -e "${RED}    Error: ${error}${NC}"
            done
        fi
        
        rm -f /tmp/test-response.json
    else
        echo -e "${RED}  ❌ Test invocation failed${NC}"
        return 1
    fi
    
    # Clean up test function
    aws lambda delete-function \
        --function-name "$test_function" \
        --region "$AWS_REGION" > /dev/null 2>&1 || true
    
    return 0
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI not found${NC}"
        exit 1
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ jq not found (required for JSON parsing)${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        echo -e "${RED}❌ AWS credentials not configured${NC}"
        exit 1
    fi
    
    # Check if lambda execution role exists
    local account_id
    account_id=$(aws sts get-caller-identity --query Account --output text)
    local role_arn="arn:aws:iam::${account_id}:role/lambda-execution-role"
    
    if ! aws iam get-role --role-name lambda-execution-role > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Creating lambda-execution-role...${NC}"
        
        # Create trust policy
        cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
        
        # Create role
        aws iam create-role \
            --role-name lambda-execution-role \
            --assume-role-policy-document file:///tmp/trust-policy.json > /dev/null
        
        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name lambda-execution-role \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        rm -f /tmp/trust-policy.json
        
        echo -e "${GREEN}  ✅ Created lambda-execution-role${NC}"
        
        # Wait for role to propagate
        sleep 10
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Main test execution
main() {
    check_prerequisites
    
    echo -e "${BLUE}Starting layer tests...${NC}"
    
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    # Test AWS Core Layer
    echo -e "\n${BLUE}Testing Foundation Layers...${NC}"
    
    if test_layer "aws-core-layer" '[
        {"module": "boto3", "name": "boto3_import"},
        {"module": "botocore", "name": "botocore_import"},
        {"module": "requests", "name": "requests_import"}
    ]' true; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test Data Processing Layer
    if test_layer "data-processing-layer" '[
        {"module": "numpy", "name": "numpy_import"},
        {"module": "pandas", "name": "pandas_import"},
        {"module": "scipy", "name": "scipy_import"}
    ]' true; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test Database Layer
    if test_layer "database-layer" '[
        {"module": "psycopg2", "name": "psycopg2_import"},
        {"module": "opensearchpy", "name": "opensearch_import"},
        {"module": "redis", "name": "redis_import"}
    ]' false; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test NLP Core Layer
    if test_layer "nlp-core-layer" '[
        {"module": "transformers", "name": "transformers_import"},
        {"module": "tokenizers", "name": "tokenizers_import"},
        {"module": "huggingface_hub", "name": "hf_hub_import"}
    ]' true; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test Application Layers
    echo -e "\n${BLUE}Testing Application Layers...${NC}"
    
    # Test Climate Risk Core Layer
    if test_layer "climate-risk-core-layer" '[
        {"module": "climate_risk_rag.utils.DocumentIDManager", "name": "document_id_manager"},
        {"module": "climate_risk_rag.utils.DatabaseManager", "name": "database_manager"},
        {"module": "climate_risk_rag.utils.ProvenanceTracker", "name": "provenance_tracker"}
    ]' false; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test KG Shared Layer
    if test_layer "kg-shared-layer" '[
        {"module": "climate_risk_rag.knowledge_graph.OntologyManager", "name": "ontology_manager"},
        {"module": "climate_risk_rag.knowledge_graph.types", "name": "kg_types"},
        {"module": "climate_risk_rag.knowledge_graph.namespaces", "name": "kg_namespaces"}
    ]' false; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test RAG Shared Layer
    if test_layer "rag-shared-layer" '[
        {"module": "climate_risk_rag.rag_system.SearchProcessorBase", "name": "search_processor_base"},
        {"module": "climate_risk_rag.rag_system.ScoreNormalizer", "name": "score_normalizer"},
        {"module": "climate_risk_rag.rag_system.ResultCombiner", "name": "result_combiner"}
    ]' false; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
    ((total_tests++))
    
    # Test Summary
    echo -e "\n${BLUE}Test Summary${NC}"
    echo -e "${BLUE}============${NC}"
    echo -e "Total Tests: ${total_tests}"
    echo -e "${GREEN}Passed: ${passed_tests}${NC}"
    echo -e "${RED}Failed: ${failed_tests}${NC}"
    
    if [[ $failed_tests -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All layer tests passed!${NC}"
        return 0
    else
        echo -e "\n${RED}❌ Some layer tests failed${NC}"
        return 1
    fi
}

# Run main function
main "$@"
