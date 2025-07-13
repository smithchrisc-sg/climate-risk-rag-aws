# Climate Risk RAG Pipeline - Current Source Files
**Last Updated**: July 13, 2025, 22:15 UTC  
**Status**: Production Ready Components

## Lambda Functions - Production Ready

### Text Extraction Pipeline

#### Text Extractor Initiator
- **File**: `lambda/text_extractor_initiator/text_extractor_initiator.py`
- **Function**: `solve-global-kr-textextractor-initiator`
- **Handler**: `text_extractor_initiator.lambda_handler`
- **Trigger**: S3 document upload
- **Purpose**: Initiate Textract jobs for PDF processing
- **Status**: ✅ Production Ready
- **Key Features**:
  - S3 event processing
  - Textract job initiation
  - SNS notification setup
  - Error handling and retry logic

#### Text Extractor Processor
- **File**: `lambda/text_extractor_processor/text_extractor_processor.py`
- **Function**: `solve-global-kr-textextractor-processor`
- **Handler**: `text_extractor_processor.lambda_handler`
- **Trigger**: Textract completion SNS
- **Purpose**: Process Textract results and extract structured text
- **Status**: ✅ Production Ready
- **Key Features**:
  - Textract result parsing
  - Text extraction and cleaning
  - Data lake storage (`/data_lake/{doc_id}/raw_text.txt`)
  - Standardized messaging for downstream processing

### Text Chunking Pipeline

#### Text Chunker Processor
- **File**: `lambda/text_chunker/text_chunker_processor.py`
- **Function**: `text-chunker-pipeline`
- **Handler**: `text_chunker_processor.lambda_handler`
- **Trigger**: Text extraction completion
- **Purpose**: Split text into semantic chunks with overlap
- **Status**: ✅ Production Ready
- **Key Features**:
  - Configurable chunk size (1000 characters default)
  - Overlap handling (200 characters default)
  - Sentence boundary preservation
  - Individual chunk JSON storage
  - `chunks_ready` message publication

### Vector Embeddings Pipeline

#### Vector Embeddings Processor
- **File**: `lambda/vector_embeddings_processor/vector_embeddings_processor.py`
- **Function**: `vector-embeddings-processor`
- **Handler**: `vector_embeddings_processor.lambda_handler`
- **Trigger**: `chunks_ready` SNS message
- **Purpose**: Coordinate vector embedding generation
- **Status**: ✅ Production Ready
- **Key Features**:
  - Standardized message processing
  - Worker delegation
  - Status tracking
  - Error handling

#### Vector Embeddings Worker
- **File**: `lambda/vector_embeddings_worker/vector_embeddings_worker.py`
- **Function**: `vector-embeddings-worker`
- **Handler**: `vector_embeddings_worker.lambda_handler`
- **Trigger**: Vector processor delegation
- **Purpose**: Generate vector embeddings using AWS Titan
- **Status**: ✅ Production Ready
- **Key Features**:
  - AWS Titan embeddings integration
  - OpenSearch vector indexing
  - Batch processing optimization
  - Data lake storage

### NLP Processing Pipeline

#### NLP Processor
- **File**: `lambda/nlp_processor/nlp_processor.py`
- **Function**: `nlp-processor`
- **Handler**: `nlp_processor.lambda_handler`
- **Trigger**: `chunks_ready` SNS message
- **Purpose**: Coordinate NLP analysis processing
- **Status**: ✅ Production Ready
- **Key Features**:
  - Standardized message processing
  - Cost threshold validation
  - Worker delegation
  - Database status tracking

#### NLP Worker
- **File**: `lambda/nlp_worker/nlp_worker.py`
- **Function**: `nlp-worker`
- **Handler**: `nlp_worker.lambda_handler`
- **Trigger**: NLP processor delegation
- **Purpose**: Perform NLP analysis using AWS Comprehend
- **Status**: ✅ Production Ready
- **Key Features**:
  - AWS Comprehend integration
  - Multiple NLP providers support (Comprehend, Flair)
  - Entity extraction and key phrase analysis
  - Chunk-level entity mapping
  - Cost optimization with thresholds
  - `nlp_complete` message publication

### Keyword Indexing Pipeline

