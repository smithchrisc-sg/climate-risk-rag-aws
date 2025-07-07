# Project Context Summary (2025-07-02T22:00:00Z)

## Current State

### Infrastructure Status
- Networking stack: UPDATE_COMPLETE
- Data stack: CREATE_COMPLETE
- AI/ML stack: CREATE_COMPLETE
- Microservices compute stack: CREATE_COMPLETE
- Data lake stack: ROLLBACK_COMPLETE (S3 buckets exist from previous deployment)

### Documentation
- Processing flow documented with Mermaid diagrams
- Lambda function implementations detailed
- Message flows and triggers defined
- Database schema designed

### Key Decisions Made
1. Document-centric processing approach
2. Parallel processing using SNS for NLP and chunking
3. Centralized Document ID Manager for metadata
4. Full-text NLP with post-processing entity-chunk mapping
5. Structured chunking with overlap

## Implementation Details

### Processing Pipeline
1. **Document Upload → Text Extraction**
   - S3 event triggers
   - Document ID generation
   - Metadata tracking
   - Textract processing

2. **Parallel Processing**
   - NLP on full text
   - Chunking with structure preservation
   - SNS-based parallel execution

3. **Entity and Chunk Processing**
   - Entity extraction from full text
   - Structured chunk creation
   - Entity-chunk mapping strategy

### Message Flow
- S3 events for initial triggers
- SNS topics for parallel processing
- SQS queues for long-running tasks
- PostgreSQL for metadata and status tracking

### Infrastructure Components
1. **Storage**
   - S3 buckets for documents, text, chunks, embeddings
   - PostgreSQL for metadata
   - OpenSearch for text and vector search
   - Neptune for knowledge graph

2. **Compute**
   - Lambda functions for processing
   - Step Functions for orchestration
   - API Gateway for external access

## Cost Considerations

### AWS Service Costs (per 100K documents)
1. **Textract**: $22,500
2. **Comprehend**: $13,500 (basic), $239,625 (with events)
3. **Titan**: $360
4. **Bedrock**: $50,000

### Cost Optimization Strategies
1. **Open Source Alternatives**
   - spaCy/Flair for NLP
   - Sentence-Transformers for embeddings
   - PDFPlumber/PyMuPDF for text extraction

2. **Hybrid Approach**
   - Selective use of AWS services
   - Open source for bulk processing
   - Cached results for development

## Next Steps

### Immediate Actions
1. Implement messaging infrastructure
   - Add SQS queues
   - Configure SNS topics
   - Update Lambda triggers

2. Update Lambda Functions
   - Add Document ID Manager integration
   - Implement message handling
   - Add error handling

3. Testing Strategy
   - Develop test document set
   - Implement monitoring
   - Validate processing flow

### Outstanding Decisions
1. NLP processing strategy (AWS vs. open source)
2. Entity-chunk mapping implementation
3. Monitoring and alerting setup
4. Error handling and recovery procedures

## Technical Debt

1. **Infrastructure**
   - Data lake stack needs resolution
   - Lambda trigger configuration verification needed
   - Message flow validation required

2. **Implementation**
   - Error handling not fully specified
   - Monitoring not implemented
   - Testing framework needed

## Reference Information

### Key Files
- `/docs/PROCESSING_FLOW.md`: Detailed processing flow documentation
- `/docs/LAMBDA_PORTING_PLAN.md`: Lambda implementation plan
- `/cdk/stacks/`: Infrastructure definition

### Database Schema
```sql
-- Core tables defined for:
-- - Document tracking
-- - Processing status
-- - Entity management
-- - Chunk tracking
```

### Message Formats
```json
{
    "document_id": "uuid-string",
    "file_hash": "hash-string",
    "stage": "text_extracted",
    "location": {
        "bucket": "bucket-name",
        "key": "object-key"
    }
}
```

## Notes and Observations

1. **Performance Considerations**
   - NLP processing on full text may require increased Lambda timeout
   - Parallel processing needs careful monitoring
   - Entity-chunk mapping strategy needs validation

2. **Scalability**
   - Document ID Manager must handle concurrent requests
   - PostgreSQL connections need management
   - S3 event triggering needs rate consideration

3. **Reliability**
   - Message delivery guarantees important
   - Error handling crucial for long-running processes
   - State management needs careful consideration

## Questions to Address

1. How to handle very large documents?
2. What is the optimal chunk size and overlap?
3. How to manage processing costs at scale?
4. What monitoring metrics are most important?

## Resources and Dependencies

### AWS Services
- S3
- Lambda
- SNS/SQS
- PostgreSQL
- OpenSearch
- Neptune
- Textract
- Comprehend
- Bedrock

### Open Source Tools
- spaCy/Flair
- Sentence-Transformers
- PDFPlumber/PyMuPDF
- BeautifulSoup (for web content)
