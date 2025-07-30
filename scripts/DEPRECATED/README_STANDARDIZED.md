# Climate Risk RAG System - Standardized Architecture

## Overview

This repository contains the Climate Risk RAG (Retrieval-Augmented Generation) system, designed to process climate risk documents and provide intelligent search and analysis capabilities. The system has been systematically redeployed using standardized Lambda layers and proper IAM roles for consistent, reliable operation.

## Architecture

### Core Components

1. **Document Processing Pipeline**
   - Text extraction using AWS Textract
   - Smart structured chunking
   - Keyword indexing with OpenSearch
   - Vector embeddings for semantic search
   - NLP processing for entity extraction

2. **Standardized Lambda Layers**
   - `database-core-layer:16` - DatabaseManager, DocumentIDManager, core utilities
   - `database-dependencies:2` - psycopg2, boto3, database dependencies
   - `opensearch-dependencies:4` - opensearch-py, requests-aws4auth

3. **IAM Role Architecture**
   - `document-processing-lambda-role` - Unified role for all document processing functions
   - Principle of least privilege with scoped permissions
   - Proper VPC, database, and service access

4. **Messaging Infrastructure**
   - SNS topics for event-driven processing
   - SQS queues for reliable message delivery
   - Event source mappings for Lambda triggers

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.11
- Access to `solve-global` AWS profile

### Option 1: Automated Deployment

```bash
# Deploy complete system using automated script
python3 deploy_complete_system.py

# Validate deployment
python3 validate_deployment.py

# Test the pipeline
python3 invoke_pipeline_test.py --num-documents 1
```

### Option 2: Manual Deployment

Follow the step-by-step guide in [REDEPLOYMENT_GUIDE.md](REDEPLOYMENT_GUIDE.md)

### Option 3: CDK Deployment

```bash
cd cdk
pip install -r requirements.txt
cdk deploy --app "python3 app_complete_standardized.py" --all
```

## System Components

### Lambda Functions

#### Core Infrastructure
- **cleanup-service** - System cleanup and maintenance
- **pipeline-test-function** - Document processing pipeline testing

#### Text Processing
- **text-extractor-initiator** - Initiates Textract jobs for document processing
- **text-extractor-processor** - Processes Textract results and saves extracted text
- **text-chunker-processor** - Creates smart structured chunks from extracted text

#### Keyword & Search (To be deployed)
- **keyword-indexer-initiator** - Initiates keyword indexing jobs
- **keyword-indexer-worker** - Processes keywords and updates OpenSearch
- **vectors-initiator** - Initiates vector embedding generation
- **vectors-worker** - Generates and stores vector embeddings

#### NLP Processing (To be deployed)
- **nlp-processor** - Entity extraction and NLP analysis
- **vector-embeddings-initiator** - Initiates embedding generation
- **vector-embeddings-worker** - Processes embeddings for semantic search

### Data Storage

#### S3 Buckets
- **Source Documents**: `solve-global-kr-dl-source-documents-*` - Original PDF documents
- **Text Storage**: `solve-global-kr-dl-text-*` - Extracted text and Textract responses
- **Chunks Storage**: `solve-global-kr-dl-chunks-*` - Smart structured text chunks
- **Vectors Storage**: `solve-global-kr-dl-vectors-*` - Vector embeddings
- **Keywords Storage**: `solve-global-kr-dl-keywords-*` - Keyword indices

#### Databases
- **PostgreSQL (RDS)**: Document metadata, processing status, audit trails
- **OpenSearch**: Full-text search, keyword indexing, vector search
- **Neptune**: Knowledge graph relationships (optional)

### Messaging & Events

#### SNS Topics
- `text-extraction-complete` - Triggered when text extraction completes
- `text-chunking-complete` - Triggered when text chunking completes
- `solve-global-kr-textract-completion` - Textract service completion notifications
- `solve-global-kr-source-document-events` - S3 document upload events

#### SQS Queues
- `solve-global-kr-textextractor-initiator-queue` - Text extraction initiation
- `solve-global-kr-textextractor-processor` - Text extraction processing
- `text-chunker-queue` - Text chunking processing
- `keyword-indexer-initiator-queue` - Keyword indexing initiation
- `nlp-worker-queue` - NLP processing

## Configuration

### Environment Variables

All Lambda functions use standardized environment variables:

```bash
DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863
DB_PORT=5432
DB_NAME=climate_risk_rag
DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
```

