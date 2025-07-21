# Vector Embeddings Initiator

Processes chunks_ready messages and initiates vector embedding jobs with audit-first database design.

## Overview

This Lambda function:
- Processes `chunks_ready` SNS messages from text chunker pipeline
- Validates chunks exist in S3
- Invokes vector embeddings worker asynchronously
- Tracks processing status using audit-first database design
- Provides fast response times (~200ms) for pipeline efficiency

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Processing started
self.db_manager.set_processing_status(doc_id, 'vector_embedding', 'in_progress')

# Processing completed successfully (job initiated)
self.db_manager.set_processing_status(doc_id, 'vector_embedding', 'completed', system_id=worker_function_name)

# Processing failed
self.db_manager.set_processing_status(doc_id, 'vector_embedding', 'failed', error_message=str(e))
```

## Message Processing

Processes standardized `chunks_ready` messages from text chunker:

```json
{
  "version": "1.0",
  "stage": "chunks_ready",
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "chunks_location": "s3://bucket/chunks/doc_id/",
    "chunk_metadata_location": "s3://bucket/chunks/doc_id/metadata.json"
  },
  "processing_metadata": {
    "chunks_created": 211
  }
}
```

## Worker Invocation

Invokes vector embeddings worker with job data:

```json
{
  "doc_id": "064762102bead7b04a39",
  "chunks_location": "s3://bucket/chunks/doc_id/",
  "chunk_metadata_location": "s3://bucket/chunks/doc_id/metadata.json",
  "processing_metadata": {...},
  "validation_data": {
    "chunks_count": 211,
    "total_size": 2456789
  }
}
```

## Environment Variables

- `VECTOR_WORKER_FUNCTION_NAME` - Name of vector embeddings worker function (default: `vector-embeddings-worker`)
- `CHUNKS_BUCKET` - S3 bucket containing chunks (default: `solve-global-kr-dl-chunks-861276078413-us-east-1`)
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-0709acdc3f0cccd7f` (Keyword Indexer Lambda)
- **Subnets**: Database subnets (`subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`
- **IAM Permissions**: S3 read access, Lambda invoke, database access

## Performance

- **Fast response**: ~200ms typical response time
- **Async delegation**: Worker invoked asynchronously for heavy processing
- **Validation**: Quick S3 validation before worker invocation
- **Error handling**: Robust error handling with database status tracking

## Deployment

```bash
cd lambda/vector-embeddings-initiator
zip -r vector-embeddings-initiator.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://vector-embeddings-initiator.zip
```
