# PROJECT CONTEXT SUMMARY - 2025-07-29 16:28:20

## 🎯 **PROJECT OVERVIEW**

The Climate Risk RAG System is a serverless document processing pipeline on AWS that extracts, processes, and indexes climate risk documents for retrieval-augmented generation. The system uses a semantic schema v3.1 with Dublin Core inheritance for hierarchical document structure representation.

## 📋 **CURRENT SYSTEM STATUS**

### **✅ COMPLETED MILESTONES**
- **Semantic Schema v3.1**: Document Structure KG processor refactored with Dublin Core inheritance
- **Vector Embeddings Compatibility**: Updated for hierarchical chunk structure v3
- **OpenSearch Migration**: Migrated from Serverless to Managed cluster
- **Cleanup Service**: Updated for managed OpenSearch and PostgreSQL schema changes
- **Infrastructure Integrity**: CDK deployment patterns maintained throughout

### **🔄 ACTIVE PROCESSING**
- **Pipeline Test Running**: 3 documents currently processing through full pipeline
- **Vector Embeddings Test**: Validating compatibility with new hierarchical chunk structure
- **Documents Processing**: 064762102bead7b04a39, 024c99ee7a0fce7be4bc, 02a2baf87408e8e97493

## 🏗️ **ARCHITECTURE OVERVIEW**

### **Core Infrastructure** (`cdk/`)
- **CDK Stacks**: Production-ready infrastructure as code
- **Lambda Functions**: Event-driven serverless processing
- **Database**: PostgreSQL for metadata and processing status
- **OpenSearch**: AWS Managed cluster for search and vector indexing
- **Neptune**: Knowledge graph storage (configured but needs endpoint setup)
- **S3 Buckets**: Data lake architecture with stage-specific buckets

### **Lambda Functions** (`lambda/`)
```
lambda/
├── text-extractor-initiator/          # Triggers Textract jobs
├── text-extractor-processor/          # Processes Textract results
├── text-chunker-processor/            # Smart hierarchical chunking
├── document-structure-kg-processor/   # Semantic schema v3.1 RDF generation
├── vector-embeddings-initiator/       # Initiates vector processing
├── vector-embeddings-worker/          # Bedrock Titan embeddings + OpenSearch
├── keyword-indexer/                   # TF-IDF keyword indexing
├── kg-triple-loader/                  # Neptune RDF loading
├── nlp-initiator/                     # NLP processing coordination
├── nlp-processor/                     # Comprehend entity extraction
├── nlp-worker/                        # NLP result processing
├── cleanup-service/                   # System cleanup and maintenance
└── pipeline-test-function/            # End-to-end testing
```

### **Lambda Layers** (`layers/`)
```
layers/
├── database-core-layer/               # PostgreSQL + DocumentMetadata
├── knowledge-graph-layer/             # Neptune + RDF utilities
└── opensearch-layer/                  # OpenSearch dependencies
```

## 🔧 **RECENT TECHNICAL ACHIEVEMENTS**

### **Semantic Schema v3.1 Implementation**
- **Dublin Core Inheritance**: `sgd:hasChild ⊆ dcterms:hasPart`, `sgd:hasParent ⊆ dcterms:isPartOf`
- **Namespace Separation**: `sgd:` (semantic), `sgm:` (metadata), `sg:` (instances), `dcterms:` (Dublin Core)
- **Hierarchical Relationships**: Parent-child-sibling chunk relationships with ordered navigation
- **Section Type Mapping**: `title→sgd:Section`, `header→sgd:Heading`, `paragraph→sgd:Paragraph`, etc.

### **Vector Embeddings Compatibility Fix**
- **Field Mapping Updates**: `section_types→section_type`, `hierarchy_levels→hierarchy_level`
- **New Hierarchical Fields**: `parent_chunk_id`, `child_chunk_ids`, `sibling_chunk_ids`
- **Embedding Purity Confirmed**: Only `chunk['text']` embedded, no metadata contamination
- **OpenSearch Mapping**: Updated for new hierarchical metadata structure

### **OpenSearch Migration Completed**
- **Authentication**: Migrated from AWS4Auth (Serverless) to basic auth (Managed)
- **Index Structure**: `chunks_vector` (embeddings), `documents` (keyword search)
- **Cleanup Service**: Updated for managed cluster compatibility

## 📊 **DATA FLOW ARCHITECTURE**

### **Processing Pipeline**
```
S3 Source Documents
    ↓
Text Extraction (Textract) → S3 Text Storage
    ↓
Hierarchical Chunking → S3 Chunks Storage
    ↓
┌─ Vector Embeddings (Titan) → OpenSearch chunks_vector
├─ Keyword Indexing (TF-IDF) → OpenSearch documents  
├─ Document Structure KG → S3 TTL → Neptune
└─ NLP Processing (Comprehend) → PostgreSQL + S3
```

### **Storage Architecture**
```
S3 Data Lake:
├── solve-global-kr-dl-source-documents-*     # Original PDFs
├── solve-global-kr-dl-text-*                 # Textract output
├── solve-global-kr-dl-chunks-*               # Hierarchical chunks
├── solve-global-kr-dl-embeddings-*           # Vector embeddings
├── solve-global-kr-dl-keywords-*             # Keyword data
├── solve-global-kr-dl-nlp-*                  # NLP results
└── solve-global-kr-dl-neptune-ttl-*          # RDF/TTL files

PostgreSQL:
├── document_processing_status                 # Pipeline tracking
├── nlp_processing_status                     # NLP stage tracking
└── [other processing status tables]

OpenSearch Managed Cluster:
├── chunks_vector                             # Vector search index
└── documents                                 # Keyword search index
```

