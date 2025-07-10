# Climate Risk RAG System - Project Context Summary
## Complete System Overview and Current Status

**Document Date**: 2025-07-10T18:30:00Z  
**Project**: Climate Risk RAG AWS System  
**Phase**: Full System Development with NLP Integration  
**Status**: Core Infrastructure Complete, NLP Analysis Ready for Implementation  

---

## 📋 PROJECT OVERVIEW

### **System Purpose**
Comprehensive Retrieval-Augmented Generation (RAG) system for climate risk analysis using AWS services, featuring:
- **Document Processing Pipeline**: PDF/text extraction and chunking
- **Multi-Modal Search**: Keyword search + vector embeddings + knowledge graph
- **NLP Entity Extraction**: AWS Comprehend integration with RDF ontology mapping
- **Knowledge Graph**: Neptune-based semantic relationships
- **Cost-Optimized Architecture**: Strategic cost reduction opportunities identified

### **Current Architecture**
```
Document Upload → Text Extraction → Chunking → Multi-Path Processing:
├── Keyword Indexing (OpenSearch)
├── Vector Embeddings (OpenSearch + Bedrock)
├── NLP Processing (Comprehend → Entity Resolution → KG)
└── Knowledge Graph (Neptune)
```

---

## 🏗️ INFRASTRUCTURE STATUS

### **✅ COMPLETED COMPONENTS**

#### **Core AWS Infrastructure**
- **CDK Stacks**: Complete infrastructure as code
- **VPC & Networking**: Multi-AZ setup with proper security groups
- **S3 Data Lake**: Organized bucket structure for document storage
- **RDS PostgreSQL**: Document metadata and processing status
- **Neptune**: Knowledge graph database (configured)
- **OpenSearch Serverless**: Search and vector storage (cost-optimized)

#### **Document Processing Pipeline**
- **Text Extractor**: Multi-service approach (Textract, Tika, PyPDF2)
- **Text Chunker**: Intelligent chunking with overlap and metadata
- **Async Processing**: SNS/SQS-based workflow orchestration
- **Error Handling**: Comprehensive retry and fallback mechanisms

#### **Search Capabilities**
- **Keyword Indexing**: OpenSearch-based full-text search
- **Vector Embeddings**: Bedrock Titan integration for semantic search
- **Dual Search**: Parallel keyword and vector search with result fusion

#### **NLP Integration** (Analysis Complete)
- **AWS Comprehend**: Entity extraction and key phrase analysis
- **RDF Ontology Mapping**: Comprehensive schema for climate entities
- **Entity Resolution**: Design for KG integration ready

### **🔄 IN PROGRESS**
- **Knowledge Graph Population**: Neptune integration pending
- **Entity Linking**: NLP results to KG nodes (design complete)
- **Advanced Query Interface**: Multi-modal search orchestration

---

## 📁 CODEBASE STRUCTURE

### **CDK Infrastructure** (`/cdk/`)
```
cdk/
├── app.py                           # Main CDK application
├── stacks/
│   ├── data_stack.py               # OpenSearch, Neptune, RDS
│   ├── networking_stack.py         # VPC, security groups
│   ├── data_lake_stack.py          # S3 buckets and policies
│   └── ai_ml_stack.py              # Bedrock permissions
├── app_keyword_indexer.py          # Keyword search Lambda deployment
├── app_async_keyword_indexer.py    # Async keyword processing
├── app_vector_embeddings_pipeline.py # Vector processing pipeline
└── deploy_data_stack_only.py       # Standalone data stack deployment
```

### **Lambda Functions** (`/lambda/`)
```
lambda/
├── text_extractor/                 # PDF/document text extraction
├── text_chunker/                   # Intelligent text chunking
├── keyword_indexer/                # OpenSearch keyword indexing
├── keyword_indexer_worker/         # Async keyword processing
├── vector_embeddings_worker/       # Vector embedding generation
├── vector_embeddings_processor/    # Vector processing orchestration
├── nlp_worker/                     # NLP analysis (Comprehend)
├── nlp_processor/                  # NLP workflow orchestration
├── kg_searcher/                    # Knowledge graph queries
├── vector_searcher/                # Vector similarity search
├── query_handler/                  # Multi-modal query orchestration
└── shared_layer/                   # Common utilities and dependencies
```

