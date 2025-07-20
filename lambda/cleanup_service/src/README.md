# Climate Risk RAG Cleanup Service

A comprehensive cleanup service for the Climate Risk RAG system that provides complete data removal across all system components for systematic testing and maintenance.

## Overview

The Cleanup Service is a production-ready AWS Lambda function that can safely and completely clean all data from your RAG system, providing a true "clean slate" for end-to-end testing and pipeline debugging.

## Supported Components

### ✅ Fully Supported & Tested
- **PostgreSQL Database**: Complete table cleanup with transaction safety
- **OpenSearch Serverless**: Individual document deletion (handles Serverless API limitations)
- **Neptune Knowledge Graph**: Complete triple deletion with verification
- **S3 Data Lake**: Batch object deletion with size tracking

### 🔧 Component-Specific Features

#### PostgreSQL
- Transactional safety with rollback on errors
- Configurable table cleanup with proper column mapping
- Support for specific document ID filtering
- Real-time record counting and verification

#### OpenSearch Serverless
- **Individual Document Deletion**: Works around Serverless `delete_by_query` limitations
- **Index Discovery**: Automatically finds indices within collections
- **Dual Collection Support**: Handles both vector and keyword search collections
- **Comprehensive Error Handling**: Graceful handling of missing indices and permission issues

#### Neptune
- **Complete Graph Cleanup**: `DELETE WHERE { ?s ?p ?o }` for total cleanup
- **Discovery Mode**: Counts and samples existing triples
- **Verification**: Post-deletion triple count verification
- **Namespace Aware**: Handles `http://solve.global/knowledge-commons/schema#` URIs

#### S3
- **Batch Processing**: Efficient deletion of large object sets
- **Size Tracking**: Reports total data size deleted
- **Preserve Structure**: Optional bucket structure preservation

## Key Features

### 🛡️ Safety Features
- **Dry Run Mode**: Test cleanup operations without actual deletion
- **Transaction Safety**: Database operations use transactions with rollback
- **Comprehensive Logging**: Detailed operation logging for audit trails
- **Error Handling**: Graceful error handling with detailed error reporting

### 📊 Comprehensive Reporting
- **Detailed Summary**: Complete breakdown of operations performed
- **Command Generation**: Shows exact SQL, SPARQL, and API commands executed
- **Impact Assessment**: Categorizes cleanup impact (LOW/MEDIUM/HIGH)
- **Verification**: Post-cleanup verification of deletion success

### 🔍 Discovery & Analysis
- **Data Discovery**: Automatically discovers and counts existing data
- **Triple Sampling**: Shows sample triples from Neptune for debugging
- **Index Mapping**: Maps OpenSearch collections to actual indices
- **Cross-Component Analysis**: Provides system-wide data overview

## Usage

### Basic Cleanup (All Components)
```json
{
  "cleanup_scope": {
    "databases": {
      "postgresql": {
        "enabled": true,
        "tables": ["documents", "document_metadata", "document_processing_status"],
        "document_ids": []
      },
      "opensearch": {
        "enabled": true,
        "collections": [
          "solve-global-kr-vectors-v2",
          "solve-global-kr-search-v2"
        ],
        "document_ids": []
      },
      "neptune": {
        "enabled": true
      }
    },
    "s3_data_lake": {
      "enabled": true,
      "buckets": [
        "solve-global-kr-dl-source-documents-861276078413-us-east-1"
      ],
      "document_ids": [],
      "preserve_structure": true
    }
  },
  "safety_checks": {
    "require_confirmation": false,
    "dry_run": false,
    "max_documents_to_delete": 5000
  }
}
```

### Dry Run (Recommended First)
```json
{
  "safety_checks": {
    "dry_run": true,
    "max_documents_to_delete": 5000
  }
}
```

### Targeted Cleanup (Specific Components)
```json
{
  "cleanup_scope": {
    "databases": {
      "postgresql": {
        "enabled": true,
        "tables": ["documents"],
        "document_ids": ["doc_123", "doc_456"]
      },
      "opensearch": {
        "enabled": false
      },
      "neptune": {
        "enabled": false
      }
    },
    "s3_data_lake": {
      "enabled": false
    }
  }
}
```

## Response Format

