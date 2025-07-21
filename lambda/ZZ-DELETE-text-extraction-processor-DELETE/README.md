# Text Extraction Processor

Gold standard text extraction Lambda functions for the Climate Risk RAG system.

## Overview

This module contains two Lambda functions that work together to extract text from PDF documents using AWS Textract:

1. **Text Extractor Initiator** (`text_extractor_initiator.py`)
   - Triggered by S3 uploads
   - Starts async Textract jobs
   - Updates processing status in database

2. **Text Extractor Processor** (`text_extractor_processor.py`)
   - Triggered by Textract completion SNS notifications
   - Retrieves and processes Textract results
   - Extracts structured text content
   - Saves results to S3 and updates database

## Key Features

- ✅ **Gold Standard DatabaseManager**: Uses context manager pattern for database connections
- ✅ **Gold Standard DocumentIDManager**: Proper document ID management
- ✅ **Structured Text Extraction**: Extracts text, tables, and forms
- ✅ **Error Handling**: Comprehensive error handling and status tracking
- ✅ **SNS Integration**: Publishes completion messages for downstream processing

## Dependencies

### Lambda Layers (Gold Standard)
- `database-core-layer:7` - DatabaseManager, DocumentIDManager, psycopg2
- `climate-risk-core-utilities:16` - Core AWS utilities

### Environment Variables

#### Text Extractor Initiator
- `DATABASE_SECRET_NAME` - RDS secret name for database credentials
- `DB_HOST` - PostgreSQL database host
- `DB_PORT` - PostgreSQL database port (default: 5432)
- `DB_NAME` - Database name
- `TEXTRACT_SNS_TOPIC_ARN` - SNS topic for Textract completion notifications
- `TEXTRACT_SERVICE_ROLE_ARN` - IAM role for Textract service
- `OUTPUT_BUCKET` - S3 bucket for Textract output

#### Text Extractor Processor
- `DATABASE_SECRET_NAME` - RDS secret name for database credentials
- `DB_HOST` - PostgreSQL database host
- `DB_PORT` - PostgreSQL database port (default: 5432)
- `DB_NAME` - Database name
- `OUTPUT_BUCKET` - S3 bucket for Textract output
- `TEXT_BUCKET` - S3 bucket for extracted text storage
- `CHUNKS_BUCKET` - S3 bucket for text chunks
- `CHUNKS_READY_TOPIC_ARN` - SNS topic for text extraction completion

## Architecture

```
text-extraction-processor/
├── text_extractor_initiator.py    # Initiator Lambda function
├── text_extractor_processor.py    # Processor Lambda function
├── requirements.txt                # Dependencies (layers only)
├── README.md                       # This file
└── src/                           # Additional source code
    ├── processors/                # Text processing modules
    ├── config/                    # Configuration modules
    └── messaging/                 # Messaging utilities
```

## Processing Flow

1. **Document Upload**: PDF uploaded to S3 source bucket
2. **Initiation**: S3 event triggers initiator Lambda
3. **Textract Job**: Initiator starts async Textract job
4. **Status Update**: Processing status updated in database
5. **Completion**: Textract sends SNS notification when complete
6. **Processing**: Processor Lambda retrieves and processes results
7. **Text Extraction**: Structured text content extracted
8. **Storage**: Results saved to S3 and database updated
9. **Notification**: SNS message published for downstream processing

## Gold Standard Patterns Used

1. **Database Connectivity**: Uses `DatabaseManager` with context manager pattern
2. **Document Management**: Uses `DocumentIDManager` for proper document ID handling
3. **Error Handling**: Comprehensive try/catch with proper logging
4. **Status Tracking**: Database-backed processing status management
5. **Async Processing**: SNS-based event-driven architecture

## Current Status

- ✅ **Layer Configuration**: Updated to gold standard layers
- ✅ **Database Integration**: Using gold standard DatabaseManager
- ✅ **Code Structure**: Clean, modular architecture
- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Ready for Testing**: Functions ready for integration testing
