#!/bin/bash

# Climate Risk RAG Data Migration Script
# Migrates 15K+ documents from local data lake to AWS S3

set -e

echo "🌍 Climate Risk RAG - Data Migration"
echo "===================================="

# Configuration
LOCAL_DATA_PATH="/Volumes/G-RAID Photo 24TB/climate_risk_rag"
AWS_REGION="us-east-1"
BATCH_SIZE=50
MAX_WORKERS=8

# Get AWS account for bucket naming
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Bucket names (will be created by CDK)
DOCUMENTS_BUCKET="climate-risk-documents-${AWS_ACCOUNT}-${AWS_REGION}"
ARTIFACTS_BUCKET="climate-risk-artifacts-${AWS_ACCOUNT}-${AWS_REGION}"

echo "📍 Configuration:"
echo "  Local Path: $LOCAL_DATA_PATH"
echo "  AWS Region: $AWS_REGION"
echo "  Documents Bucket: $DOCUMENTS_BUCKET"
echo "  Artifacts Bucket: $ARTIFACTS_BUCKET"
echo "  Batch Size: $BATCH_SIZE"
echo "  Max Workers: $MAX_WORKERS"
echo ""

# Check if local data exists
if [ ! -d "$LOCAL_DATA_PATH" ]; then
    echo "❌ Local data path not found: $LOCAL_DATA_PATH"
    echo "Please update LOCAL_DATA_PATH in this script"
    exit 1
fi

# Check if buckets exist
echo "🔍 Checking S3 buckets..."
if ! aws s3 ls "s3://$DOCUMENTS_BUCKET" > /dev/null 2>&1; then
    echo "❌ Documents bucket not found: $DOCUMENTS_BUCKET"
    echo "Please deploy the infrastructure first: ./deploy.sh"
    exit 1
fi

if ! aws s3 ls "s3://$ARTIFACTS_BUCKET" > /dev/null 2>&1; then
    echo "❌ Artifacts bucket not found: $ARTIFACTS_BUCKET"
    echo "Please deploy the infrastructure first: ./deploy.sh"
    exit 1
fi

echo "✅ S3 buckets found"

# Install migration dependencies
echo "📦 Installing migration dependencies..."
cd migration
pip install -r requirements.txt
cd ..

# Perform dry run first
echo ""
echo "🧪 Performing dry run..."
python3 migration/bulk_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --artifacts-bucket "$ARTIFACTS_BUCKET" \
    --region "$AWS_REGION" \
    --batch-size "$BATCH_SIZE" \
    --max-workers "$MAX_WORKERS" \
    --dry-run

echo ""
read -p "🤔 Proceed with actual migration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

# Perform actual migration
echo ""
echo "🚀 Starting data migration..."
echo "This may take 30-60 minutes for 15K documents..."

python3 migration/bulk_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --artifacts-bucket "$ARTIFACTS_BUCKET" \
    --region "$AWS_REGION" \
    --batch-size "$BATCH_SIZE" \
    --max-workers "$MAX_WORKERS"

# Validate migration
echo ""
echo "🔍 Validating migration..."
python3 migration/validate_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --artifacts-bucket "$ARTIFACTS_BUCKET" \
    --region "$AWS_REGION" \
    --output-file "migration_validation_results.json"

echo ""
echo "✅ Migration completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Check migration logs: migration/bulk_migration.log"
echo "2. Review validation results: migration_validation_results.json"
echo "3. Test document processing:"
echo "   aws s3 cp s3://$DOCUMENTS_BUCKET/documents/[sample-doc].pdf /tmp/"
echo "4. Test the query API with uploaded documents"
echo ""
echo "🎉 Your 15K+ documents are now in AWS and ready for processing!"
