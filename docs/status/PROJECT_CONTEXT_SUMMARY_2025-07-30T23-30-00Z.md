# PROJECT CONTEXT SUMMARY - 2025-07-30 23:30:00

## 🎯 **PROJECT OVERVIEW**

The Climate Risk RAG System is a serverless document processing pipeline on AWS that extracts, processes, and indexes climate risk documents for retrieval-augmented generation. The system uses event-driven architecture with comprehensive error handling, cost optimization, and semantic document structure representation.

## 📋 **CURRENT SYSTEM STATUS**

### **✅ COMPLETED MILESTONES**
- **Semantic Schema v3.1**: Document Structure KG processor with Dublin Core inheritance
- **Vector Embeddings Pipeline**: Hierarchical chunk structure compatibility
- **OpenSearch Migration**: Migrated from Serverless to Managed cluster
- **NLP Processing**: Comprehend integration with polling-based job monitoring
- **Infrastructure Integrity**: CDK deployment patterns maintained throughout
- **Cost Optimization**: Implemented safeguards for expensive services

### **🚨 CRITICAL DISCOVERY: COMPREHEND LIMITATIONS**
**AWS Comprehend entity detection and key phrase detection jobs do NOT support SNS notifications.** This is a fundamental service limitation discovered through testing:
- `NotificationConfig` parameter is not supported by `start_entities_detection_job` or `start_key_phrases_detection_job`
- Polling via `comprehend-job-monitor` (every 2 minutes) is the ONLY available approach
- This explains why the original polling architecture was necessary

### **🔄 CURRENT ARCHITECTURE STATE**
- **comprehend-job-monitor**: Restored and operational (polling every 2 minutes)
- **nlp-initiator**: Corrected to remove invalid NotificationConfig parameters
- **EventBridge Rule**: `comprehend-job-monitor-schedule` active
- **Pipeline Flow**: Document → Text Extraction → Chunking → NLP Initiator → Comprehend Jobs → Monitor (polling) → NLP Workers

## 🏗️ **ARCHITECTURE OVERVIEW**

### **Core Infrastructure** (`cdk/`)
- **CDK Stacks**: Production-ready infrastructure as code
- **Lambda Functions**: Event-driven serverless processing with VPC configuration
- **Database**: PostgreSQL for metadata and processing status tracking
- **OpenSearch**: AWS Managed cluster for search and vector indexing
- **Neptune**: Knowledge graph storage (configured, endpoint setup needed)
- **S3 Buckets**: Data lake architecture with stage-specific buckets
- **SNS/SQS**: Event-driven messaging between pipeline stages

### **Lambda Functions** (`lambda/`)

#### **Processing Pipeline**
- **text-extractor**: AWS Textract integration for PDF text extraction
- **text-chunker**: Hierarchical document chunking with semantic structure
- **nlp-initiator**: Starts Comprehend entity/keyphrase detection jobs
- **comprehend-job-monitor**: Polls Comprehend jobs every 2 minutes (SNS not supported)
- **nlp-worker-entity**: Processes entity detection results
- **nlp-worker-keyphrase**: Processes key phrase detection results
- **vector-embeddings**: Titan embeddings generation for chunks
- **document-structure-kg-processor**: Semantic schema v3.1 with Dublin Core

#### **Support Functions**
- **cleanup-service**: Removes processed data (OpenSearch + PostgreSQL compatible)
- **pipeline-test-function**: End-to-end pipeline testing
- **opensearch-bulk-load**: Batch indexing for vector embeddings

### **Lambda Layers** (`lambda/shared_layer/`)
- **database-core-layer**: PostgreSQL connection pooling and utilities
- **database-dependencies**: Database drivers and dependencies
- **knowledge-graph-layer**: Neptune integration utilities
- **opensearch-dependencies**: OpenSearch client and utilities

### **Deprecated Components** (`lambda-DEPRECATED/`)
- **comprehend-monitor**: Preserved for reference (now restored to active use)
- **Deprecation documentation**: Comprehensive notes on architectural decisions

## 💰 **COST OPTIMIZATION & EXPENSE MANAGEMENT**

