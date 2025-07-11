# Project Context Summary - Climate Risk RAG System
## Date: 2025-07-11T01:00:00Z

## 🎯 PROJECT OVERVIEW

The Climate Risk RAG (Retrieval-Augmented Generation) system is a comprehensive AWS-based pipeline for processing climate-related documents, extracting entities, building knowledge graphs, and enabling semantic search. The system processes PDFs through text extraction, chunking, NLP analysis, entity resolution, and knowledge graph integration.

## 🏗️ CURRENT ARCHITECTURE STATUS

### **✅ COMPLETED MAJOR COMPONENTS**

#### **1. Data Lake Bucket Reorganization (COMPLETE)**
- **Legacy Buckets Preserved**: `solve-global-kr-*-861276078413-us-east-1` (for reference)
- **New Data Lake Buckets**: `solve-global-kr-dl-*-861276078413-us-east-1` (production)
  - `solve-global-kr-dl-chunks-861276078413-us-east-1`
  - `solve-global-kr-dl-embeddings-861276078413-us-east-1`
  - `solve-global-kr-dl-neptune-ttl-861276078413-us-east-1`
  - `solve-global-kr-dl-ner-results-861276078413-us-east-1`
  - `solve-global-kr-dl-text-861276078413-us-east-1`
- **All Code Updated**: Lambda functions, CDK, tests, documentation updated to use new buckets
- **Clean Separation**: Legacy POC vs. production data lake structure

#### **2. Entity Resolution Service (IMPLEMENTATION COMPLETE)**
- **Location**: `/lambda/entity_resolver/`
- **Core Components**:
  - `entity_resolver.py` - Main Lambda handler with multi-entity type support
  - `uri_minter.py` - Consistent URI generation using `kr:` namespace
  - `rdf_entity_builder.py` - TTL generation from resolved entities
  - `entity_chunk_resolver.py` - Maps entities to chunks using offsets
  - `document_entity_extractor.py` - Extracts metadata-based entities
  - `test_entity_resolver.py` - Comprehensive test suite
- **Entity Types Supported**: PERSON, ORGANIZATION, LOCATION, DATE, QUANTITY, CONCEPT
- **RDF Schema**: Uses `@prefix kr: <http://solve.global/knowledge-commons/schema#>`
- **Integration Ready**: Works with existing KG integration worker

#### **3. KG Integration Extensions (COMPLETE)**
- **Location**: `/lambda/kg_integration_worker/`
- **Enhanced Components**:
  - `entity_integration_handler.py` - Entity-specific KG integration
  - `kg_integration_worker_updated.py` - Updated worker with entity support
- **Capabilities**: SPARQL generation, Neptune loading, entity validation

#### **4. Pipeline Test Scripts with Source URL Integration (COMPLETE)**
- **Location**: Root directory
- **Scripts**:
  - `test_complete_pipeline_with_source_urls.py` - Full-featured version
  - `test_pipeline_parallel_simple.py` - Simplified, recommended version
- **Features**:
  - SQLite database integration (`/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db`)
  - Source URL lookup and proper document ID generation
  - Multi-threaded processing of 10 documents in parallel
  - Error handling and result tracking

### **🔄 EXISTING WORKING COMPONENTS**

#### **CDK Infrastructure** (`/cdk/`)
- **Text Extraction Pipeline**: TextExtractor with Textract integration
- **Text Chunking**: Smart structured chunking with DocumentIDManager
- **NLP Processing**: AWS Comprehend integration for entity extraction
- **Vector Embeddings**: Titan embeddings generation
- **Knowledge Graph**: Neptune integration with SPARQL loading
- **Database**: PostgreSQL for pipeline status tracking

#### **Lambda Functions** (`/lambda/`)
- **Text Processing**:
  - `text_extractor/` - Textract-based text extraction
  - `text_extractor_processor/` - Text extraction processing
  - `text_chunker/` - Smart structured text chunking
- **NLP & Analysis**:
  - `nlp_worker/` - AWS Comprehend NLP processing
  - `nlp_processor/` - NLP result processing
  - `keyword_indexer/` - Keyword extraction and indexing
- **Vector & Embeddings**:
  - `vector_embeddings_worker/` - Titan embeddings generation
  - `vector_embeddings_processor/` - Embeddings processing
- **Knowledge Graph**:
  - `document_structure_kg_processor/` - Document structure RDF generation
  - `kg_integration_worker/` - Neptune SPARQL loading
- **Search & Query**:
  - `vector_searcher/` - Vector similarity search
  - `kg_searcher/` - Knowledge graph querying
  - `query_handler/` - Unified query processing

#### **Shared Layers** (`/layers/`)
- **Core Utilities** (`/layers/app-source/utils/`):
  - `DatabaseManager.py` - PostgreSQL database operations
  - `DocumentIDManager.py` - Document ID generation and management
