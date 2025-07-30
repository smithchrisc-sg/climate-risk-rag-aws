#!/bin/bash

# Climate Risk RAG Selective Data Migration Script
# Migrates selected data for testing and comparison:
# - All documents (15,176 PDFs)
# - All embeddings (1.02M files, 32GB)
# - Flair NER results (91 files, 4.9MB)
# - Extracted text (15,155 files, 2.5GB)
# - Sample chunks (1,000 documents for comparison)

set -e

echo "🌍 Climate Risk RAG - Selective Data Migration"
echo "=============================================="

# Configuration
LOCAL_DATA_PATH="/Volumes/G-RAID Photo 24TB/climate_risk_rag"
AWS_REGION="us-east-1"
SAMPLE_CHUNKS=1000
MAX_WORKERS=8

# Get AWS account for bucket naming
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Bucket names (will be created by CDK)
DOCUMENTS_BUCKET="climate-risk-documents-${AWS_ACCOUNT}-${AWS_REGION}"
ARTIFACTS_BUCKET="climate-risk-artifacts-${AWS_ACCOUNT}-${AWS_REGION}"

echo "📍 Selective Migration Configuration:"
echo "  Local Path: $LOCAL_DATA_PATH"
echo "  AWS Region: $AWS_REGION"
echo "  Documents Bucket: $DOCUMENTS_BUCKET"
echo "  Artifacts Bucket: $ARTIFACTS_BUCKET"
echo "  Sample Chunks: $SAMPLE_CHUNKS documents"
echo "  Max Workers: $MAX_WORKERS"
echo ""
echo "📦 What will be migrated:"
echo "  ✅ All documents (15,176 PDFs, ~45GB)"
echo "  ✅ All embeddings (1.02M files, ~32GB)"
echo "  ✅ Flair NER results (91 files, ~5MB)"
echo "  ✅ Extracted text (15,155 files, ~2.5GB)"
echo "  ✅ Sample chunks ($SAMPLE_CHUNKS documents, ~8GB)"
echo "  📊 Total: ~88GB, estimated cost: $20/month"
echo ""

# Check if local data exists
if [ ! -d "$LOCAL_DATA_PATH" ]; then
    echo "❌ Local data path not found: $LOCAL_DATA_PATH"
    echo "Please update LOCAL_DATA_PATH in this script"
    exit 1
fi

# Check required directories
echo "🔍 Checking local data structure..."
if [ ! -d "$LOCAL_DATA_PATH/data/raw" ]; then
    echo "❌ Raw documents directory not found"
    exit 1
fi

if [ ! -d "$LOCAL_DATA_PATH/data/processed" ]; then
    echo "❌ Processed data directory not found"
    exit 1
fi

echo "✅ Local data structure verified"

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

# Show what will be migrated
echo ""
echo "📊 Data Analysis:"
echo "Documents: $(ls "$LOCAL_DATA_PATH/data/raw"/*.pdf 2>/dev/null | wc -l) PDFs"
echo "Embedding folders: $(ls -d "$LOCAL_DATA_PATH/data/processed/embeddings"/*/ 2>/dev/null | wc -l)"
echo "Flair NER files: $(ls "$LOCAL_DATA_PATH/data/processed/ner_Flair"/*.json 2>/dev/null | wc -l)"
echo "Text files: $(ls "$LOCAL_DATA_PATH/data/processed/text"/*.txt 2>/dev/null | wc -l)"
echo "Chunk folders available: $(ls -d "$LOCAL_DATA_PATH/data/chunks"/*/ 2>/dev/null | wc -l)"

# Perform dry run first
echo ""
echo "🧪 Performing dry run..."
python3 migration/selective_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --artifacts-bucket "$ARTIFACTS_BUCKET" \
    --region "$AWS_REGION" \
    --sample-chunks "$SAMPLE_CHUNKS" \
    --max-workers "$MAX_WORKERS" \
    --dry-run

echo ""
echo "⚠️  IMPORTANT: This is a SELECTIVE migration for testing purposes."
echo "   - Full chunk collection (4.24M files) will NOT be migrated"
echo "   - Only a sample of $SAMPLE_CHUNKS documents' chunks will be migrated"
echo "   - This is designed for AWS vs POC comparison testing"
echo "   - Estimated duration: 2-3 hours"
echo "   - Estimated monthly cost: ~$20 (time-limited for testing)"
echo ""
read -p "🤔 Proceed with selective migration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

# Perform actual migration
echo ""
echo "🚀 Starting selective data migration..."
echo "This will take approximately 2-3 hours..."

python3 migration/selective_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --artifacts-bucket "$ARTIFACTS_BUCKET" \
    --region "$AWS_REGION" \
    --sample-chunks "$SAMPLE_CHUNKS" \
    --max-workers "$MAX_WORKERS"

echo ""
echo "✅ Selective migration completed!"
echo ""
echo "📋 What was migrated:"
echo "✅ All documents → s3://$DOCUMENTS_BUCKET/documents/"
echo "✅ All embeddings → s3://$ARTIFACTS_BUCKET/processed_embeddings/"
echo "✅ Flair NER results → s3://$ARTIFACTS_BUCKET/processed_ner_flair/"
echo "✅ Extracted text → s3://$ARTIFACTS_BUCKET/processed_text/"
echo "✅ Sample chunks → s3://$ARTIFACTS_BUCKET/sample_chunks/"
echo "✅ Metadata → s3://$ARTIFACTS_BUCKET/metadata/"
echo ""
echo "📋 Next Steps for Testing:"
echo "1. Check migration logs: migration/selective_migration.log"
echo "2. Review migration summary: s3://$ARTIFACTS_BUCKET/selective_migration_summary.json"
echo "3. Start comparison testing:"
echo "   - Your embeddings vs AWS Titan embeddings"
echo "   - Your Flair NER vs AWS Comprehend"
echo "   - Your 5-sentence chunks vs AWS structured chunks"
echo "   - Your text extraction vs AWS Textract"
echo "4. Test document processing with new AWS pipeline"
echo "5. Use comparison framework to analyze results"
echo ""
echo "💰 Cost Management:"
echo "   - Current storage: ~$20/month (time-limited for testing)"
echo "   - After testing: delete artifacts, keep documents only (~$10/month)"
echo "   - Full production: implement chosen approach"
echo ""
echo "🎉 Your selective migration is ready for AWS vs POC comparison testing!"

# ⚠️⚠️⚠️ WARNING: THIS SCRIPT IS BROKEN ⚠️⚠️⚠️
# This script claims to do "selective" migration but actually migrates ALL data
# Cost: ~$88/month instead of claimed $20/month
# Use migrate_data_selective.sh instead
# ⚠️⚠️⚠️ DO NOT USE THIS SCRIPT ⚠️⚠️⚠️
