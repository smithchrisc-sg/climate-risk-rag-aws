# Project Context Summary - August 13, 2025 22:40

## Current Project State

### Major Breakthrough: NLP Pipeline Fixed
The NLP processing pipeline has been successfully debugged and is now functional. We've resolved multiple critical issues and achieved entity extraction from documents.

### Key Achievements
- **3,691 entities** and **8,996 key phrases** successfully extracted from test document
- **Message flow orchestration** completely fixed
- **IAM permissions** properly configured
- **File format issues** resolved
- **Duplicate subscriptions** eliminated

## Critical Issues Resolved

### 1. Message Flow Orchestration (FIXED ✅)
**Problem**: Both nlp-initiator and nlp-worker were triggered by the same `chunks_ready` message, causing nlp-worker to receive empty `comprehend_jobs: {}`.

**Solution**: 
- Created new SNS topic: `nlp-jobs-submitted`
- nlp-initiator now publishes `nlp_jobs_submitted` message with actual Comprehend job IDs
- nlp-worker only receives messages with proper job data
- Removed duplicate subscription to `text-chunking-complete`

**Files Modified**:
- `/lambda/nlp-initiator/src/nlp_initiator.py` - Added message publishing logic
- IAM policy updated to allow SNS publish to new topic

### 2. Comprehend File Format Issue (FIXED ✅)
**Problem**: Comprehend creates `output` files (JSON without .json extension), but code expected `.json` files.

**Solution**: Modified tar extraction logic to handle both formats:
```python
if member.name.endswith('output') or member.name.endswith('.json'):
```

**Files Modified**:
- `/lambda/nlp-worker/src/nlp_worker.py` - Line 391, tar extraction logic

### 3. IAM Permissions (FIXED ✅)
**Problem**: nlp-initiator couldn't publish to new `nlp-jobs-submitted` topic.

**Solution**: Updated `nlp-integration-policy` to include new topic ARN.

## Current Outstanding Issue

### Entity-to-Chunk Mapping (IN PROGRESS 🔄)
**Problem**: While entities are extracted successfully, they cannot be mapped to document chunks due to coordinate system mismatch.

**Root Cause**: Smart chunking uses Textract layout analysis, losing original document character offsets that Comprehend entities reference.

**Current Status**: 
- 91%+ chunk position success
- 0% entity mapping success
- Empty `*_by_chunk.json` files

**Solution Designed**: Comprehensive offset reconstruction algorithm (see design document)

## Project Structure

### Key Directories
- **`/cdk/`** - Infrastructure as Code (CDK stacks)
- **`/lambda/`** - Lambda function implementations
  - `/nlp-initiator/` - Starts Comprehend jobs, publishes nlp_jobs_submitted
  - `/nlp-worker/` - Processes Comprehend results, maps entities to chunks
  - `/text-chunker-processor/` - Creates smart structured chunks (TARGET for offset fix)
- **`/layers/`** - Lambda layers for shared dependencies
- **`/docs/`** - Documentation and status tracking
  - `/status/` - Project context and progress summaries
  - `/design/` - Technical design documents
  - `/infrastructure/` - Infrastructure documentation

### Critical Lambda Functions
1. **nlp-initiator** - Receives `chunks_ready`, starts Comprehend, publishes `nlp_jobs_submitted`
2. **nlp-worker** - Receives `nlp_jobs_submitted`, processes entity results
3. **text-chunker-processor** - Creates chunks (needs offset reconstruction)

### Database Integration
- **DatabaseManager** - Audit-first design with processing status tracking
- **Status Updates** - All stages tracked in PostgreSQL database
- **Metadata Storage** - Processing metadata and results stored

## Infrastructure State

### SNS Topics
- **text-chunking-complete** - Triggers nlp-initiator
- **nlp-jobs-submitted** - Triggers nlp-worker (NEW)
- **nlp-processing-complete** - Final completion notifications

### SQS Queues
- **nlp-initiator-queue** - Subscribed to text-chunking-complete
- **nlp-worker-queue** - Subscribed to nlp-jobs-submitted (UPDATED)

### S3 Buckets
- **Text Storage** - Raw extracted text
- **Chunks Storage** - Smart structured chunks
- **NER Results** - Comprehend entity/key phrase results
- **Comprehend Output** - Raw Comprehend job results

### IAM Policies
- **nlp-integration-policy** - Updated with nlp-jobs-submitted permissions

## Cost Management and Testing

### Expense Control Measures
**CRITICAL**: Be extremely careful with test runs to avoid excessive charges.

#### High-Cost Services
1. **AWS Textract**
   - Charges per page processed
   - Current test document: ~20 pages
   - Estimated cost: $0.10-0.20 per test run

2. **AWS Comprehend**
   - Charges per 100 characters for entity/key phrase detection
   - Current test document: 225K characters
   - Estimated cost: $0.45 per test run

