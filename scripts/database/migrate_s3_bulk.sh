#!/bin/bash

# Optimized Bulk S3 Migration Script
# Uses parallel transfers and optimized settings for large datasets

set -e

PROFILE="solve-global"
SOURCE_REGION="us-west-2"
DEST_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Optimized bulk sync function
bulk_sync() {
    local source_bucket=$1
    local dest_bucket=$2
    
    log "Starting optimized bulk sync: $source_bucket -> $dest_bucket"
    
    # Use optimized AWS CLI settings for bulk transfers
    aws configure set default.s3.max_concurrent_requests 20 --profile "$PROFILE"
    aws configure set default.s3.max_bandwidth 1GB/s --profile "$PROFILE"
    aws configure set default.s3.multipart_threshold 64MB --profile "$PROFILE"
    aws configure set default.s3.multipart_chunksize 16MB --profile "$PROFILE"
    aws configure set default.s3.max_queue_size 10000 --profile "$PROFILE"
    
    # Perform optimized sync
    time aws s3 sync \
        "s3://$source_bucket" \
        "s3://$dest_bucket" \
        --source-region "$SOURCE_REGION" \
        --region "$DEST_REGION" \
        --profile "$PROFILE" \
        --no-progress \
        --only-show-errors \
        --storage-class STANDARD
    
    if [ $? -eq 0 ]; then
        success "Bulk sync completed: $source_bucket -> $dest_bucket"
        return 0
    else
        error "Bulk sync failed: $source_bucket"
        return 1
    fi
}

# Alternative: Use S3 Batch Operations (for very large datasets)
create_batch_job() {
    local source_bucket=$1
    local dest_bucket=$2
    
    log "Creating S3 Batch Operations job for: $source_bucket -> $dest_bucket"
    
    # Create manifest of all objects
    aws s3api list-objects-v2 \
        --bucket "$source_bucket" \
        --region "$SOURCE_REGION" \
        --profile "$PROFILE" \
        --query 'Contents[].{Key: Key}' \
        --output json > "/tmp/${source_bucket}_manifest.json"
    
    # Upload manifest to S3
    aws s3 cp "/tmp/${source_bucket}_manifest.json" \
        "s3://$dest_bucket/batch-manifests/${source_bucket}_manifest.json" \
        --profile "$PROFILE"
    
    log "Manifest created for batch job. You can create the batch job in AWS Console."
    log "Manifest location: s3://$dest_bucket/batch-manifests/${source_bucket}_manifest.json"
}

# Main migration with all buckets in parallel
migrate_all_parallel() {
    log "Starting parallel migration of all buckets"
    
    # List of bucket pairs
    local buckets=(
        "solve-global-kr-text-861276078413-us-west-2:solve-global-kr-text-861276078413-us-east-1"
        "solve-global-kr-chunks-861276078413-us-west-2:solve-global-kr-chunks-861276078413-us-east-1"
        "solve-global-kr-embeddings-861276078413-us-west-2:solve-global-kr-embeddings-861276078413-us-east-1"
        "solve-global-kr-ner-861276078413-us-west-2:solve-global-kr-ner-861276078413-us-east-1"
        "solve-global-kr-kg-data-861276078413-us-west-2:solve-global-kr-kg-data-861276078413-us-east-1"
        "solve-global-kr-cache-861276078413-us-west-2:solve-global-kr-cache-861276078413-us-east-1"
    )
    
    # Start all migrations in parallel
    local pids=()
    
    for bucket_pair in "${buckets[@]}"; do
        local source_bucket=$(echo "$bucket_pair" | cut -d: -f1)
        local dest_bucket=$(echo "$bucket_pair" | cut -d: -f2)
        
        log "Starting parallel migration: $source_bucket"
        bulk_sync "$source_bucket" "$dest_bucket" &
        pids+=($!)
    done
    
    # Wait for all parallel jobs to complete
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            ((failed++))
        fi
    done
    
    if [ $failed -eq 0 ]; then
        success "All parallel migrations completed successfully!"
    else
        error "$failed migrations failed"
        return 1
    fi
}

# Single bucket optimized sync
migrate_single() {
    local source_bucket=$1
    local dest_bucket=$2
    
    if [ -z "$source_bucket" ] || [ -z "$dest_bucket" ]; then
        error "Usage: $0 --single <source-bucket> <dest-bucket>"
        exit 1
    fi
    
    bulk_sync "$source_bucket" "$dest_bucket"
}

# Main function
main() {
    log "AWS S3 Optimized Bulk Migration"
    
    # Verify AWS profile
    if ! aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
        error "AWS profile '$PROFILE' not configured"
        exit 1
    fi
    
    success "AWS profile verified"
    
    case "${1:-}" in
        --parallel)
            migrate_all_parallel
            ;;
        --single)
            migrate_single "$2" "$3"
            ;;
        --batch)
            # For extremely large datasets, use S3 Batch Operations
            log "S3 Batch Operations mode - creating manifests"
            create_batch_job "solve-global-kr-chunks-861276078413-us-west-2" "solve-global-kr-chunks-861276078413-us-east-1"
            create_batch_job "solve-global-kr-embeddings-861276078413-us-west-2" "solve-global-kr-embeddings-861276078413-us-east-1"
            ;;
        --help|-h)
            echo "Usage: $0 [--parallel|--single <src> <dest>|--batch|--help]"
            echo ""
            echo "Optimized S3 bulk migration options:"
            echo "  --parallel    Migrate all buckets in parallel (fastest)"
            echo "  --single      Migrate single bucket pair"
            echo "  --batch       Create S3 Batch Operations jobs (for massive datasets)"
            echo "  --help        Show this help"
            ;;
        *)
            log "Starting sequential optimized migration"
            
            # Sequential but optimized migration
            local buckets=(
                "solve-global-kr-text-861276078413-us-west-2:solve-global-kr-text-861276078413-us-east-1"
                "solve-global-kr-chunks-861276078413-us-west-2:solve-global-kr-chunks-861276078413-us-east-1"
                "solve-global-kr-embeddings-861276078413-us-west-2:solve-global-kr-embeddings-861276078413-us-east-1"
                "solve-global-kr-ner-861276078413-us-west-2:solve-global-kr-ner-861276078413-us-east-1"
            )
            
            for bucket_pair in "${buckets[@]}"; do
                local source_bucket=$(echo "$bucket_pair" | cut -d: -f1)
                local dest_bucket=$(echo "$bucket_pair" | cut -d: -f2)
                
                bulk_sync "$source_bucket" "$dest_bucket"
                echo "----------------------------------------"
            done
            ;;
    esac
}

main "$@"
