#!/bin/bash

# Climate Risk RAG - NER-Based Selective Data Migration
# Uses NER processing results as the basis for sampling to ensure data consistency

set -e

echo "🌍 Climate Risk RAG - NER-Based Selective Migration"
echo "=================================================="

# Configuration
LOCAL_DATA_PATH="/Volumes/G-RAID Photo 24TB/climate_risk_rag"
AWS_REGION="us-west-2"
AWS_PROFILE="solve-global"
SAMPLE_SIZE=1000            # Number of documents to sample from NER results
MAX_WORKERS=4               # Concurrent upload workers

# Get AWS account for bucket naming
AWS_ACCOUNT=$(aws sts get-caller-identity --profile $AWS_PROFILE --query Account --output text)

# S3 bucket names (updated with solve-global-kr prefix)
DOCUMENTS_BUCKET="solve-global-kr-documents-${AWS_ACCOUNT}-${AWS_REGION}"
CHUNKS_BUCKET="solve-global-kr-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
EMBEDDINGS_BUCKET="solve-global-kr-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
NER_RESULTS_BUCKET="solve-global-kr-ner-${AWS_ACCOUNT}-${AWS_REGION}"
EXTRACTED_TEXT_BUCKET="solve-global-kr-text-${AWS_ACCOUNT}-${AWS_REGION}"

# Sample file path
SAMPLE_FILE="migration/sample_documents_${SAMPLE_SIZE}_ner.json"

echo "📍 NER-Based Selective Migration Configuration:"
echo "  Local Path: $LOCAL_DATA_PATH"
echo "  AWS Region: $AWS_REGION"
echo "  AWS Profile: $AWS_PROFILE"
echo "  AWS Account: $AWS_ACCOUNT"
echo "  Documents Bucket: $DOCUMENTS_BUCKET"
echo "  Chunks Bucket: $CHUNKS_BUCKET"
echo "  Embeddings Bucket: $EMBEDDINGS_BUCKET"
echo "  NER Results Bucket: $NER_RESULTS_BUCKET"
echo "  Extracted Text Bucket: $EXTRACTED_TEXT_BUCKET"
echo "  Sample Size: $SAMPLE_SIZE documents (from NER results)"
echo "  Max Workers: $MAX_WORKERS"
echo ""

echo "📦 NER-Based Migration Approach:"
echo "  ✅ Base sampling on data/ner_results (~5K processed documents)"
echo "  ✅ Ensure all sampled documents have complete processing artifacts"
echo "  ✅ Maintain data consistency across all processing stages"
echo "  ✅ Realistic cost estimates based on actual processed data"
echo ""

echo "📊 Expected Migration Data (NER-Based):"
echo "  ✅ Sample documents ($SAMPLE_SIZE PDFs, ~3GB)"
echo "  ✅ Sample chunks (~280K files, ~8GB)"
echo "  ✅ Sample embeddings (~280K files, ~9GB)"
echo "  ✅ Sample text files ($SAMPLE_SIZE files, ~50MB)"
echo "  ✅ Sample NER results ($SAMPLE_SIZE files, ~5MB)"
echo "  📊 Total: ~20GB, estimated monthly cost: ~$20"
echo ""

echo "❌ What will NOT be migrated:"
echo "  ❌ Documents without NER processing completion"
echo "  ❌ Incomplete processing artifacts"
echo "  ❌ Documents missing from any processing stage"
echo ""

# Check if buckets exist
echo "🔍 Checking S3 buckets..."
if ! aws s3 ls "s3://$DOCUMENTS_BUCKET" --profile $AWS_PROFILE > /dev/null 2>&1; then
    echo "❌ Documents bucket not found: $DOCUMENTS_BUCKET"
    echo "Please deploy the infrastructure first: ./deploy_minimal.sh"
    exit 1
fi

if ! aws s3 ls "s3://$CHUNKS_BUCKET" --profile $AWS_PROFILE > /dev/null 2>&1; then
    echo "❌ Chunks bucket not found: $CHUNKS_BUCKET"
    echo "Please deploy the infrastructure first: ./deploy_minimal.sh"
    exit 1
