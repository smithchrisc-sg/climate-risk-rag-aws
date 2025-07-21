# Keyword Indexer Initiator

Processes text extraction completion messages and initiates async keyword indexing jobs using audit-first database design.

## Overview

This Lambda function:
- Processes `text_ready` SNS messages from text extraction pipeline
- Initiates async keyword indexing jobs via worker lambda
- Tracks processing status using audit-first database design
- Uses LOCKED database-core-layer (DO NOT MODIFY)

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Job initiation
self.db_manager.set_processing_status(doc_id, 'keyword_index_initiate', 'in_progress')

# Worker invoked successfully  
self.db_manager.set_processing_status(doc_id, 'keyword_index_initiate', 'completed', system_id=worker_function_name)

# Job failed
self.db_manager.set_processing_status(doc_id, 'keyword_index_initiate', 'failed', error_message=str(e))
```

## Message Processing

Processes standardized `text_ready` messages:

```json
{
  "version": "1.0",
  "stage": "text_ready",
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "text_location": "s3://bucket/dl-text/doc_id/raw_text.txt",
    "structure_location": "s3://bucket/dl-text/doc_id/textract_response.json"
  }
}
```

## Environment Variables

- `TEXT_BUCKET` - S3 bucket containing text extraction output
- `WORKER_FUNCTION_NAME` - Name of keyword indexer worker function
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-0c9e10b9cfb4c9eb0` (Async Keyword Indexer Lambdas)
- **Subnets**: Database subnets (`subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`

## Deployment

```bash
cd lambda/keyword-indexer-initiator
zip -r keyword-indexer-initiator.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://keyword-indexer-initiator.zip
```
