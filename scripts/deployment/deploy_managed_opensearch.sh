#!/bin/bash

# Deploy AWS Managed OpenSearch Stack
# This script deploys the new cost-optimized OpenSearch infrastructure

set -e

echo "🚀 Deploying AWS Managed OpenSearch Stack..."
echo "This will replace OpenSearch Serverless with AWS Managed OpenSearch"
echo "Expected cost savings: 90%+ reduction"
echo ""

# Activate virtual environment
source venv/bin/activate

# Navigate to CDK directory
cd cdk

# Set environment variable to silence Node.js version warning
export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1

# Check AWS credentials
echo "✅ Checking AWS credentials..."
aws sts get-caller-identity

# Synthesize the stack first to catch any errors
echo "🔍 Synthesizing CDK stack..."
cdk synth -a "python app_production_ready_managed_opensearch.py" --no-staging > /dev/null

# Deploy the stack
echo "🚀 Deploying stack..."
echo "This will create:"
echo "  - AWS Managed OpenSearch domain (m6g.medium.search)"
echo "  - Updated Lambda functions with OpenSearch environment variables"
echo "  - Security groups and IAM permissions"
echo "  - All existing infrastructure remains intact"
echo ""

read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cdk deploy -a "python app_production_ready_managed_opensearch.py" \
        --require-approval never \
        --progress events \
        --outputs-file ../opensearch-outputs.json
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "📊 Cost Comparison:"
    echo "  Before (Serverless): ~$1,500-2,200/month"
    echo "  After (Managed):     ~$44/month"
    echo "  Savings:             ~94% reduction"
    echo ""
    echo "🔗 Next Steps:"
    echo "1. Update Lambda functions to use new OpenSearch endpoint"
    echo "2. Test vector and keyword search functionality"
    echo "3. Migrate any existing data (if needed)"
    echo "4. Remove old serverless collection"
    echo ""
    echo "📄 Outputs saved to: opensearch-outputs.json"
else
    echo "Deployment cancelled."
    exit 1
fi
