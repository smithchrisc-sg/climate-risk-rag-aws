# TextChunker Integration Plan
## Date: 2025-07-03T22:00:00Z

## 🎯 **Integration Objective**

Integrate the structured TextChunker with the operational TextExtractor pipeline to create intelligent, structure-aware document chunks that preserve semantic meaning and document hierarchy.

## 📊 **Current State Analysis**

### **✅ What's Working (TextExtractor)**
- Complete async pipeline: S3 → Textract → SNS → SQS → Lambda → Database
- Real Textract API integration with 100% success rate
- Database integration with job lifecycle tracking
- VPC-enabled Lambda functions with proper security groups
- Cost-efficient operation within AWS free tier

### **🔧 What Needs Integration (TextChunker)**
- Structured chunking algorithm using Textract output
- Database schema for chunk storage and management
- Lambda function for async chunk processing
- Integration with TextExtractor completion workflow
- SQS queue for TextChunker processing

### **📋 Integration Points**
1. **TextExtractor Processor** → **TextChunker Initiator** (via SQS)
2. **Textract Results** → **Structured Chunking Algorithm**
3. **Chunk Results** → **Database Storage** (new text_chunks table)
4. **Processing Status** → **Pipeline Tracking** (document_processing_status)

## 🏗️ **Integration Architecture**

### **Extended Async Pipeline**
```
S3 Document → TextExtractor Initiator → Textract API → 
SNS Notification → SQS Queue → TextExtractor Processor → 
[NEW] SQS Queue → TextChunker Processor → Database Update → 
Next Stage (Embeddings)
```

### **New Components Required**
1. **TextChunker SQS Queue**: `solve-global-kr-textchunker-processor`
2. **TextChunker Lambda Function**: Structured chunking processor
3. **Database Schema**: `text_chunks` table with rich metadata
4. **Integration Logic**: TextExtractor → TextChunker handoff

## 📋 **Implementation Plan**

### **Phase 1: Database Schema & Infrastructure (Priority 1)**

#### **1.1 Create text_chunks Table**
```sql
CREATE TABLE text_chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    doc_hash VARCHAR(255) NOT NULL,
    textract_job_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_type VARCHAR(50) NOT NULL,  -- paragraph, header, table, list
    hierarchy_level INTEGER DEFAULT 0,
    page_number INTEGER NOT NULL,
    section_context TEXT,
    word_count INTEGER NOT NULL,
    sentence_count INTEGER NOT NULL,
    bounding_box JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key relationships
    FOREIGN KEY (textract_job_id) REFERENCES textract_jobs(job_id),
    
    -- Indexes for performance
    INDEX idx_text_chunks_doc_hash (doc_hash),
    INDEX idx_text_chunks_job_id (textract_job_id),
    INDEX idx_text_chunks_type (chunk_type),
    INDEX idx_text_chunks_page (page_number)
);
```

#### **1.2 Create TextChunker SQS Queue**
```python
# Add to textextractor_messaging_stack_complete.py
self.textchunker_dlq = sqs.Queue(
    self, "TextChunkerDLQ",
    queue_name="solve-global-kr-textchunker-dlq",
    retention_period=Duration.days(14)
)

self.textchunker_queue = sqs.Queue(
    self, "TextChunkerQueue", 
    queue_name="solve-global-kr-textchunker-processor",
    visibility_timeout=Duration.minutes(10),
    retention_period=Duration.days(4),
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,
        queue=self.textchunker_dlq
    )
)
```

### **Phase 2: TextChunker Lambda Function (Priority 1)**

#### **2.1 Enhanced Structured Chunker**
```python
# lambda/text_chunker_processor/text_chunker_processor.py

class TextChunkerProcessor:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.structured_chunker = StructuredChunker(
            min_chunk_size=100,
            max_chunk_size=1000,
            overlap_sentences=2,
            preserve_tables=True
        )
        self.s3 = boto3.client('s3')
        self.sqs = boto3.client('sqs')
    
    def process_textract_completion(self, job_id: str, doc_hash: str):
        """Process completed Textract job for chunking"""
        
        # 1. Get Textract results from AWS
        textract_response = self._get_textract_results(job_id)
        
        # 2. Create structured chunks
        chunks = self.structured_chunker.chunk_document(textract_response)
        
        # 3. Store chunks in database
        self._store_chunks(chunks, doc_hash, job_id)
        
        # 4. Update processing status
        self._update_processing_status(doc_hash, 'COMPLETED')
        
        # 5. Trigger next stage (embeddings)
        self._trigger_next_stage(doc_hash, chunks)
```

