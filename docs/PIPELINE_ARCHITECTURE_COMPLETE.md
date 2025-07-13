# Climate Risk RAG Pipeline - Complete Architecture Documentation

## Overview

This document describes the complete, integrated Climate Risk RAG (Retrieval-Augmented Generation) pipeline architecture as implemented and tested. The pipeline processes PDF documents through multiple stages to create a comprehensive knowledge base with vector embeddings, NLP analysis, keyword indexing, and knowledge graph representation.

## Pipeline Architecture

### High-Level Flow

```
Document Upload → Text Extraction → Text Chunking → Parallel Processing → Knowledge Integration
```

### Detailed Pipeline Flow

```
1. Document Upload (S3 Trigger)
   ↓
2. Text Extraction (Textract)
   ├─ Text Extractor Initiator
   └─ Text Extractor Processor
   ↓
3. Text Chunking
   └─ Text Chunker Processor
   ↓
4. chunks_ready message (SNS)
   ↓
5. PARALLEL PROCESSING
   ├─ Vector Embeddings Processor → Vector Embeddings Worker
   ├─ Keyword Indexer → Keyword Indexer Worker  
   ├─ NLP Processor → NLP Worker
   └─ Document Structure KG Processor
   ↓
6. COMPLETION MESSAGES
   ├─ embeddings_ready
   ├─ keywords_ready
   ├─ nlp_complete → Entity Resolver (future)
   └─ kg_structure_ready
```

## Data Lake Structure

All processed data is stored in S3 with a consistent folder structure:

```
s3://bucket-name/data_lake/{doc_id}/
├── raw_text.txt                    # Extracted text
├── {doc_id}_chunk_0000.json        # Individual chunks
├── {doc_id}_chunk_0001.json
├── ...
├── nlp/                            # NLP analysis results
│   ├── entities.json
│   ├── key_phrases.json
│   └── chunk_mappings.json
├── embeddings/                     # Vector embeddings
│   └── embeddings.json
└── keywords/                       # Keyword analysis
    └── keywords.json
```

## Standardized Messaging Format

All pipeline components use a standardized message format for consistency:

```json
{
  "version": "1.0",
  "timestamp": "2025-07-13T22:00:00Z",
  "source": "climate-risk-rag-system",
  "stage": "chunks_ready|nlp_complete|embeddings_ready|keywords_ready",
  "doc_id": "document_identifier",
  "doc_hash": "content_hash",
  "data_locations": {
    "chunks_folder_url": "s3://bucket/data_lake/{doc_id}/",
    "text_folder_url": "s3://bucket/data_lake/{doc_id}/",
    "specific_results_location": "s3://bucket/data_lake/{doc_id}/results/"
  },
  "document_metadata": {
    "filename": "document.pdf",
    "file_size": 1234567,
    "upload_timestamp": "2025-07-13T22:00:00Z",
    "content_type": "application/pdf"
  },
  "processing_metadata": {
    "chunks_count": 25,
    "total_characters": 50000,
    "processing_time": 45.2
  },
  "integration_flags": {
    "database_tracking_enabled": true,
    "s3_data_lake_storage": true
  }
}
```

## Component Details

### 1. Text Extraction Components

#### Text Extractor Initiator
- **Function**: `solve-global-kr-textextractor-initiator`
- **Trigger**: S3 document upload
- **Purpose**: Initiate Textract jobs for PDF processing
- **Output**: Textract job ID and metadata

#### Text Extractor Processor  
- **Function**: `solve-global-kr-textextractor-processor`
- **Trigger**: Textract completion (SNS)
- **Purpose**: Process Textract results and extract structured text
- **Output**: Raw text stored in data lake, triggers text chunking

### 2. Text Chunking Component

#### Text Chunker Processor
- **Function**: `text-chunker-pipeline`
- **Trigger**: Text extraction completion
- **Purpose**: Split text into semantic chunks with overlap
- **Features**:
  - Configurable chunk size (default: 1000 characters)
  - Overlap handling (default: 200 characters)
  - Sentence boundary preservation
  - Metadata preservation
- **Output**: Individual chunk JSON files, triggers parallel processing

### 3. Parallel Processing Components

#### Vector Embeddings Processor & Worker
- **Processor**: `vector-embeddings-processor`
- **Worker**: `vector-embeddings-worker`
- **Trigger**: `chunks_ready` message
- **Purpose**: Generate vector embeddings for semantic search
- **Features**:
  - AWS Titan embeddings integration
  - OpenSearch vector indexing
  - Batch processing optimization
- **Output**: `embeddings_ready` message

#### NLP Processor & Worker
- **Processor**: `nlp-processor`
- **Worker**: `nlp-worker`
- **Trigger**: `chunks_ready` message
- **Purpose**: Extract entities, key phrases, and sentiment
- **Features**:
  - AWS Comprehend integration
  - Multiple NLP providers (Comprehend, Flair)
  - Cost optimization with thresholds
  - Chunk-level entity mapping
- **Output**: `nlp_complete` message

#### Keyword Indexer & Worker
- **Processor**: `keyword-indexer`
- **Worker**: `keyword-indexer-worker`
- **Trigger**: `chunks_ready` message
- **Purpose**: Extract and index keywords for search
- **Features**:
  - TF-IDF analysis
  - OpenSearch keyword indexing
  - Structure-aware processing
- **Output**: `keywords_ready` message

#### Document Structure KG Processor
- **Function**: `document-structure-kg-processor`
- **Trigger**: `chunks_ready` message
- **Purpose**: Generate document structure RDF for knowledge graph
- **Features**:
  - Dublin Core vocabulary integration
  - TTL generation for Neptune
  - Document metadata modeling
