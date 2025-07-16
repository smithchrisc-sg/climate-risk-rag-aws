# Project Context Summary (2025-07-16T23-34-20Z)

## Overview

The Climate Risk RAG (Retrieval-Augmented Generation) system is a comprehensive document processing pipeline that extracts, processes, and indexes climate risk-related documents. The system uses AWS services including S3, Lambda, Textract, RDS PostgreSQL, Neptune, OpenSearch, and various AI/ML services to process documents and make their content searchable and analyzable.

## Recent Work: SNS/SQS Workflow for Text Extraction

We've implemented an SNS/SQS workflow for the text extraction process to decouple the document upload from the text extraction process. This improves the system's reliability, scalability, and error handling.

### Key Components

1. **S3 Event Notifications**: When a document is uploaded to the source bucket (`solve-global-kr-dl-source-documents-*`), an S3 event notification is sent to an SNS topic.

2. **SNS Topic**: The `solve-global-kr-source-document-events` topic receives S3 event notifications and forwards them to subscribers.

3. **SQS Queue**: The `solve-global-kr-textextractor-initiator-queue` receives messages from the SNS topic and buffers them for processing.

4. **Dead Letter Queue**: The `solve-global-kr-textextractor-initiator-dlq` captures messages that fail processing after multiple attempts.

5. **Lambda Event Source Mapping**: The text extractor initiator Lambda function is triggered by messages in the SQS queue.

6. **Text Extractor Initiator Lambda**: Processes the SQS messages, extracts the S3 event information, and starts Textract jobs.

### Implementation Details

- **CDK Infrastructure**: Created a new CDK stack (`SourceDocumentEventsStack`) in `cdk/stacks/source_document_events_stack.py` and a CDK app in `cdk/app_source_document_events.py` to deploy the SNS/SQS workflow.

- **Lambda Function Updates**: Updated the text extractor initiator Lambda function to handle SQS events by extracting the S3 event information from the SNS message.

- **Pipeline Test Handler**: Updated the pipeline test handler in `lambda/pipeline_test_function/pipeline_test_handler.py` to support the SNS/SQS workflow and added a `--skip-lambda-invocation` flag to the `invoke_pipeline_test.py` script.

- **Documentation**: Created a README file in `docs/source_document_events.md` that explains the SNS/SQS workflow.

## Project Structure

### Key Directories

- **`cdk/`**: Contains CDK (Cloud Development Kit) code for infrastructure deployment
  - `app_*.py`: CDK applications for different components
  - `stacks/`: CDK stack definitions
  
- **`lambda/`**: Contains Lambda function code
  - `pipeline_test_function/`: Pipeline test Lambda function
  - `text_extractor_initiator/`: Text extractor initiator Lambda function
  - `text_extractor_processor/`: Text extractor processor Lambda function
  - Other Lambda functions for various pipeline stages

- **`layers/`**: Contains Lambda layer code
  - `climate-risk-core-utilities/`: Core utilities for the pipeline
  - `database-dependencies/`: Database dependencies for PostgreSQL
  - Other layers for specific functionalities

- **`docs/`**: Contains documentation
  - `status/`: Project status and context documents
  - Other documentation files

### Key Files

- **`invoke_pipeline_test.py`**: Script to invoke the pipeline test Lambda function
- **`deploy_updated_pipeline_test.py`**: Script to deploy updates to the pipeline test Lambda function
- **`deploy_source_document_events.py`**: Script to deploy the SNS/SQS workflow

## Cost Considerations

### Textract Costs

Textract is one of the more expensive services used in this pipeline. Each page processed by Textract incurs a cost, and these costs can add up quickly when processing large documents or many documents.

**Cost Reduction Strategies:**
- Use the `--skip-lambda-invocation` flag when testing the pipeline to avoid triggering Textract jobs
- Limit the number and size of documents processed during testing
- Clean up test documents after testing to avoid reprocessing
- Use the cleanup Lambda function to remove test artifacts

### Other AI/ML Service Costs

Other AI/ML services like Amazon Comprehend and Amazon Titan (for embeddings) also incur costs based on usage.

**Cost Reduction Strategies:**
- Test with a small number of documents
- Use mock data or cached results when possible
- Monitor usage and costs regularly

### Database and Storage Costs

RDS PostgreSQL, Neptune, and S3 storage also contribute to the overall cost.

**Cost Reduction Strategies:**
- Clean up test data after testing
- Use smaller instance sizes for development and testing
- Monitor storage usage and delete unnecessary data

## Related Documentation

For more detailed information, refer to these documents:

- **[source_document_events.md](/docs/source_document_events.md)**: Details on the SNS/SQS workflow for text extraction
- **[TEXTEXTRACTOR_COMPLETION_SUMMARY.md](/docs/status/TEXTEXTRACTOR_COMPLETION_SUMMARY.md)**: Overview of the text extraction process
- **[LAMBDA_LAYER_IMPORTS_FIXED_2025-07-05T19-20-00Z.md](/docs/status/LAMBDA_LAYER_IMPORTS_FIXED_2025-07-05T19-20-00Z.md)**: Information on Lambda layer imports
- **[DATABASE_CONFIGURATION_COMPLETE_2025-07-05T20-10-00Z.md](/docs/status/DATABASE_CONFIGURATION_COMPLETE_2025-07-05T20-10-00Z.md)**: Database configuration details
- **[AWS_COST_BREAKDOWN_2025-07-10T03-00-00Z.md](/docs/status/AWS_COST_BREAKDOWN_2025-07-10T03-00-00Z.md)**: Cost breakdown for AWS services

## Current Status

The SNS/SQS workflow for text extraction is now implemented and tested. The pipeline test handler has been updated to support this workflow, and the text extractor initiator Lambda function has been updated to handle SQS events.

The system now has a more robust and scalable architecture for processing documents, with better error handling and retry capabilities.

## Next Steps

See the accompanying NEXT_STEPS document for details on the next steps for the project.