3. **Amazon Titan Embeddings** (Future)
   - Will charge per token for vector generation
   - Estimate: $0.50-1.00 per document for embeddings

#### Cost Control Strategies
- **Single Document Testing**: Always use `--num-documents 1` for development
- **Size Limits**: Use `--max-size-mb 4` to control document size
- **Avoid Batch Testing**: Don't run large document sets during development
- **Monitor Costs**: Check AWS billing dashboard regularly

#### Test Command Template
```bash
python3 invoke_pipeline_test.py --num-documents 1 --max-size-mb 4
```

### Current Test Document
- **Document ID**: `064762102bead7b04a39`
- **Size**: 1.5 MB (~20 pages)
- **Content**: World Bank climate risk document
- **Status**: Successfully processes through NLP pipeline

## Recent Work Summary References

### Related Documentation
- **CHUNK_OFFSET_RECONSTRUCTION_DESIGN.md** - Detailed solution design for entity mapping
- **Previous status documents** in `/docs/status/` - Historical context and progress
- **Infrastructure documentation** in `/docs/infrastructure/` - System architecture

### Debug and Monitoring
- **Enhanced Debug Logging** - Comprehensive logging added to nlp-worker
- **Status Tracking** - Database integration for processing status
- **Error Handling** - Graceful degradation and error reporting

## Message Flow Architecture

### Current Working Flow
```
Document Upload → Text Extraction → Text Chunking → chunks_ready
                                                        ↓
nlp-initiator ← chunks_ready message
     ↓
Start Comprehend Jobs
     ↓
Publish nlp_jobs_submitted (with job IDs)
     ↓
nlp-worker ← nlp_jobs_submitted message
     ↓
Process Comprehend Results → Entity Mapping (NEEDS FIX)
     ↓
Store Results → Publish nlp_processing_complete
```

### Key Message Formats

#### chunks_ready Message
```json
{
  "stage": "chunks_ready",
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "chunks_location": "s3://bucket/path/",
    "text_location": "s3://bucket/path/raw_text.txt"
  }
}
```

#### nlp_jobs_submitted Message (NEW)
```json
{
  "stage": "nlp_jobs_submitted",
  "doc_id": "064762102bead7b04a39",
  "comprehend_jobs": {
    "entity_job_id": "94c8a9eec9e1019781645e2e89e68859",
    "key_phrases_job_id": "b9976d3f4d5dace22566e817c8700c97"
  },
  "data_locations": {
    "chunks_location": "s3://bucket/path/",
    "text_location": "s3://bucket/path/raw_text.txt"
  }
}
```

## Next Phase Focus

### Immediate Priority
**Implement chunk offset reconstruction** to enable entity-to-chunk mapping.

### Success Criteria
- Entity mapping success rate >50% (currently 0%)
- Search quality impact >0.0 (currently 0.0)
- Non-empty `*_by_chunk.json` files in S3

### Implementation Target
- **File**: `/lambda/text-chunker-processor/src/smart_structured_chunker.py`
- **Method**: Add `add_document_offsets()` method
- **Integration**: Call after chunk creation in `create_smart_chunks()`

## Development Environment

### Testing Workflow
1. **Code Changes** - Modify Lambda functions locally
2. **Package Creation** - Create deployment ZIP files
3. **Lambda Deployment** - Update function code via AWS CLI
4. **Pipeline Testing** - Run single document test
5. **Log Analysis** - Check CloudWatch logs for results
6. **Iteration** - Refine based on results

### Key Commands
```bash
# Test pipeline
cd /Users/chris/climate-risk-rag-aws
python3 invoke_pipeline_test.py --num-documents 1 --max-size-mb 4

# Deploy Lambda function
aws lambda update-function-code --function-name FUNCTION_NAME --zip-file fileb://path/to/package.zip --profile solve-global --region us-east-1
```

## Risk Factors

### Technical Risks
- **Offset reconstruction complexity** - Algorithm may need refinement
- **Performance impact** - Text processing may slow chunking
- **Edge cases** - Cross-page chunks, special characters

### Operational Risks
- **Cost overruns** - Careful testing required
- **Service limits** - Comprehend has rate limits
- **Data consistency** - Ensure all pipeline stages remain synchronized

## Success Metrics

### Pipeline Health
- **End-to-end success rate** - Documents processed without errors
- **Entity extraction rate** - Entities found per document
- **Entity mapping rate** - Entities successfully mapped to chunks
- **Processing time** - Total pipeline duration

### Current Baseline
- **Documents processed**: 1 (test document)
- **Entities extracted**: 3,691
- **Key phrases extracted**: 8,996
- **Entity mapping success**: 0% (TARGET: >50%)
- **Processing time**: ~5 minutes per document

This context summary provides complete information to resume development on the chunk offset reconstruction implementation.