- **Document Processing** (`/layers/app-source/document_processing/`):
  - Document metadata handling and processing utilities

## 📊 PIPELINE FLOW

### **Current Working Pipeline**
```
1. Document Upload (S3)
   ↓
2. Text Extraction (Textract)
   ↓ SNS: text_ready
3. Text Chunking (Smart Structured)
   ↓ SNS: chunks_ready
4. NLP Processing (Comprehend)
   ↓ SNS: nlp_complete
5. Entity Resolution (NEW - READY TO DEPLOY)
   ↓ SNS: entities_resolved
6. Knowledge Graph Integration
   ↓ SNS: kg_complete
7. Vector Embeddings (Titan)
   ↓ SNS: embeddings_ready
8. Search Index Updates
```

### **Message Flow Architecture**
- **Standardized Messaging**: Uses `StandardizedMessagePublisher` classes
- **SNS/SQS Integration**: Event-driven pipeline coordination
- **Status Tracking**: PostgreSQL database for processing status
- **Error Handling**: Comprehensive error recovery and logging

## 🔧 TECHNICAL SPECIFICATIONS

### **RDF Schema & Ontologies**
- **Primary Namespace**: `@prefix kr: <http://solve.global/knowledge-commons/schema#>`
- **Standard Ontologies**: FOAF, Schema.org, Dublin Core, SKOS, QUDT, Time Ontology
- **Entity Types**: Person (foaf:Person), Organization (foaf:Organization), Location (schema:Place)
- **Climate Extensions**: Custom properties for climate-specific metadata

### **Database Architecture**
- **PostgreSQL**: Pipeline status, document metadata, processing tracking
- **Neptune**: RDF knowledge graph with SPARQL endpoint
- **SQLite (POC)**: Legacy document corpus with source URLs (15,171 documents)

### **AWS Services Integration**
- **Textract**: Document text extraction and structure analysis
- **Comprehend**: NLP entity extraction and key phrase detection
- **Titan**: Vector embeddings generation
- **Neptune**: Graph database for RDF knowledge graph
- **S3**: Data lake storage with organized bucket structure
- **Lambda**: Serverless processing pipeline
- **SNS/SQS**: Event-driven messaging and coordination

## 💰 COST MANAGEMENT & TESTING CONSIDERATIONS

### **⚠️ HIGH-COST SERVICES - EXERCISE CAUTION**

#### **1. Amazon Textract**
- **Cost**: ~$1.50 per 1,000 pages for document analysis
- **Current Usage**: Text extraction from PDFs
- **Testing Strategy**: 
  - Use small document batches (5-10 documents) for testing
  - Leverage existing extracted text when possible
  - Monitor costs in AWS Cost Explorer
- **Production Consideration**: Implement cost thresholds and alerts

#### **2. Amazon Comprehend**
- **Cost**: ~$0.0001 per unit (100 characters) for entity detection
- **Current Usage**: Entity extraction from document chunks
- **Testing Strategy**:
  - Test with shorter text samples first
  - Implement confidence thresholds to reduce processing
  - Use batch processing for efficiency
- **Production Consideration**: Set up cost monitoring and limits

#### **3. Amazon Titan (Embeddings)**
- **Cost**: ~$0.0001 per 1,000 input tokens
- **Current Usage**: Vector embeddings generation for semantic search
- **Testing Strategy**:
  - Test with limited chunk sets
  - Use existing embeddings when available
  - Implement caching to avoid reprocessing
- **Production Consideration**: Optimize chunk sizes and implement deduplication

#### **4. Amazon Neptune**
- **Cost**: Instance-based pricing (~$0.348/hour for db.t3.medium)
- **Current Usage**: RDF knowledge graph storage and querying
- **Testing Strategy**:
  - Use development instance sizes
  - Implement query optimization
  - Monitor SPARQL query performance
- **Production Consideration**: Right-size instances and implement query caching

### **Cost Monitoring Setup**
- **AWS Cost Explorer**: Monitor service-specific costs
- **CloudWatch Alarms**: Set up cost threshold alerts
- **Budget Alerts**: Configure monthly budget notifications
- **Resource Tagging**: Tag all resources for cost attribution

## 📚 KEY DOCUMENTATION REFERENCES

### **Implementation Status Documents** (`/docs/status/`)
- `DUBLIN_CORE_INTEGRATION_COMPLETE_2025-07-10T20-30-00Z.md`
- `DOCUMENT_STRUCTURE_KG_LAMBDAS_READY_2025-07-10T21-00-00Z.md`
- Previous project context summaries with architectural decisions

