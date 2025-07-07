#!/bin/bash

# Climate Risk RAG Selective Data Migration Script (CORRECTED)
# Migrates ONLY a representative sample for cost-effective testing:
# - 1,000 sample documents (not all 15,176)
# - Corresponding chunks, embeddings, and NER results for sample documents only
# - Estimated cost: ~$20/month (not $88/month)

set -e

echo "🌍 Climate Risk RAG - Selective Data Migration (CORRECTED)"
echo "=========================================================="

# Configuration
LOCAL_DATA_PATH="/Volumes/G-RAID Photo 24TB/climate_risk_rag"
AWS_REGION="us-west-2"
AWS_PROFILE="solve-global"
SAMPLE_SIZE=1000            # Number of documents to migrate (NOT all documents)
MAX_WORKERS=4               # Reduced for selective migration

# Get AWS account for bucket naming
AWS_ACCOUNT=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)

# Bucket names (will be created by CDK - using actual CDK bucket names)
DOCUMENTS_BUCKET="climate-risk-documents-${AWS_ACCOUNT}-${AWS_REGION}"
EXTRACTED_TEXT_BUCKET="climate-risk-extracted-text-${AWS_ACCOUNT}-${AWS_REGION}"
CHUNKS_BUCKET="climate-risk-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
EMBEDDINGS_BUCKET="climate-risk-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
NER_RESULTS_BUCKET="climate-risk-ner-results-${AWS_ACCOUNT}-${AWS_REGION}"

echo "📍 CORRECTED Selective Migration Configuration:"
echo "  Local Path: $LOCAL_DATA_PATH"
echo "  AWS Region: $AWS_REGION"
echo "  Documents Bucket: $DOCUMENTS_BUCKET"
echo "  Chunks Bucket: $CHUNKS_BUCKET"
echo "  Embeddings Bucket: $EMBEDDINGS_BUCKET"
echo "  Artifacts Bucket: $ARTIFACTS_BUCKET"
echo "  Sample Size: $SAMPLE_SIZE documents (NOT all 15,176)"
echo "  Max Workers: $MAX_WORKERS"
echo ""
echo "📦 What will be migrated (CORRECTED SCOPE):"
echo "  ✅ Sample documents ($SAMPLE_SIZE PDFs, ~3GB)"
echo "  ✅ Sample chunks (~280,000 files, ~8GB)"
echo "  ✅ Sample embeddings (~280,000 files, ~9GB)"
echo "  ✅ Sample NER results (~$SAMPLE_SIZE files, ~3MB)"
echo "  📊 Total: ~20GB, estimated cost: $20/month"
echo ""
echo "❌ What will NOT be migrated:"
echo "  ❌ All 15,176 documents (would cost $200+/month)"
echo "  ❌ All 4.24M chunks (would be 120GB+)"
echo "  ❌ All embeddings (would be 135GB+)"
echo ""

# Check if local data exists
if [ ! -d "$LOCAL_DATA_PATH" ]; then
    echo "❌ Local data path not found: $LOCAL_DATA_PATH"
    echo "Please update LOCAL_DATA_PATH in this script"
    exit 1
fi

# Check if buckets exist
echo "🔍 Checking S3 buckets..."
if ! aws s3 ls "s3://$DOCUMENTS_BUCKET" --profile $AWS_PROFILE > /dev/null 2>&1; then
    echo "❌ Documents bucket not found: $DOCUMENTS_BUCKET"
    echo "Please deploy the infrastructure first: cd cdk && cdk deploy --all --profile $AWS_PROFILE"
    exit 1
fi

if ! aws s3 ls "s3://$CHUNKS_BUCKET" --profile $AWS_PROFILE > /dev/null 2>&1; then
    echo "❌ Chunks bucket not found: $CHUNKS_BUCKET"
    echo "Please deploy the infrastructure first: cd cdk && cdk deploy --all --profile $AWS_PROFILE"
    exit 1
fi

echo "✅ S3 buckets found"

# Check if sample selection exists
SAMPLE_FILE="migration/sample_documents_${SAMPLE_SIZE}.json"
if [ ! -f "$SAMPLE_FILE" ]; then
    echo "📋 Generating representative document sample..."
    cd migration
    python3 generate_sample_selection.py \
        --local-path "$LOCAL_DATA_PATH" \
        --sample-size $SAMPLE_SIZE \
        --strategy stratified \
        --output "sample_documents_${SAMPLE_SIZE}.json"
    cd ..
    echo "✅ Sample selection generated: $SAMPLE_FILE"
