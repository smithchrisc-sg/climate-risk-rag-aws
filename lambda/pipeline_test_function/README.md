# Pipeline Test Function

Modernized pipeline test Lambda function using gold standard patterns.

## Overview

This function runs parameterized pipeline tests from within the VPC with database access. It uses the gold standard `database-core-layer:6` for database connectivity and document management.

## Key Features

- ✅ **Gold Standard DatabaseManager**: Uses context manager pattern for database connections
- ✅ **Gold Standard DocumentIDManager**: Modernized document ID management
- ✅ **Standardized Error Handling**: Comprehensive logging and error reporting
- ✅ **Health Check Endpoint**: Built-in health monitoring
- ✅ **Clean Architecture**: Separated concerns with proper entry point

## Dependencies

### Lambda Layers (Gold Standard)
- `database-core-layer:6` - DatabaseManager, DocumentIDManager, psycopg2
- `climate-risk-core-utilities:16` - Core AWS utilities

### Environment Variables
- `DATABASE_SECRET_NAME` - RDS secret name for database credentials
- `DATABASE_CONNECTION_METHOD` - Set to "secrets_manager"
- `DB_HOST` - PostgreSQL database host
- `DB_PORT` - PostgreSQL database port (default: 5432)
- `DB_NAME` - Database name
- `SOURCE_DOCUMENTS_BUCKET` - S3 bucket for source documents
- `SQLITE_S3_BUCKET` - S3 bucket for SQLite cache
- `SQLITE_S3_KEY` - S3 key for SQLite database file

## Usage

### Health Check
```json
{
  "action": "health_check"
}
```

### Run Pipeline Test
```json
{
  "action": "test",
  "test_config": {
    "test_name": "document_processing_test",
    "doc_id_from_filename": "test_document_123",
    "target_functions": [
      "solve-global-kr-textextractor-initiator",
      "solve-global-kr-text-chunker-v2"
    ]
  },
  "download_sqlite": true
}
```

## Architecture

```
pipeline_test_function/
├── src/
│   └── pipeline_test_handler.py  # Main business logic
├── handler.py                    # Clean entry point
├── requirements.txt              # Dependencies (layers only)
└── README.md                     # This file
```

## Gold Standard Patterns Used

1. **Database Connectivity**: Uses `DatabaseManager` with context manager pattern
2. **Document Management**: Uses `DocumentIDManager` for proper document ID handling
3. **Error Handling**: Comprehensive try/catch with proper logging
4. **Import Strategy**: Clean imports from layer structure
5. **Environment Configuration**: Standardized environment variable usage

## Deployment

This function is deployed using CDK with:
- Application subnets for VPC access
- Gold standard layer versions
- Comprehensive IAM permissions
- Proper environment variable configuration
