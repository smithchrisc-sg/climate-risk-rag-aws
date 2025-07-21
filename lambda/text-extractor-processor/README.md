# Text Extractor Processor

Processes completed Textract jobs and extracts structured text using audit-first database design.

## Overview

This Lambda function:
- Processes Textract completion SNS notifications
- Retrieves and processes Textract results
- Extracts structured text content (lines, tables, forms)
- Saves results to S3 in standardized format
- Publishes completion messages with doc_id
- Tracks processing status using audit-first database design

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Processing started
self.db_manager.set_processing_status(doc_id, 'textract_complete', 'in_progress', system_id=job_id)

# Processing completed successfully
self.db_manager.set_processing_status(doc_id, 'textract_complete', 'completed', system_id=job_id)

# Processing failed
self.db_manager.set_processing_status(doc_id, 'textract_complete', 'failed', error_message=str(e), system_id=job_id)
```

## Output Structure

Saves to S3 bucket under `dl-text/{doc_id}/`:
- `raw_text.txt` - Extracted plain text
- `textract_response.json` - Full Textract response with structure
- `text_analysis.json` - Processing statistics and metadata

## Standardized Messaging

Publishes completion messages with doc_id included:

```json
{
  "version": "1.0",
  "stage": "text_ready", 
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "text_location": "s3://bucket/dl-text/doc_id/raw_text.txt",
    "structure_location": "s3://bucket/dl-text/doc_id/textract_response.json"
  },
  "processing_metadata": {
    "total_characters": 15420,
    "line_count": 245,
    "table_count": 3,
    "form_count": 1
  }
}
```

## Environment Variables

- `OUTPUT_BUCKET` - S3 bucket for text extraction output
- `TEXT_EXTRACTION_COMPLETE_TOPIC_ARN` - SNS topic for completion notifications
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-08518057bfb59e735` (Text Extractor Lambda Security Group)
- **Subnets**: Database subnets (`subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`

## Deployment

```bash
cd lambda/text-extractor-processor
zip -r text-extractor-processor.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://text-extractor-processor.zip
```
