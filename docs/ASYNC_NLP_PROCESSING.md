# Asynchronous NLP Processing Pipeline

## Overview

The Asynchronous NLP Processing Pipeline provides a scalable, event-driven approach to natural language processing using AWS Comprehend. This system eliminates synchronous waiting and timeout issues by processing entity detection and key phrase detection jobs independently.

## Architecture

### Components

1. **NLP Processor** (`nlp-processor`)
   - Initiates Comprehend jobs asynchronously
   - No longer waits for job completion
   - Triggers both entity and key phrase detection jobs

2. **Entity Worker** (`nlp-worker-entity`)
   - Processes entity detection results independently
   - Triggered by Comprehend job completion events
   - Updates `nlp_entity_processing` stage

3. **Key Phrase Worker** (`nlp-worker-keyphrase`)
   - Processes key phrase detection results independently
   - Triggered by Comprehend job completion events
   - Updates `nlp_keyphrase_processing` stage

4. **Job Monitor** (`comprehend-job-monitor`)
   - Polls for completed Comprehend jobs every 2 minutes
   - Triggers appropriate workers when jobs complete
   - Handles job completion detection

### Infrastructure

#### SNS Topics
- `comprehend-entity-completion`: Entity job completion notifications
- `comprehend-keyphrase-completion`: Key phrase job completion notifications

#### SQS Queues
- `nlp-worker-entity-queue`: Entity worker message queue
- `nlp-worker-keyphrase-queue`: Key phrase worker message queue
- Dead letter queues for both workers

#### Lambda Functions
- `nlp-processor`: Updated async processor
- `nlp-worker-entity`: Entity results processor
- `nlp-worker-keyphrase`: Key phrase results processor
- `comprehend-job-monitor`: Job completion monitor

#### CloudWatch Events
- `comprehend-job-monitor-schedule`: Triggers monitor every 2 minutes

## Database Schema Changes

### New Processing Stages

The following stages were added to the `valid_stage` constraints:

```sql
-- New stages for async NLP processing
'nlp_entity_processing'     -- Entity detection processing
'nlp_keyphrase_processing'  -- Key phrase detection processing
```

### Processing Flow

1. `nlp_initiate` → `in_progress` → `completed`
2. `nlp_processing` → `in_progress`
3. `nlp_entity_processing` → `in_progress` → `completed`
4. `nlp_keyphrase_processing` → `in_progress` → `completed`

## Message Flow

### 1. Document Processing Initiation
```
chunks-ready SNS → NLP Processor Lambda
```

### 2. Comprehend Job Initiation
```
NLP Processor → AWS Comprehend (Entity + Key Phrase Jobs)
```

### 3. Job Completion Detection
```
CloudWatch Events (every 2 minutes) → Job Monitor Lambda
Job Monitor → Check Comprehend job status
```

### 4. Worker Triggering
```
Job Monitor → Trigger Entity Worker (if entity job complete)
Job Monitor → Trigger Key Phrase Worker (if key phrase job complete)
```

### 5. Results Processing
```
Entity Worker → Process entity results → Update database
Key Phrase Worker → Process key phrase results → Update database
```

## Configuration

### Environment Variables

#### Common Variables (All Functions)
```bash
NER_RESULTS_BUCKET=solve-global-kr-dl-ner-results-861276078413-us-east-1
CHUNKS_BUCKET=solve-global-kr-dl-chunks-861276078413-us-east-1
COMPREHEND_REGION=us-east-1
DATABASE_SECRET_NAME=rds!db-0f16c155-35f6-463b-96d8-4a2d8da7e863
DB_PORT=5432
DB_NAME=climate_risk_rag
DB_HOST=solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com
```

#### NLP Processor Specific
```bash
COMPREHEND_OUTPUT_BUCKET=solve-global-kr-dl-ner-results-861276078413-us-east-1
COMPREHEND_DATA_ACCESS_ROLE_ARN=arn:aws:iam::861276078413:role/comprehend-data-access-role
ENTITY_COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:comprehend-entity-completion
KEYPHRASE_COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:comprehend-keyphrase-completion
```

#### Job Monitor Specific
```bash
ENTITY_COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:comprehend-entity-completion
KEYPHRASE_COMPLETION_TOPIC_ARN=arn:aws:sns:us-east-1:861276078413:comprehend-keyphrase-completion
ENTITY_WORKER_FUNCTION=nlp-worker-entity
KEYPHRASE_WORKER_FUNCTION=nlp-worker-keyphrase
```

## IAM Permissions

### Required Permissions

#### NLP Processor
- `comprehend:StartEntitiesDetectionJob`
- `comprehend:StartKeyPhrasesDetectionJob`
- `s3:GetObject` (text and chunks buckets)
- `s3:PutObject` (comprehend input bucket)
- `sns:Publish` (completion topics)
- `iam:PassRole` (comprehend data access role)

#### Workers
- `comprehend:DescribeEntitiesDetectionJob`
- `comprehend:DescribeKeyPhrasesDetectionJob`
- `s3:GetObject` (comprehend output, chunks buckets)
- `s3:PutObject` (results bucket)
- `sqs:ReceiveMessage`, `sqs:DeleteMessage` (worker queues)

