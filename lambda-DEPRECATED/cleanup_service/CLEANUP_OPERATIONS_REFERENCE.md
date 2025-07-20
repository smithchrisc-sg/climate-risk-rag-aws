# Cleanup Operations Reference

This document provides detailed technical reference for all cleanup operations performed by the Climate Risk RAG Cleanup Service.

## Database Operations (PostgreSQL)

### Tables Cleaned
- `documents`: Main document records
- `document_metadata`: Document metadata and processing information  
- `document_processing_status`: Document processing status tracking

### SQL Commands Executed
```sql
-- Count records (dry run)
SELECT COUNT(*) as count FROM documents;
SELECT COUNT(*) as count FROM document_metadata;
SELECT COUNT(*) as count FROM document_processing_status;

-- Delete all records (actual cleanup)
DELETE FROM documents;
DELETE FROM document_metadata;
DELETE FROM document_processing_status;

-- Targeted deletion (when document_ids specified)
DELETE FROM documents WHERE doc_id = ANY($1);
DELETE FROM document_metadata WHERE doc_id = ANY($1);
DELETE FROM document_processing_status WHERE doc_hash = ANY($1);
```

### Transaction Safety
- All operations wrapped in database transactions
- Automatic rollback on any error
- Commit only after all operations succeed

## OpenSearch Operations

### Collections Cleaned
- `solve-global-kr-vectors-v2`: Vector embeddings collection
- `solve-global-kr-search-v2`: Keyword search collection

### Index Discovery Process
1. Try collection name as index name
2. Try collection name with `-index` suffix
3. Try common index names: `documents`, `vectors`, `embeddings`
4. Use `_cat/indices` API to discover all indices

### Deletion Process (OpenSearch Serverless Compatible)
```javascript
// 1. Search for all document IDs
POST /index-name/_search
{
  "query": {"match_all": {}},
  "size": 1000,
  "_source": false
}

// 2. Delete each document individually
DELETE /index-name/_doc/{document-id}
```

### Why Individual Deletion?
OpenSearch Serverless doesn't support the `_delete_by_query` API, so we:
1. Search for all document IDs in the index
2. Delete each document individually using the `DELETE /_doc/{id}` API
3. Track successful deletions and report counts

## Neptune Operations

### Complete Graph Cleanup
```sparql
-- Count all triples (dry run/verification)
SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }

-- Delete ALL triples (complete cleanup)
DELETE WHERE { ?s ?p ?o }
```

### Discovery Queries
```sparql
-- Count documents
SELECT (COUNT(*) as ?count) WHERE { 
  ?s a <http://solve.global/knowledge-commons/schema#Document> 
}

-- Count document chunks  
SELECT (COUNT(*) as ?count) WHERE { 
  ?s a <http://solve.global/knowledge-commons/schema#DocumentChunk> 
}

-- Count entities
SELECT (COUNT(*) as ?count) WHERE { 
  ?s a <http://solve.global/knowledge-commons/schema#Entity> 
}

-- Sample triples for debugging
SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 50
```

### Verification Process
1. Count triples before deletion
2. Execute `DELETE WHERE { ?s ?p ?o }`
3. Count triples after deletion (should be 0)
4. Report verification results

## S3 Operations

### Buckets Cleaned
- `solve-global-kr-dl-source-documents-{account-id}-{region}`: Source documents

### Deletion Process
```python
# List all objects in bucket
response = s3_client.list_objects_v2(Bucket=bucket_name)

# Batch delete objects (up to 1000 per batch)
s3_client.delete_objects(
    Bucket=bucket_name,
    Delete={
        'Objects': [
            {'Key': obj['Key']} for obj in objects
        ]
    }
)
```

### AWS CLI Equivalent
```bash
aws s3 rm s3://bucket-name/ --recursive
```

## Error Handling

### PostgreSQL Errors
- **Connection errors**: Retry with exponential backoff
- **Transaction errors**: Automatic rollback, detailed error logging
- **Constraint violations**: Report specific constraint issues

### OpenSearch Errors
- **404 Not Found**: Index doesn't exist (treated as already clean)
- **403 Forbidden**: Permission issues (detailed in logs)
- **Connection timeouts**: VPC/security group configuration issues

### Neptune Errors
- **Connection timeouts**: VPC/security group configuration
- **SPARQL syntax errors**: Query validation and error reporting
- **Permission denied**: IAM role configuration issues

### S3 Errors
- **Access denied**: IAM permission issues
- **Bucket not found**: Bucket name or region configuration
- **Rate limiting**: Automatic retry with backoff

