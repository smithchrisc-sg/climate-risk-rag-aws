# Text Chunker Processor

Processes text_ready messages and performs smart structured chunking with audit-first database design.

## Overview

This Lambda function:
- Processes `text_ready` SNS messages from text extraction pipeline (parallel with keyword indexing)
- Downloads text and structure files from S3
- Performs smart structured chunking with Textract structure analysis
- Uploads chunks and metadata to S3
- Publishes `chunks_ready` completion messages
- Tracks processing status using audit-first database design
- **PRESERVES ALL SMART CHUNKING FUNCTIONALITY**

## Database Operations

Uses only the locked `DatabaseManager.set_processing_status()` method:

```python
# Processing started
self.db_manager.set_processing_status(doc_id, 'chunking', 'in_progress')

# Processing completed successfully
self.db_manager.set_processing_status(doc_id, 'chunking', 'completed')

# Processing failed
self.db_manager.set_processing_status(doc_id, 'chunking', 'failed', error_message=str(e))
```

## Smart Structured Chunking

**PRESERVED FUNCTIONALITY - NO CHANGES:**

### Chunking Features
- **Structure-aware chunking**: Uses Textract structure analysis
- **Semantic overlap**: Intelligent overlap when beneficial
- **Boundary respect**: Respects section boundaries
- **Table preservation**: Keeps tables intact
- **List preservation**: Keeps lists intact
- **Header context**: Includes context with headers
- **Hierarchy awareness**: Understands document hierarchy

### Chunking Settings
```python
SmartStructuredChunker(
    min_chunk_size=150,         # Larger for complete thoughts
    max_chunk_size=1200,        # Allow larger chunks for sections
    overlap_sentences=0,        # No fixed overlap
    semantic_overlap=True,      # Smart overlap when needed
    respect_boundaries=True,    # Respect section boundaries
    preserve_tables=True,       # Keep tables intact
    preserve_lists=True,        # Keep lists intact
    header_context=True         # Include context with headers
)
```

## Message Processing

Processes standardized `text_ready` messages (same as keyword indexer):

```json
{
  "version": "1.0",
  "stage": "text_ready",
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "text_location": "s3://bucket/dl-text/doc_id/raw_text.txt",
    "structure_location": "s3://bucket/dl-text/doc_id/textract_response.json"
  }
}
```

## Output Format

Publishes standardized `chunks_ready` messages:

```json
{
  "version": "1.0",
  "stage": "chunks_ready",
  "doc_id": "064762102bead7b04a39",
  "data_locations": {
    "chunks_location": "s3://bucket/chunks/doc_id/",
    "chunk_metadata_location": "s3://bucket/chunks/doc_id/metadata.json"
  },
  "processing_metadata": {
    "chunks_created": 45,
    "chunking_method": "smart_structured",
    "total_characters": 225215
  }
}
```

## Chunk Structure

Each chunk contains:

```json
{
  "chunk_id": "064762102bead7b04a39_chunk_0001",
  "doc_id": "064762102bead7b04a39",
  "chunk_index": 1,
  "text": "chunk content with smart structure awareness",
  "character_count": 856,
  "page_numbers": [1, 2],
  "section_types": ["title", "paragraph"],
  "hierarchy_levels": [1, 5],
  "table_count": 0,
  "list_count": 1,
  "semantic_context": "Previous context for continuity",
  "overlap_with_previous": false,
  "overlap_with_next": true
}
```

## Environment Variables

- `TEXT_BUCKET` - S3 bucket containing text extraction output
- `CHUNKS_BUCKET` - S3 bucket for chunk storage (default: `solve-global-kr-dl-chunks-861276078413-us-east-1`)
- `CHUNKS_READY_TOPIC_ARN` - SNS topic for completion notifications (optional)
- `DATABASE_SECRET_NAME` - RDS secret name (handled by DatabaseManager)

## Infrastructure Requirements

- **Security Group**: `sg-099296a5c809e8d9d` (Text Chunker Pipeline Lambda)
- **Subnets**: Application subnets (`subnet-03d8bd6cf3491f38c`, `subnet-0c0be1dd59f70f70e`)
- **Layers**: 
  - `database-core-layer-v3:2` (LOCKED)
  - `climate-risk-core-utilities:16`
- **IAM Permissions**: S3 read/write access, SNS publish, database access

## Parallel Processing

Runs in parallel with keyword indexing:
- Both triggered by same `text_ready` message
- Independent processing pipelines
- Horizontal scaling via SNS/SQS fan-out

## Deployment

```bash
cd lambda/text-chunker-processor
zip -r text-chunker-processor.zip src/ handler.py requirements.txt
aws lambda update-function-code --function-name <function-name> --zip-file fileb://text-chunker-processor.zip
```
