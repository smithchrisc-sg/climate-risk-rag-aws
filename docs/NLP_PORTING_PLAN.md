# NLP Processing Functions Porting Plan

## Overview

This plan outlines the systematic porting of the existing NLP processor and worker functions to integrate with the audit-first database design. The NLP functions use Amazon Comprehend for entity extraction and key phrase detection, which can be expensive, so we must be frugal with iterations and testing.

## Current State Analysis

### Existing Functions
- **`nlp-processor`**: Initiator function that validates documents and delegates to worker
- **`nlp-worker`**: Background processor that performs Comprehend analysis and stores results

### Current Architecture
- **Input**: Receives `chunks_ready` messages from text chunking stage
- **Processing**: Uses Amazon Comprehend for entity extraction and key phrase detection
- **Output**: Stores results in S3 data lake and publishes `nlp_complete` messages
- **Database**: Uses legacy `nlp_processing_status` table (not audit-first design)

### Key Dependencies
- **Amazon Comprehend**: Entity detection and key phrase extraction
- **S3 Data Lake**: Storage for NLP results (`solve-global-kr-dl-ner-results-*`)
- **Offset Mapping**: Maps NLP results back to original chunks
- **Cost Management**: Built-in cost estimation and thresholds

## Database Schema Requirements

### Current Schema Issues
The existing functions use a legacy `nlp_processing_status` table that doesn't align with our audit-first design. We need to integrate with the standardized `document_processing_status` table.

### Required Schema Updates

#### 1. Add NLP Stages to Processing Status
The current schema has `nlp_initiate` and `nlp_complete` stages, but we need to add intermediate stages for better tracking:

```sql
-- Add to processing_stage_enum in migrate_to_audit_schema.sql
ALTER TYPE processing_stage_enum ADD VALUE 'nlp_processing';
ALTER TYPE processing_stage_enum ADD VALUE 'nlp_entity_extraction';  
ALTER TYPE processing_stage_enum ADD VALUE 'nlp_key_phrases';
ALTER TYPE processing_stage_enum ADD VALUE 'nlp_offset_mapping';
ALTER TYPE processing_stage_enum ADD VALUE 'nlp_storage';
```

#### 2. NLP-Specific Metadata Schema
We need to define the metadata structure for NLP processing stages:

```sql
-- Example metadata structure for nlp_initiate stage:
{
  "nlp_config": {
    "provider": "comprehend",
    "processing_type": "entity_and_phrases", 
    "cost_threshold": 0.50,
    "estimated_cost": 0.0234
  },
  "input_data": {
    "chunks_location": "s3://bucket/chunks/doc_id/",
    "text_location": "s3://bucket/text/doc_id/",
    "character_count": 125000,
    "chunks_count": 45
  }
}

-- Example metadata structure for nlp_complete stage:
{
  "processing_results": {
    "entities_count": 156,
    "key_phrases_count": 89,
    "chunks_mapped": true,
    "actual_cost": 0.0234,
    "processing_time_ms": 12500
  },
  "output_locations": {
    "entities_file": "s3://bucket/ner-results/doc_id/entities.json",
    "key_phrases_file": "s3://bucket/ner-results/doc_id/key_phrases.json", 
    "chunk_mappings_file": "s3://bucket/ner-results/doc_id/chunk_mappings.json"
  },
  "cost_analysis": {
    "estimated_cost": 0.0234,
    "actual_cost": 0.0234,
    "under_threshold": true,
    "threshold": 0.50
  }
}
```

## Porting Strategy

### Phase 1: Schema Preparation (Manual)
**Owner**: You (manual schema updates)

1. **Add NLP processing stages** to `processing_stage_enum`
2. **Remove legacy table**: Drop `nlp_processing_status` table if it exists
3. **Test schema changes** with a sample document

### Phase 2: NLP Initiator Porting
**Function**: `nlp-processor` → `nlp-initiator`

#### 2.1 Core Changes
- **Database Integration**: Replace legacy status table with `DocumentIDManager`
- **Status Tracking**: Use `nlp_initiate` → `in_progress` → `completed`/`failed`
- **Cost Validation**: Enhanced cost estimation with database tracking
- **Message Format**: Preserve existing message structure for compatibility

