#!/bin/bash

# Minimal Climate Risk RAG AWS Deployment - S3 Buckets Only
# This creates just the S3 buckets needed for migration

set -e

echo "🌍 Climate Risk RAG - Minimal S3 Deployment"
echo "============================================"

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

# Define bucket names (updated with solve-global-kr prefix)
BUCKETS=(
    "solve-global-kr-documents-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-text-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-ner-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-kg-data-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-cache-${AWS_ACCOUNT}-${AWS_REGION}"
)

echo "🪣 Creating S3 buckets..."

for bucket in "${BUCKETS[@]}"; do
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
echo "✅ S3 Buckets Deployment Complete!"
echo ""
echo "📋 Created buckets:"
for bucket in "${BUCKETS[@]}"; do
    echo "  ✅ $bucket"
done
echo ""
echo "🚀 Ready for data migration!"
echo "   Run: ./migrate_data_selective_ner.sh"
