# Pipeline Testing Solution

## Overview

This document describes the Lambda-based pipeline testing solution for the Climate Risk RAG system. The solution allows parameterized testing of the document processing pipeline with proper database access and safety controls.

## Architecture

### Components

1. **Pipeline Test Lambda Function** - Runs inside VPC with database access
2. **Local Client Script** - Invokes Lambda with parameters from local machine
3. **Source Documents Bucket** - Staging area for end-state testing
4. **CDK Infrastructure** - Deploys Lambda with proper permissions

### Data Flow

```
Local Machine → Lambda Function (VPC) → PostgreSQL Database
     ↓                    ↓                      ↓
Parameters          Document Selection    DocumentIDManager
     ↓                    ↓                      ↓
Results ←          S3 Operations ←        Pipeline Triggers
```

## Key Features

### Parameterized Testing
- **Document Count**: 1-10 documents (Textract parallel limit)
- **Size Range**: Configurable min/max MB limits
- **Document Types**: Filter by report, policy, research, project, financial, technical
- **Page Targeting**: Select documents near target average page count
- **Language**: Filter by document language (default: English)

### Safety Controls
- **Page Limit**: Warns if total pages > 100 (cost protection)
- **Parallel Limit**: Max 10 concurrent Textract jobs
- **Size Limit**: Blocks documents > 400MB (Textract limit)
- **Force Override**: `--force` flag to bypass warnings

### Actions
- **setup_only**: Prepare documents without triggering pipeline
- **test_only**: Test existing prepared documents
- **setup_and_test**: Complete end-to-end test (default)

## Setup Instructions

### 1. Deploy Infrastructure

First, ensure the source documents bucket exists:
```bash
# Deploy source documents bucket (if not already done)
cd /Users/chris/climate-risk-rag-aws/cdk
cdk deploy solve-global-kr-source-documents-bucket --app "python3 app_source_bucket_only.py" --require-approval never
```

Deploy the pipeline test Lambda function:
```bash
# Deploy pipeline test Lambda
python3 deploy_pipeline_test_lambda.py
```

### 2. Verify Prerequisites

Ensure these resources exist:
- ✅ Source documents bucket: `solve-global-kr-dl-source-documents-861276078413-us-east-1`
- ✅ PostgreSQL database with proper connection string
- ✅ SQLite database uploaded to S3 cache bucket
- ✅ DocumentIDManager and shared layers deployed

### 3. Test the Setup

Run a basic connectivity test:
```bash
python3 invoke_pipeline_test.py --num-documents 1 --action setup_only
```

## Usage Examples

### Basic Tests

**Small document test (recommended first test):**
```bash
python3 invoke_pipeline_test.py --num-documents 3 --max-size-mb 5
```

**Medium-scale test:**
```bash
python3 invoke_pipeline_test.py --num-documents 5 --max-size-mb 10 --target-avg-pages 20
```

### Targeted Tests

**Policy documents only:**
```bash
python3 invoke_pipeline_test.py --num-documents 3 --document-types policy --target-avg-pages 15
```

**Research papers:**
```bash
python3 invoke_pipeline_test.py --num-documents 4 --document-types research --min-size-mb 2 --max-size-mb 8
```

**Mixed document types:**
```bash
python3 invoke_pipeline_test.py --num-documents 6 --document-types report policy research
```

### Advanced Usage

**Setup documents for later testing:**
```bash
python3 invoke_pipeline_test.py --action setup_only --num-documents 10 --max-size-mb 15
```

**Test existing prepared documents:**
```bash
python3 invoke_pipeline_test.py --action test_only
```

**Force large test (bypass safety limits):**
```bash
python3 invoke_pipeline_test.py --num-documents 8 --target-avg-pages 30 --force
```

**Save results to file:**
```bash
python3 invoke_pipeline_test.py --num-documents 5 --save-results
```

## Command Line Parameters

### Document Selection
- `--num-documents N` - Number of documents (1-10, default: 5)
- `--min-size-mb X` - Minimum size in MB (default: 1.0)
- `--max-size-mb Y` - Maximum size in MB (default: 10.0)
- `--target-avg-pages N` - Target average pages (default: 20)
- `--language LANG` - Document language (default: english)
- `--document-types TYPE1 TYPE2` - Filter by types: report, policy, research, project, financial, technical

### Test Control
- `--action ACTION` - setup_only, test_only, setup_and_test (default: setup_and_test)
- `--force` - Skip safety confirmations
- `--save-results` - Save results to JSON file

## Output Interpretation

### Success Indicators
- ✅ **Documents Prepared**: Number of documents successfully copied to source bucket
- ✅ **Successful Triggers**: Number of pipeline triggers that succeeded
- ✅ **Trigger Success Rate**: Percentage of successful triggers (aim for >90%)

