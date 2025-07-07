# TextExtractor Async Architecture Design
## Two-Lambda Pattern with PostgreSQL State Management

## 🎯 **Architecture Overview**

### **Design Principles**
- **Efficiency**: No idle Lambda time during Textract processing
- **Frugality**: Pay only for actual processing, not waiting
- **Simplicity**: Clear separation of concerns with minimal complexity
- **Maintainability**: Straightforward async pattern using existing infrastructure
- **Scalability**: Handle any document volume without coordination issues

### **Component Architecture**
```
S3 Document Upload
       ↓
TextExtractor Initiator Lambda
       ↓
Start Async Textract Job
       ↓
Store Job State in PostgreSQL
       ↓
Textract Processing (AWS Managed)
       ↓
SNS Notification on Completion
       ↓
TextExtractor Processor Lambda
       ↓
Retrieve & Save Structured Output
       ↓
Update PostgreSQL & Trigger Next Stage
```

## 📊 **Data Flow Design**

### **Input Processing**
1. **S3 Event Trigger**: PDF uploaded to documents bucket
2. **Document Hash Extraction**: Generate unique identifier from filename/content
3. **Job Initiation**: Start async Textract with rich feature analysis
4. **State Persistence**: Store job metadata in PostgreSQL
5. **Async Processing**: Textract processes document independently

### **Output Processing**
1. **SNS Notification**: Textract completion signal
2. **Job Retrieval**: Get job metadata from PostgreSQL
3. **Result Processing**: Fetch complete Textract response (with pagination)
4. **Structured Storage**: Save multiple file formats to S3
5. **State Cleanup**: Update PostgreSQL and trigger downstream processing

## 🗂️ **Output Structure Design**

### **S3 Storage Pattern**
```
s3://solve-global-kr-text-new-861276078413-us-east-1/
└── extracted_documents/
    └── {doc_hash}/
        ├── textract_response.json      # Complete API response (4MB+)
        ├── raw_text.txt               # Plain text extraction
        ├── layout.csv                 # Layout elements with hierarchy
        ├── key_values.csv             # Form-like relationships  
        ├── table_1.csv                # Individual tables
        ├── table_2.csv                # Additional tables
        ├── signatures.csv             # Digital signatures (if any)
        ├── query_answers.csv          # Query-based extractions
        └── processing_metadata.json    # Processing information
```

### **File Format Specifications**

**textract_response.json**: Complete AWS Textract API response
- All blocks with full geometry and relationships
- Confidence scores for every element
- Page-level organization
- Block type classifications (LAYOUT_*, TABLE, KEY_VALUE_SET, etc.)

**raw_text.txt**: Plain text in reading order
- Preserves document flow
- Line breaks maintained
- No formatting or structure

**layout.csv**: Structured layout analysis
```csv
Page,Layout_Type,Text,Reading_Order,Confidence,Hierarchy_Level
1,LAYOUT_TITLE,"Document Title",1,95.5,1
1,LAYOUT_SECTION_HEADER,"Introduction",2,88.2,2
1,LAYOUT_TEXT,"Paragraph content...",3,92.1,3
```

**key_values.csv**: Form-like relationships
```csv
Page,Key,Value,Key_Confidence,Value_Confidence
1,"Author:","John Smith",85.2,90.1
1,"Date:","2024-01-15",92.3,88.7
```

**table_N.csv**: Individual table data
```csv
Row,Col1,Col2,Col3,Confidence_Col1,Confidence_Col2,Confidence_Col3
1,"Header 1","Header 2","Header 3",95.1,92.3,89.7
2,"Data 1","Data 2","Data 3",88.2,91.5,87.9
```

## 🗄️ **PostgreSQL Schema Design**