- **Output**: TTL files, triggers KG integration

### 4. Knowledge Graph Components

#### KG Integration Worker
- **Function**: `kg-integration-worker`
- **Trigger**: TTL generation completion
- **Purpose**: Load RDF data into Neptune using SPARQL
- **Features**:
  - SPARQL INSERT operations
  - Data validation queries
  - Error handling and retry logic

#### Entity Resolver (Future Integration)
- **Function**: `entity-resolution-service`
- **Trigger**: `nlp_complete` message (enriched)
- **Purpose**: Resolve NLP entities to consistent RDF entities
- **Status**: Implemented but not yet integrated with pipeline

## AWS Services Integration

### Core Services
- **AWS Lambda**: All processing components
- **Amazon S3**: Data lake storage and document input
- **Amazon SNS**: Message passing between components
- **Amazon Textract**: PDF text extraction
- **Amazon Comprehend**: NLP analysis
- **Amazon OpenSearch**: Vector and keyword search
- **Amazon Neptune**: Knowledge graph storage
- **Amazon RDS (PostgreSQL)**: Processing status tracking

### Cost Optimization Features
- **Textract**: ~$0.039 per 26-page document
- **Comprehend**: Configurable cost thresholds per document
- **Titan Embeddings**: Batch processing for efficiency
- **Lambda**: Right-sized memory and timeout configurations

## Database Schema

### Processing Status Tracking
```sql
-- Document processing status
CREATE TABLE document_processing_status (
    doc_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50),
    stage VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata JSONB
);

-- NLP processing status
CREATE TABLE nlp_processing_status (
    doc_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50),
    message TEXT,
    updated_at TIMESTAMP
);
```

## File Structure

### Lambda Functions
```
lambda/
├── text_extractor_initiator/       # Text extraction initiation
├── text_extractor_processor/       # Textract result processing
├── text_chunker/                   # Text chunking logic
├── vector_embeddings_processor/    # Vector processing coordinator
├── vector_embeddings_worker/       # Vector generation worker
├── nlp_processor/                  # NLP processing coordinator
├── nlp_worker/                     # NLP analysis worker
├── keyword_indexer/                # Keyword processing coordinator
├── keyword_indexer_worker/         # Keyword extraction worker
├── document_structure_kg_processor/ # Document KG generation
├── kg_integration_worker/          # Neptune integration
└── entity_resolver/                # Entity resolution (future)
```

### CDK Infrastructure
```
cdk/
├── lib/
│   ├── climate-risk-rag-stack.ts  # Main infrastructure stack
│   ├── lambda-stack.ts            # Lambda function definitions
│   ├── storage-stack.ts           # S3 and database resources
│   └── messaging-stack.ts         # SNS topics and subscriptions
└── bin/
    └── climate-risk-rag.ts        # CDK app entry point
```

### Shared Layers
```
layers/
└── python/
    └── utils/
        ├── DatabaseManager.py      # Database connection management
        ├── DocumentIDManager.py    # Document ID utilities
        └── standardized_messaging.py # Message format utilities
```

## Testing Strategy

### Unit Tests
- Individual component testing with mock data
- Message format validation
- Error handling verification

### Integration Tests
- End-to-end pipeline testing
- Cross-component message passing
- Data lake consistency validation

### Cost Management Tests
- Service usage monitoring
- Cost threshold validation
- Resource optimization verification

## Monitoring and Observability

### CloudWatch Integration
- Lambda function logs and metrics
- Custom metrics for processing stages
- Error rate and duration monitoring

### Status Tracking
- PostgreSQL database for processing status
- SNS message tracking
- S3 data lake validation

## Security Considerations

### IAM Policies
- Least privilege access for Lambda functions
- Service-specific permissions
- Cross-service access controls

### Data Protection
- Encryption at rest (S3, RDS)
- Encryption in transit (HTTPS, TLS)
- VPC isolation for sensitive components

## Performance Characteristics

### Processing Capacity
- **Text Extraction**: ~2-3 minutes per 26-page document
- **Text Chunking**: ~30-45 seconds per document
- **Parallel Processing**: ~2-5 minutes depending on content
- **Total Pipeline**: ~5-10 minutes per document

### Scalability
- Auto-scaling Lambda functions
- Concurrent processing support
- Batch processing optimization

## Deployment

### CDK Deployment
```bash
cd cdk
npm install
cdk deploy --all
```

### Lambda Function Updates
```bash
cd lambda/{function_name}
zip -r function.zip .
aws lambda update-function-code --function-name {function-name} --zip-file fileb://function.zip
```

## Future Enhancements

### Planned Features
1. **Entity Resolver Integration**: Complete NLP entity resolution pipeline
2. **Advanced Search**: Multi-modal search combining vector, keyword, and graph
3. **Query Interface**: Natural language query processing
4. **Batch Processing**: Large document set processing optimization

### Architecture Evolution
1. **Microservices**: Further decomposition of processing components
2. **Event Sourcing**: Complete audit trail of document processing
3. **Multi-tenant**: Support for multiple document collections
4. **Real-time Processing**: Stream processing for live document updates

## Troubleshooting

### Common Issues
1. **Database Connection Pool**: Ensure proper connection management
2. **S3 Permissions**: Verify cross-bucket access permissions
3. **Message Format**: Validate standardized message structure
4. **Cost Thresholds**: Monitor service usage and adjust limits

### Debug Tools
- CloudWatch logs analysis
- S3 data lake inspection
- Database status queries
- SNS message tracing

---

**Last Updated**: July 13, 2025
**Version**: 1.0 - Complete Pipeline Integration
**Status**: Production Ready (Text Extraction → Document Structure KG)