### Key Metrics
- **Total Estimated Pages**: Sum of estimated pages across all documents
- **Average Pages per Doc**: Average document size in pages
- **Total Size**: Combined size of all documents in MB
- **Processing Duration**: Time taken for setup and triggering

### Error Handling
- **Database Connection Errors**: Check VPC connectivity and DATABASE_URL
- **S3 Access Errors**: Verify bucket permissions and existence
- **Textract Limit Errors**: Reduce document count or use --force
- **Document Selection Errors**: Adjust filtering criteria

## Troubleshooting

### Common Issues

**1. Lambda Function Not Found**
```
Error: Function not found: solve-global-kr-pipeline-test-function
```
**Solution**: Deploy the Lambda function using `python3 deploy_pipeline_test_lambda.py`

**2. Database Connection Failed**
```
Error: Database connection string required
```
**Solution**: Verify DATABASE_URL in Lambda environment variables

**3. No Documents Match Criteria**
```
Error: No documents match criteria
```
**Solution**: Relax filtering parameters (increase size range, remove document type filters)

**4. SQLite Database Not Found**
```
Error: Failed to download SQLite database
```
**Solution**: Upload SQLite database to S3 cache bucket at `database/corpus_document_ids.db`

**5. Textract Limits Exceeded**
```
Error: Total estimated pages (150) exceeds recommended limit of 100
```
**Solution**: Reduce `--num-documents` or `--max-size-mb`, or use `--force`

### Debug Mode

For detailed logging, check Lambda function logs:
```bash
aws logs tail /aws/lambda/solve-global-kr-pipeline-test-function --follow
```

## File Structure

```
climate-risk-rag-aws/
├── lambda/pipeline_test_function/
│   └── pipeline_test_handler.py          # Main Lambda function
├── cdk/
│   ├── app_pipeline_test_lambda.py       # CDK deployment
│   └── app_source_bucket_only.py         # Source bucket deployment
├── invoke_pipeline_test.py               # Local client script
├── deploy_pipeline_test_lambda.py        # Lambda deployment script
├── setup_and_test_pipeline.py           # Original local script (deprecated)
└── PIPELINE_TESTING.md                  # This documentation
```

## Cost Considerations

### AWS Service Costs
- **Lambda Execution**: ~$0.20 per 1GB-second (15-minute max execution)
- **Textract Processing**: ~$1.50 per 1,000 pages
- **S3 Operations**: Minimal (copy operations)
- **Data Transfer**: Minimal (within same region)

### Cost Estimation Examples
- **5 documents, 20 pages each**: ~$0.15 Textract + ~$0.05 Lambda = ~$0.20
- **10 documents, 30 pages each**: ~$0.45 Textract + ~$0.10 Lambda = ~$0.55

### Cost Controls
- Page limit warnings (>100 pages)
- Document count limits (≤10 parallel)
- Size limits (≤400MB per document)
- Force confirmation for expensive operations

## Integration with CI/CD

### Automated Testing
```bash
# Basic smoke test
python3 invoke_pipeline_test.py --num-documents 1 --max-size-mb 2 --action setup_only

# Regression test
python3 invoke_pipeline_test.py --num-documents 3 --document-types report --save-results
```

### Monitoring
- Lambda function logs in CloudWatch
- S3 bucket monitoring for document preparation
- Pipeline trigger success rates
- Processing duration trends

## Security Considerations

### Access Control
- Lambda function runs in private VPC subnets
- Database access restricted to VPC
- S3 bucket policies limit access to Lambda role
- No public internet access from Lambda

### Data Protection
- Documents copied with metadata preservation
- Source URLs stored securely in PostgreSQL
- SQLite database contains only document IDs and URLs
- All data encrypted at rest and in transit

## Future Enhancements

### Planned Features
- **Real-time Monitoring**: WebSocket-based progress updates
- **Batch Processing**: Support for larger document sets
- **Result Comparison**: Compare results across test runs
- **Performance Metrics**: Detailed timing and resource usage
- **Custom Filters**: Advanced document selection criteria

### Integration Opportunities
- **CI/CD Pipeline**: Automated testing on code changes
- **Monitoring Dashboard**: Real-time pipeline health
- **Cost Optimization**: Intelligent document selection
- **Quality Assurance**: Automated result validation

## Support

For issues or questions:
1. Check Lambda function logs in CloudWatch
2. Verify all prerequisites are met
3. Review troubleshooting section
4. Test with minimal parameters first
5. Use `--force` flag cautiously for limit overrides

---

**Last Updated**: July 11, 2025
**Version**: 1.0
**Author**: Climate Risk RAG Team