### **🚨 HIGH-COST SERVICES - TESTING PRECAUTIONS**

#### **AWS Textract**
- **Cost**: ~$1.50 per 1,000 pages
- **Mitigation**: 
  - Cost validation in `text-extractor` with configurable thresholds
  - Page count estimation before processing
  - Test with small documents first
- **Testing Strategy**: Use documents <10 pages for development

#### **Amazon Comprehend**
- **Cost**: ~$0.0001 per unit (100 characters) for entity/keyphrase detection
- **Mitigation**:
  - Cost validation in `nlp-initiator` with $0.50 default threshold
  - Text length validation before job submission
  - Batch processing optimization
- **Testing Strategy**: Monitor job costs in CloudWatch

#### **Amazon Titan Embeddings**
- **Cost**: ~$0.0001 per 1,000 input tokens
- **Mitigation**:
  - Chunk size optimization (target 512 tokens)
  - Batch processing for efficiency
  - Cost tracking per document
- **Testing Strategy**: Process small document sets initially

#### **OpenSearch Managed Cluster**
- **Cost**: ~$0.10/hour for t3.small.search instances
- **Mitigation**:
  - Right-sized cluster configuration
  - Automated scaling policies
  - Development vs production cluster separation
- **Testing Strategy**: Use minimal cluster size for development

### **Cost Monitoring Tools**
- **AWS Cost Explorer**: Track service-specific costs
- **CloudWatch Metrics**: Monitor processing volumes
- **Lambda Cost Validation**: Built-in cost checks before expensive operations

## 📊 **DATA FLOW & PROCESSING STAGES**

### **Stage 1: Document Ingestion**
```
S3 Upload → text-extractor → Textract → extracted text (S3)
```

### **Stage 2: Text Processing**
```
Text → text-chunker → hierarchical chunks → chunk metadata (PostgreSQL)
```

### **Stage 3: NLP Processing**
```
Chunks → nlp-initiator → Comprehend jobs → comprehend-monitor (polling) → nlp-workers
```

### **Stage 4: Knowledge Graph**
```
Processed chunks → document-structure-kg-processor → semantic TTL → Neptune
```

### **Stage 5: Vector Indexing**
```
Chunks → vector-embeddings → Titan → embeddings → OpenSearch
```

## 🗄️ **DATABASE SCHEMA**

### **PostgreSQL Tables**
- **documents**: Document metadata and processing status
- **document_processing_status**: Stage-by-stage processing tracking
- **chunks**: Hierarchical chunk structure with parent-child relationships
- **entities**: Named entity recognition results
- **key_phrases**: Key phrase extraction results
- **vector_embeddings**: Embedding metadata and references

### **OpenSearch Indices**
- **climate-risk-chunks**: Vector embeddings with metadata
- **climate-risk-entities**: Entity search index
- **climate-risk-keyphrases**: Key phrase search index

## 🔧 **SEMANTIC SCHEMA v3.1**

### **Namespace Definitions**
- **sgd:** (semantic document) - Core document structure classes
- **sgm:** (semantic metadata) - Processing and technical metadata
- **sg:** (semantic instances) - Specific document instances
- **dcterms:** (Dublin Core) - Standard metadata terms

### **Dublin Core Inheritance**
- **sgd:hasChild** inherits from **dcterms:hasPart**
- **sgd:hasParent** inherits from **dcterms:isPartOf**
- Provides standards compliance while maintaining document-specific semantics

### **Section Type Mapping**
- title → sgd:Section
- header → sgd:Heading  
- paragraph → sgd:Paragraph
- list → sgd:List
- table → sgd:Table
- figure → sgd:Figure

## 🧪 **TESTING & VALIDATION**

### **Pipeline Testing Tools**
- **invoke_pipeline_test.py**: End-to-end pipeline testing with document selection
- **invoke_pretest_cleanup.py**: Clean test environment before runs
- **pipeline-test-function**: Lambda-based testing with cost controls

### **Testing Best Practices**
1. **Start Small**: Use documents <5MB, <20 pages for initial tests
2. **Cost Monitoring**: Check AWS billing dashboard before large test runs
3. **Incremental Testing**: Test one stage at a time before full pipeline
4. **Cleanup**: Always run cleanup after tests to avoid ongoing costs

