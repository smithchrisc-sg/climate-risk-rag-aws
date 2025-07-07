#!/bin/bash

# Cross-Region S3 Migration Script
# Migrates data from us-west-2 to us-east-1 buckets

set -e

# Ensure we're using bash 4+ for associative arrays
if [ "${BASH_VERSION%%.*}" -lt 4 ]; then
    echo "This script requires Bash 4.0 or later for associative arrays"
    exit 1
fi

PROFILE="solve-global"
SOURCE_REGION="us-west-2"
DEST_REGION="us-east-1"
ACCOUNT_ID="861276078413"

# Bucket mappings
declare -A BUCKET_MAPPING
BUCKET_MAPPING["solve-global-kr-documents-861276078413-us-west-2"]="solve-global-kr-documents-861276078413-us-east-1"
BUCKET_MAPPING["solve-global-kr-text-861276078413-us-west-2"]="solve-global-kr-text-861276078413-us-east-1"
BUCKET_MAPPING["solve-global-kr-chunks-861276078413-us-west-2"]="solve-global-kr-chunks-861276078413-us-east-1"
BUCKET_MAPPING["solve-global-kr-embeddings-861276078413-us-west-2"]="solve-global-kr-embeddings-861276078413-us-east-1"
BUCKET_MAPPING["solve-global-kr-ner-861276078413-us-west-2"]="solve-global-kr-ner-861276078413-us-east-1"
BUCKET_MAPPING["solve-global-kr-kg-data-861276078413-us-west-2"]="solve-global-kr-kg-data-861276078413-us-east-1"
BUCKET_MAPPING["solve-global-kr-cache-861276078413-us-west-2"]="solve-global-kr-cache-861276078413-us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get bucket size
get_bucket_size() {
    local bucket=$1
    local region=$2
    
    aws s3api list-objects-v2 \
        --bucket "$bucket" \
        --region "$region" \
        --profile "$PROFILE" \
        --query 'sum(Contents[].Size)' \
        --output text 2>/dev/null || echo "0"
}

# Function to get object count
get_object_count() {
    local bucket=$1
    local region=$2
    
    aws s3api list-objects-v2 \
        --bucket "$bucket" \
        --region "$region" \
        --profile "$PROFILE" \
        --query 'length(Contents)' \
        --output text 2>/dev/null || echo "0"
}

# Function to migrate a bucket
migrate_bucket() {
    local source_bucket=$1
    local dest_bucket=$2
    
    log "Starting migration: $source_bucket -> $dest_bucket"
    
    # Check if source bucket exists and has content
    local source_size=$(get_bucket_size "$source_bucket" "$SOURCE_REGION")
    local source_count=$(get_object_count "$source_bucket" "$SOURCE_REGION")
    
    if [ "$source_size" = "0" ] || [ "$source_count" = "0" ]; then
        warning "Source bucket $source_bucket is empty or doesn't exist. Skipping."
        return 0
    fi
    
    log "Source bucket: $source_count objects, $(($source_size / 1024 / 1024)) MB"
    
    # Check if destination bucket exists
    if ! aws s3api head-bucket --bucket "$dest_bucket" --region "$DEST_REGION" --profile "$PROFILE" 2>/dev/null; then
        error "Destination bucket $dest_bucket doesn't exist!"
        return 1
    fi
    
    # Perform the sync
    log "Syncing $source_bucket to $dest_bucket..."
    
    aws s3 sync \
        "s3://$source_bucket" \
        "s3://$dest_bucket" \
        --source-region "$SOURCE_REGION" \
        --region "$DEST_REGION" \
        --profile "$PROFILE" \
        --delete \
        --exact-timestamps
    
    if [ $? -eq 0 ]; then
        # Verify migration
        local dest_size=$(get_bucket_size "$dest_bucket" "$DEST_REGION")
        local dest_count=$(get_object_count "$dest_bucket" "$DEST_REGION")
        
        log "Destination bucket: $dest_count objects, $(($dest_size / 1024 / 1024)) MB"
        
        if [ "$source_count" -eq "$dest_count" ]; then
            success "Migration completed successfully: $source_bucket -> $dest_bucket"
            return 0
        else
            error "Object count mismatch! Source: $source_count, Dest: $dest_count"
            return 1
        fi
    else
        error "Migration failed for $source_bucket"
        return 1
    fi
}

# Main migration function
main() {
    log "Starting cross-region S3 migration from $SOURCE_REGION to $DEST_REGION"
    
    # Check AWS CLI and profile
    if ! aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
        error "AWS profile '$PROFILE' not configured or invalid"
        exit 1
    fi
    
    success "AWS profile '$PROFILE' verified"
    
    # Migration summary
    log "Migration plan:"
    for source_bucket in "${!BUCKET_MAPPING[@]}"; do
        dest_bucket="${BUCKET_MAPPING[$source_bucket]}"
        echo "  $source_bucket -> $dest_bucket"
    done
    
    # Confirm before proceeding
    echo
    read -p "Do you want to proceed with the migration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Migration cancelled by user"
        exit 0
    fi
    
    # Perform migrations
    local failed_migrations=0
    local total_migrations=${#BUCKET_MAPPING[@]}
    
    for source_bucket in "${!BUCKET_MAPPING[@]}"; do
        dest_bucket="${BUCKET_MAPPING[$source_bucket]}"
        
        if ! migrate_bucket "$source_bucket" "$dest_bucket"; then
            ((failed_migrations++))
        fi
        
        echo "----------------------------------------"
    done
    
    # Summary
    log "Migration Summary:"
    log "Total buckets: $total_migrations"
    log "Successful: $((total_migrations - failed_migrations))"
    log "Failed: $failed_migrations"
    
    if [ $failed_migrations -eq 0 ]; then
        success "All migrations completed successfully!"
    else
        error "$failed_migrations migrations failed. Please check the logs above."
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --dry-run)
        log "DRY RUN MODE - No actual migration will be performed"
        # Show what would be migrated
        for source_bucket in "${!BUCKET_MAPPING[@]}"; do
            dest_bucket="${BUCKET_MAPPING[$source_bucket]}"
            source_size=$(get_bucket_size "$source_bucket" "$SOURCE_REGION")
            source_count=$(get_object_count "$source_bucket" "$SOURCE_REGION")
            
            if [ "$source_size" != "0" ] && [ "$source_count" != "0" ]; then
                log "Would migrate: $source_bucket ($source_count objects, $(($source_size / 1024 / 1024)) MB) -> $dest_bucket"
            else
                warning "Would skip: $source_bucket (empty or doesn't exist)"
            fi
        done
        ;;
    --help|-h)
        echo "Usage: $0 [--dry-run|--help]"
        echo ""
        echo "Cross-region S3 migration script"
        echo ""
        echo "Options:"
        echo "  --dry-run    Show what would be migrated without performing migration"
        echo "  --help       Show this help message"
        echo ""
        echo "This script migrates S3 buckets from us-west-2 to us-east-1"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