### **Lambda Layers** (`/layers/`)
```
layers/
├── climate-risk-core-utilities/    # Database, S3, common utilities
├── database-dependencies/          # PostgreSQL drivers and ORM
├── opensearch-dependencies/        # OpenSearch client libraries
└── nlp-dependencies/               # NLP processing libraries
```

### **Documentation** (`/docs/`)
```
docs/
├── status/                         # Project status and context documents
├── analysis/                       # Technical analysis and decisions
├── cost-optimization/              # Cost reduction strategies and plans
├── knowledge-graph/                # KG design and RDF ontology mapping
└── architecture/                   # System design and diagrams
```

---

## 💰 COST OPTIMIZATION STATUS

### **✅ COMPLETED ANALYSIS**
- **Current Monthly Cost**: ~$674 (primarily OpenSearch Serverless)
- **Optimization Opportunity**: $534/month savings (79% reduction)
- **Strategy**: Migration from OpenSearch Serverless to Managed OpenSearch

### **📋 Cost Optimization Roadmap**
**Priority 1**: OpenSearch Migration ($534/month savings)
- **Status**: Ready for implementation after full functionality complete
- **Effort**: 16-24 hours
- **Risk**: Low (parallel deployment strategy)

**Priority 2**: RDS Right-sizing ($50-150/month potential savings)
**Priority 3**: Lambda Optimization ($20-50/month potential savings)

### **📊 Key Documents**
- `docs/cost-optimization/COST_OPTIMIZATION_ROADMAP.md`
- `docs/cost-optimization/OPENSEARCH_MIGRATION_GUIDE.md`
- `docs/analysis/OPENSEARCH_IMPLEMENTATION_COMPLETE_2025-07-10T04-20-00Z.md`

---

## 🧠 NLP & KNOWLEDGE GRAPH STATUS

### **✅ ANALYSIS COMPLETE**
- **AWS Comprehend Integration**: Entity extraction working
- **RDF Ontology Mapping**: Comprehensive schema design complete
- **Entity Types Supported**: Person, Organization, Location, Date, Quantity, Title
- **Ontology Stack**: FOAF, Schema.org, Dublin Core, SKOS, QUDT

### **🎯 Implementation Ready**
- **Entity Resolution Service**: Design complete with deduplication
- **KG Integration Pipeline**: Neptune integration architecture ready
- **Document Schema Migration**: Dublin Core refactoring planned

### **📊 Key Documents**
- `docs/knowledge-graph/NLP_ENTITY_RDF_SCHEMA_MAPPING.md`
- `docs/knowledge-graph/KG_ENTITY_INTEGRATION_GUIDE.md`
- `analyze_comprehend_entities.py` (analysis script)

---

## ⚠️ COST MANAGEMENT & TESTING GUIDELINES

### **🚨 CRITICAL: Expense Control for Testing**

#### **High-Cost Services Requiring Careful Testing**
1. **AWS Textract**
   - **Cost**: $1.50 per 1,000 pages
   - **Testing Strategy**: Use small document samples (1-5 pages max)
   - **Monitoring**: Track page count in CloudWatch
   - **Safeguard**: Implement document size limits in Lambda

2. **AWS Comprehend**
   - **Cost**: $0.0001 per 100 characters (entities + key phrases = $0.0002/100 chars)
   - **Testing Strategy**: Use short text samples (<1000 characters)
   - **Monitoring**: Character count logging before API calls
   - **Safeguard**: Text length validation and chunking

3. **Bedrock Titan Embeddings**
   - **Cost**: $0.0001 per 1,000 input tokens
   - **Testing Strategy**: Limit test documents to <10 chunks
   - **Monitoring**: Token count estimation before processing
   - **Safeguard**: Batch size limits and cost thresholds

4. **OpenSearch Serverless**
   - **Current Cost**: $674/month (always running)
   - **Testing Impact**: Minimal additional cost for queries
   - **Note**: Cost optimization planned (see roadmap above)

