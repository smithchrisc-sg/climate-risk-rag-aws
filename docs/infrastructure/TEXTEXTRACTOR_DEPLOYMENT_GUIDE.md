# TextExtractor Async Architecture - Deployment Guide

## 🚀 **Deployment Steps**

### **1. Database Schema Setup**

First, apply the PostgreSQL schema to your RDS instance:

```bash
# Connect to your PostgreSQL database
psql -h your-rds-endpoint -U postgres -d climate_risk_rag

# Apply the schema
\i database/textextractor_schema.sql

# Verify tables were created
\dt

# Check views
\dv
```

### **2. CDK Infrastructure Deployment**

Update your main CDK stack to include the TextExtractor async components:

```typescript
// In your main stack file
import { TextExtractorAsyncStack } from './infrastructure/textextractor_async_stack';

// Add to your stack constructor
const textExtractorStack = new TextExtractorAsyncStack(this, 'TextExtractorAsync', {
  documentsBucket: this.documentsBucket,
  textBucket: this.textBucket,
  database: this.database,
  vpc: this.vpc,
  databaseSecurityGroup: this.databaseSecurityGroup
});
```

Deploy the infrastructure:

```bash
# Deploy the TextExtractor async stack
cdk deploy TextExtractorAsync

# Note the outputs - you'll need these ARNs for configuration
```

### **3. Lambda Function Deployment**

Package and deploy the Lambda functions:

```bash
# Package Initiator Lambda
cd lambda/text_extractor_initiator
pip install -r requirements.txt -t .
zip -r text_extractor_initiator.zip .

# Package Processor Lambda  
cd ../text_extractor_processor
pip install -r requirements.txt -t .
zip -r text_extractor_processor.zip .

# Deploy via CDK (already configured in the stack)
cdk deploy
```

### **4. Environment Configuration**

Ensure the following environment variables are set correctly:

**TextExtractor Initiator:**
- `DATABASE_URL`: PostgreSQL connection string
- `TEXTRACT_SNS_TOPIC_ARN`: SNS topic for completion notifications
- `TEXTRACT_SERVICE_ROLE_ARN`: IAM role for Textract service
- `OUTPUT_BUCKET`: S3 bucket for structured output

**TextExtractor Processor:**
- `DATABASE_URL`: PostgreSQL connection string
- `OUTPUT_BUCKET`: S3 bucket for structured output
- `NEXT_STAGE_QUEUE_URL`: SQS queue for chunking triggers

## 🧪 **Testing Guide**

### **1. Unit Testing**

Test individual Lambda functions locally:

```python
# Test Initiator Lambda
import json
from text_extractor_initiator import handler

# Mock S3 event
test_event = {
    "Records": [{
        "eventSource": "aws:s3",
        "s3": {
            "bucket": {"name": "your-documents-bucket"},
            "object": {"key": "documents/test.pdf"}
        }
    }]
}

result = handler(test_event, None)
print(json.dumps(result, indent=2))
```

```python
# Test Processor Lambda
from text_extractor_processor import handler

# Mock SNS event
test_event = {
    "Records": [{
        "EventSource": "aws:sns",
        "Sns": {
            "Message": json.dumps({
                "JobId": "test-job-id",
                "Status": "SUCCEEDED"
            })
        }
    }]
}

result = handler(test_event, None)
print(json.dumps(result, indent=2))
```

### **2. Integration Testing**

Test the complete async flow:

```bash
# 1. Upload a test PDF to trigger the pipeline
aws s3 cp test-document.pdf s3://your-documents-bucket/documents/

# 2. Monitor the database for job creation
psql -h your-rds-endpoint -U postgres -d climate_risk_rag -c "
SELECT job_id, doc_hash, status, started_at 
FROM textract_jobs 
ORDER BY started_at DESC 
LIMIT 5;"

# 3. Check CloudWatch logs for both Lambda functions
aws logs tail /aws/lambda/TextExtractorInitiator --follow
aws logs tail /aws/lambda/TextExtractorProcessor --follow

# 4. Verify structured output in S3
aws s3 ls s3://your-text-bucket/extracted_documents/ --recursive

# 5. Check processing pipeline status
psql -h your-rds-endpoint -U postgres -d climate_risk_rag -c "
SELECT * FROM processing_pipeline_status 
WHERE filename LIKE '%test-document%';"
```