#### Keyword Indexer Processor
- **File**: `lambda/keyword_indexer/keyword_indexer_processor.py`
- **Function**: `keyword-indexer`
- **Handler**: `keyword_indexer_processor.lambda_handler`
- **Trigger**: `chunks_ready` SNS message
- **Purpose**: Coordinate keyword extraction and indexing
- **Status**: ✅ Production Ready
- **Key Features**:
  - Standardized message processing
  - Worker delegation
  - OpenSearch integration
  - Status tracking

#### Keyword Indexer Worker
- **File**: `lambda/keyword_indexer_worker/keyword_indexer_worker.py`
- **Function**: `keyword-indexer-worker`
- **Handler**: `keyword_indexer_worker.lambda_handler`
- **Trigger**: Keyword processor delegation
- **Purpose**: Extract keywords using TF-IDF and index in OpenSearch
- **Status**: ✅ Production Ready
- **Key Features**:
  - TF-IDF keyword extraction
  - OpenSearch keyword indexing
  - Structure-aware processing
  - Data lake storage

### Knowledge Graph Pipeline

#### Document Structure KG Processor
- **File**: `lambda/document_structure_kg_processor/document_structure_kg_processor.py`
- **Function**: `document-structure-kg-processor`
- **Handler**: `document_structure_kg_processor.lambda_handler`
- **Trigger**: `chunks_ready` SNS message
- **Purpose**: Generate document structure RDF for knowledge graph
- **Status**: ✅ Production Ready
- **Key Features**:
  - Dublin Core vocabulary integration
  - TTL generation for Neptune
  - Document metadata modeling
  - Data lake compatibility
  - Enhanced metadata support

#### Document TTL Generator
- **File**: `lambda/document_structure_kg_processor/document_ttl_generator.py`
- **Purpose**: Generate TTL representations using Dublin Core vocabulary
- **Status**: ✅ Production Ready
- **Key Features**:
  - RDF/TTL generation
  - S3 data integration
  - URI minting support
  - Enhanced metadata processing

#### KG Integration Worker
- **File**: `lambda/kg_integration_worker/kg_integration_worker_updated.py`
- **Function**: `kg-integration-worker`
- **Handler**: `kg_integration_worker.lambda_handler`
- **Trigger**: TTL generation completion
- **Purpose**: Load RDF data into Neptune using SPARQL
- **Status**: ✅ Ready for Integration
- **Key Features**:
  - SPARQL INSERT operations
  - Data validation queries
  - Error handling and retry logic
  - Entity integration support

### Entity Resolution Pipeline

#### Entity Resolver
- **File**: `lambda/entity_resolver/entity_resolver.py`
- **Function**: `entity-resolution-service`
- **Handler**: `entity_resolver.lambda_handler`
- **Trigger**: `nlp_complete` message (pending integration)
- **Purpose**: Resolve NLP entities to consistent RDF entities
- **Status**: 🔧 Implemented, Needs Pipeline Integration
- **Key Features**:
  - Entity resolution and deduplication
  - URI minting for consistent entity references
  - Chunk-level entity mapping
  - RDF entity generation

#### Supporting Entity Components
- **File**: `lambda/entity_resolver/entity_chunk_resolver.py` - Chunk-level entity resolution
- **File**: `lambda/entity_resolver/rdf_entity_builder.py` - RDF entity construction
- **File**: `lambda/entity_resolver/uri_minter.py` - Consistent URI generation
- **File**: `lambda/entity_resolver/document_entity_extractor.py` - Document-level entity extraction

## Shared Utilities and Layers

### Lambda Layer - Python Utilities
- **Path**: `layers/python/utils/`
- **Purpose**: Shared utilities across Lambda functions

#### Database Manager
- **File**: `layers/python/utils/DatabaseManager.py`
- **Purpose**: PostgreSQL connection management
- **Features**:
  - Connection pooling
  - Secrets Manager integration
  - Retry logic and error handling
  - Status tracking methods

#### Document ID Manager
- **File**: `layers/python/utils/DocumentIDManager.py`
- **Purpose**: Document ID utilities and validation
- **Features**:
  - ID generation and validation
  - Hash computation
  - Metadata extraction

### Standardized Messaging
- **Files**: `lambda/*/standardized_messaging.py` (replicated per function)
- **Purpose**: Consistent message format handling
- **Features**:
  - Message parsing and validation
  - SNS message publishing
  - Format standardization
  - Error handling

## Infrastructure as Code

