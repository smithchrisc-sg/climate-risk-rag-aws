#!/bin/bash

# Deploy Climate Risk RAG Cleanup Service
# This script deploys the centralized cleanup Lambda function

set -e

echo "🧹 Deploying Climate Risk RAG Cleanup Service..."

# Change to CDK directory
cd cdk

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing CDK dependencies..."
    npm install
fi

# Bootstrap CDK if needed (usually only needed once per account/region)
echo "🚀 Bootstrapping CDK (if needed)..."
cdk bootstrap --app "python app_cleanup_service.py" || true

# Deploy the cleanup service stack
echo "🏗️  Deploying cleanup service stack..."
cdk deploy CleanupServiceStack \
    --app "python app_cleanup_service.py" \
    --require-approval never \
    --verbose

echo "✅ Cleanup service deployment completed!"

# Get function details
echo ""
echo "📋 Function Details:"
aws lambda get-function --function-name solve-global-kr-cleanup-service --query 'Configuration.{FunctionName:FunctionName,Runtime:Runtime,Timeout:Timeout,MemorySize:MemorySize,LastModified:LastModified}' --output table

echo ""
echo "🔧 Usage Examples:"
echo ""
echo "# Dry run full cleanup:"
echo "aws lambda invoke --function-name solve-global-kr-cleanup-service --payload file://lambda/cleanup_service/examples/cleanup_full_dry_run.json response.json"
echo ""
echo "# S3 only cleanup:"
echo "aws lambda invoke --function-name solve-global-kr-cleanup-service --payload file://lambda/cleanup_service/examples/cleanup_s3_only.json response.json"
echo ""
echo "# Specific document cleanup:"
echo "aws lambda invoke --function-name solve-global-kr-cleanup-service --payload file://lambda/cleanup_service/examples/cleanup_specific_documents.json response.json"
echo ""
echo "📖 See lambda/cleanup_service/README.md for detailed usage instructions"