### Success Response
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
          "records_affected": {
            "documents": 1007,
            "document_metadata": 1005,
            "document_processing_status": 27
          }
        },
        "opensearch": {
          "success": true,
          "documents_affected": {
            "solve-global-kr-search-v2": 3
          }
        },
        "neptune": {
          "success": true,
          "triples_affected": 422
        }
      },
      "s3_data_lake": {
        "success": true,
        "total_objects_deleted": 1,
        "total_size_deleted": 1570490
      }
    },
    "cleanup_summary": {
      "overview": {
        "total_items_to_clean": 2465,
        "operations_count": 8,
        "estimated_impact": "HIGH"
      },
      "commands_to_execute": {
        "sql_statements": [
          {
            "command": "DELETE FROM documents;",
            "estimated_rows_affected": 1007
          }
        ],
        "sparql_statements": [
          {
            "query": "DELETE WHERE { ?s ?p ?o }",
            "description": "Delete all triples"
          }
        ]
      }
    }
  }
}
```

## Deployment

### Prerequisites
- AWS Lambda function with appropriate IAM permissions
- VPC configuration for database and Neptune access
- Lambda layers for dependencies

### Required IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": [
        "arn:aws:aoss:us-east-1:*:collection/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "neptune-db:*"
      ],
      "Resource": [
        "arn:aws:neptune-db:us-east-1:*:cluster/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::solve-global-kr-*",
        "arn:aws:s3:::solve-global-kr-*/*"
      ]
    }
  ]
}
```

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
OPENSEARCH_VECTOR_ENDPOINT=https://collection-id.region.aoss.amazonaws.com
OPENSEARCH_KEYWORD_ENDPOINT=https://collection-id.region.aoss.amazonaws.com
NEPTUNE_ENDPOINT=cluster-endpoint.region.neptune.amazonaws.com
NEPTUNE_PORT=8182
AWS_ACCOUNT_ID=123456789012
```

### Lambda Configuration
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 900 seconds (15 minutes)
- **VPC**: Same VPC as database and Neptune
- **Security Groups**: Access to all target services

## Architecture

### Core Components
- `cleanup_service.py`: Main Lambda handler and orchestration
- `database_cleanup.py`: PostgreSQL cleanup operations
- `opensearch_cleanup.py`: OpenSearch Serverless operations
- `neptune_cleanup.py`: Neptune knowledge graph operations
- `s3_cleanup.py`: S3 data lake operations
- `safety_validator.py`: Input validation and safety checks

### Key Technical Solutions

#### OpenSearch Serverless Compatibility
- **Problem**: OpenSearch Serverless doesn't support `delete_by_query` API
- **Solution**: Individual document deletion after ID discovery
- **Implementation**: Search for all document IDs, then delete each individually

#### Neptune Complete Cleanup
- **Problem**: Need to delete all triples for clean slate
- **Solution**: `DELETE WHERE { ?s ?p ?o }` SPARQL query
- **Verification**: Post-deletion count verification

#### Cross-Service Coordination
- **Problem**: Different APIs and authentication methods
- **Solution**: Service-specific clients with unified error handling
- **Result**: Consistent behavior across all components

## Testing

### Validation Tests
```bash
# Dry run test
aws lambda invoke --function-name cleanup-service \
  --payload '{"safety_checks":{"dry_run":true}}' \
  response.json

# Targeted test
aws lambda invoke --function-name cleanup-service \
  --payload '{"cleanup_scope":{"databases":{"postgresql":{"enabled":true}}}}' \
  response.json
```

### Expected Results
- **Complete Cleanup**: All components return 0 items
- **Verification**: Post-cleanup queries confirm deletion
- **Logging**: Detailed CloudWatch logs for audit

## Troubleshooting

### Common Issues

#### OpenSearch 404 Errors
- **Cause**: Collection or index doesn't exist
- **Solution**: Check collection names and index discovery logs

#### Neptune Connection Timeouts
- **Cause**: VPC/Security group configuration
- **Solution**: Ensure Lambda uses same security group as Neptune

#### PostgreSQL Transaction Errors
- **Cause**: Foreign key constraints or locks
- **Solution**: Check table dependencies and active connections

### Debug Mode
Enable detailed logging by checking CloudWatch logs:
```bash
aws logs get-log-events \
  --log-group-name "/aws/lambda/cleanup-service" \
  --log-stream-name "latest-stream"
```

## Production Considerations

### Safety
- **Always run dry-run first** in production environments
- **Backup critical data** before cleanup operations
- **Test in development** environment first
- **Monitor CloudWatch logs** during operations

### Performance
- **Large datasets**: Consider pagination for very large datasets
- **Timeouts**: Adjust Lambda timeout for large cleanup operations
- **Concurrency**: Service handles one cleanup at a time for safety

### Monitoring
- **CloudWatch Metrics**: Track cleanup operation success/failure
- **Alarms**: Set up alarms for cleanup failures
- **Audit Logs**: Maintain cleanup operation logs for compliance

## Version History

### v2.0.0 (Current)
- ✅ Complete OpenSearch Serverless support with individual document deletion
- ✅ Neptune complete cleanup with `DELETE WHERE { ?s ?p ?o }`
- ✅ Comprehensive reporting and command generation
- ✅ Production-ready error handling and verification
- ✅ Cross-component coordination and safety features

### v1.0.0
- Basic cleanup functionality
- Limited OpenSearch support
- No Neptune integration

## Support

For issues or questions:
1. Check CloudWatch logs for detailed error information
2. Verify IAM permissions and VPC configuration
3. Test with dry-run mode first
4. Review the troubleshooting section above

## License

Part of the Climate Risk RAG system - internal use only.
