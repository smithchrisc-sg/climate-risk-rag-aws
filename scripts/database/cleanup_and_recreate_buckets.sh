#!/bin/bash

# Cleanup and Recreate S3 Buckets with Correct Naming
# Deletes old climate-risk-* buckets and creates new solve-global-knowledge-repository-* buckets

set -e

echo "🧹 S3 Bucket Cleanup and Recreation"
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

echo "📍 Account: $AWS_ACCOUNT, Region: $AWS_REGION, Profile: $AWS_PROFILE"

# Define old bucket names (to delete)
OLD_BUCKETS=(
    "climate-risk-documents-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-extracted-text-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-ner-results-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-knowledge-graph-data-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-query-cache-${AWS_ACCOUNT}-${AWS_REGION}"
)

# Define new bucket names (to create)
NEW_BUCKETS=(
    "solve-global-knowledge-repository-documents-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-knowledge-repository-extracted-text-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-knowledge-repository-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-knowledge-repository-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-knowledge-repository-ner-results-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-knowledge-repository-knowledge-graph-data-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-knowledge-repository-query-cache-${AWS_ACCOUNT}-${AWS_REGION}"
)

echo ""
echo "🗑️  Deleting old climate-risk-* buckets..."

for bucket in "${OLD_BUCKETS[@]}"; do
    echo "  Checking bucket: $bucket"
    
    # Check if bucket exists
    if aws s3api head-bucket --bucket "$bucket" --profile $AWS_PROFILE 2>/dev/null; then
        echo "    🗑️  Deleting bucket: $bucket"
        
        # First, delete all objects in the bucket (if any)
        echo "    📦 Removing all objects from bucket..."
        aws s3 rm "s3://$bucket" --recursive --profile $AWS_PROFILE 2>/dev/null || true
        
        # Delete all versions and delete markers (if versioning was enabled)
        echo "    🔄 Removing all versions and delete markers..."
        aws s3api list-object-versions --bucket "$bucket" --profile $AWS_PROFILE --output json 2>/dev/null | \
        jq -r '.Versions[]?, .DeleteMarkers[]? | select(.Key != null) | "\(.Key)\t\(.VersionId)"' 2>/dev/null | \
        while IFS=$'\t' read -r key version_id; do
            if [ ! -z "$key" ] && [ ! -z "$version_id" ]; then
                aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version_id" --profile $AWS_PROFILE 2>/dev/null || true
            fi
        done || true
        
        # Now delete the bucket
        if aws s3api delete-bucket --bucket "$bucket" --profile $AWS_PROFILE 2>/dev/null; then
            echo "    ✅ Deleted bucket: $bucket"
        else
            echo "    ⚠️  Could not delete bucket: $bucket (may not exist or have remaining objects)"
        fi
    else
        echo "    ℹ️  Bucket does not exist: $bucket"
    fi
done

echo ""
echo "🪣 Creating new solve-global-knowledge-repository-* buckets..."

for bucket in "${NEW_BUCKETS[@]}"; do
    echo "  Creating bucket: $bucket"
    
    # Check if bucket already exists
    if aws s3api head-bucket --bucket "$bucket" --profile $AWS_PROFILE 2>/dev/null; then
        echo "    ✅ Bucket already exists: $bucket"
    else
        # Create bucket
        if aws s3api create-bucket \
            --bucket "$bucket" \
            --region "$AWS_REGION" \
            --profile $AWS_PROFILE \
            --create-bucket-configuration LocationConstraint="$AWS_REGION" 2>/dev/null; then
            echo "    ✅ Created bucket: $bucket"
            
            # Enable versioning
            aws s3api put-bucket-versioning \
                --bucket "$bucket" \
                --versioning-configuration Status=Enabled \
                --profile $AWS_PROFILE
            
            # Block public access
            aws s3api put-public-access-block \
                --bucket "$bucket" \
                --public-access-block-configuration \
                "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
                --profile $AWS_PROFILE
            
            # Enable server-side encryption
            aws s3api put-bucket-encryption \
                --bucket "$bucket" \
                --server-side-encryption-configuration \
                '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}' \
                --profile $AWS_PROFILE
                
        else
            echo "    ❌ Failed to create bucket: $bucket"
            exit 1
        fi
    fi
done

echo ""
echo "✅ Bucket Cleanup and Recreation Complete!"
echo ""
echo "📋 New buckets created:"
for bucket in "${NEW_BUCKETS[@]}"; do
    echo "  ✅ $bucket"
done
echo ""
echo "🚀 Ready for data migration with correct bucket names!"
echo "   Run: ./migrate_data_selective_ner.sh"