#### 2.2 Key Preservation Requirements
- **Cost Threshold Logic**: Maintain existing cost estimation and validation
- **Message Compatibility**: Ensure worker can still process messages
- **S3 Location Handling**: Support both folder URL and direct path formats
- **Error Handling**: Comprehensive error tracking with database persistence

#### 2.3 Implementation Structure
```
lambda/nlp-initiator/
├── README.md
├── handler.py
├── requirements.txt
└── src/
    └── nlp_initiator.py
```

### Phase 3: NLP Worker Porting  
**Function**: `nlp-worker` → `nlp-worker` (in-place update)

#### 3.1 Core Changes
- **Database Integration**: Replace legacy status tracking with audit-first design
- **Enhanced Status Tracking**: Track each processing sub-stage
- **Error Recovery**: Improved error handling with detailed audit trail
- **Cost Tracking**: Record actual vs estimated costs

#### 3.2 Processing Stages Tracking
1. **`nlp_processing`**: Overall processing started
2. **`nlp_entity_extraction`**: Entity extraction in progress
3. **`nlp_key_phrases`**: Key phrase extraction in progress  
4. **`nlp_offset_mapping`**: Mapping results to chunks
5. **`nlp_storage`**: Storing results to S3 data lake
6. **`nlp_complete`**: All processing completed successfully

#### 3.3 Key Preservation Requirements
- **Comprehend Integration**: Maintain existing NLP provider interface
- **Offset Mapping**: Preserve chunk-to-result mapping functionality
- **S3 Data Lake**: Keep existing storage patterns and file structures
- **Cost Management**: Maintain cost estimation and threshold enforcement
- **Result Format**: Preserve output format for downstream consumers

## Cost Management Strategy

### Frugal Testing Approach
Given Comprehend's cost ($0.0001 per 100 characters), we need to be strategic:

1. **Use Small Test Documents**: Start with documents < 10,000 characters (~$0.01 cost)
2. **Mock Comprehend Responses**: Create test mode that simulates Comprehend responses
3. **Cost Validation First**: Test cost estimation logic before actual Comprehend calls
4. **Staged Rollout**: Test with single document before batch processing

### Cost Monitoring
- **Pre-processing Validation**: Estimate and validate costs before Comprehend calls
- **Real-time Tracking**: Monitor actual costs vs estimates
- **Threshold Enforcement**: Strict adherence to cost thresholds
- **Database Logging**: Track all cost-related decisions in audit trail

## Infrastructure Requirements

### Lambda Configuration
- **Runtime**: Python 3.11
- **Memory**: 1024MB (for NLP processing)
- **Timeout**: 15 minutes (Comprehend can be slow)
- **VPC**: Application subnets (`subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`)
- **Security Group**: `sg-0c9e10b9cfb4c9eb0`

