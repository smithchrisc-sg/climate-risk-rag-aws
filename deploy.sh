#!/bin/bash

# Climate Risk RAG AWS Deployment Script

set -e

echo "🌍 Climate Risk RAG - AWS Deployment"
echo "===================================="

# Configuration
AWS_PROFILE="solve-global"
AWS_REGION="us-west-2"

# Check if AWS CLI is configured with the profile
if ! aws sts get-caller-identity --profile $AWS_PROFILE > /dev/null 2>&1; then
    echo "❌ AWS CLI profile '$AWS_PROFILE' not configured or not working."
    echo "Please ensure the profile is set up correctly."
    exit 1
fi

# Get AWS account
AWS_ACCOUNT=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)

echo "📍 Deploying to Account: $AWS_ACCOUNT, Region: $AWS_REGION, Profile: $AWS_PROFILE"

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK not found. Installing..."
    npm install -g aws-cdk
fi

# Navigate to CDK directory
cd cdk

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Bootstrap CDK (if not already done)
echo "🚀 Bootstrapping CDK..."
cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION --profile $AWS_PROFILE

# Deploy stacks in order
echo "🏗️  Deploying infrastructure stacks..."

echo "1️⃣  Deploying Networking Stack..."
cdk deploy climate-risk-rag-networking --require-approval never --profile $AWS_PROFILE

echo "2️⃣  Deploying AI/ML Stack..."
cdk deploy climate-risk-rag-ai-ml --require-approval never --profile $AWS_PROFILE

echo "3️⃣  Deploying Data Stack..."
cdk deploy climate-risk-rag-data --require-approval never --profile $AWS_PROFILE

echo "4️⃣  Deploying Compute Stack..."
cdk deploy climate-risk-rag-compute --require-approval never --profile $AWS_PROFILE

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Enable Bedrock models in the AWS Console:"
echo "   - Go to Amazon Bedrock console"
echo "   - Navigate to Model access"
echo "   - Enable: Titan Embed Text, Titan Text Express, Claude 3 Haiku"
echo ""
echo "2. Upload your first document to test:"
echo "   aws s3 cp your-document.pdf s3://solve-global-kr-documents-$AWS_ACCOUNT-$AWS_REGION/documents/ --profile $AWS_PROFILE"
echo ""
echo "3. Test the API:"
echo "   curl -X POST [API_GATEWAY_URL]/query -d '{\"query\":\"climate risk\"}'"
echo ""

# Get outputs
echo "🔗 Important URLs and ARNs:"
cdk list --long 2>/dev/null | grep -E "(APIGatewayURL|OpenSearchCollectionEndpoint|NeptuneClusterEndpoint)" || true

cd ..

echo ""
echo "🎉 Your Climate Risk RAG system is ready!"