### CDK Stack Definitions
- **Main Stack**: `cdk/lib/climate-risk-rag-stack.ts`
- **Lambda Stack**: `cdk/lib/lambda-stack.ts`
- **Storage Stack**: `cdk/lib/storage-stack.ts`
- **Messaging Stack**: `cdk/lib/messaging-stack.ts`
- **CDK App**: `cdk/bin/climate-risk-rag.ts`

### Configuration Files
- **CDK Config**: `cdk/cdk.json`
- **Package Config**: `cdk/package.json`
- **TypeScript Config**: `cdk/tsconfig.json`

## Test Scripts

### Integration Tests
- **File**: `test_document_structure_kg_integration.py` - KG processor testing
- **File**: `test_nlp_integration.py` - NLP pipeline testing
- **File**: `test_vector_embeddings_integration.py` - Vector processing testing
- **File**: `test_keyword_indexer_integration.py` - Keyword processing testing
- **File**: `test_kg_message_format.py` - Message format validation
- **File**: `test_kg_minimal.py` - Minimal functionality testing

### Analysis Scripts
- **File**: `analyze_pipeline_orchestration.py` - Pipeline flow analysis
- **File**: `monitor_pipeline_status.py` - Pipeline status monitoring
- **File**: `simple_chunking_test.py` - Text chunking validation

## Deprecated Files

All outdated versions have been renamed with `DEPRECATED_` prefix to maintain history while clarifying current state. These files should not be used for development but are preserved for reference.

### Examples of Deprecated Files
- `lambda/nlp_processor/DEPRECATED_nlp_processor.py`
- `lambda/nlp_processor/DEPRECATED_nlp_processor_simplified.py`
- `lambda/text_chunker/DEPRECATED_text_chunker_processor.py`
- `lambda/vector_embeddings_worker/DEPRECATED_vector_embeddings_worker.py`
- And many others across all components

## Requirements Files

### Lambda Function Requirements
Each Lambda function has its own `requirements.txt` file specifying Python dependencies:
- `lambda/*/requirements.txt` - Function-specific dependencies
- Common dependencies: boto3, psycopg2, requests, json, datetime

### CDK Requirements
- `cdk/package.json` - Node.js dependencies for CDK
- `cdk/package-lock.json` - Locked dependency versions

## Documentation

### Architecture Documentation
- **File**: `docs/PIPELINE_ARCHITECTURE_COMPLETE.md` - Complete architecture overview
- **File**: `docs/CURRENT_SOURCE_FILES.md` - This file
- **File**: `docs/DEFERRED_FIXES_LIST.md` - Known issues and future fixes

### Status Documentation
- **Path**: `docs/status/` - Project status and context documents
- **File**: `docs/status/PROJECT_CONTEXT_SUMMARY_2025-07-13_22-15.md` - Current project context
- **File**: `docs/status/NEXT_STEPS_2025-07-13_22-15.md` - Next steps and priorities

### Work Summaries
- **Path**: `docs/work_summaries/` - Session work summaries
- Previous session documentation for context and history

## File Organization Principles

### Naming Conventions
1. **Production Files**: Use descriptive names matching Lambda function names
2. **Deprecated Files**: Prefixed with `DEPRECATED_` for clarity
3. **Test Files**: Prefixed with `test_` for easy identification
4. **Documentation**: Clear, descriptive names with timestamps where relevant

### Directory Structure
1. **Functional Grouping**: Components grouped by pipeline stage
2. **Shared Resources**: Common utilities in `layers/` directory
3. **Infrastructure**: CDK files in dedicated `cdk/` directory
4. **Documentation**: Centralized in `docs/` with subdirectories

### Version Control
1. **Git Integration**: All changes committed with descriptive messages
2. **Branch Strategy**: Feature branches for major changes
3. **History Preservation**: Deprecated files maintained for reference
4. **Documentation Updates**: Documentation updated with code changes

---

**IMPORTANT NOTES**:

1. **Production Readiness**: All files marked as "Production Ready" have been tested and integrated
2. **Deprecation Policy**: Deprecated files are preserved for reference but should not be used
3. **Testing Strategy**: Test files provide comprehensive validation of components
4. **Cost Awareness**: All production components include cost optimization features
5. **Documentation Currency**: This document reflects the current state as of July 13, 2025

**For Development**: Always use the current (non-deprecated) files and refer to the architecture documentation for understanding component interactions and data flow.