### **Test Document Selection**
- SQLite database: `/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db`
- Document filtering by size, type, and estimated page count
- Source URL tracking for document provenance

## 📚 **KEY REFERENCE DOCUMENTS**

### **Recent Work Summaries**
- `docs/status/PROJECT_CONTEXT_SUMMARY_2025-07-29_162820.md`: Previous context
- `docs/status/NEXT_STEPS_2025-07-29_162820.md`: Previous next steps
- `docs/status/BULK_LOAD_INTEGRATION_COMPLETE_2025-07-23T02-00-00Z.md`: OpenSearch integration
- `docs/status/KNOWLEDGE_GRAPH_LAYER_COMPLETE_2025-07-23T01-30-00Z.md`: Neptune setup

### **Architecture Documentation**
- `docs/PIPELINE_ARCHITECTURE_COMPLETE.md`: Complete pipeline overview
- `docs/ASYNC_NLP_PROCESSING.md`: NLP processing architecture
- `docs/database-design-architecture.md`: Database schema design
- `docs/schema/`: Semantic schema definitions and examples

### **Infrastructure Documentation**
- `docs/infrastructure/`: CDK deployment guides
- `docs/migration/`: Service migration procedures
- `docs/cost-optimization/`: Cost management strategies
- `docs/setup/`: Initial setup and configuration

## 🔍 **CURRENT ISSUES & LIMITATIONS**

### **Known Service Limitations**
1. **Comprehend SNS**: Entity/keyphrase jobs don't support SNS notifications (polling required)
2. **Neptune Endpoint**: Knowledge graph endpoint needs configuration
3. **VPC Networking**: Lambda functions require VPC configuration for database access

### **Performance Considerations**
1. **Comprehend Polling**: 2-minute maximum delay for job completion detection
2. **Vector Embeddings**: Batch processing needed for large document sets
3. **OpenSearch Indexing**: Bulk operations required for efficiency

## 🛠️ **DEVELOPMENT ENVIRONMENT**

### **Local Development**
- **AWS CLI**: Configured with SSO authentication
- **CDK**: Infrastructure deployment and updates
- **Python 3.11**: Lambda runtime compatibility
- **Git**: Version control with descriptive commit messages

### **Deployment Patterns**
- **CDK Deploy**: Infrastructure changes via `cdk deploy --all`
- **Lambda Updates**: Direct code updates via AWS CLI for rapid iteration
- **Layer Management**: Shared dependencies via Lambda layers
- **Environment Variables**: Configuration via Lambda environment variables

## 🎯 **SUCCESS METRICS**

### **Pipeline Performance**
- **End-to-End Processing**: Document → searchable results
- **Error Handling**: Comprehensive error tracking and recovery
- **Cost Efficiency**: Processing costs within acceptable thresholds
- **Scalability**: Handles concurrent document processing

### **Data Quality**
- **Semantic Structure**: Hierarchical document representation
- **Entity Extraction**: High-quality named entity recognition
- **Vector Embeddings**: Accurate semantic similarity matching
- **Knowledge Graph**: Rich relationship representation

## 🔄 **OPERATIONAL STATUS**

### **Active Services**
- ✅ **Text Extraction**: Operational with cost controls
- ✅ **Text Chunking**: Hierarchical structure v3 compatible
- ✅ **NLP Processing**: Comprehend integration with polling monitor
- ✅ **Vector Embeddings**: Titan integration operational
- ✅ **OpenSearch**: Managed cluster with bulk indexing
- ⚠️ **Neptune**: Configured but endpoint setup needed

### **Monitoring & Alerting**
- **CloudWatch Logs**: Comprehensive logging across all functions
- **Error Tracking**: Database-backed error logging
- **Cost Monitoring**: Built-in cost validation and alerts
- **Processing Status**: Real-time pipeline stage tracking

---

**This document provides complete context for resuming development work on the Climate Risk RAG System. All architectural decisions, cost considerations, and current limitations are documented for informed development planning.**
