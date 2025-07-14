# Climate Risk RAG Cleanup Service

A centralized Lambda function for cleaning up test artifacts across PostgreSQL, OpenSearch, Neptune, and S3 data lake resources.

## Overview

The cleanup service provides safe, configurable cleanup of document processing artifacts across all system components. It runs within the VPC with proper security group access to reach private resources.

## Features

- **Multi-Service Cleanup**: PostgreSQL, OpenSearch, Neptune, and S3
- **Granular Control**: Clean specific documents or all data
- **Safety Features**: Dry-run mode, confirmation requirements, limits
- **Comprehensive Logging**: Detailed operation tracking and error reporting
- **Flexible Configuration**: JSON payload-driven operations

## Architecture

```
cleanup_service.py          # Main orchestrator and Lambda handler
├── database_cleanup.py     # PostgreSQL operations
├── opensearch_cleanup.py   # OpenSearch vector/keyword indices
├── neptune_cleanup.py      # Knowledge graph triples
├── s3_cleanup.py          # S3 data lake objects
└── safety_validator.py    # Payload validation and safety checks
```

## Usage

### Command Line Invocation

```bash
# Full cleanup (dry run)
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload file://examples/cleanup_full_dry_run.json \
  response.json

# Specific document cleanup
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload file://examples/cleanup_specific_documents.json \
  response.json

# S3 only cleanup
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload file://examples/cleanup_s3_only.json \
  response.json
```

### Payload Structure

```json
{
  "cleanup_scope": {
    "databases": {
      "postgresql": {
        "enabled": true,
        "tables": ["document_processing_status", "nlp_processing_status"],
        "document_ids": ["doc-123", "doc-456"]  // optional, empty = all
      },
      "opensearch": {
        "enabled": true,
        "collections": ["climate-risk-vectorsearch", "climate-risk-keyword-index"],
        "document_ids": ["doc-123", "doc-456"]  // optional
      },
      "neptune": {
        "enabled": true,
        "clear_all_triples": false,
        "document_ids": ["doc-123", "doc-456"]  // optional
      }
    },
    "s3_data_lake": {
      "enabled": true,
      "buckets": ["solve-global-kr-dl-*"],
      "document_ids": ["doc-123", "doc-456"],  // optional
      "preserve_structure": true
    }
  },
  "safety_checks": {
    "require_confirmation": true,
    "dry_run": false,
    "max_documents_to_delete": 100
  }
}
```

## Safety Features

### Dry Run Mode
Set `"dry_run": true` to preview what would be deleted without making changes.

### Confirmation Requirements
Dangerous operations (full cleanup) require explicit confirmation or will be blocked.

### Limits and Validation
- Maximum document deletion limits
- Payload structure validation
- Dangerous operation detection

### Comprehensive Logging
All operations are logged to CloudWatch with detailed success/failure information.

## Service-Specific Operations

### PostgreSQL Cleanup
- Deletes records from specified tables by document_id
- Supports table-specific cleanup
- Optional VACUUM after cleanup

### OpenSearch Cleanup
- Removes documents from vector and keyword collections
- Supports both specific document and full collection cleanup
- Handles multiple collection types

### Neptune Cleanup
- Deletes RDF triples related to documents
- Preserves ontology/schema triples
- Supports full document-related cleanup

### S3 Data Lake Cleanup
- Removes objects from data lake folder structure
- Supports document-specific or full bucket cleanup
- Option to preserve folder structure

## Environment Variables

Required environment variables:

```bash
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
OPENSEARCH_VECTOR_ENDPOINT=https://vector-endpoint
OPENSEARCH_KEYWORD_ENDPOINT=https://keyword-endpoint
NEPTUNE_ENDPOINT=neptune-cluster-endpoint
NEPTUNE_PORT=8182
AWS_DEFAULT_REGION=us-east-1
```

## Example Scenarios

### Pre-Test Cleanup
Use `cleanup_full_dry_run.json` to see what test artifacts exist, then run without dry_run to clean.

### Specific Document Cleanup
Use `cleanup_specific_documents.json` to clean up after testing specific documents.

### S3-Only Cleanup
Use `cleanup_s3_only.json` when you only need to clean S3 objects (fastest option).

### Database-Only Cleanup
Use `cleanup_databases_only.json` to clean databases while preserving S3 objects.

## Response Format

```json
{
  "statusCode": 200,
  "body": {
    "success": true,
    "results": {
      "dry_run": false,
      "databases": {
        "postgresql": {
          "success": true,
          "records_affected": {"document_processing_status": 10},
          "operations_performed": [...]
        },
        "opensearch": {...},
        "neptune": {...}
      },
      "s3_data_lake": {
        "success": true,
        "total_objects_deleted": 150,
        "total_size_deleted": 1048576
      },
      "summary": {
        "total_operations": 4,
        "successful_operations": 4,
        "failed_operations": 0,
        "errors": []
      }
    }
  }
}
```

## Error Handling

- Individual service failures don't stop other operations
- Detailed error messages in response
- Rollback for database operations on failure
- Comprehensive error logging

## Security Considerations

- Runs in VPC with database access security groups
- Requires broad permissions (use carefully)
- Validates all input payloads
- Logs all operations for audit trail

## Deployment

The cleanup service will be deployed as part of the CDK infrastructure with:
- VPC access to private subnets
- Security group access to databases
- Required IAM permissions
- Lambda layers for dependencies

## Testing

Always test with `dry_run: true` first to preview operations before executing actual cleanup.