### **Integration Documentation** (`/docs/integration/`)
- `PIPELINE_INTEGRATION_DESIGN_2025-07-05T20-58-00Z.md`
- `NLP_INTEGRATION_PLAN_2025-07-06T22-30-00Z.md`
- `VECTOR_INDEX_INTEGRATION_PLAN_2025-07-06T16-00-00Z.md`

### **Implementation Details** (`/docs/implementation/`)
- `TEXT_CHUNKER_INTEGRATION_COMPLETE_2025-07-05T18-50-00Z.md`
- `NLP_INTEGRATION_TESTING_COMPLETE_2025-07-08T17-35-00Z.md`
- `CORRECTED_TEXTEXTRACTOR_COMPLETE_2025-07-04T23-25-00Z.md`

### **Analysis Documents** (`/docs/analysis/`)
- `MANUAL_VS_ACTUAL_TTL_COMPARISON_2025-07-09T22-45-00Z.md`
- `S3_INTEGRATION_FIXES_SUMMARY_2025-07-09T23-15-00Z.md`

## 🎯 CURRENT DEVELOPMENT STATUS

### **✅ READY FOR DEPLOYMENT**
1. **Entity Resolution Service** - Complete implementation, tested components
2. **KG Integration Extensions** - Enhanced worker with entity support
3. **Pipeline Test Scripts** - Multi-threaded testing with source URL integration
4. **Data Lake Architecture** - Clean bucket organization and code migration

### **🔄 WORKING & STABLE**
1. **Text Extraction Pipeline** - Textract integration working
2. **Text Chunking** - Smart structured chunking operational
3. **NLP Processing** - Comprehend integration functional
4. **Knowledge Graph Integration** - Neptune loading working
5. **Vector Embeddings** - Titan embeddings generation operational

### **⏳ PENDING INTEGRATION**
1. **Entity Resolution Deployment** - CDK deployment script needed
2. **End-to-End Testing** - Full pipeline validation with entity resolution
3. **Performance Optimization** - Cost and performance tuning
4. **Production Monitoring** - Enhanced logging and alerting

## 🔍 TESTING APPROACH

### **Current Test Documents**
- **POC Database**: 15,171 documents with source URLs
- **S3 Documents**: PDF files in `solve-global-kr-documents-861276078413-us-east-1`
- **Test Scripts**: Multi-threaded parallel processing validation

### **Testing Strategy**
1. **Small Batch Testing**: Start with 5-10 documents to validate pipeline
2. **Parallel Processing**: Test with 10 documents simultaneously
3. **Cost Monitoring**: Track expenses during testing phases
4. **Incremental Validation**: Test each pipeline stage independently
5. **Error Recovery**: Validate error handling and retry mechanisms

## 🚨 CRITICAL CONSIDERATIONS

### **Data Consistency**
- **Document IDs**: Ensure consistent ID generation across pipeline stages
- **Source URLs**: Maintain traceability to original document sources
- **Metadata Preservation**: Keep document metadata throughout processing

### **Performance & Scalability**
- **Parallel Processing**: Architecture supports concurrent document processing
- **Resource Limits**: Monitor Lambda concurrency and timeout limits
- **Database Connections**: Manage PostgreSQL and Neptune connection pools

### **Security & Access**
- **AWS Credentials**: Ensure proper IAM roles and permissions
- **Database Access**: Secure PostgreSQL and Neptune access
- **S3 Bucket Policies**: Appropriate read/write permissions

## 📁 KEY DIRECTORIES & FILES

### **Core Implementation**
- `/cdk/` - CDK infrastructure definitions
- `/lambda/` - Lambda function implementations
- `/layers/` - Shared utilities and libraries
- `/docs/` - Comprehensive documentation

### **Entity Resolution (NEW)**
- `/lambda/entity_resolver/` - Complete entity resolution service
- `/lambda/kg_integration_worker/entity_integration_handler.py` - KG extensions

### **Testing & Validation**
- `test_pipeline_parallel_simple.py` - Recommended test script
- `test_complete_pipeline_with_source_urls.py` - Full-featured test
- `/lambda/entity_resolver/test_entity_resolver.py` - Entity resolution tests

### **Configuration & Data**
- SQLite Database: `/Volumes/G-RAID Photo 24TB/climate_risk_rag/db/corpus_document_ids.db`
- AWS Profile: `solve-global` (configured in ~/.aws/credentials)

## 🎯 IMMEDIATE PRIORITIES

1. **Deploy Entity Resolution Service** - Create CDK deployment
2. **Run Pipeline Tests** - Validate end-to-end processing with cost monitoring
3. **Performance Tuning** - Optimize for cost and speed
4. **Production Readiness** - Enhanced monitoring and error handling

---

**Status**: Entity Resolution Service implementation complete, ready for deployment and testing
**Next Phase**: Deployment, testing, and production optimization
**Critical**: Monitor costs during testing phases, especially Textract and Comprehend usage