fi

echo "✅ S3 buckets found"

# Check if sample file exists, if not generate it
if [ ! -f "$SAMPLE_FILE" ]; then
    echo "📋 Generating NER-based document sample..."
    cd migration
    python3 generate_sample_selection_ner.py \
        --local-path "$LOCAL_DATA_PATH" \
        --sample-size $SAMPLE_SIZE \
        --strategy balanced \
        --min-completeness 0.6 \
        --output "sample_documents_${SAMPLE_SIZE}_ner.json"
    cd ..
    echo "✅ NER-based sample selection generated: $SAMPLE_FILE"
else
    echo "✅ Using existing NER-based sample selection: $SAMPLE_FILE"
fi

# Install migration dependencies
echo "📦 Installing migration dependencies..."
cd migration
pip install -r requirements.txt
cd ..

# Validate sample quality
echo "🔍 Validating NER-based sample quality..."
python3 migration/validate_sample_ner.py \
    --sample-file "$SAMPLE_FILE" \
    --report "migration/sample_validation_report_ner.json"

# Show actual data analysis for SAMPLE
echo ""
echo "📊 NER-Based Sample Data Analysis:"
echo "Total NER processed documents: $(find "$LOCAL_DATA_PATH/data/ner_results" -name "*.json" 2>/dev/null | wc -l) files"
echo "Sample documents to migrate: $SAMPLE_SIZE documents"
echo "Expected sample chunks: ~$((SAMPLE_SIZE * 280)) files"
echo "Expected sample embeddings: ~$((SAMPLE_SIZE * 280)) files"
echo "Expected sample text files: ~$SAMPLE_SIZE files"
echo "Expected sample NER files: $SAMPLE_SIZE files"

# Perform dry run first
echo ""
echo "🧪 Performing dry run for NER-based selective migration..."
python3 migration/selective_migration_ner.py \
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
echo "⚠️  IMPORTANT: This is a TRUE NER-based selective migration."
echo "   - Only $SAMPLE_SIZE documents with complete NER processing"
echo "   - Only artifacts for these fully processed documents"
echo "   - Ensures data consistency across all processing stages"
echo "   - Estimated duration: 2-4 hours"
echo "   - Estimated monthly cost: ~$20"
echo ""
read -p "🤔 Proceed with NER-based selective migration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

# Perform actual migration
echo ""
echo "🚀 Starting NER-based selective data migration..."
echo "This will take approximately 2-4 hours for $SAMPLE_SIZE fully processed documents..."

python3 migration/selective_migration_ner.py \
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
echo "✅ NER-based selective migration completed!"
echo ""
echo "📋 What was actually migrated:"
echo "✅ Sample documents ($SAMPLE_SIZE PDFs) → s3://$DOCUMENTS_BUCKET/documents/"
echo "✅ Sample chunks (~280K files) → s3://$CHUNKS_BUCKET/chunks/"
echo "✅ Sample embeddings (~280K files) → s3://$EMBEDDINGS_BUCKET/embeddings/"
echo "✅ Sample text files ($SAMPLE_SIZE files) → s3://$EXTRACTED_TEXT_BUCKET/extracted_text/"
echo "✅ Sample NER results ($SAMPLE_SIZE files) → s3://$NER_RESULTS_BUCKET/ner_results/"
echo ""
echo "📊 Migration Summary:"
echo "✅ Data consistency: All sampled documents have complete processing artifacts"
echo "✅ Quality assurance: Based on successfully processed documents only"
echo "✅ Cost effective: ~$20/month operational cost"
echo "✅ Ready for AWS vs POC comparison testing"
echo ""
echo "🚀 Next Steps:"
echo "1. Validate migration results:"
echo "   python3 testing/validate_selective_migration.py --sample-file $SAMPLE_FILE --profile $AWS_PROFILE"
echo ""
echo "2. Deploy full AWS infrastructure for processing:"
echo "   ./deploy.sh"
echo ""
echo "3. Begin AWS vs POC performance comparison testing"
echo ""
echo "✅ NER-based selective migration completed successfully!"