#### Job Monitor
- `comprehend:ListEntitiesDetectionJobs`
- `comprehend:ListKeyPhrasesDetectionJobs`
- `comprehend:DescribeEntitiesDetectionJob`
- `comprehend:DescribeKeyPhrasesDetectionJob`
- `lambda:InvokeFunction` (worker functions)

## Results Storage

### S3 Structure

```
s3://solve-global-kr-dl-ner-results-861276078413-us-east-1/
├── comprehend-input/
│   └── {doc_id}/
│       └── input.txt
├── comprehend-output/
│   └── {doc_id}/
│       ├── entities/
│       │   └── {job_id}/output/output.tar.gz
│       └── key-phrases/
│           └── {job_id}/output/output.tar.gz
└── nlp-results/
    └── {doc_id}/
        ├── entities.json
        ├── entities_by_chunk.json
        ├── key_phrases.json
        └── key_phrases_by_chunk.json
```

### Result Format

#### entities.json
```json
[
  {
    "text": "climate change",
    "type": "OTHER",
    "score": 0.95,
    "begin_offset": 123,
    "end_offset": 137
  }
]
```

#### entities_by_chunk.json
```json
[
  {
    "chunk_id": "chunk_001",
    "entity": "climate change",
    "type": "OTHER", 
    "score": 0.95,
    "begin_offset": 23,
    "end_offset": 37
  }
]
```

## Monitoring and Observability

### CloudWatch Logs

- `/aws/lambda/nlp-processor`
- `/aws/lambda/nlp-worker-entity`
- `/aws/lambda/nlp-worker-keyphrase`
- `/aws/lambda/comprehend-job-monitor`

### Key Metrics

- Job completion time
- Processing success/failure rates
- Queue depth and message age
- Lambda duration and memory usage

### Alarms

- Dead letter queue message count
- Lambda error rates
- Job processing delays

## Deployment

### CDK Deployment

```bash
# Deploy the infrastructure
./deploy_async_nlp_processing.py

# Or manually
cd cdk
cdk deploy -a 'python app_async_nlp_processing.py'
```

### Manual Deployment Steps

1. Create SNS topics and SQS queues
2. Deploy Lambda functions with proper environment variables
3. Set up event source mappings
4. Configure CloudWatch Events rule
5. Update IAM permissions

## Testing

### End-to-End Test

```bash
# Run pipeline test
python3 invoke_pipeline_test.py --num-documents 1 --min-size-mb 0.2 --max-size-mb 0.4
```

### Manual Testing

```python
# Test individual workers
import boto3
import json

lambda_client = boto3.client('lambda')

# Test entity worker
entity_payload = {
    "Records": [{
        "body": json.dumps({
            "Type": "Notification",
            "Message": json.dumps({
                "JobId": "job-id-here",
                "JobName": "entities-doc-id-timestamp",
                "JobStatus": "COMPLETED",
                "JobType": "entities-detection"
            })
        })
    }]
}

lambda_client.invoke(
    FunctionName='nlp-worker-entity',
    InvocationType='Event',
    Payload=json.dumps(entity_payload)
)
```

## Troubleshooting

### Common Issues

1. **Jobs not being detected**
   - Check job monitor logs
   - Verify Comprehend job naming convention
   - Ensure jobs completed within monitoring window

2. **Workers not processing**
   - Check SQS queue visibility timeout
   - Verify event source mappings
   - Check Lambda function permissions

3. **Database constraint errors**
   - Ensure new stages added to valid_stage constraints
   - Check database connection and permissions

### Debug Commands

```bash
# Check Comprehend job status
aws comprehend describe-entities-detection-job --job-id {job-id}

# Check SQS queue messages
aws sqs receive-message --queue-url {queue-url}

# Check Lambda logs
aws logs filter-log-events --log-group-name "/aws/lambda/{function-name}"
```

## Performance Considerations

### Scaling

- Workers scale automatically with SQS message volume
- Monitor concurrent executions and adjust reserved concurrency if needed
- Consider batch processing for high-volume scenarios

### Cost Optimization

- Comprehend jobs are billed per request
- Lambda costs scale with processing time
- S3 storage costs for results and intermediate files
- Consider lifecycle policies for old results

## Security

### Data Protection

- All data encrypted in transit and at rest
- VPC isolation for Lambda functions
- IAM least-privilege access
- Secrets Manager for database credentials

### Access Control

- Role-based access to Lambda functions
- S3 bucket policies for data access
- SNS/SQS access policies

## Future Enhancements

### Potential Improvements

1. **Real-time Processing**: EventBridge integration for immediate job completion detection
2. **Batch Processing**: Support for processing multiple documents in single jobs
3. **Custom Models**: Integration with custom Comprehend models
4. **Result Caching**: Cache frequently accessed results
5. **Advanced Monitoring**: Custom metrics and dashboards

### Migration Path

The current implementation provides a foundation for future enhancements while maintaining backward compatibility with existing pipeline stages.
