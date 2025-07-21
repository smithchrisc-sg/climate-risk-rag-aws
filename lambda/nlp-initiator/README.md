# NLP Initiator Lambda Function

## Overview

The NLP Initiator processes `chunks_ready` messages and initiates asynchronous Amazon Comprehend jobs for entity extraction and key phrase detection. It follows the audit-first database design pattern.

## Functionality

1. **Receives** `chunks_ready` messages from text chunking stage
2. **Loads** full text from S3 for processing
3. **Validates** processing cost against threshold
4. **Starts** async Comprehend jobs (entities + key phrases)
5. **Notifies** NLP worker with job information
6. **Exits** immediately (no waiting for Comprehend)

## Processing Flow

```
chunks_ready → Load Text → Cost Validation → Start Comprehend Jobs → Notify Worker → Exit
```

## Database Status Tracking

- `nlp_initiate` → `in_progress` → `completed`/`failed`
- `nlp_processing` → `in_progress` (when Comprehend jobs started)

## Environment Variables

- `NLP_COST_THRESHOLD`: Maximum cost per document (default: $0.50)
- `COMPREHEND_REGION`: AWS region for Comprehend (default: us-east-1)
- `NLP_WORKER_TOPIC_ARN`: SNS topic for worker notifications
- `COMPREHEND_DATA_ACCESS_ROLE_ARN`: IAM role for Comprehend S3 access
- `COMPREHEND_OUTPUT_BUCKET`: S3 bucket for Comprehend results

## Cost Management

- Estimates cost: $0.0002 per 100 characters (entities + key phrases)
- Validates against threshold before processing
- Tracks estimated vs actual costs in database metadata

## Infrastructure Requirements

- **VPC**: Application subnets
- **Security Group**: `sg-0c9e10b9cfb4c9eb0`
- **Timeout**: 5 minutes
- **Memory**: 512MB
- **Layers**: database-core-layer-v3, climate-risk-core-utilities
