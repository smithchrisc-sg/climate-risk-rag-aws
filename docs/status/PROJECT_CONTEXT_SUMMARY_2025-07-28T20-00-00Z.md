# Climate Risk RAG System - Project Context Summary
## Date: 2025-07-28T20:00:00Z
## Status: Hierarchical Document Chunking and Semantic Schema Complete

## OVERVIEW

The Climate Risk RAG (Retrieval-Augmented Generation) system is a serverless, event-driven document processing pipeline on AWS that extracts, structures, and analyzes climate risk documents. The system has recently completed a major upgrade to hierarchical document chunking with semantic schema integration.

## CURRENT SYSTEM ARCHITECTURE

### Core Infrastructure (CDK)
- **Location**: `/cdk/` directory
- **Status**: Deployed and operational
- **Components**:
  - S3 buckets for document storage, text extraction, and chunks
  - Lambda functions for each processing stage
  - SNS topics for event-driven coordination
  - PostgreSQL database for metadata and processing status
  - OpenSearch for vector search capabilities
  - Neptune for knowledge graph storage

### Lambda Functions
- **Location**: `/lambda/` directory
- **Key Functions**:
  - `text-extractor-initiator`: Triggers Textract with LAYOUT analysis
  - `text-extractor-processor`: Processes Textract results with LAYOUT blocks
  - `text-chunker-processor`: **RECENTLY UPGRADED** with hierarchical chunker
  - `keyword-indexer`: Extracts keywords from chunks
  - `vector-embeddings-*`: Creates embeddings for chunks
  - `knowledge-graph`: Builds relationships between entities
  - `document-structure-kg-processor`: Maps document structure to RDF

### Shared Layers
- **Location**: `/lambda/shared_layer/` directory
- **Components**: Common utilities, database managers, and processing libraries

## RECENT MAJOR ACHIEVEMENTS

### 1. TEXTRACT LAYOUT ANALYSIS INTEGRATION
- **Status**: ✅ COMPLETE
- **Implementation**: Successfully integrated Textract LAYOUT feature
- **Benefits**: Enhanced document structure recognition with no additional cost
- **Files Updated**:
  - `lambda/text-extractor-initiator/src/text_extractor_initiator.py`
  - `lambda/text-extractor-processor/src/text_extractor_processor.py`
  - `lambda/text-chunker-processor/src/text_chunker_processor.py`

### 2. HIERARCHICAL LAYOUT-BASED CHUNKER
- **Status**: ✅ COMPLETE AND DEPLOYED
- **Implementation**: New `TextractLayoutChunker` class
- **Location**: `lambda/text-chunker-processor/src/textract_layout_chunker.py`
- **Key Features**:
  - Respects document tree structure from LAYOUT blocks
  - Creates parent-child chunk relationships
  - Sentence-based paragraph splitting with overlap
  - Clean section type boundaries (no mixed types)
  - Eliminates artificial context brackets
  - Fallback to legacy chunker if no LAYOUT blocks

