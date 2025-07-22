# Climate Risk RAG System - Systematic Redeployment Guide

## Overview
This guide documents the systematic redeployment process for the Climate Risk RAG system using standardized Lambda layers and proper IAM roles. This approach ensures consistent, reliable deployments with proper dependency management.

## Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11 environment
- Access to solve-global AWS profile

## Core Architecture Components

### 1. Standardized Lambda Layers
Our system uses a standardized layer architecture for consistent dependency management:

#### Database Core Layer (Version 16)
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16`
- **Contents**: DatabaseManager, DocumentIDManager, core utilities
- **Used by**: All functions requiring database access

#### Database Dependencies Layer (Version 2)  
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2`
- **Contents**: psycopg2, boto3, and database-related dependencies
- **Used by**: All functions requiring database access

#### OpenSearch Dependencies Layer (Version 4)
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:opensearch-dependencies:4`
- **Contents**: opensearch-py, requests-aws4auth
- **Used by**: Functions requiring OpenSearch access

### 2. IAM Roles

#### Document Processing Lambda Role
- **ARN**: `arn:aws:iam::861276078413:role/document-processing-lambda-role`
- **Policy**: `arn:aws:iam::861276078413:policy/document-processing-policy`
- **Permissions**:
  - CloudWatch Logs (create/write)
  - VPC access (ENI management)
  - Textract (start/get operations)
  - Comprehend (entity/keyphrase detection)
  - S3 (read/write to solve-global-kr-* buckets)
  - SNS (publish to all topics)
  - SQS (receive/delete messages)
  - Secrets Manager (RDS credentials)
  - IAM (pass role for Textract/Comprehend)
  - OpenSearch (HTTP operations)

### 3. Environment Configuration
Standard environment variables for all functions:
```bash
DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863
DB_PORT=5432
DB_NAME=climate_risk_rag
DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
```

### 4. VPC Configuration
All Lambda functions deployed in VPC:
- **Subnets**: subnet-03d8bd6cf3491f38c, subnet-0c0be1dd59f70f70e
- **Security Group**: sg-0c9e10b9cfb4c9eb0

## Deployment Process

### Phase 1: Core Infrastructure Functions

#### 1. Cleanup Service
```bash
cd /Users/chris/climate-risk-rag-aws/lambda/cleanup-service
zip -r cleanup-service.zip . -x "*.pyc" "*__pycache__*" "*.DS_Store"

aws lambda create-function \
  --function-name cleanup-service \
  --runtime python3.11 \
  --role arn:aws:iam::861276078413:role/document-processing-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://cleanup-service.zip \
  --timeout 300 \
  --memory-size 512 \
  --layers \
    arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16 \
    arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2 \
  --environment Variables='{DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863,DB_PORT=5432,DB_NAME=climate_risk_rag,DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com}' \
  --vpc-config SubnetIds=subnet-03d8bd6cf3491f38c,subnet-0c0be1dd59f70f70e,SecurityGroupIds=sg-0c9e10b9cfb4c9eb0 \
  --profile solve-global
```

#### 2. Pipeline Test Function
```bash
cd /Users/chris/climate-risk-rag-aws/lambda/pipeline-test-function
zip -r pipeline-test-function.zip . -x "*.pyc" "*__pycache__*" "*.DS_Store"

aws lambda create-function \
  --function-name pipeline-test-function \
  --runtime python3.11 \
  --role arn:aws:iam::861276078413:role/document-processing-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://pipeline-test-function.zip \
  --timeout 300 \
  --memory-size 512 \
  --layers \
    arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16 \
    arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2 \
  --environment Variables='{DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863,DB_PORT=5432,DB_NAME=climate_risk_rag,DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com,SOURCE_BUCKET=solve-global-kr-dl-source-documents-861276078413-us-east-1}' \
  --vpc-config SubnetIds=subnet-03d8bd6cf3491f38c,subnet-0c0be1dd59f70f70e,SecurityGroupIds=sg-0c9e10b9cfb4c9eb0 \
  --profile solve-global
