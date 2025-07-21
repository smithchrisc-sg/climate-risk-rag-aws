# Vector Embeddings Worker

Processes vector embedding jobs with AWS Bedrock Titan and OpenSearch integration using audit-first database design.

## Overview

This Lambda function:
- Loads chunks from S3 chunks bucket
- Generates embeddings using AWS Bedrock Titan models
- Saves embeddings to S3 for backup/reprocessing
- Indexes vectors in OpenSearch with full metadata
- Publishes `vector_embeddings_ready` completion messages
- Tracks processing status using audit-first database design
- **PRESERVES ALL EMBEDDING AND INDEXING FUNCTIONALITY**

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Processing started
self.db_manager.set_processing_status(doc_id, 'vector_indexing', 'in_progress')

# Processing completed successfully
self.db_manager.set_processing_status(doc_id, 'vector_indexing', 'completed')

# Processing failed
self.db_manager.set_processing_status(doc_id, 'vector_indexing', 'failed', error_message=str(e))
```

## Multi-Service Integration

**PRESERVED FUNCTIONALITY - NO CHANGES:**

### AWS Bedrock Titan Embeddings
- **Model**: `amazon.titan-embed-text-v1`
- **Dimension**: 1536 vectors
- **Batch processing**: Respects API limits (25 texts per batch)
- **Error handling**: Fallback to zero vectors on failures
- **Region**: Configurable via `BEDROCK_REGION`

### OpenSearch Vector Indexing
- **Index**: `climate-risk-vector-index`
- **Vector field**: `content_vector` with kNN configuration
- **Mapping**: Enhanced mapping with vector fields and metadata
- **Bulk indexing**: Efficient bulk operations
- **Search ready**: Immediate searchability with refresh=true

### S3 Storage
- **Embeddings backup**: Individual embedding files saved
- **Metadata**: Complete embedding metadata with model info
- **Reprocessing**: Embeddings can be reloaded from S3

## Processing Flow

1. **Load chunks** from S3 chunks bucket
2. **Generate embeddings** using Bedrock Titan API
3. **Save embeddings** to S3 embeddings bucket
4. **Index vectors** in OpenSearch with full metadata
5. **Publish completion** message for next pipeline stage
6. **Update database** status to completed

## Chunk Processing

Processes chunks with complete metadata preservation:

```json
{
  "chunk_id": "064762102bead7b04a39_chunk_0001",
  "text": "chunk content",
  "embedding": [0.123, -0.456, ...],
  "character_count": 856,
  "page_numbers": [1, 2],
  "section_types": ["title", "paragraph"],
  "hierarchy_levels": [1, 5],
  "table_count": 0,
  "list_count": 1,
  "semantic_context": "Previous context",
  "embedding_model": "amazon.titan-embed-text-v1",
  "embedding_dimension": 1536
}
```

## OpenSearch Vector Index

**Enhanced mapping with vector fields:**

```json
{
  "content_vector": {
    "type": "knn_vector",
    "dimension": 1536,
    "method": {
      "name": "hnsw",
      "space_type": "cosinesimil",
      "engine": "nmslib"
    }
  }
}
```

## Output Format

Publishes standardized `vector_embeddings_ready` messages:

```json
{
  "version": "1.0",
  "stage": "vector_embeddings_ready",
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "embeddings_location": "s3://bucket/embeddings/doc_id/",
    "embeddings_metadata_location": "s3://bucket/embeddings/doc_id/metadata.json",
    "vector_index_name": "climate-risk-vector-index"
  },
  "processing_metadata": {
    "vectors_created": 211,
    "embedding_model": "amazon.titan-embed-text-v1",
    "vector_dimension": 1536
  }
}
```

## Environment Variables

- `CHUNKS_BUCKET` - S3 bucket containing chunks (default: `solve-global-kr-dl-chunks-861276078413-us-east-1`)
- `EMBEDDINGS_BUCKET` - S3 bucket for embeddings storage (default: `solve-global-kr-dl-embeddings-861276078413-us-east-1`)
- `OPENSEARCH_ENDPOINT` - OpenSearch Serverless endpoint URL
- `BEDROCK_REGION` - AWS Bedrock region (default: `us-east-1`)
- `COMPLETION_TOPIC_ARN` - SNS topic for completion notifications (optional)
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-0709acdc3f0cccd7f` (Keyword Indexer Lambda)
- **Subnets**: Application subnets (`subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`
  - `numpy-dependencies-lambda:1`
  - `opensearch-dependencies:4`
- **IAM Permissions**: S3 read/write, Bedrock invoke, OpenSearch access, SNS publish, database access

## Performance Considerations

- **Batch processing**: Titan API calls batched for efficiency
- **Memory usage**: Handles large documents with streaming
- **Timeout**: Configured for long-running embedding generation
- **Error recovery**: Robust error handling for multi-service failures

## Future Optimization Notes

- **Per-chunk processing**: Could be optimized with SQS queuing for parallel chunk processing
- **Cost efficiency**: Document-level vs chunk-level lambda invocations
- **Orchestration**: More complex but potentially more cost-effective for large documents

## Deployment

```bash
cd lambda/vector-embeddings-worker
zip -r vector-embeddings-worker.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://vector-embeddings-worker.zip
```
