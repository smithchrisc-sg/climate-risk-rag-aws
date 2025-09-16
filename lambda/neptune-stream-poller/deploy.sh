#!/bin/bash

# Deploy Neptune Stream Poller Lambda Function
# This script packages and deploys the customized Neptune Stream Poller

set -e

# Configuration
LAMBDA_FUNCTION_NAME="NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3"
PACKAGE_NAME="neptune-stream-poller.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying Neptune Stream Poller Lambda Function"
echo "=================================================="

# Change to the Lambda directory
cd "$SCRIPT_DIR"

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -f "$PACKAGE_NAME"
rm -rf __pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create deployment package
echo "📦 Creating deployment package..."
zip -r "$PACKAGE_NAME" . \
    -x "*.zip" \
    -x "*.md" \
    -x "deploy.sh" \
    -x "__pycache__/*" \
    -x "*/__pycache__/*" \
    -x "*.pyc" \
    -x ".DS_Store" \
    -x "*/.*"

# Check package size
PACKAGE_SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
echo "📊 Package size: $PACKAGE_SIZE"

# Deploy to AWS Lambda
echo "☁️  Deploying to AWS Lambda..."
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file "fileb://$PACKAGE_NAME"

# Wait for update to complete
echo "⏳ Waiting for deployment to complete..."
aws lambda wait function-updated \
    --function-name "$LAMBDA_FUNCTION_NAME"

# Get function info
echo "ℹ️  Function information:"
aws lambda get-function-configuration \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --query '{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,MemorySize:MemorySize,Timeout:Timeout,LastModified:LastModified}' \
    --output table

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Monitor CloudWatch logs: /aws/lambda/$LAMBDA_FUNCTION_NAME"
echo "2. Check processing metrics in CloudWatch dashboard"
echo "3. Test FTS queries once data is indexed"
echo ""
echo "🔧 To enable ontology filtering:"
echo "aws lambda update-function-configuration \\"
echo "    --function-name $LAMBDA_FUNCTION_NAME \\"
echo "    --environment Variables='{\"ONTOLOGY_FILTERING_ENABLED\":\"true\"}'"
