#!/bin/bash

# Cleanup and Recreate S3 Buckets with Correct Naming (Fixed Length)
# Deletes old climate-risk-* buckets and creates new solve-global-kr-* buckets
# (kr = knowledge repository, shortened to fit S3 63-character limit)

set -e

echo "🧹 S3 Bucket Cleanup and Recreation (Fixed)"
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

echo "📍 Account: $AWS_ACCOUNT, Region: $AWS_REGION, Profile: $AWS_PROFILE"

# Define old bucket names (to delete) - any remaining
OLD_BUCKETS=(
    "climate-risk-documents-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-extracted-text-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-ner-results-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-knowledge-graph-data-${AWS_ACCOUNT}-${AWS_REGION}"
    "climate-risk-query-cache-${AWS_ACCOUNT}-${AWS_REGION}"
)

# Define new bucket names (shortened to fit 63-char limit)
# solve-global-kr = solve-global knowledge repository
NEW_BUCKETS=(
    "solve-global-kr-documents-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-text-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-chunks-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-embeddings-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-ner-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-kg-data-${AWS_ACCOUNT}-${AWS_REGION}"
    "solve-global-kr-cache-${AWS_ACCOUNT}-${AWS_REGION}"
)

echo ""
echo "📏 Checking bucket name lengths..."
for bucket in "${NEW_BUCKETS[@]}"; do
    length=$(echo -n "$bucket" | wc -c)
    echo "  $bucket: $length characters"
    if [ $length -gt 63 ]; then
        echo "    ❌ Too long! (max 63 characters)"
        exit 1
    fi
done
echo "  ✅ All bucket names are within 63-character limit"

echo ""
echo "🗑️  Checking for any remaining old buckets..."

for bucket in "${OLD_BUCKETS[@]}"; do
    # Check if bucket exists
    if aws s3api head-bucket --bucket "$bucket" --profile $AWS_PROFILE 2>/dev/null; then
        echo "  Found remaining bucket: $bucket - deleting..."
        aws s3 rm "s3://$bucket" --recursive --profile $AWS_PROFILE 2>/dev/null || true
        aws s3api delete-bucket --bucket "$bucket" --profile $AWS_PROFILE 2>/dev/null || true
        echo "    ✅ Deleted: $bucket"
    fi
done

echo ""
echo "🪣 Creating new solve-global-kr-* buckets..."

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
echo "📋 New buckets created (solve-global-kr = solve-global knowledge repository):"
for bucket in "${NEW_BUCKETS[@]}"; do
    echo "  ✅ $bucket"
done
echo ""
echo "📝 Bucket naming convention:"
echo "  solve-global-kr = Solve Global Knowledge Repository"
echo "  kr = knowledge repository (abbreviated for length)"
echo "  text = extracted-text (abbreviated)"
echo "  ner = ner-results (abbreviated)"
echo "  kg-data = knowledge-graph-data (abbreviated)"
echo ""
echo "🚀 Ready for data migration with correct bucket names!"
echo "   Next: Update scripts to use new bucket names"