#### **2.2 Integration with TextExtractor**
```python
# Update text_extractor_processor.py
def process_textract_completion(self, job_id: str, status: str):
    """Enhanced to trigger TextChunker"""
    
    # Existing processing...
    result = self._process_job_completion(job_id, status)
    
    if result['success'] and status == 'SUCCEEDED':
        # Trigger TextChunker
        self._trigger_textchunker(job_id, result['doc_hash'])
    
    return result

def _trigger_textchunker(self, job_id: str, doc_hash: str):
    """Send message to TextChunker queue"""
    message = {
        'job_id': job_id,
        'doc_hash': doc_hash,
        'source': 'textextractor',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    self.sqs.send_message(
        QueueUrl=os.environ['TEXTCHUNKER_QUEUE_URL'],
        MessageBody=json.dumps(message)
    )
```

### **Phase 3: Enhanced Structured Chunking (Priority 2)**

#### **3.1 Textract Integration Enhancement**
```python
class EnhancedStructuredChunker(StructuredChunker):
    """Enhanced chunker with better Textract integration"""
    
    def chunk_document(self, textract_response: Dict) -> List[StructuredChunk]:
        """Enhanced chunking with rich metadata"""
        
        # 1. Extract document structure
        sections = self._extract_document_structure(textract_response)
        
        # 2. Classify sections by type
        classified_sections = self._classify_sections(sections)
        
        # 3. Create intelligent chunks
        chunks = self._create_intelligent_chunks(classified_sections)
        
        # 4. Add contextual metadata
        enhanced_chunks = self._add_contextual_metadata(chunks)
        
        return enhanced_chunks
    
    def _classify_sections(self, sections: List[DocumentSection]) -> List[DocumentSection]:
        """Classify sections using ML-based approach"""
        for section in sections:
            section.section_type = self._predict_section_type(section)
            section.hierarchy_level = self._determine_hierarchy(section)
        return sections
    
    def _create_intelligent_chunks(self, sections: List[DocumentSection]) -> List[StructuredChunk]:
        """Create chunks that preserve semantic meaning"""
        chunks = []
        
        for section in sections:
            if section.section_type == SectionType.TABLE:
                # Preserve table integrity
                chunks.append(self._create_table_chunk(section))
            elif section.section_type in [SectionType.HEADER, SectionType.TITLE]:
                # Include context from following paragraphs
                chunks.append(self._create_contextual_chunk(section, sections))
            else:
                # Standard paragraph chunking with overlap
                chunks.extend(self._create_paragraph_chunks(section))
        
        return chunks
```

#### **3.2 Advanced Chunk Metadata**
```python
@dataclass
class EnhancedStructuredChunk(StructuredChunk):
    """Enhanced chunk with rich metadata"""
    
    # Existing fields...
    
    # New fields for better integration
    parent_section_id: str
    child_sections: List[str]
    semantic_tags: List[str]
    entity_mentions: List[Dict]
    table_data: Optional[Dict]  # For table chunks
    list_items: Optional[List[str]]  # For list chunks
    cross_references: List[str]  # References to other chunks
    confidence_score: float
    processing_metadata: Dict
```

### **Phase 4: CDK Infrastructure Updates (Priority 2)**

#### **4.1 Update Messaging Stack**
```python
# Add to textextractor_messaging_stack_complete.py

# TextChunker Queue
self.textchunker_queue = sqs.Queue(
    self, "TextChunkerQueue",
    queue_name="solve-global-kr-textchunker-processor",
    visibility_timeout=Duration.minutes(10),
    retention_period=Duration.days(4),
    receive_message_wait_time=Duration.seconds(20),
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,
        queue=self.textchunker_dlq
    )
)

# Update Lambda role permissions
self.textextractor_lambda_role.add_to_policy(
    iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["sqs:SendMessage"],
        resources=[self.textchunker_queue.queue_arn]
    )
)
```

#### **4.2 Create TextChunker Lambda Stack**
```python
# New file: textchunker_lambda_stack.py

class TextChunkerLambdaStack(Stack):
    def __init__(self, scope, construct_id, vpc, messaging_stack, database_url, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # TextChunker Processor Lambda
        self.textchunker_processor = lambda_.Function(
            self, "TextChunkerProcessor",
            function_name="solve-global-kr-textchunker-processor",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="text_chunker_processor.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/text_chunker_processor"),
            layers=[messaging_stack.textextractor_layer],
            timeout=Duration.minutes(10),
            memory_size=1024,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[messaging_stack.lambda_security_group],
            role=messaging_stack.textextractor_lambda_role,
            environment={
                "DATABASE_URL": database_url,
                "OUTPUT_BUCKET": f"solve-global-kr-chunks-{self.account}-{self.region}",
                "NEXT_STAGE_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/placeholder/embedding-queue"
            }
        )
        
        # Add SQS trigger
        self.textchunker_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                messaging_stack.textchunker_queue,
                batch_size=1,
                max_batching_window=Duration.seconds(5)
            )
        )
```

