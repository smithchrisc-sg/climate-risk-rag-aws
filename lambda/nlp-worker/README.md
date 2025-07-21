# NLP Worker Lambda Function

## Overview

The NLP Worker processes Comprehend job results, maps them to chunks, and stores results in the S3 data lake. It follows the audit-first database design pattern.

## Functionality

1. **Receives** messages with Comprehend job IDs from NLP initiator
2. **Waits** for Comprehend jobs to complete
3. **Downloads** Comprehend results from S3
4. **Maps** entities and key phrases to original chunks
5. **Stores** results in S3 data lake
6. **Publishes** completion message

## Processing Flow

```
Job IDs → Wait for Completion → Download Results → Map to Chunks → Store in Data Lake → Publish Complete
```

## Database Status Tracking

- `nlp_results_processing` → `in_progress`
- `nlp_offset_mapping` → `in_progress`
- `nlp_storage` → `in_progress`
- `nlp_complete` → `completed`/`failed`

## Environment Variables

- `COMPREHEND_REGION`: AWS region for Comprehend (default: us-east-1)
- `NER_RESULTS_BUCKET`: S3 bucket for storing NLP results
- `NLP_COMPLETION_TOPIC_ARN`: SNS topic for completion notifications

## Data Lake Storage

Results are stored in structured format:
```
s3://bucket/nlp-results/{doc_id}/
├── entities.json           # Raw entity detection results
├── key_phrases.json        # Raw key phrase results
├── chunk_mappings.json     # Results mapped to chunks
└── summary.json           # Processing summary
```

## Offset Mapping

Maps Comprehend results (with character offsets) back to original document chunks:
- Finds which chunk contains each entity/phrase
- Calculates relative offset within chunk
- Preserves original Comprehend confidence scores

## Infrastructure Requirements

- **VPC**: Application subnets
- **Security Group**: `sg-0c9e10b9cfb4c9eb0`
- **Timeout**: 15 minutes (waits for Comprehend completion)
- **Memory**: 1024MB
- **Layers**: database-core-layer-v3, climate-risk-core-utilities
