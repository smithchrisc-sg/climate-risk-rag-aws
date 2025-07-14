# Climate Risk RAG Cleanup Service - Operations Reference

## Overview

This document provides detailed information about the specific operations performed by the cleanup service for each AWS service. It includes the exact commands, queries, and deletion patterns used to clean up test artifacts.

## Table of Contents

1. [Service Operations Summary](#service-operations-summary)
2. [PostgreSQL Operations](#postgresql-operations)
3. [OpenSearch Operations](#opensearch-operations)
4. [Neptune Operations](#neptune-operations)
5. [S3 Data Lake Operations](#s3-data-lake-operations)
6. [Safety Mechanisms](#safety-mechanisms)
7. [Operation Sequencing](#operation-sequencing)

---

## Service Operations Summary

| Service | What Gets Deleted | Deletion Method | Scope Control | Rollback Capability |
|---------|-------------------|-----------------|---------------|-------------------|
| **PostgreSQL** | Document processing status records | SQL DELETE statements | By document_id or all records | Transaction rollback |
| **OpenSearch** | Vector embeddings & keyword documents | delete_by_query API | By document_id or match_all | No rollback |
| **Neptune** | RDF triples related to documents | SPARQL DELETE queries | By document URI or all document triples | No rollback |
| **S3** | Document artifacts in data lake | Batch delete operations | By document_id prefix or all objects | No rollback (unless versioning) |

---

## PostgreSQL Operations

### Tables Affected

| Table Name | Purpose | Records Deleted |
|------------|---------|-----------------|
| `document_processing_status` | Overall document processing tracking | Records matching document_id |
| `nlp_processing_status` | NLP-specific processing status | Records matching document_id |
| `vector_processing_status` | Vector embedding processing status | Records matching document_id |
| `keyword_processing_status` | Keyword indexing processing status | Records matching document_id |
| `kg_processing_status` | Knowledge graph processing status | Records matching document_id |

### SQL Operations

#### Specific Document Cleanup
```sql
-- For each specified document_id
DELETE FROM document_processing_status WHERE document_id = ANY($1);
DELETE FROM nlp_processing_status WHERE document_id = ANY($1);
DELETE FROM vector_processing_status WHERE document_id = ANY($1);
DELETE FROM keyword_processing_status WHERE document_id = ANY($1);
DELETE FROM kg_processing_status WHERE document_id = ANY($1);
```

#### Full Table Cleanup
```sql
-- When no document_ids specified (cleans all records)
DELETE FROM document_processing_status;
DELETE FROM nlp_processing_status;
DELETE FROM vector_processing_status;
DELETE FROM keyword_processing_status;
DELETE FROM kg_processing_status;
```

#### Dry Run Queries
```sql
-- Count records that would be deleted (specific documents)
SELECT COUNT(*) FROM document_processing_status WHERE document_id = ANY($1);

-- Count all records (full cleanup)
SELECT COUNT(*) FROM document_processing_status;
```

#### Post-Cleanup Maintenance
```sql
-- Optional VACUUM operations to reclaim space
VACUUM ANALYZE document_processing_status;
VACUUM ANALYZE nlp_processing_status;
VACUUM ANALYZE vector_processing_status;
VACUUM ANALYZE keyword_processing_status;
VACUUM ANALYZE kg_processing_status;
```

### Connection Details
- **Database URL**: `postgresql://postgres:password@host:5432/climate_risk_rag?sslmode=require`
- **Transaction Handling**: All operations within a single transaction for rollback capability
- **Error Handling**: Individual table failures don't stop other operations

---

## OpenSearch Operations

### Collections Affected

| Collection Name | Purpose | Documents Deleted |
|-----------------|---------|-------------------|
| `climate-risk-vectorsearch` | Vector embeddings for semantic search | Documents matching document_id |
| `climate-risk-keyword-index` | Keyword indices for exact match search | Documents matching document_id |

### OpenSearch API Operations

#### Specific Document Cleanup
```json
// Delete by query for specific document
POST /climate-risk-vectorsearch/_delete_by_query
{
  "query": {
    "bool": {
      "should": [
        {"term": {"document_id": "doc-123"}},
        {"term": {"document_id.keyword": "doc-123"}},
        {"prefix": {"_id": "doc-123"}}
      ]
    }
  }
}
```

#### Full Collection Cleanup
```json
// Delete all documents in collection
POST /climate-risk-vectorsearch/_delete_by_query
{
  "query": {
    "match_all": {}
  },
  "wait_for_completion": true
}
```

#### Dry Run Queries
```json
// Count documents that would be deleted (specific document)
POST /climate-risk-vectorsearch/_search
{
  "query": {
    "bool": {
      "should": [
        {"term": {"document_id": "doc-123"}},
        {"term": {"document_id.keyword": "doc-123"}},
        {"prefix": {"_id": "doc-123"}}
      ]
    }
  },
  "size": 0
}

// Count all documents
POST /climate-risk-vectorsearch/_count
```

### Authentication & Access
- **Authentication**: AWS4Auth with IAM credentials
- **Endpoints**: 
  - Vector: `https://search-climate-risk-vectorsearch-collection.us-east-1.aoss.amazonaws.com`
  - Keyword: `https://search-climate-risk-keyword-index.us-east-1.es.amazonaws.com`
- **Connection**: HTTPS with SSL verification

---

## Neptune Operations

### RDF Data Affected

| Data Type | RDF Pattern | Deletion Scope |
|-----------|-------------|----------------|
| **Document Instances** | `<doc-uri> a climate-risk:Document` | All triples where document is subject/object |
| **Document Chunks** | `<chunk-uri> climate-risk:hasDocument <doc-uri>` | All chunk-related triples |
| **Extracted Entities** | `<entity-uri> climate-risk:extractedFrom <doc-uri>` | All entity-related triples |
| **Document Metadata** | `<doc-uri> climate-risk:hasTitle "..."` | All document property triples |

### SPARQL Operations

#### Specific Document Cleanup
```sparql
# Delete triples where document is subject
DELETE WHERE { 
  <http://climate-risk.org/document/doc-123> ?p ?o 
}

# Delete triples where document is object
DELETE WHERE { 
  ?s ?p <http://climate-risk.org/document/doc-123> 
}

# Delete document chunks
DELETE WHERE { 
  ?s <http://climate-risk.org/hasDocument> <http://climate-risk.org/document/doc-123> . 
  ?s ?p ?o 
}

# Delete extracted entities
DELETE WHERE { 
  ?s <http://climate-risk.org/extractedFrom> <http://climate-risk.org/document/doc-123> . 
  ?s ?p ?o 
}
```

#### Full Document Data Cleanup
```sparql
# Delete all document instances
DELETE WHERE { 
  ?s a <http://climate-risk.org/Document> . 
  ?s ?p ?o 
}

# Delete all document chunks
DELETE WHERE { 
  ?s a <http://climate-risk.org/DocumentChunk> . 
  ?s ?p ?o 
}

# Delete all entities
DELETE WHERE { 
  ?s a <http://climate-risk.org/Entity> . 
  ?s ?p ?o 
}
```

#### Dry Run Queries
```sparql
# Count document-related triples (specific document)
SELECT (COUNT(*) as ?count) WHERE { 
  <http://climate-risk.org/document/doc-123> ?p ?o 
}

# Count all document instances
SELECT (COUNT(*) as ?count) WHERE { 
  ?s a <http://climate-risk.org/Document> . 
  ?s ?p ?o 
}
```

### Connection Details
- **SPARQL Endpoint**: `https://neptune-endpoint:8182/sparql`
- **Authentication**: IAM-based authentication
- **Query Types**: Both SELECT (for counting) and UPDATE (for deletion)
- **Limitations**: Neptune doesn't return exact count of deleted triples

---

## S3 Data Lake Operations

### Bucket Structure

| Bucket Pattern | Purpose | Objects Deleted |
|----------------|---------|-----------------|
| `solve-global-kr-dl-source-documents-*` | Original uploaded documents | PDF files and metadata |
| `solve-global-kr-dl-text-*` | Extracted text from Textract | JSON files with extracted text |
| `solve-global-kr-dl-chunks-*` | Text chunks for processing | JSON files with chunked text |
| `solve-global-kr-dl-embeddings-*` | Vector embeddings | JSON files with embedding vectors |
| `solve-global-kr-dl-keywords-*` | Keyword extraction results | JSON files with keywords |
| `solve-global-kr-dl-nlp-*` | NLP analysis results | JSON files with entities/phrases |
| `solve-global-kr-dl-neptune-ttl-*` | Knowledge graph TTL files | TTL/RDF files for Neptune |

### Data Lake Folder Structure
```
/data_lake/{document_id}/
├── source/           # Original document
├── text/            # Extracted text
├── chunks/          # Text chunks
├── embeddings/      # Vector embeddings
├── keywords/        # Keyword extraction
├── nlp/            # NLP analysis
└── kg/             # Knowledge graph data
```

### S3 API Operations

#### Specific Document Cleanup
```python
# List objects with document prefix
response = s3_client.list_objects_v2(
    Bucket='bucket-name',
    Prefix=f'data_lake/{document_id}/'
)

# Batch delete objects (up to 1000 per request)
s3_client.delete_objects(
    Bucket='bucket-name',
    Delete={
        'Objects': [
            {'Key': obj['Key']} for obj in objects_to_delete
        ]
    }
)
```

#### Full Bucket Cleanup
```python
# List all objects in bucket
paginator = s3_client.get_paginator('list_objects_v2')
page_iterator = paginator.paginate(Bucket='bucket-name')

# Delete in batches
for page in page_iterator:
    if 'Contents' in page:
        objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
        s3_client.delete_objects(
            Bucket='bucket-name',
            Delete={'Objects': objects_to_delete}
        )
```

#### Dry Run Operations
```python
# Count objects that would be deleted
total_objects = 0
total_size = 0

for page in page_iterator:
    if 'Contents' in page:
        total_objects += len(page['Contents'])
        total_size += sum(obj['Size'] for obj in page['Contents'])
```

### Bucket Resolution
- **Pattern Matching**: Buckets specified with `*` are resolved by listing all buckets
- **Account/Region**: Automatically resolved using STS caller identity
- **Error Handling**: Missing buckets are skipped with warnings

---

## Safety Mechanisms

### Pre-Operation Validation

| Check Type | Validation | Action on Failure |
|------------|------------|-------------------|
| **Payload Structure** | Required fields present | Reject operation |
| **Data Types** | Boolean/list/string validation | Reject operation |
| **Dangerous Operations** | Full cleanup detection | Require confirmation |
| **Limits** | Document count limits | Reject if exceeded |

### Dry Run Implementation

| Service | Dry Run Method | Information Returned |
|---------|----------------|---------------------|
| **PostgreSQL** | COUNT queries instead of DELETE | Exact record counts |
| **OpenSearch** | Search queries instead of delete_by_query | Exact document counts |
| **Neptune** | SELECT COUNT instead of DELETE | Approximate triple counts |
| **S3** | List operations instead of delete | Exact object counts and sizes |

### Error Handling

| Error Type | Handling Strategy | Impact |
|------------|-------------------|--------|
| **Connection Failures** | Log error, continue with other services | Partial cleanup |
| **Permission Errors** | Log error, continue with other operations | Partial cleanup |
| **Invalid Queries** | Log error, skip operation | Operation skipped |
| **Timeout Errors** | Log error, report failure | Operation failed |

---

## Operation Sequencing

### Execution Order
1. **Payload Validation** - Validate structure and safety checks
2. **PostgreSQL Cleanup** - Database records (transactional)
3. **OpenSearch Cleanup** - Search indices (non-transactional)
4. **Neptune Cleanup** - Knowledge graph (non-transactional)
5. **S3 Cleanup** - Data lake objects (non-transactional)

### Parallel vs Sequential
- **Database Operations**: Sequential within each service
- **Cross-Service Operations**: Independent (failure in one doesn't stop others)
- **Batch Operations**: S3 deletes in batches of 1000 objects

### Transaction Boundaries

| Service | Transaction Support | Rollback Capability |
|---------|-------------------|-------------------|
| **PostgreSQL** | Full transaction support | Complete rollback on error |
| **OpenSearch** | No transactions | No rollback |
| **Neptune** | No transactions | No rollback |
| **S3** | No transactions | No rollback |

---

## Monitoring and Logging

### CloudWatch Logs
- **Function**: `/aws/lambda/solve-global-kr-cleanup-service`
- **Log Level**: INFO with ERROR for failures
- **Log Format**: Structured JSON with operation details

### Metrics Tracked
- Operations performed per service
- Records/documents/objects affected
- Execution time per service
- Success/failure rates
- Error details and stack traces

### Audit Trail
Every operation logs:
- Timestamp and operation type
- Service and scope (document IDs or "all")
- Success/failure status
- Count of items affected
- Error messages if applicable

---

## Recovery Procedures

### PostgreSQL Recovery
```sql
-- Restore from backup if available
-- Or recreate records from S3 data lake if needed
```

### OpenSearch Recovery
- Re-run vector embeddings pipeline
- Re-run keyword indexing pipeline
- Documents will be recreated from processing pipeline

### Neptune Recovery
- Re-run knowledge graph processing pipeline
- TTL files in S3 can be re-imported if preserved

### S3 Recovery
- **No automatic recovery** - objects are permanently deleted
- Restore from backups if available
- Re-upload source documents and re-run pipeline

---

## Best Practices

### Before Cleanup
1. **Always run dry-run first** to preview operations
2. **Review dry-run results** carefully
3. **Backup critical data** if needed
4. **Verify test document IDs** are correct

### During Cleanup
1. **Monitor CloudWatch logs** for errors
2. **Check operation summaries** in response
3. **Verify expected counts** match dry-run results

### After Cleanup
1. **Verify cleanup success** with status queries
2. **Check for any remaining artifacts**
3. **Document cleanup results** for reference
4. **Proceed with testing** on clean environment

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|---------|
| **Connection timeout** | VPC/security group misconfiguration | Check network settings |
| **Permission denied** | IAM policy insufficient | Update IAM permissions |
| **Partial cleanup** | Service-specific errors | Check individual service logs |
| **Validation errors** | Malformed payload | Fix payload structure |

### Debug Commands
```bash
# Check function logs
aws logs tail /aws/lambda/solve-global-kr-cleanup-service --follow

# Test connectivity
aws lambda invoke --function-name solve-global-kr-cleanup-service \
  --payload '{"cleanup_scope":{"databases":{"postgresql":{"enabled":false},"opensearch":{"enabled":false},"neptune":{"enabled":false}},"s3_data_lake":{"enabled":false}},"safety_checks":{"dry_run":true}}' \
  response.json
```

---

*Last Updated: 2025-07-14*  
*Version: 1.0*