### **3. Performance Testing**

Test with multiple documents:

```bash
# Upload multiple PDFs
for i in {1..10}; do
    aws s3 cp test-doc-$i.pdf s3://your-documents-bucket/documents/
done

# Monitor processing statistics
psql -h your-rds-endpoint -U postgres -d climate_risk_rag -c "
SELECT * FROM textract_job_stats;"

# Check queue depth
aws sqs get-queue-attributes \
    --queue-url your-chunking-queue-url \
    --attribute-names ApproximateNumberOfMessages
```

## 📊 **Monitoring & Troubleshooting**

### **Key Metrics to Monitor**

1. **Lambda Function Metrics:**
   - Invocation count
   - Error rate
   - Duration
   - Concurrent executions

2. **Queue Metrics:**
   - Message count
   - Age of oldest message
   - Dead letter queue depth

3. **Database Metrics:**
   - Job success rate
   - Average processing time
   - Failed job count

### **Common Issues & Solutions**

**Issue: Textract jobs timing out**
```sql
-- Find long-running jobs
SELECT job_id, doc_hash, started_at, 
       EXTRACT(EPOCH FROM (NOW() - started_at))/60 as minutes_running
FROM textract_jobs 
WHERE status = 'IN_PROGRESS' 
  AND started_at < NOW() - INTERVAL '10 minutes';
```

**Issue: Lambda function errors**
```bash
# Check recent errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/TextExtractorInitiator \
    --filter-pattern "ERROR" \
    --start-time $(date -d '1 hour ago' +%s)000
```

**Issue: Database connection issues**
```sql
-- Check active connections
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

### **Cleanup & Maintenance**

**Regular cleanup of completed jobs:**
```sql
-- Clean up old completed jobs (run weekly)
DELETE FROM textract_jobs 
WHERE status IN ('SUCCEEDED', 'FAILED') 
  AND completed_at < NOW() - INTERVAL '30 days';
```

**Monitor disk usage:**
```bash
# Check S3 storage usage
aws s3api list-objects-v2 \
    --bucket your-text-bucket \
    --prefix extracted_documents/ \
    --query 'sum(Contents[].Size)' \
    --output text
```

## 🔧 **Configuration Tuning**

### **Lambda Function Optimization**

**Memory allocation based on document size:**
- Initiator: 512 MB (sufficient for job initiation)
- Processor: 1024 MB (handles large JSON responses)

**Timeout settings:**
- Initiator: 5 minutes (job initiation + database operations)
- Processor: 15 minutes (large document processing)

### **Queue Configuration**

**Visibility timeout:** 15 minutes (matches processor timeout)
**Dead letter queue:** 3 max receives before DLQ
**Message retention:** 14 days

### **Database Connection Pooling**

Consider implementing connection pooling for high-volume processing:

```python
# Example connection pool configuration
import psycopg2.pool

connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    dsn=database_url
)
```

## 📈 **Scaling Considerations**

### **Concurrent Processing Limits**

- **Textract**: 600 concurrent jobs (AWS quota)
- **Lambda**: 1000 concurrent executions (default)
- **Database**: Monitor connection count

### **Cost Optimization**

- **Textract**: $5 per 1000 pages (AnalyzeDocument)
- **Lambda**: Pay per execution time
- **S3**: Storage costs for structured output
- **Database**: Connection time and storage

### **Performance Tuning**

1. **Batch processing**: Group small documents
2. **Parallel processing**: Leverage Lambda concurrency
3. **Caching**: Store frequently accessed metadata
4. **Monitoring**: Set up CloudWatch dashboards

This deployment guide provides everything needed to successfully deploy and operate the TextExtractor async architecture in production.