### **Phase 5: Testing & Validation (Priority 3)**

#### **5.1 Integration Testing**
```python
# tests/test_textchunker_integration.py

class TestTextChunkerIntegration:
    def test_end_to_end_pipeline(self):
        """Test complete TextExtractor → TextChunker pipeline"""
        
        # 1. Trigger TextExtractor
        response = self.trigger_textextractor(test_document)
        assert response['statusCode'] == 200
        
        # 2. Wait for Textract completion
        job_id = self.wait_for_textract_completion()
        
        # 3. Verify TextChunker was triggered
        chunks = self.wait_for_chunking_completion(job_id)
        assert len(chunks) > 0
        
        # 4. Validate chunk quality
        self.validate_chunk_structure(chunks)
        self.validate_chunk_metadata(chunks)
        
    def test_structured_chunking_quality(self):
        """Test chunking preserves document structure"""
        
        chunks = self.get_chunks_for_document(test_doc_id)
        
        # Verify hierarchy preservation
        headers = [c for c in chunks if c.chunk_type == 'header']
        assert len(headers) > 0
        
        # Verify table preservation
        tables = [c for c in chunks if c.chunk_type == 'table']
        for table in tables:
            assert table.metadata.get('table_data') is not None
        
        # Verify semantic coherence
        self.validate_semantic_coherence(chunks)
```

#### **5.2 Performance Testing**
```python
def test_chunking_performance():
    """Test chunking performance with various document sizes"""
    
    test_cases = [
        {'pages': 1, 'expected_time': 5},
        {'pages': 10, 'expected_time': 30},
        {'pages': 50, 'expected_time': 120}
    ]
    
    for case in test_cases:
        start_time = time.time()
        chunks = process_document(case['pages'])
        duration = time.time() - start_time
        
        assert duration < case['expected_time']
        assert len(chunks) > case['pages']  # At least one chunk per page
```

## 📊 **Database Schema Design**

### **Complete text_chunks Table**
```sql
CREATE TABLE text_chunks (
    -- Primary identification
    chunk_id VARCHAR(255) PRIMARY KEY,
    doc_hash VARCHAR(255) NOT NULL,
    textract_job_id VARCHAR(255) NOT NULL,
    
    -- Chunk content and structure
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_type VARCHAR(50) NOT NULL,  -- paragraph, header, table, list, title
    hierarchy_level INTEGER DEFAULT 0,
    
    -- Document positioning
    page_number INTEGER NOT NULL,
    section_context TEXT,
    parent_section_id VARCHAR(255),
    
    -- Content metrics
    word_count INTEGER NOT NULL,
    sentence_count INTEGER NOT NULL,
    character_count INTEGER NOT NULL,
    
    -- Spatial information
    bounding_box JSONB,  -- {x, y, width, height}
    
    -- Rich metadata
    metadata JSONB,  -- Flexible metadata storage
    semantic_tags TEXT[],  -- Array of semantic tags
    confidence_score FLOAT DEFAULT 1.0,
    
    -- Processing information
    processing_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints and indexes
    CONSTRAINT fk_textract_job FOREIGN KEY (textract_job_id) REFERENCES textract_jobs(job_id),
    CONSTRAINT valid_chunk_type CHECK (chunk_type IN ('paragraph', 'header', 'subheader', 'title', 'table', 'list', 'footer', 'caption')),
    CONSTRAINT positive_counts CHECK (word_count > 0 AND sentence_count > 0 AND character_count > 0)
);

-- Performance indexes
CREATE INDEX idx_text_chunks_doc_hash ON text_chunks(doc_hash);
CREATE INDEX idx_text_chunks_job_id ON text_chunks(textract_job_id);
CREATE INDEX idx_text_chunks_type ON text_chunks(chunk_type);
CREATE INDEX idx_text_chunks_page ON text_chunks(page_number);
CREATE INDEX idx_text_chunks_hierarchy ON text_chunks(hierarchy_level);
CREATE INDEX idx_text_chunks_created ON text_chunks(created_at);

-- Full-text search index
CREATE INDEX idx_text_chunks_content ON text_chunks USING gin(to_tsvector('english', chunk_text));
```

### **Update document_processing_status**
```sql
-- Add TextChunker status tracking
ALTER TABLE document_processing_status 
ADD COLUMN chunking_job_id VARCHAR(255),
ADD COLUMN chunks_created INTEGER DEFAULT 0,
ADD COLUMN chunking_version VARCHAR(50);
```

