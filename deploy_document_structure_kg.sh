#!/bin/bash
"""
Deploy Document Structure Knowledge Graph Integration
Deploys Lambda functions for integrating document structure into Neptune KG
"""

set -e

echo "🚀 Deploying Document Structure Knowledge Graph Integration..."

# Set AWS profile and region
export AWS_PROFILE=solve-global
export AWS_DEFAULT_REGION=us-east-1

# Change to CDK directory
cd /Users/chris/climate-risk-rag-aws

echo "📦 Installing CDK dependencies..."
cd cdk
npm install

echo "🔧 Synthesizing CDK stack..."
cdk synth --app "python3 app_document_structure_kg.py"

echo "🚀 Deploying CDK stack..."
cdk deploy --app "python3 app_document_structure_kg.py" --require-approval never

echo "✅ Document Structure KG Integration deployed successfully!"

echo "📋 Next steps:"
echo "1. Connect text chunker completion to document structure KG processor"
echo "2. Test with a sample document"
echo "3. Verify TTL generation and Neptune loading"
echo "4. Monitor CloudWatch logs for any issues"

echo "🔍 Useful commands:"
echo "  # Test document structure KG processor:"
echo "  aws lambda invoke --function-name document-structure-kg-processor --payload '{\"Records\":[{\"EventSource\":\"aws:sns\",\"Sns\":{\"Message\":\"{\\\"document_id\\\":\\\"0032f6cb_f0caef34\\\",\\\"status\\\":\\\"completed\\\"}\"}}]}' /tmp/kg_test_result.json"
echo ""
echo "  # Check CloudWatch logs:"
echo "  aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/document-structure-kg'"
