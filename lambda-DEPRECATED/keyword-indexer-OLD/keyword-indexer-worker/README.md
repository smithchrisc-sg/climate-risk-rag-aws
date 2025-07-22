# Keyword Indexer Worker

Background worker that processes documents for OpenSearch indexing with Textract structure analysis using audit-first database design.

## Overview

This Lambda function:
- Processes keyword indexing jobs from initiator lambda
- Downloads text and structure files from S3
- Performs structure-aware OpenSearch indexing with Textract analysis
- Publishes completion messages
- Tracks processing status using audit-first database design
- **PRESERVES ALL OPENSEARCH FUNCTIONALITY**

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Processing started
self.db_manager.set_processing_status(doc_id, 'keyword_index_complete', 'in_progress')

# Processing completed successfully
self.db_manager.set_processing_status(doc_id, 'keyword_index_complete', 'completed')

# Processing failed
self.db_manager.set_processing_status(doc_id, 'keyword_index_complete', 'failed', error_message=str(e))
```

## OpenSearch Integration

**PRESERVED FUNCTIONALITY - NO CHANGES:**

### Structure-Aware Processing
- Analyzes Textract structure (titles, headings, tables, forms)
- Applies intelligent boosting based on content type
- Creates enhanced index mappings with custom analyzers
- Fallback to basic indexing if structure analysis fails

### Index Structure
```json
{
  "doc_id": "064762102bead7b04a39",
  "content": "full document text",
  "title_content": "extracted titles (boost: 3.0)",
  "heading_content": "extracted headings (boost: 2.0)", 
  "table_content": "table data (boost: 1.5)",
  "form_content": "form fields (boost: 1.3)",
  "structure_metadata": {
    "page_count": 20,
    "table_count": 3,
    "form_count": 1,
    "has_tables": true,
    "has_forms": true
  }
}
```

### OpenSearch Configuration
- **Endpoint**: `https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com`
- **Index**: `solve-global-kr-search-v2`
- **Authentication**: AWS IAM with OpenSearch Serverless

## Job Processing

Receives job data from initiator:

```json
{
  "doc_id": "064762102bead7b04a39",
  "text_location": "s3://bucket/dl-text/doc_id/raw_text.txt",
  "structure_location": "s3://bucket/dl-text/doc_id/textract_response.json",
  "processing_metadata": {...},
  "document_metadata": {...}
}
```

## Completion Messages

Publishes standardized completion messages:

```json
{
  "version": "1.0",
  "stage": "keyword_index_ready",
  "doc_id": "064762102bead7b04a39",
  "processing_metadata": {
    "indexing_method": "structure_aware",
    "character_count": 225215,
    "blocks_processed": 4436,
    "index_name": "solve-global-kr-search-v2"
  }
}
```

## Environment Variables

- `TEXT_BUCKET` - S3 bucket containing text extraction output
- `OPENSEARCH_ENDPOINT` - OpenSearch service endpoint
- `INDEX_NAME` - OpenSearch index name
- `COMPLETION_TOPIC_ARN` - SNS topic for completion notifications (optional)
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-0c9e10b9cfb4c9eb0` (Async Keyword Indexer Lambdas)
- **Subnets**: Database subnets (`subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`
- **IAM Permissions**: OpenSearch access, S3 read access, SNS publish

## Deployment

```bash
cd lambda/keyword-indexer-worker
zip -r keyword-indexer-worker.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://keyword-indexer-worker.zip
```