```

### Phase 2: Text Extraction Functions

#### 1. Text Extractor Initiator
```bash
cd /Users/chris/climate-risk-rag-aws/lambda/text-extractor-initiator
zip -r text-extractor-initiator.zip . -x "*.pyc" "*__pycache__*" "*.DS_Store"

aws lambda create-function \
  --function-name text-extractor-initiator \
  --runtime python3.11 \
  --role arn:aws:iam::861276078413:role/document-processing-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://text-extractor-initiator.zip \
  --timeout 300 \
  --memory-size 512 \
  --layers \
    arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16 \
    arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2 \
  --environment Variables='{DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863,DB_PORT=5432,DB_NAME=climate_risk_rag,DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com,TEXTRACT_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:solve-global-kr-textract-completion,TEXTRACT_SERVICE_ROLE_ARN=arn:aws:iam::861276078413:role/solve-global-kr-textract-service-role,OUTPUT_BUCKET=solve-global-kr-dl-text-861276078413-us-east-1}' \
  --vpc-config SubnetIds=subnet-03d8bd6cf3491f38c,subnet-0c0be1dd59f70f70e,SecurityGroupIds=sg-0c9e10b9cfb4c9eb0 \
  --profile solve-global

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name text-extractor-initiator \
  --event-source-arn arn:aws:sqs:us-east-1:861276078413:solve-global-kr-textextractor-initiator-queue \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --profile solve-global
```

#### 2. Text Extractor Processor
```bash
cd /Users/chris/climate-risk-rag-aws/lambda/text-extractor-processor
zip -r text-extractor-processor.zip . -x "*.pyc" "*__pycache__*" "*.DS_Store"

aws lambda create-function \
  --function-name text-extractor-processor \
  --runtime python3.11 \
  --role arn:aws:iam::861276078413:role/document-processing-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://text-extractor-processor.zip \
  --timeout 300 \
  --memory-size 512 \
  --layers \
    arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16 \
    arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2 \
  --environment Variables='{DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863,DB_PORT=5432,DB_NAME=climate_risk_rag,DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com,OUTPUT_BUCKET=solve-global-kr-dl-text-861276078413-us-east-1,COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:text-extraction-complete}' \
  --vpc-config SubnetIds=subnet-03d8bd6cf3491f38c,subnet-0c0be1dd59f70f70e,SecurityGroupIds=sg-0c9e10b9cfb4c9eb0 \
  --profile solve-global

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name text-extractor-processor \
  --event-source-arn arn:aws:sqs:us-east-1:861276078413:solve-global-kr-textextractor-processor \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --profile solve-global
```

### Phase 3: Text Chunking Functions

#### 1. Text Chunker Processor
```bash
cd /Users/chris/climate-risk-rag-aws/lambda/text-chunker-processor
zip -r text-chunker-processor.zip . -x "*.pyc" "*__pycache__*" "*.DS_Store"

aws lambda create-function \
  --function-name text-chunker-processor \
  --runtime python3.11 \
  --role arn:aws:iam::861276078413:role/document-processing-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://text-chunker-processor.zip \
  --timeout 300 \
  --memory-size 1024 \
  --layers \
    arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:16 \
    arn:aws:lambda:us-east-1:861276078413:layer:database-dependencies:2 \
  --environment Variables='{DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863,DB_PORT=5432,DB_NAME=climate_risk_rag,DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com,TEXT_BUCKET=solve-global-kr-dl-text-861276078413-us-east-1,CHUNKS_BUCKET=solve-global-kr-dl-chunks-861276078413-us-east-1,CHUNKS_READY_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:text-chunking-complete}' \
  --vpc-config SubnetIds=subnet-03d8bd6cf3491f38c,subnet-0c0be1dd59f70f70e,SecurityGroupIds=sg-0c9e10b9cfb4c9eb0 \
  --profile solve-global

# Create event source mapping
aws lambda create-event-source-mapping \
  --function-name text-chunker-processor \
  --event-source-arn arn:aws:sqs:us-east-1:861276078413:text-chunker-queue \
  --batch-size 10 \
  --maximum-batching-window-in-seconds 5 \
  --profile solve-global