### **textract_jobs Table**
```sql
CREATE TABLE textract_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    doc_hash VARCHAR(64) NOT NULL,
    source_bucket VARCHAR(255) NOT NULL,
    source_key VARCHAR(1024) NOT NULL,
    output_bucket VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    pages_processed INTEGER,
    blocks_extracted INTEGER,
    files_created JSONB,
    textract_model_version VARCHAR(50),
    feature_types JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_textract_jobs_doc_hash ON textract_jobs(doc_hash);
CREATE INDEX idx_textract_jobs_status ON textract_jobs(status);
CREATE INDEX idx_textract_jobs_started_at ON textract_jobs(started_at);
```

### **document_processing_status Table** (for pipeline tracking)
```sql
CREATE TABLE document_processing_status (
    doc_hash VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(1024) NOT NULL,
    source_bucket VARCHAR(255) NOT NULL,
    source_key VARCHAR(1024) NOT NULL,
    text_extraction_status VARCHAR(50) DEFAULT 'PENDING',
    text_extraction_job_id VARCHAR(255),
    text_extraction_completed_at TIMESTAMP WITH TIME ZONE,
    chunking_status VARCHAR(50) DEFAULT 'PENDING',
    embedding_status VARCHAR(50) DEFAULT 'PENDING',
    ner_status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (text_extraction_job_id) REFERENCES textract_jobs(job_id)
);

CREATE INDEX idx_doc_processing_text_status ON document_processing_status(text_extraction_status);
```

## 🔧 **Lambda Function Specifications**

### **Lambda 1: TextExtractor Initiator**
- **Trigger**: S3 Event (PDF upload to documents bucket)
- **Purpose**: Start async Textract jobs and track state
- **Timeout**: 5 minutes (sufficient for job initiation)
- **Memory**: 512 MB
- **Environment Variables**:
  - `TEXTRACT_SNS_TOPIC_ARN`
  - `TEXTRACT_SERVICE_ROLE_ARN`
  - `OUTPUT_BUCKET`
  - `DATABASE_URL`

### **Lambda 2: TextExtractor Processor**
- **Trigger**: SNS notification from Textract completion
- **Purpose**: Process results and save structured output
- **Timeout**: 15 minutes (for large document processing)
- **Memory**: 1024 MB (for processing large JSON responses)
- **Environment Variables**:
  - `OUTPUT_BUCKET`
  - `DATABASE_URL`
  - `NEXT_STAGE_QUEUE_URL` (for triggering chunking)

## 📡 **SNS/SQS Configuration**

### **SNS Topic: textract-completion**
- **Purpose**: Receive Textract job completion notifications
- **Subscribers**: TextExtractor Processor Lambda
- **Message Format**: Standard Textract completion notification

### **SQS Queue: text-chunking-queue**
- **Purpose**: Trigger downstream text chunking process
- **Message Format**: Document processing completion notification
- **Dead Letter Queue**: text-chunking-dlq (for failed processing)
- **Visibility Timeout**: 15 minutes (match chunking Lambda timeout)

### **Message Flow**
```json
// SNS Message from Textract
{
  "JobId": "abc123...",
  "Status": "SUCCEEDED",
  "API": "StartDocumentAnalysis",
  "Timestamp": "2024-01-15T10:30:00Z",
  "DocumentLocation": {
    "S3ObjectName": "documents/doc123.pdf",
    "S3Bucket": "solve-global-kr-documents-..."
  }
}

// SQS Message to Chunking
{
  "doc_hash": "abc123def456...",
  "source_document": {
    "bucket": "solve-global-kr-documents-...",
    "key": "documents/doc123.pdf"
  },
  "extracted_data": {
    "bucket": "solve-global-kr-text-new-...",
    "base_key": "extracted_documents/abc123def456"
  },
  "processing_metadata": {
    "pages_processed": 9,
    "blocks_extracted": 4250,
    "files_created": ["textract_response.json", "raw_text.txt", "layout.csv", ...]
  },
  "timestamp": "2024-01-15T10:35:00Z"
}
```

## 🏗️ **CDK Infrastructure Requirements**