### 3. SEMANTIC DOCUMENT STRUCTURE SCHEMA
- **Status**: ✅ COMPLETE
- **Location**: `docs/schema/document_structure_schema_v3.ttl`
- **Documentation**: `docs/schema/SEMANTIC_DOCUMENT_STRUCTURE_SCHEMA_EXPLANATION_2025-07-28.md`
- **Key Features**:
  - Semantic-first approach (what content means vs. how it's processed)
  - New namespaces: `sgd:` (semantic), `sgm:` (processing), `sgi:` (entities)
  - Tree-based relationships without explicit hierarchy levels
  - Direct mapping from chunker output to semantic classes
  - Clean separation of processing metadata

## CURRENT PROCESSING PIPELINE

### Document Flow
1. **Upload**: PDF documents uploaded to S3 source bucket
2. **Text Extraction**: Textract processes with LAYOUT analysis enabled
3. **Hierarchical Chunking**: New layout-based chunker creates semantic structure
4. **Keyword Indexing**: Keywords extracted from chunks
5. **Vector Embeddings**: Embeddings generated for semantic search
6. **Knowledge Graph**: Document structure and entities mapped to RDF

### Chunk Structure (NEW)
- **604 chunks** created from test document
- **5 hierarchy levels** with clean semantic boundaries
- **6 section types**: title, header, paragraph, list, table, figure
- **588 parent-child relationships** established
- **25 split paragraphs** with sentence overlap
- **Zero artificial context brackets** (clean text)

## TESTING AND VALIDATION

### Test Documents
- **Primary Test**: Document `064762102bead7b04a39` (World Bank financial sector report)
- **Secondary Test**: Document `00eb3286786882b6163b` (climate risk framework)
- **Test Scripts**:
  - `invoke_pipeline_test.py`: End-to-end pipeline testing
  - `analyze_hierarchical_success.py`: Chunk structure analysis
  - `review_chunks_for_rdf.py`: RDF design validation

### Validation Results
- ✅ Hierarchical structure properly maintained
- ✅ Clean section type boundaries (no mixed types)
- ✅ Parent-child relationships correctly established
- ✅ No artificial context injection
- ✅ Sentence-based paragraph splitting working
- ✅ LAYOUT block integration successful

## COST MANAGEMENT AND TESTING GUIDELINES

### ⚠️ CRITICAL: AWS SERVICE COSTS

#### Textract Costs
- **LAYOUT Analysis**: Included in base pricing (no additional cost)
- **Document Processing**: ~$1.50 per 1,000 pages
- **Testing Strategy**: Use small document sets, avoid repeated processing of same documents
- **Monitoring**: Check AWS Cost Explorer regularly during development

#### Future Cost Considerations
- **Amazon Comprehend**: ~$0.0001 per unit for entity extraction
- **Amazon Titan Embeddings**: ~$0.0001 per 1,000 input tokens
- **OpenSearch**: Ongoing cluster costs (~$50-200/month depending on size)
- **Neptune**: Ongoing cluster costs (~$100-300/month depending on size)

#### Cost Control Measures
1. **Use `invoke_pipeline_test.py`** with `--num-documents 1` for testing
2. **Avoid processing large document sets** during development
3. **Monitor S3 storage costs** - clean up test data regularly
4. **Use `--force` flag judiciously** - only when necessary
5. **Check CloudWatch logs** before assuming processing failed
6. **Implement processing limits** in production deployment

## KEY DIRECTORIES AND FILES

### Infrastructure
- `/cdk/`: AWS CDK infrastructure definitions
- `/lambda/`: All Lambda function code
- `/lambda/shared_layer/`: Common utilities and libraries

### Documentation
- `/docs/schema/`: RDF schema definitions and explanations
- `/docs/status/`: Project status and context documents
- `/docs/architecture_diagram.png`: System architecture overview
- `/README.md`: Project overview and getting started guide

### Testing and Scripts
- `invoke_pipeline_test.py`: Primary testing script
- `analyze_hierarchical_success.py`: Chunk analysis
- `review_chunks_for_rdf.py`: RDF structure analysis
- `deploy_hierarchical_chunker.py`: Deployment script
- `update_layout_lambdas.py`: Lambda update utility

### Configuration
- `requirements.txt`: Python dependencies
- `package.json`: Node.js dependencies for CDK
- Various `requirements.txt` files in Lambda directories

## WORK SUMMARY REFERENCES

### Previous Context Documents
- `PROJECT_CONTEXT.md`: Original project context and goals
- `NEXT_STEPS.md`: Previous next steps (may be outdated)
- Various timestamped status documents in `/docs/status/`

### Schema Evolution
- `docs/schema/document_structure_schema.ttl`: Original schema (v2.0)
- `docs/schema/document_structure_schema_v3.ttl`: Current semantic schema
- `docs/schema/DOCUMENT_STRUCTURE_SCHEMA_EXPLANATION_2025-07-09T22-30-00Z.md`: Original explanation
- `docs/schema/SEMANTIC_DOCUMENT_STRUCTURE_SCHEMA_EXPLANATION_2025-07-28.md`: Current explanation

## CURRENT SYSTEM STATUS

### ✅ COMPLETED COMPONENTS
- [x] Textract LAYOUT analysis integration
- [x] Hierarchical layout-based chunker
- [x] Semantic document structure schema
- [x] Tree-based chunk relationships
- [x] Processing metadata separation
- [x] Clean section type boundaries
- [x] Sentence-based paragraph splitting
- [x] S3 storage integration
- [x] Dublin Core metadata integration

### 🔄 IN PROGRESS
- Document structure KG processor updates (needs semantic schema integration)
- Entity extraction pipeline (Comprehend integration planned)
- Vector embeddings optimization for semantic chunks

### 📋 READY FOR NEXT PHASE
- NLP entity extraction with clean chunk anchoring
- Knowledge graph construction with semantic relationships
- Advanced querying capabilities with tree traversal
- Vector search optimization for semantic paragraphs

## DEVELOPMENT ENVIRONMENT

### Prerequisites
- AWS Account with appropriate permissions
- AWS CLI configured with SSO
- Python 3.11+
- Node.js 18+ (for CDK)
- Access to solve.global AWS organization

### Key Commands
```bash
# Deploy infrastructure
cdk deploy --all

# Run pipeline test (COST-CONSCIOUS)
python3 invoke_pipeline_test.py --action test --num-documents 1

# Update Lambda functions
python3 deploy_hierarchical_chunker.py

# Analyze results
python3 analyze_hierarchical_success.py
```

### Environment Variables
- Various S3 bucket names and ARNs configured in Lambda environment
- Database connection strings for PostgreSQL
- OpenSearch and Neptune cluster endpoints

## CRITICAL SUCCESS FACTORS

### Technical
1. **Semantic chunk structure** provides clean entity anchoring points
2. **Tree-based relationships** enable contextual entity extraction
3. **Processing metadata separation** keeps semantic queries clean
4. **LAYOUT analysis integration** improves structure recognition accuracy

### Operational
1. **Cost management** through careful testing and monitoring
2. **Incremental deployment** to avoid breaking existing functionality
3. **Comprehensive testing** with real-world documents
4. **Documentation maintenance** for knowledge continuity

## TEAM KNOWLEDGE TRANSFER

### Key Concepts to Understand
1. **Semantic vs. Processing**: Schema separates what content means from how it's processed
2. **Tree Structure**: Document hierarchy through parent-child relationships, not levels
3. **Chunk Mapping**: S3 chunks represent semantic elements (Section, Paragraph, Table)
4. **LAYOUT Integration**: Textract LAYOUT blocks provide document structure understanding
5. **Cost Awareness**: AWS services have significant costs that must be managed

### Critical Files to Review
1. `textract_layout_chunker.py`: Core hierarchical chunking logic
2. `document_structure_schema_v3.ttl`: Semantic schema definition
3. `invoke_pipeline_test.py`: Primary testing methodology
4. Architecture diagram and README for system overview

This context summary provides the foundation for continuing development of the Climate Risk RAG system with full understanding of current capabilities, recent achievements, and cost management requirements.
