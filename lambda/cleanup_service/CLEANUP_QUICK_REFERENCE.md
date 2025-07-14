# Cleanup Service - Quick Reference

## Deletion Operations Summary

| Service | Target | Specific Document Command/Query | Full Cleanup Command/Query | Dry Run Method |
|---------|--------|--------------------------------|---------------------------|----------------|
| **PostgreSQL** | Processing status records | `DELETE FROM table WHERE document_id = ANY($1)` | `DELETE FROM table` | `SELECT COUNT(*) FROM table [WHERE...]` |
| **OpenSearch** | Vector/keyword documents | `POST /index/_delete_by_query {"query":{"term":{"document_id":"doc-123"}}}` | `POST /index/_delete_by_query {"query":{"match_all":{}}}` | `POST /index/_search {"size":0, "query":{...}}` |
| **Neptune** | RDF triples | `DELETE WHERE {<doc-uri> ?p ?o}` | `DELETE WHERE {?s a climate-risk:Document . ?s ?p ?o}` | `SELECT (COUNT(*) as ?count) WHERE {...}` |
| **S3** | Data lake objects | `list_objects_v2(Prefix="data_lake/doc-123/")` + `delete_objects()` | `list_objects_v2()` + `delete_objects()` | `list_objects_v2()` (count only) |

## Service-Specific Details

### PostgreSQL Tables
- `document_processing_status` - Overall processing tracking
- `nlp_processing_status` - NLP analysis status  
- `vector_processing_status` - Vector embedding status
- `keyword_processing_status` - Keyword indexing status
- `kg_processing_status` - Knowledge graph status

### OpenSearch Collections
- `climate-risk-vectorsearch` - Vector embeddings for semantic search
- `climate-risk-keyword-index` - Keyword indices for exact matching

### Neptune RDF Classes
- `climate-risk:Document` - Document instances
- `climate-risk:DocumentChunk` - Text chunk instances
- `climate-risk:Entity` - Extracted entity instances

### S3 Bucket Patterns
- `solve-global-kr-dl-source-documents-*` - Original PDFs
- `solve-global-kr-dl-text-*` - Extracted text
- `solve-global-kr-dl-chunks-*` - Text chunks
- `solve-global-kr-dl-embeddings-*` - Vector embeddings
- `solve-global-kr-dl-keywords-*` - Keyword results
- `solve-global-kr-dl-nlp-*` - NLP analysis
- `solve-global-kr-dl-neptune-ttl-*` - Knowledge graph TTL

## Data Lake Structure
```
/data_lake/{document_id}/
├── source/           # Original document
├── text/            # Textract results
├── chunks/          # Text chunks
├── embeddings/      # Vector embeddings  
├── keywords/        # TF-IDF keywords
├── nlp/            # Comprehend results
└── kg/             # Knowledge graph TTL
```

## Safety Features
- ✅ **Dry Run Mode** - Preview without deletion
- ✅ **Payload Validation** - Structure and type checking
- ✅ **Confirmation Required** - For dangerous operations
- ✅ **Transaction Rollback** - PostgreSQL operations only
- ✅ **Comprehensive Logging** - All operations tracked

## Common Usage Patterns

### Full System Cleanup (Dry Run)
```bash
aws lambda invoke --function-name solve-global-kr-cleanup-service \
  --payload file://examples/cleanup_full_dry_run.json response.json
```

### S3 Only Cleanup
```bash
aws lambda invoke --function-name solve-global-kr-cleanup-service \
  --payload file://examples/cleanup_s3_only.json response.json
```

### Specific Documents
```bash
aws lambda invoke --function-name solve-global-kr-cleanup-service \
  --payload file://examples/cleanup_specific_documents.json response.json
```

## Response Format
```json
{
  "success": true,
  "results": {
    "databases": {
      "postgresql": {"records_affected": {"table": count}},
      "opensearch": {"documents_affected": {"collection": count}},
      "neptune": {"triples_affected": count}
    },
    "s3_data_lake": {
      "total_objects_deleted": count,
      "total_size_deleted": bytes
    },
    "summary": {
      "total_operations": 4,
      "successful_operations": 4,
      "failed_operations": 0
    }
  }
}
```