## 💰 **COST MANAGEMENT & TESTING GUIDELINES**

### **⚠️ EXPENSIVE SERVICES - USE WITH CAUTION**

#### **AWS Textract** 💸
- **Cost**: ~$1.50 per 1,000 pages
- **Mitigation**: Use `invoke_pipeline_test.py --num-documents 3` for testing
- **Monitoring**: Check page estimates before processing large document sets

#### **Amazon Comprehend** 💸
- **Cost**: ~$0.019 per document for entity detection
- **Mitigation**: Limit NLP testing to small document sets
- **Monitoring**: Track document counts in NLP processing

#### **Amazon Bedrock Titan Embeddings** 💸
- **Cost**: ~$0.002 per document for embeddings generation
- **Mitigation**: Use existing processed documents for testing when possible
- **Monitoring**: Monitor chunk counts (100-500 chunks per document)

### **🧪 COST-EFFECTIVE TESTING STRATEGIES**

#### **Recommended Testing Approach**
```bash
# 1. Use pipeline test with minimal documents
python3 invoke_pipeline_test.py --num-documents 3 --force

# 2. Test with existing processed documents
# Check S3 for already processed documents before triggering new processing

# 3. Use cleanup service to reset state
python3 simple_cleanup.py  # Clean databases/indices without reprocessing
```

#### **Cost Monitoring Commands**
```bash
# Check document counts before processing
aws s3 ls s3://solve-global-kr-documents-861276078413-us-east-1/ --recursive | wc -l

# Monitor processing status
# Check PostgreSQL document_processing_status table

# Estimate costs before large runs
# Pages per document * $1.50/1000 pages = Textract cost
# Document count * $0.019 = Comprehend cost
```

## 📚 **KEY REFERENCE DOCUMENTS**

### **Architecture & Design**
- `docs/infrastructure/INFRASTRUCTURE_REFERENCE.md` - Complete infrastructure mappings
- `docs/infrastructure/MESSAGING_ALIGNMENT_SUMMARY.md` - SNS topic patterns
- `docs/design/LAMBDA_LAYER_DESIGN_UPDATED.md` - Layer usage patterns

### **Implementation Summaries**
- `SEMANTIC_DOCUMENT_STRUCTURE_SCHEMA_EXPLANATION_2025-07-29.md` - Schema v3.1 details
- `DATABASE_LAYER_ARCHITECTURE.md` - Database layer design
- `OPENSEARCH_MIGRATION_GUIDE.md` - OpenSearch migration details
- `VECTOR_EMBEDDINGS_COMPREHENSIVE_FIX.md` - Embeddings compatibility

### **Status & Progress**
- `CURRENT_STATUS_SUMMARY.md` - Recent progress summary
- `PIPELINE_PROGRESS_SUMMARY.md` - Pipeline development status
- `NLP_STAGE_INTEGRATION_COMPLETE.md` - NLP integration details

## 🔧 **DEVELOPMENT ENVIRONMENT**

### **Key Scripts & Tools**
- `invoke_pipeline_test.py` - Primary testing entry point
- `run_test_with_cleanup.py` - Cleanup + test workflow
- `simple_cleanup.py` - Database/OpenSearch cleanup
- `cdk/` - Infrastructure deployment

### **Environment Requirements**
- **Python**: 3.9+ (Lambda runtime)
- **AWS CLI**: Configured with SSO
- **CDK**: Node.js 18+ for infrastructure
- **Dependencies**: See `requirements.txt` and layer definitions

## 🎯 **CURRENT TECHNICAL STATE**

### **✅ WORKING COMPONENTS**
- Text extraction pipeline (Textract)
- Hierarchical chunking with semantic schema v3.1
- Vector embeddings with Bedrock Titan
- Keyword indexing with OpenSearch
- Document structure knowledge graph generation
- PostgreSQL metadata tracking
- Cleanup service for all components

### **🔄 IN PROGRESS**
- Pipeline test validation (3 documents processing)
- Vector embeddings compatibility verification
- NLP integration testing

### **⏳ PENDING**
- Neptune endpoint configuration for knowledge graph loading
- Production-scale testing and optimization
- Advanced search interface development

## 🚨 **ARCHITECTURAL DISCIPLINE REMINDERS**

### **Code Quality Standards**
- **No file variants**: Avoid `_updated.py`, `_fixed.py` patterns
- **Layer integrity**: Don't modify shared layers without approval
- **CDK patterns**: Follow established infrastructure patterns
- **Testing costs**: Always estimate costs before large test runs

### **Development Workflow**
1. **Planning**: Review architectural checklist
2. **Implementation**: Use existing patterns and layers
3. **Testing**: Start with `invoke_pipeline_test.py`
4. **Cleanup**: Remove temporary files and consolidate code
5. **Validation**: Confirm end-to-end pipeline functionality

## 📈 **SUCCESS METRICS**

### **Pipeline Performance**
- **Document Processing**: ~10-15 minutes per document end-to-end
- **Chunk Generation**: ~100-500 chunks per document
- **Vector Indexing**: ~3-5 minutes per document
- **Knowledge Graph**: ~746KB TTL per document (604 chunks)

### **Quality Indicators**
- **Schema Compliance**: Dublin Core + semantic relationships
- **Embedding Purity**: Text-only embeddings (no metadata contamination)
- **Search Accuracy**: Hybrid keyword + vector search capability
- **Infrastructure Integrity**: CDK deployment patterns maintained

---

**Last Updated**: 2025-07-29 16:28:20  
**Pipeline Status**: Active processing (3 documents)  
**Next Milestone**: Vector embeddings validation complete  
**Cost Status**: Within testing budget (<$5 current run)