else
    echo "✅ Using existing sample selection: $SAMPLE_FILE"
fi

# Install migration dependencies
echo "📦 Installing migration dependencies..."
cd migration
pip install -r requirements.txt
cd ..

# Show actual data analysis for SAMPLE
echo ""
echo "📊 Sample Data Analysis:"
echo "Total documents available: $(ls "$LOCAL_DATA_PATH/data/raw"/*.pdf 2>/dev/null | wc -l) PDFs"
echo "Sample documents to migrate: $SAMPLE_SIZE PDFs"
echo "Expected sample chunks: ~$((SAMPLE_SIZE * 280)) files"
echo "Expected sample embeddings: ~$((SAMPLE_SIZE * 280)) files"
echo "Expected sample NER files: ~$SAMPLE_SIZE files"

# Perform dry run first
echo ""
echo "🧪 Performing dry run for SAMPLE migration..."
python3 migration/selective_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --chunks-bucket "$CHUNKS_BUCKET" \
    --embeddings-bucket "$EMBEDDINGS_BUCKET" \
    --ner-results-bucket "$NER_RESULTS_BUCKET" \
    --extracted-text-bucket "$EXTRACTED_TEXT_BUCKET" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --sample-file "$SAMPLE_FILE" \
    --max-workers "$MAX_WORKERS" \
    --dry-run

echo ""
echo "⚠️  IMPORTANT: This is a TRUE SELECTIVE migration for testing."
echo "   - Only $SAMPLE_SIZE documents will be migrated (not all 15,176)"
echo "   - Only chunks/embeddings for these $SAMPLE_SIZE documents"
echo "   - Designed for cost-effective AWS vs POC comparison"
echo "   - Estimated duration: 2-4 hours"
echo "   - Estimated monthly cost: ~$20 (not $88)"
echo ""
read -p "🤔 Proceed with corrected selective migration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

# Perform actual migration
echo ""
echo "🚀 Starting CORRECTED selective data migration..."
echo "This will take approximately 2-4 hours for $SAMPLE_SIZE documents..."

python3 migration/selective_migration.py \
    --local-path "$LOCAL_DATA_PATH" \
    --documents-bucket "$DOCUMENTS_BUCKET" \
    --chunks-bucket "$CHUNKS_BUCKET" \
    --embeddings-bucket "$EMBEDDINGS_BUCKET" \
    --ner-results-bucket "$NER_RESULTS_BUCKET" \
    --extracted-text-bucket "$EXTRACTED_TEXT_BUCKET" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --sample-file "$SAMPLE_FILE" \
    --max-workers "$MAX_WORKERS"

echo ""
echo "✅ Corrected selective migration completed!"
echo ""
echo "📋 What was actually migrated:"
echo "✅ Sample documents ($SAMPLE_SIZE PDFs) → s3://$DOCUMENTS_BUCKET/documents/"
echo "✅ Sample chunks (~$((SAMPLE_SIZE * 280)) files) → s3://$ARTIFACTS_BUCKET/chunks/"
echo "✅ Sample embeddings (~$((SAMPLE_SIZE * 280)) files) → s3://$ARTIFACTS_BUCKET/embeddings/"
echo "✅ Sample NER results (~$SAMPLE_SIZE files) → s3://$ARTIFACTS_BUCKET/ner_results/"
echo "✅ Sample metadata → s3://$ARTIFACTS_BUCKET/metadata/"
echo ""
echo "💰 Estimated monthly cost: ~$20 (storage only)"
echo "📊 Total storage used: ~20GB"
echo ""
echo "📋 Next Steps for Testing:"
echo "1. Check migration logs: migration/selective_migration.log"
echo "2. Run validation: python testing/validate_selective_migration.py"
echo "3. Start performance testing: python testing/performance_tests.py"
echo "4. Compare with POC: python testing/comparison_tests.py"
echo ""
echo "🎯 After successful validation, consider full migration with:"
echo "   ./migrate_data.sh  # Full migration script"