```

## SNS Topic Configuration

### Required SNS Topics
```bash
# Create text-chunking-complete topic if it doesn't exist
aws sns create-topic --name text-chunking-complete --profile solve-global

# Subscribe downstream services
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:861276078413:text-chunking-complete --protocol sqs --notification-endpoint arn:aws:sqs:us-east-1:861276078413:keyword-indexer-initiator-queue --profile solve-global

aws sns subscribe --topic-arn arn:aws:sns:us-east-1:861276078413:text-chunking-complete --protocol sqs --notification-endpoint arn:aws:sqs:us-east-1:861276078413:nlp-worker-queue --profile solve-global
```

## S3 Bucket Notification Configuration

### Update S3 notifications for data-lake/ folder structure
```bash
# Configure S3 bucket notifications to support both data_lake/ and data-lake/ paths
aws s3api put-bucket-notification-configuration --bucket solve-global-kr-dl-source-documents-861276078413-us-east-1 --notification-configuration '{
  "TopicConfigurations": [
    {
      "Id": "ZTdiZjBkNGYtNGU5NS00ODE0LTliYjItMTc2OTZlZTExZDFk",
      "TopicArn": "arn:aws:sns:us-east-1:861276078413:solve-global-kr-source-document-events",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "Prefix", "Value": "data_lake/"},
            {"Name": "Suffix", "Value": ".pdf"}
          ]
        }
      }
    },
    {
      "Id": "data-lake-hyphen-config",
      "TopicArn": "arn:aws:sns:us-east-1:861276078413:solve-global-kr-source-document-events",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {"Name": "Prefix", "Value": "data-lake/"},
            {"Name": "Suffix", "Value": ".pdf"}
          ]
        }
      }
    }
  ]
}' --profile solve-global
```

## Testing the Pipeline

### 1. Test Document Processing
```bash
cd /Users/chris/climate-risk-rag-aws
python3 invoke_pipeline_test.py --num-documents 1 --min-size-mb 1 --max-size-mb 2
```

### 2. Monitor Pipeline Execution
```bash
# Monitor text extraction
aws logs filter-log-events --log-group-name "/aws/lambda/text-extractor-initiator" --start-time $(date -v-10M +%s)000 --profile solve-global

# Monitor text chunking
aws logs filter-log-events --log-group-name "/aws/lambda/text-chunker-processor" --start-time $(date -v-10M +%s)000 --profile solve-global
```

## Key Success Indicators

1. ✅ **Document Upload**: Pipeline test function successfully copies documents to S3
2. ✅ **Text Extraction**: Textract jobs complete successfully, text saved to S3
3. ✅ **Text Chunking**: Smart structured chunks created and saved to S3
4. ✅ **Completion Messages**: SNS messages published for downstream processing
5. ✅ **Database Tracking**: All processing stages tracked in database

## Troubleshooting

### Common Issues
1. **Environment Variables**: Ensure all required environment variables are set
2. **IAM Permissions**: Verify document-processing-lambda-role has all required permissions
3. **VPC Configuration**: Ensure Lambda functions can access RDS and internet
4. **Layer Versions**: Use correct layer versions (database-core-layer:16, database-dependencies:2)
5. **SNS Topics**: Verify all required SNS topics exist and have proper subscriptions

### Validation Commands
```bash
# Check function configuration
aws lambda get-function-configuration --function-name [FUNCTION_NAME] --profile solve-global

# Check event source mappings
aws lambda list-event-source-mappings --function-name [FUNCTION_NAME] --profile solve-global

# Check SNS subscriptions
aws sns list-subscriptions-by-topic --topic-arn [TOPIC_ARN] --profile solve-global
```

## Next Steps
After completing this redeployment:
1. Deploy keyword indexing functions
2. Deploy vector embedding functions  
3. Deploy NLP processing functions
4. Update CDK code to reflect current architecture
5. Create automated deployment scripts

---

**Last Updated**: 2025-07-22  
**Version**: 1.0  
**Status**: Tested and Validated