#### **Testing Best Practices**
```python
# Example cost-aware testing pattern
def test_with_cost_control(test_data):
    # Validate input size before processing
    if len(test_data) > MAX_TEST_SIZE:
        raise ValueError(f"Test data too large: {len(test_data)} > {MAX_TEST_SIZE}")
    
    # Log estimated cost
    estimated_cost = calculate_processing_cost(test_data)
    logger.info(f"Estimated test cost: ${estimated_cost:.4f}")
    
    if estimated_cost > COST_THRESHOLD:
        raise ValueError(f"Test cost too high: ${estimated_cost}")
    
    # Proceed with test
    return process_data(test_data)
```

#### **Cost Monitoring Setup**
- **CloudWatch Alarms**: Set for unusual spending patterns
- **Budget Alerts**: Monthly budget with 80% threshold alerts
- **Service-Specific Monitoring**: Track usage metrics for high-cost services
- **Test Environment Limits**: Separate test budgets and resource limits

---

## 📊 KEY WORK SUMMARY DOCUMENTS

### **Technical Analysis Documents**
- `docs/analysis/OPENSEARCH_IMPLEMENTATION_COMPLETE_2025-07-10T04-20-00Z.md`
  - OpenSearch cost optimization implementation results
  - Critical finding: Standby replicas cannot be disabled
  - System functionality verified and operational

- `docs/analysis/OPENSEARCH_COST_ANALYSIS_2025-07-09T21-45-00Z.md`
  - Detailed cost breakdown and optimization opportunities
  - Current spending analysis and projections

### **Architecture Decisions**
- `docs/architecture/TEXT_EXTRACTION_ANALYSIS_2025-07-08T20-30-00Z.md`
  - Multi-service text extraction strategy
  - Textract, Tika, PyPDF2 integration approach

### **Implementation Guides**
- `docs/cost-optimization/OPENSEARCH_MIGRATION_GUIDE.md`
  - Step-by-step migration from Serverless to Managed OpenSearch
  - 79% cost reduction implementation plan

- `docs/knowledge-graph/KG_ENTITY_INTEGRATION_GUIDE.md`
  - Technical implementation for NLP entity to KG integration
  - Lambda functions and database schema updates

---

## 🔧 DEVELOPMENT ENVIRONMENT

### **AWS Configuration**
- **Profile**: `solve-global`
- **Region**: `us-east-1`
- **Account**: `861276078413`

### **Key Environment Variables**
```bash
# Database
DATABASE_URL=postgresql://postgres:password@endpoint:5432/climate_risk_rag

# OpenSearch (Current - Cost Optimized)
OPENSEARCH_KEYWORD_ENDPOINT=https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com
OPENSEARCH_VECTOR_ENDPOINT=https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com

# S3 Buckets
TEXT_BUCKET=solve-global-kr-text-new-861276078413-us-east-1
DOCUMENTS_BUCKET=solve-global-kr-documents-861276078413-us-east-1
```

### **Deployment Commands**
```bash
# Deploy individual stacks
cdk deploy --app "python3 app_keyword_indexer.py" --profile solve-global
cdk deploy --app "python3 app_vector_embeddings_pipeline.py" --profile solve-global

# Deploy main infrastructure (has cyclic dependency issues - use individual apps)
# cdk deploy solve-global-kr-rag-data --profile solve-global
```

---

## 🎯 CURRENT SYSTEM CAPABILITIES

### **✅ WORKING FEATURES**
1. **Document Upload & Processing**
   - PDF text extraction (multi-service fallback)
   - Intelligent text chunking with metadata
   - S3 data lake storage with organized structure

2. **Search Capabilities**
   - **Keyword Search**: Full-text search via OpenSearch
   - **Vector Search**: Semantic similarity via Bedrock embeddings
   - **Dual Search**: Parallel search with result fusion

3. **NLP Processing**
   - **Entity Extraction**: AWS Comprehend integration
   - **Key Phrase Analysis**: Automated phrase extraction
   - **Offset Mapping**: Entities mapped to specific text chunks

4. **Data Management**
   - **PostgreSQL**: Document metadata and processing status
   - **S3 Data Lake**: Structured storage for all processing results
   - **Error Handling**: Comprehensive retry and fallback mechanisms

