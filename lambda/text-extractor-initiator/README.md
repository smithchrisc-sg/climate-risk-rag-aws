# Text Extractor Initiator

Initiates async Textract jobs for PDF documents using audit-first database design.

## Overview

This Lambda function:
- Processes S3 upload events (via SNS/SQS)
- Starts async Textract document analysis jobs
- Tracks processing status using audit-first database design
- Uses LOCKED database-core-layer (DO NOT MODIFY)

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Job initiation
self.db_manager.set_processing_status(doc_id, 'textract_initiate', 'in_progress')

# Job started successfully  
self.db_manager.set_processing_status(doc_id, 'textract_initiate', 'completed', system_id=job_id)

# Job failed
self.db_manager.set_processing_status(doc_id, 'textract_initiate', 'failed', error_message=str(e))
```

## Environment Variables

- `TEXTRACT_SNS_TOPIC_ARN` - SNS topic for Textract completion notifications
- `TEXTRACT_SERVICE_ROLE_ARN` - IAM role for Textract service
- `OUTPUT_BUCKET` - S3 bucket for Textract output
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-08518057bfb59e735` (Text Extractor Lambda Security Group)
- **Subnets**: Database subnets (`subnet-0e9efc5fdf29e9da0`, `subnet-00efdcc220a613ae3`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`

## Deployment

```bash
cd lambda/text-extractor-initiator
zip -r text-extractor-initiator.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://text-extractor-initiator.zip
```