### **Additional Resources Needed**
1. **SNS Topic**: textract-completion
2. **SQS Queue**: text-chunking-queue + DLQ
3. **IAM Roles**: Textract service role for SNS publishing
4. **Lambda Permissions**: SNS subscription, SQS publishing
5. **Database Schema**: PostgreSQL table creation
6. **S3 Bucket Policies**: Cross-bucket access permissions

### **Lambda Environment Configuration**
```typescript
// Environment variables for both Lambdas
const commonEnvironment = {
  DATABASE_URL: rdsInstance.instanceEndpoint.socketAddress,
  OUTPUT_BUCKET: textBucket.bucketName,
  AWS_REGION: 'us-east-1'
};

// Initiator-specific
const initiatorEnvironment = {
  ...commonEnvironment,
  TEXTRACT_SNS_TOPIC_ARN: textractTopic.topicArn,
  TEXTRACT_SERVICE_ROLE_ARN: textractServiceRole.roleArn
};

// Processor-specific  
const processorEnvironment = {
  ...commonEnvironment,
  NEXT_STAGE_QUEUE_URL: chunkingQueue.queueUrl
};
```

## 📈 **Performance & Cost Analysis**

### **Processing Time Estimates**
- **Job Initiation**: 2-5 seconds per document
- **Textract Processing**: 30-120 seconds (AWS managed)
- **Result Processing**: 10-30 seconds per document
- **Total Pipeline Time**: 1-3 minutes per document

### **Cost Breakdown (per 1000 documents)**
- **Lambda Execution**: $2-5 (initiator + processor)
- **Textract AnalyzeDocument**: $50 (with TABLES, FORMS, LAYOUT)
- **S3 Storage**: $1-2 (structured output files)
- **PostgreSQL**: $0.10 (state tracking)
- **SNS/SQS**: $0.50 (notifications)
- **Total**: ~$54 per 1000 documents

### **Scalability Characteristics**
- **Concurrent Jobs**: Limited by Textract quotas (600 concurrent)
- **Processing Rate**: 1000+ documents/hour (with proper scaling)
- **Storage Growth**: ~5-10MB per document (structured output)
- **Database Load**: Minimal (simple CRUD operations)

## 🔍 **Error Handling & Monitoring**

### **Error Scenarios**
1. **Textract Job Failure**: Update PostgreSQL status, send to DLQ
2. **Lambda Timeout**: Retry with exponential backoff
3. **S3 Access Issues**: Log error, update status, alert
4. **Database Connection**: Retry with connection pooling
5. **Malformed Documents**: Log details, mark as failed

### **Monitoring Points**
- **Job Success Rate**: Percentage of successful extractions
- **Processing Time**: Average time per document
- **Error Rates**: Failed jobs by error type
- **Queue Depth**: Backlog in processing pipeline
- **Cost Tracking**: Per-document processing costs

## 🎯 **Integration with Existing Pipeline**

### **Upstream Integration**
- **Input**: S3 events from document uploads
- **Compatibility**: Works with existing document bucket structure
- **Migration**: Can process both new and migrated documents

### **Downstream Integration**
- **Output**: Structured data ready for chunking
- **Triggering**: SQS messages to text chunking Lambda
- **Data Format**: Rich structure for enhanced chunking algorithms

### **Pipeline Flow**
```
Document Upload → TextExtractor → TextChunker → EmbeddingGenerator
                                              ↘ NERProcessor
```

## 🚀 **Implementation Phases**

### **Phase 1: Core Infrastructure**
1. Create PostgreSQL schema
2. Set up SNS/SQS resources
3. Deploy Lambda functions
4. Test with sample documents

### **Phase 2: Integration & Testing**
1. Connect to existing S3 buckets
2. Test end-to-end processing
3. Validate structured output format
4. Performance optimization

### **Phase 3: Production Deployment**
1. Deploy to production environment
2. Monitor performance metrics
3. Scale based on document volume
4. Integrate with downstream processing

This architecture provides a robust, scalable, and cost-effective solution for async text extraction while maintaining simplicity and leveraging existing PostgreSQL infrastructure.