### **🔄 READY FOR IMPLEMENTATION**
1. **Knowledge Graph Integration**
   - Neptune database configured
   - RDF ontology mapping designed
   - Entity resolution architecture ready

2. **Cost Optimization**
   - OpenSearch migration plan ready
   - 79% cost reduction achievable
   - Implementation guide complete

---

## 🚨 KNOWN ISSUES & LIMITATIONS

### **Technical Limitations**
1. **OpenSearch Serverless**: Standby replicas cannot be disabled (AWS limitation)
2. **CDK Cyclic Dependencies**: Main app has dependency issues, use individual apps
3. **Vector Pipeline**: Database migration component has deployment issues (non-critical)

### **Cost Considerations**
1. **Current High Costs**: $674/month primarily from OpenSearch Serverless
2. **Testing Costs**: Must be careful with Textract, Comprehend, and Bedrock usage
3. **Optimization Pending**: Waiting for full functionality before cost optimization

### **Development Notes**
1. **Git Branch**: `feature/nlp-integration`
2. **IDE Files**: Added to .gitignore (Obsidian workspace files)
3. **Testing**: Use small samples to avoid excessive charges

---

## 🔄 INTEGRATION STATUS

### **Service Integration Matrix**
| Service | Status | Integration | Notes |
|---------|--------|-------------|-------|
| **S3** | ✅ Complete | Data lake storage | Multi-bucket organization |
| **RDS** | ✅ Complete | Metadata storage | PostgreSQL with proper schema |
| **OpenSearch** | ✅ Complete | Search indexing | Cost-optimized collections |
| **Bedrock** | ✅ Complete | Vector embeddings | Titan model integration |
| **Comprehend** | ✅ Complete | NLP analysis | Entity extraction working |
| **Neptune** | 🔄 Configured | Knowledge graph | Ready for entity integration |
| **Textract** | ✅ Complete | PDF processing | Cost-aware implementation |
| **SNS/SQS** | ✅ Complete | Async messaging | Workflow orchestration |

---

## 📈 PERFORMANCE METRICS

### **Current System Performance**
- **Text Extraction**: ~30-60 seconds per document
- **Chunking**: ~5-10 seconds per document
- **Keyword Indexing**: ~10-20 seconds per document
- **Vector Embeddings**: ~30-60 seconds per document
- **NLP Processing**: ~15-30 seconds per document

### **Scalability Targets**
- **Throughput**: 100+ documents per hour
- **Search Latency**: <500ms for keyword search
- **Vector Search**: <1000ms for semantic search
- **Entity Resolution**: <200ms per entity

---

## 🎯 SYSTEM READINESS ASSESSMENT

### **✅ PRODUCTION READY COMPONENTS**
- Document processing pipeline
- Keyword and vector search
- NLP entity extraction
- Data lake storage and organization
- Error handling and monitoring

### **🔄 IMPLEMENTATION READY**
- Knowledge graph entity integration
- Cost optimization (OpenSearch migration)
- Advanced query orchestration
- Entity-based search capabilities

### **📋 PENDING DEVELOPMENT**
- User interface for document upload and search
- Advanced analytics and reporting
- Real-time processing capabilities
- Multi-tenant support

---

## 🔍 CONTEXT FOR NEW CONVERSATIONS

### **Essential Information**
1. **Project Goal**: Climate risk RAG system with multi-modal search
2. **Current Phase**: Core functionality complete, KG integration ready
3. **Architecture**: AWS-native with cost optimization focus
4. **Key Challenge**: Balance functionality with cost management
5. **Next Priority**: Complete KG integration, then cost optimization

### **Important Constraints**
1. **Cost Management**: Careful testing required for expensive services
2. **AWS Account**: solve-global profile, us-east-1 region
3. **Development Approach**: Infrastructure-first, then optimization
4. **Quality Focus**: Comprehensive error handling and monitoring

### **Success Criteria**
1. **Functional**: Multi-modal search working across all content types
2. **Performance**: Sub-second search response times
3. **Cost**: <$200/month operational costs after optimization
4. **Quality**: >90% accuracy in entity extraction and search relevance

This context summary provides complete information needed to continue development from any point in the project lifecycle.