Function-specific variables:
- `SOURCE_BUCKET` - Source documents bucket
- `OUTPUT_BUCKET` - Text output bucket  
- `CHUNKS_BUCKET` - Chunks output bucket
- `TEXTRACT_SNS_TOPIC_ARN` - Textract completion topic
- `COMPLETION_TOPIC_ARN` - Function completion topic

### VPC Configuration

All Lambda functions are deployed in VPC:
- **Subnets**: `subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`
- **Security Group**: `sg-0c9e10b9cfb4c9eb0`

## Testing

### Pipeline Testing

```bash
# Test with single document
python3 invoke_pipeline_test.py --num-documents 1

# Test with specific size range
python3 invoke_pipeline_test.py --num-documents 5 --min-size-mb 1 --max-size-mb 3

# Test with specific document types
python3 invoke_pipeline_test.py --num-documents 2 --document-types report policy
```

### Monitoring

```bash
# Monitor text extraction
aws logs filter-log-events --log-group-name "/aws/lambda/text-extractor-initiator" --start-time $(date -v-10M +%s)000 --profile solve-global

# Monitor text chunking
aws logs filter-log-events --log-group-name "/aws/lambda/text-chunker-processor" --start-time $(date -v-10M +%s)000 --profile solve-global

# Check processing status
python3 monitor_pipeline_status.py
```

## Development

### Adding New Functions

1. Create function directory in `lambda/`
2. Use standardized layers and IAM role
3. Follow environment variable conventions
4. Add to deployment scripts
5. Update CDK configuration

### Layer Management

```bash
# Build database core layer
cd layers/database-core-layer
./build_layer.sh

# Build database dependencies layer  
cd layers/database-dependencies
./build_layer.sh

# Deploy updated layers
aws lambda publish-layer-version --layer-name database-core-layer --zip-file fileb://layer.zip --profile solve-global
```

### Database Schema

The system uses an audit-first database design with comprehensive tracking:

```sql
-- Document processing status tracking
CREATE TABLE document_processing_status (
    doc_id VARCHAR(64) PRIMARY KEY,
    stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document metadata
CREATE TABLE documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    original_filename VARCHAR(255),
    source_url TEXT,
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Common Issues

1. **Lambda Function Timeouts**
   - Check VPC configuration and NAT gateway
   - Verify database connectivity
   - Review memory allocation

2. **Layer Import Errors**
   - Ensure correct layer versions
   - Check layer compatibility with Python 3.11
   - Verify layer ARNs in function configuration

3. **Database Connection Issues**
   - Verify security group rules
   - Check RDS instance status
   - Validate secrets manager configuration

4. **S3 Event Notifications**
   - Verify bucket notification configuration
   - Check SNS topic permissions
   - Validate SQS queue subscriptions

### Debugging Commands

```bash
# Check function configuration
aws lambda get-function-configuration --function-name [FUNCTION_NAME] --profile solve-global

# Test function directly
aws lambda invoke --function-name [FUNCTION_NAME] --payload '{}' response.json --profile solve-global

# Check event source mappings
aws lambda list-event-source-mappings --function-name [FUNCTION_NAME] --profile solve-global

# Monitor CloudWatch logs
aws logs tail /aws/lambda/[FUNCTION_NAME] --follow --profile solve-global
```

## Security

### IAM Permissions

The system follows the principle of least privilege:
- Functions only have access to required AWS services
- S3 access scoped to specific bucket patterns
- Database access through secrets manager
- VPC isolation for sensitive operations

### Data Protection

- All data encrypted at rest (S3, RDS, OpenSearch)
- Secrets managed through AWS Secrets Manager
- VPC isolation for database access
- Audit trails for all processing operations

## Performance

### Optimization

- Smart chunking preserves document structure
- Batch processing for efficiency
- Connection pooling for database operations
- Asynchronous processing with SQS/SNS

### Monitoring

- CloudWatch metrics for all functions
- Database performance monitoring
- S3 access patterns analysis
- Cost optimization recommendations

## Contributing

1. Follow the standardized architecture patterns
2. Use existing layers and IAM roles
3. Add comprehensive logging
4. Include unit tests
5. Update documentation

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Validate deployment with `validate_deployment.py`
4. Consult the [REDEPLOYMENT_GUIDE.md](REDEPLOYMENT_GUIDE.md)

---

**Last Updated**: 2025-07-22  
**Architecture Version**: Standardized v1.0  
**Status**: Production Ready