## 🔄 **Integration Workflow**

### **Complete Pipeline Flow**
```
1. S3 Document Upload
   ↓
2. TextExtractor Initiator
   - Creates document record
   - Starts Textract job
   - Updates status: 'text_extraction_started'
   ↓
3. Textract Processing
   - Extracts text and structure
   - Sends completion notification to SNS
   ↓
4. TextExtractor Processor
   - Processes Textract results
   - Updates job status: 'SUCCEEDED'
   - Updates status: 'text_extraction_completed'
   - Sends message to TextChunker queue
   ↓
5. TextChunker Processor
   - Retrieves Textract results
   - Creates structured chunks
   - Stores chunks in database
   - Updates status: 'chunking_completed'
   - Triggers next stage (embeddings)
```

### **Error Handling & Recovery**
```python
class TextChunkerErrorHandler:
    def handle_chunking_failure(self, job_id: str, error: Exception):
        """Handle chunking failures with retry logic"""
        
        # 1. Log error details
        logger.error(f"Chunking failed for job {job_id}: {error}")
        
        # 2. Update processing status
        self._update_status(job_id, 'chunking_failed', str(error))
        
        # 3. Implement retry logic
        if self._should_retry(error):
            self._schedule_retry(job_id)
        else:
            self._send_to_dlq(job_id, error)
    
    def _should_retry(self, error: Exception) -> bool:
        """Determine if error is retryable"""
        retryable_errors = [
            'ConnectionError',
            'TimeoutError', 
            'TemporaryDatabaseError'
        ]
        return any(err in str(error) for err in retryable_errors)
```

## 📋 **Implementation Timeline**

### **Week 1: Foundation**
- [ ] Create text_chunks database table
- [ ] Update CDK messaging stack with TextChunker queue
- [ ] Create basic TextChunker Lambda function
- [ ] Test database integration

### **Week 2: Core Integration**
- [ ] Implement TextExtractor → TextChunker handoff
- [ ] Deploy enhanced structured chunking algorithm
- [ ] Add comprehensive error handling
- [ ] Create integration tests

### **Week 3: Enhancement & Testing**
- [ ] Add advanced chunk metadata
- [ ] Implement performance optimizations
- [ ] Create comprehensive test suite
- [ ] Performance testing and tuning

### **Week 4: Production Readiness**
- [ ] Complete CDK infrastructure
- [ ] Documentation and deployment guides
- [ ] Production deployment
- [ ] Monitoring and alerting setup

## 🎯 **Success Criteria**

### **Functional Requirements**
- [ ] Complete TextExtractor → TextChunker integration
- [ ] Structured chunks preserve document hierarchy
- [ ] Database stores rich chunk metadata
- [ ] Error handling with retry logic
- [ ] Performance meets requirements (<2 minutes per document)

### **Quality Requirements**
- [ ] Chunk quality maintains semantic coherence
- [ ] Table and list structures preserved
- [ ] Hierarchical relationships maintained
- [ ] Cross-references between chunks tracked
- [ ] Metadata enables downstream processing

### **Operational Requirements**
- [ ] Complete CDK infrastructure deployment
- [ ] Monitoring and logging in place
- [ ] Cost efficiency maintained
- [ ] Scalability for production volumes
- [ ] Documentation for maintenance

## 💰 **Cost Impact Analysis**

### **Additional AWS Resources**
- **TextChunker Lambda**: ~$0.01/month (minimal execution time)
- **Additional SQS Queue**: ~$0.01/month (low message volume)
- **Database Storage**: ~$0.10/month (chunk metadata)
- **Total Additional Cost**: ~$0.12/month

### **Performance Impact**
- **Processing Time**: +30-60 seconds per document
- **Storage Requirements**: +50-100MB per 100 documents
- **Lambda Memory**: 1024MB recommended for complex documents

## 🔍 **Risk Assessment**

### **Technical Risks**
- **Complexity**: Structured chunking algorithm complexity
- **Performance**: Large document processing time
- **Memory**: Lambda memory limits for complex documents

### **Mitigation Strategies**
- **Incremental Implementation**: Phase-based rollout
- **Performance Testing**: Comprehensive testing with various document types
- **Monitoring**: Real-time performance monitoring
- **Fallback**: Simple chunking fallback for complex documents

---

**Status**: 📋 **INTEGRATION PLAN COMPLETE - READY FOR IMPLEMENTATION**  
**Priority**: **HIGH** - Next major pipeline component  
**Estimated Effort**: 3-4 weeks for complete integration  
**Dependencies**: TextExtractor pipeline (✅ Complete)