### IAM Permissions
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "comprehend:DetectEntities",
                "comprehend:DetectKeyPhrases",
                "comprehend:DetectDominantLanguage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::solve-global-kr-dl-chunks-*",
                "arn:aws:s3:::solve-global-kr-dl-chunks-*/*",
                "arn:aws:s3:::solve-global-kr-dl-text-*", 
                "arn:aws:s3:::solve-global-kr-dl-text-*/*",
                "arn:aws:s3:::solve-global-kr-dl-ner-results-*",
                "arn:aws:s3:::solve-global-kr-dl-ner-results-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["lambda:InvokeFunction"],
            "Resource": ["arn:aws:lambda:us-east-1:861276078413:function:nlp-worker"]
        },
        {
            "Effect": "Allow",
            "Action": ["sns:Publish"],
            "Resource": [
                "arn:aws:sns:us-east-1:861276078413:nlp-worker",
                "arn:aws:sns:us-east-1:861276078413:nlp-processing-complete"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": ["arn:aws:secretsmanager:us-east-1:861276078413:secret:rds!db-*"]
        }
    ]
}
```

### Layer Dependencies
- **database-core-layer-v3**: For DatabaseManager and DocumentIDManager
- **climate-risk-core-utilities**: For shared utilities
- **nlp-dependencies**: For Comprehend SDK and NLP utilities (may need creation)

## Testing Strategy

### Phase 1: Schema Testing
1. **Manual Schema Updates**: Add NLP stages to enum
2. **Basic Status Test**: Verify status updates work with new stages
3. **Metadata Validation**: Test metadata structure storage

### Phase 2: Initiator Testing
1. **Unit Tests**: Database operations, cost estimation, message parsing
2. **Integration Test**: End-to-end with mock worker
3. **Cost Validation**: Test cost threshold enforcement
4. **Error Scenarios**: Database failures, invalid messages

### Phase 3: Worker Testing  
1. **Mock Comprehend**: Test processing logic without API calls
2. **Small Document Test**: Single small document (~$0.01 cost)
3. **Cost Tracking**: Verify actual vs estimated cost tracking
4. **Error Recovery**: Test failure scenarios and status tracking

### Phase 4: End-to-End Validation
1. **Pipeline Integration**: Test with real chunks_ready message
2. **Database Audit**: Verify complete audit trail creation
3. **Cost Monitoring**: Monitor actual Comprehend costs
4. **Performance Validation**: Ensure processing times are acceptable

## Risk Mitigation

### Cost Control
- **Strict Thresholds**: Enforce cost limits at multiple levels
- **Pre-validation**: Always estimate before processing
- **Monitoring**: Real-time cost tracking and alerts
- **Circuit Breaker**: Stop processing if costs exceed limits

### Error Handling
- **Comprehensive Logging**: Detailed error tracking in database
- **Graceful Degradation**: Continue pipeline even if NLP fails
- **Retry Logic**: Smart retry for transient Comprehend failures
- **Status Recovery**: Ability to resume from any processing stage

### Performance
- **Batch Processing**: Process multiple documents efficiently
- **Timeout Management**: Handle long-running Comprehend operations
- **Memory Optimization**: Efficient handling of large text documents
- **Concurrent Processing**: Parallel processing where possible

## Success Criteria

### Functional Requirements
- ✅ All existing NLP functionality preserved
- ✅ Cost estimation and threshold enforcement working
- ✅ Database audit trail for all processing stages
- ✅ S3 data lake storage maintained
- ✅ Offset mapping to chunks preserved
- ✅ Message format compatibility maintained

### Technical Requirements  
- ✅ Integration with locked DatabaseManager
- ✅ Proper infrastructure configuration
- ✅ Comprehensive error handling with database persistence
- ✅ Cost tracking and monitoring
- ✅ Performance equivalent or better than existing

### Validation Checklist
- [ ] Schema updates applied successfully
- [ ] Functions deploy without errors
- [ ] Database operations work correctly
- [ ] Cost estimation matches actual Comprehend costs
- [ ] Status tracking appears in database audit trail
- [ ] S3 data lake storage working
- [ ] Offset mapping produces correct results
- [ ] Integration tests pass with real documents
- [ ] Error scenarios handled gracefully
- [ ] Performance meets requirements

## Implementation Timeline

### Week 1: Schema and Planning
- **Day 1-2**: Manual schema updates and testing
- **Day 3-4**: NLP initiator implementation
- **Day 5**: Initial testing and validation

### Week 2: Worker Implementation
- **Day 1-3**: NLP worker porting and testing
- **Day 4-5**: Integration testing and cost validation

### Week 3: Production Validation
- **Day 1-2**: End-to-end testing with real documents
- **Day 3-4**: Performance optimization and monitoring
- **Day 5**: Production deployment and validation

## Next Steps

1. **Review and Approve Plan**: Confirm approach and cost management strategy
2. **Manual Schema Updates**: Add NLP stages to processing_stage_enum
3. **Begin NLP Initiator Implementation**: Start with database integration
4. **Cost Validation Setup**: Implement cost estimation testing
5. **Iterative Development**: Small, testable increments with cost monitoring

This plan ensures we maintain all existing NLP functionality while adding comprehensive audit capabilities and cost management, following our established porting methodology.
