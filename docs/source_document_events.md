# Source Document Events Infrastructure

This document describes the SNS/SQS infrastructure for source document events in the Climate Risk RAG system.

## Overview

When a document is added to the source bucket, the following workflow is triggered:

1. S3 event notification is sent to the SNS topic (`solve-global-kr-source-document-events`)
2. SNS topic forwards the message to the SQS queue (`solve-global-kr-textextractor-initiator-queue`)
3. Text extractor initiator Lambda is triggered by the SQS queue
4. Text extractor initiator Lambda processes the document and starts the Textract job
5. When the Textract job completes, it sends a notification to the Textract completion SNS topic
6. Textract completion SNS topic forwards the message to the text extractor processor SQS queue
7. Text extractor processor Lambda is triggered by the SQS queue and processes the Textract results

## Components

### SNS Topic

- **Name**: `solve-global-kr-source-document-events`
- **Purpose**: Receive S3 event notifications when documents are added to the source bucket

### SQS Queue

- **Name**: `solve-global-kr-textextractor-initiator-queue`
- **Purpose**: Buffer messages from the SNS topic and trigger the text extractor initiator Lambda
- **Visibility Timeout**: 5 minutes
- **Retention Period**: 4 days
- **Dead Letter Queue**: `solve-global-kr-textextractor-initiator-dlq`

### Dead Letter Queue

- **Name**: `solve-global-kr-textextractor-initiator-dlq`
- **Purpose**: Capture messages that fail processing after multiple attempts
- **Retention Period**: 14 days

### S3 Event Notification

- **Bucket**: `solve-global-kr-dl-source-documents-{account}-{region}`
- **Event Type**: `ObjectCreated`
- **Prefix**: `data_lake/`
- **Suffix**: `.pdf`
- **Destination**: SNS topic `solve-global-kr-source-document-events`

### Lambda Event Source Mapping

- **Function**: `solve-global-kr-textextractor-initiator`
- **Event Source**: SQS queue `solve-global-kr-textextractor-initiator-queue`
- **Batch Size**: 1
- **Max Batching Window**: 5 seconds

## Deployment

To deploy the source document events infrastructure, run:

```bash
python deploy_source_document_events.py
```

This will deploy the CDK stack `solve-global-kr-rag-source-document-events` which creates all the necessary resources.

## Testing

To test the source document events infrastructure, you can:

1. Upload a PDF document to the source bucket with the prefix `data_lake/`
2. Check the CloudWatch logs for the text extractor initiator Lambda to see if it was triggered
3. Check the CloudWatch logs for the text extractor processor Lambda to see if it processed the document

You can also use the pipeline test Lambda with the `--skip-lambda-invocation` flag to test the workflow:

```bash
python invoke_pipeline_test.py --action setup_and_test --num-documents 1 --skip-lambda-invocation
```

This will copy a document to the source bucket and let the SNS/SQS workflow trigger the text extraction process.
