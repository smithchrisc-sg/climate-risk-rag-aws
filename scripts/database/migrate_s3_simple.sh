#!/bin/bash

# Simple S3 Migration Script (Bash 3.2 compatible)
# Migrates data from us-west-2 to us-east-1 buckets

set -e

PROFILE="solve-global"
SOURCE_REGION="us-west-2"
DEST_REGION="us-east-1"
ACCOUNT_ID="861276078413"

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

# Function to migrate a bucket
migrate_bucket() {
    local source_bucket=$1
    local dest_bucket=$2
    
    log "Starting migration: $source_bucket -> $dest_bucket"
    
    # Check if source bucket exists and has content
    local source_count=$(aws s3api list-objects-v2 \
        --bucket "$source_bucket" \
        --region "$SOURCE_REGION" \
        --profile "$PROFILE" \
        --query 'length(Contents)' \
        --output text 2>/dev/null || echo "0")
    
    if [ "$source_count" = "0" ] || [ "$source_count" = "null" ]; then
        warning "Source bucket $source_bucket is empty or doesn't exist. Skipping."
        return 0
    fi
    
    log "Source bucket has $source_count objects"
    
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
        --exact-timestamps
    
    if [ $? -eq 0 ]; then
        success "Migration completed successfully: $source_bucket -> $dest_bucket"
        return 0
    else
        error "Migration failed for $source_bucket"
        return 1
    fi
}

# Function to migrate documents bucket first
migrate_documents() {
    log "=== MIGRATING DOCUMENTS BUCKET FIRST ==="
    migrate_bucket "solve-global-kr-documents-861276078413-us-west-2" "solve-global-kr-documents-861276078413-us-east-1"
}

# Function to migrate all other buckets
migrate_all_others() {
    log "=== MIGRATING ALL OTHER BUCKETS ==="
    
    # List of other buckets to migrate
    local buckets=(
        "solve-global-kr-text-861276078413-us-west-2:solve-global-kr-text-861276078413-us-east-1"
        "solve-global-kr-chunks-861276078413-us-west-2:solve-global-kr-chunks-861276078413-us-east-1"
        "solve-global-kr-embeddings-861276078413-us-west-2:solve-global-kr-embeddings-861276078413-us-east-1"
        "solve-global-kr-ner-861276078413-us-west-2:solve-global-kr-ner-861276078413-us-east-1"
        "solve-global-kr-kg-data-861276078413-us-west-2:solve-global-kr-kg-data-861276078413-us-east-1"
        "solve-global-kr-cache-861276078413-us-west-2:solve-global-kr-cache-861276078413-us-east-1"
    )
    
    local failed_migrations=0
    
    for bucket_pair in "${buckets[@]}"; do
        local source_bucket=$(echo "$bucket_pair" | cut -d: -f1)
        local dest_bucket=$(echo "$bucket_pair" | cut -d: -f2)
        
        if ! migrate_bucket "$source_bucket" "$dest_bucket"; then
            ((failed_migrations++))
        fi
        
        echo "----------------------------------------"
    done
    
    log "Other buckets migration summary: $failed_migrations failed"
    return $failed_migrations
}

# Main function
main() {
    log "Starting S3 migration from $SOURCE_REGION to $DEST_REGION"
    
    # Check AWS CLI and profile
    if ! aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
        error "AWS profile '$PROFILE' not configured or invalid"
        exit 1
    fi
    
    success "AWS profile '$PROFILE' verified"
    
    case "${1:-}" in
        --documents-only)
            migrate_documents
            ;;
        --others-only)
            migrate_all_others
            ;;
        --dry-run)
            log "DRY RUN MODE - Showing what would be migrated"
            
            # Check documents bucket
            local doc_count=$(aws s3api list-objects-v2 \
                --bucket "solve-global-kr-documents-861276078413-us-west-2" \
                --region "$SOURCE_REGION" \
                --profile "$PROFILE" \
                --query 'length(Contents)' \
                --output text 2>/dev/null || echo "0")
            
            if [ "$doc_count" != "0" ] && [ "$doc_count" != "null" ]; then
                log "Would migrate documents: $doc_count objects"
            else
                warning "Documents bucket is empty or doesn't exist"
            fi
            
            # Check other buckets
            local buckets=(
                "solve-global-kr-text-861276078413-us-west-2"
                "solve-global-kr-chunks-861276078413-us-west-2"
                "solve-global-kr-embeddings-861276078413-us-west-2"
                "solve-global-kr-ner-861276078413-us-west-2"
                "solve-global-kr-kg-data-861276078413-us-west-2"
                "solve-global-kr-cache-861276078413-us-west-2"
            )
            
            for bucket in "${buckets[@]}"; do
                local count=$(aws s3api list-objects-v2 \
                    --bucket "$bucket" \
                    --region "$SOURCE_REGION" \
                    --profile "$PROFILE" \
                    --query 'length(Contents)' \
                    --output text 2>/dev/null || echo "0")
                
                if [ "$count" != "0" ] && [ "$count" != "null" ]; then
                    log "Would migrate $bucket: $count objects"
                else
                    warning "Would skip $bucket (empty or doesn't exist)"
                fi
            done
            ;;
        *)
            # Full migration - documents first, then others
            log "Starting full migration - documents first"
            
            echo
            read -p "Do you want to proceed with the full migration? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log "Migration cancelled by user"
                exit 0
            fi
            
            # Migrate documents first
            if migrate_documents; then
                log "Documents migration completed successfully"
                
                echo
                read -p "Continue with other buckets? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    migrate_all_others
                else
                    log "Stopping after documents migration as requested"
                fi
            else
                error "Documents migration failed. Stopping."
                exit 1
            fi
            ;;
    esac
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--documents-only|--others-only|--dry-run|--help]"
        echo ""
        echo "Simple S3 migration script"
        echo ""
        echo "Options:"
        echo "  --documents-only    Migrate only the documents bucket"
        echo "  --others-only       Migrate all buckets except documents"
        echo "  --dry-run          Show what would be migrated"
        echo "  --help             Show this help message"
        echo ""
        echo "Default: Full migration (documents first, then others)"
        ;;
    *)
        main "$1"
        ;;
esac