## Safety Mechanisms

### Dry Run Mode
- All count/discovery operations executed
- No actual deletion operations performed
- Full reporting of what would be deleted

### Transaction Safety
- Database operations use transactions
- Rollback on any error
- Atomic operations where possible

### Verification
- Post-deletion counts to verify success
- Detailed logging of all operations
- Error reporting with specific failure details

## Performance Characteristics

### Typical Execution Times
- **PostgreSQL cleanup**: 1-5 seconds for thousands of records
- **OpenSearch cleanup**: 2-10 seconds per document (individual deletion)
- **Neptune cleanup**: 5-30 seconds depending on triple count
- **S3 cleanup**: 1-10 seconds depending on object count

### Resource Usage
- **Memory**: ~100-150 MB peak usage
- **CPU**: Low to moderate during operations
- **Network**: Moderate for OpenSearch individual deletions

### Scalability Limits
- **OpenSearch**: 1000 documents per operation (can be increased)
- **S3**: 1000 objects per batch delete operation
- **Neptune**: No practical limit for `DELETE WHERE { ?s ?p ?o }`
- **PostgreSQL**: No practical limit for table operations

## Monitoring and Logging

### CloudWatch Logs
```
[INFO] Starting cleanup operation
[INFO] PostgreSQL cleanup: 1007 records deleted
[INFO] OpenSearch cleanup: 3 documents deleted via individual deletion
[INFO] Neptune cleanup: 422 triples deleted, 0 remaining
[INFO] S3 cleanup: 1 object deleted (1.5 MB)
[INFO] Cleanup operation completed successfully
```

### Key Log Patterns
- `Starting cleanup for table: {table_name}`
- `Successfully deleted {count} documents from index {index_name}`
- `About to delete {count} triples from Neptune`
- `Verification: {count} triples remaining after deletion`

### Error Log Patterns
- `Failed to delete from index {index_name}: {error}`
- `SPARQL query failed: {error}`
- `Database cleanup failed: {error}`

## API Response Format

### Successful Response
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
          "operations_performed": [
            {
              "operation": "discovery_successful",
              "collection": "solve-global-kr-search-v2",
              "indices_found": ["climate-risk-keyword-index"],
              "documents_found": 3,
              "documents_actually_deleted": 3,
              "deletion_method": "individual_document_deletion"
            }
          ]
        },
        "neptune": {
          "success": true,
          "operations_performed": [
            {
              "operation": "delete_all_triples",
              "query": "DELETE WHERE { ?s ?p ?o }",
              "triples_deleted": 422,
              "verification": {
                "remaining_triples": 0,
                "deletion_successful": true
              }
            }
          ]
        }
      }
    },
    "cleanup_summary": {
      "overview": {
        "total_items_to_clean": 2465,
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

### Error Response
```json
{
  "statusCode": 500,
  "body": {
    "success": false,
    "error": "Cleanup operation failed",
    "results": {
      "databases": {
        "postgresql": {
          "success": false,
          "errors": ["Connection timeout"]
        }
      },
      "summary": {
        "failed_operations": 1,
        "errors": ["PostgreSQL connection failed"]
      }
    }
  }
}
```

## Configuration Reference

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# OpenSearch Serverless
OPENSEARCH_VECTOR_ENDPOINT=https://collection-id.region.aoss.amazonaws.com
OPENSEARCH_KEYWORD_ENDPOINT=https://collection-id.region.aoss.amazonaws.com

# Neptune
NEPTUNE_ENDPOINT=cluster-endpoint.region.neptune.amazonaws.com
NEPTUNE_PORT=8182

# AWS
AWS_ACCOUNT_ID=123456789012
```

### Lambda Configuration
```yaml
Runtime: python3.11
MemorySize: 1024
Timeout: 900
VpcConfig:
  SecurityGroupIds: 
    - sg-0c043bcb40f656321  # Lambda security group with access to all services
  SubnetIds:
    - subnet-03d8bd6cf3491f38c
    - subnet-0c0be1dd59f70f70e
```

### Required IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["aoss:APIAccessAll"],
      "Resource": ["arn:aws:aoss:*:*:collection/*"]
    },
    {
      "Effect": "Allow", 
      "Action": ["neptune-db:*"],
      "Resource": ["arn:aws:neptune-db:*:*:cluster/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:DeleteObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::solve-global-kr-*/*"]
    }
  ]
}
```

This reference provides the complete technical details for all cleanup operations performed by the service.
