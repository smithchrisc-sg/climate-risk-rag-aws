# PROJECT CONTEXT SUMMARY
**Updated:** 2025-11-19T19:22:00Z  
**Branch:** feature/climate-risk-ontology-filtering  
**Status:** Related documents feature implemented, TSD indexing validated

## PROJECT OVERVIEW
Climate Risk RAG (Retrieval-Augmented Generation) system providing intelligent search over climate risk solutions and trusted source documents (TSDs) using hybrid search combining keyword (BM25), vector (semantic), and knowledge graph filtering.

## CURRENT ARCHITECTURE

### Core Components
- **Knowledge Graph**: Neptune with climate risk ontology and solution metadata
- **Search Indices**: OpenSearch with `documents_keyword` (BM25) and `chunks_vector` (semantic) indices
- **Vector Embeddings**: Bedrock Titan (`amazon.titan-embed-text-v1`) for semantic search
- **API Gateway**: RESTful search API with Cognito authentication
- **Frontend**: React webapp with advanced filtering, pagination, and related documents display
- **Database**: PostgreSQL for document metadata, processing status, and audit trails

### Search Pipeline (Hybrid)
1. **Query Processing**: Tokenization, stop word filtering, strategy routing
2. **Knowledge Graph Filtering**: SPARQL queries for solution universe with filters
3. **BM25 Search**: Keyword search with field boosting (title^3, content^2, full_text^1)
4. **Vector Search**: Semantic search using Titan embeddings with KNN
5. **RRF Fusion**: Reciprocal Rank Fusion combining BM25 + Vector rankings
6. **3-way Intersection**: KG ∩ BM25 ∩ Vector for final results
7. **Session Management**: S3-cached paginated results with RRF scores
8. **Related Documents**: Hybrid search for TSDs related to each solution

### Document Processing Pipeline
1. **S3 Upload**: Documents uploaded to processing bucket
2. **Text Extraction**: Textract for PDF text extraction
3. **Deduplication**: Hash-based duplicate detection to avoid reprocessing
4. **NLP Processing**: Offset mapping and entity extraction
5. **Keyword Indexing**: OpenSearch BM25 index with content_type field
6. **Vector Embeddings**: Bedrock Titan embeddings for semantic search
7. **Knowledge Graph**: Triple extraction and Neptune loading

## DIRECTORY STRUCTURE

### `/cdk/`
- Infrastructure as Code using AWS CDK
- Stacks for Neptune, OpenSearch, Lambda layers, API Gateway
- **Key files**: `app.py`, `stacks/` directory with component stacks

### `/lambda/`
- **`/search/`**: Main search Lambda function with hybrid search and related documents
  - `src/search/coordinator.py`: Main search orchestration
  - `src/search/bm25_search_service.py`: Keyword search service
  - `src/search/vector_search_service.py`: Semantic search with Titan
  - `src/search/ranking_engine.py`: RRF fusion implementation
  - `src/search/solution_searcher.py`: Knowledge graph integration
  - `src/search/session_manager.py`: S3-based result caching
  - `src/search/related_documents_service.py`: TSD retrieval for solutions
  - `src/search/postgres.py`: Database access utility
- **`/keyword-indexer/`**: OpenSearch BM25 indexing with content_type differentiation
- **`/vector-embeddings-worker/`**: Bedrock Titan embedding generation
- **`/text-extractor-initiator/`**: Textract job initiation with deduplication
- **`/text-extractor-processor/`**: Textract result processing
- **Other Lambda functions**: NLP processing, KG triple loading, etc.

### `/layers/`
- Shared Lambda layers for database connectivity, knowledge graph operations
- **`database-core-layer/`**: Core database utilities with DatabaseManager
- **`knowledge-graph-layer/`**: Neptune and SPARQL operations

### `/solution_ingestion/`
- Document processing pipeline for ingesting climate risk solutions and TSDs
- **`process_manifest_pipeline.py`**: Batch document processing with skip flags
- **`generators/embeddings_generator.py`**: Titan embedding generation (reference)

### `/trusted_source_document_selection/`
- TSD manifest files and processing scripts
- **`wb_natcat_tsd_manifest_lexical.jsonl`**: 477 World Bank natural catastrophe TSDs
- **`estimate_page_counts.py`**: Page count estimation for cost planning
- **`test_tsd_opensearch.sh`**: OpenSearch searchability testing script

### `/test-v2-webapp/`
- React frontend application
- **`app.js`**: Main application with search interface, filtering, and related documents display
- **`index.html`**: HTML structure and styling

### `/docs/`
- **`/status/`**: Project status documents and context summaries
- **`/infrastructure/`**: Architecture and deployment guides
- **`/api/`**: API specifications and system architecture

## CURRENT IMPLEMENTATION STATUS

### ✅ COMPLETED (2025-11-19)
- **Related Documents Feature**: Hybrid BM25 + Vector search for TSDs related to solutions
- **TSD Content Type**: Added `content_type` field to differentiate TSDs from solutions
- **TSD Metadata Integration**: Database lookups for title, source_url, and source_name
- **Vector Chunk Summaries**: Use best matching chunk text instead of document truncation
- **TSD Searchability Validation**: Verified 228 TSDs indexed, 13 test TSDs processed successfully
- **Performance Optimization**: Removed OpenSearch highlights (15x slowdown), optimized queries
- **Keyword Indexer Fix**: Fixed syntax error and deployed content_type determination
- **Webapp Enhancement**: Display source name (World Bank, IMF) and rank for related docs
- **Bulk Update Script**: Manual OpenSearch update for content_type field on existing TSDs

### ✅ COMPLETED (Previous Sessions)
- **Full Hybrid Search**: BM25 + Vector + Knowledge Graph filtering
- **RRF Fusion**: Reciprocal Rank Fusion with k=60 for ranking combination
- **Vector Search**: Bedrock Titan integration with proper field mapping
- **3-way Intersection**: Proper doc_id handling between search systems
- **Session Management**: S3-cached results with RRF score persistence
- **Enhanced API**: Country names, risk type labels, solution type labels
- **Relevance Scoring**: RRF-based scores replacing position-based scoring
- **Query Processing**: Smart routing between filter-only and hybrid search
- **Graceful Fallbacks**: BM25-only when vector fails, filter-only when both fail
- **Deduplication System**: Hash-based duplicate detection to avoid reprocessing
- **Pipeline Fixes**: 8 critical fixes including timeout resolution, authentication, content type

### 🔄 IN PROGRESS
- **TSD Bulk Loading**: 477 World Bank natural catastrophe documents ready for processing
- **Summary Generation**: Investigating better summary methods (LLM or highlights optimization)

### 📋 PENDING
- **OpenSearch Highlights Optimization**: Investigate why content field highlighting is slow
- **Pre-computed Summaries**: Generate summaries during indexing phase
- **Query Expansion**: Synonym handling and related term expansion
- **Search Analytics**: Track query patterns, success rates, user engagement
- **A/B Testing Framework**: Test different ranking algorithms and UI changes

## TECHNICAL DETAILS

### Search Indices
- **documents_keyword**: BM25 search with `content_type` field ('solution' or 'trusted_source_document')
- **chunks_vector**: Vector search with 1536-dimension Titan embeddings and `content_type` field
- **Field mappings**: `doc_id` for intersection, `vector` field for KNN search, `text` for chunk content

### Knowledge Graph Schema
- **Solutions**: `sgd:Solution` with `dcterms:identifier` for doc_id extraction
- **Risk Types**: Mapped to human-readable labels via `rdfs:label`
- **Countries**: GeoNames integration for country name resolution
- **Solution Types**: Categorized solution approaches with label mapping

### Database Schema
- **documents**: doc_id, source_url, title, file_hash, content_type, timestamps
- **document_processing_status**: Processing stage tracking with metadata
- **document_processing_audit**: Audit trail for all processing events

### API Response Format
```json
{
  "status": "success",
  "total_results": 150,
  "results": {
    "solutions": [{
      "solution_id": "sol_abc123",
      "title": "Solution Title",
      "relevance_score": 0.8542,
      "risk_types": ["Climate Risk"],
      "countries": ["Thailand"],
      "related_documents": [{
        "doc_id": "tsd_456",
        "title": "World Bank Climate Report 2024",
        "summary": "Best matching chunk text...",
        "rank": 1,
        "source_url": "https://documents.worldbank.org/...",
        "source_name": "World Bank",
        "content_type": "trusted_source_document"
      }]
    }]
  }
}
```

## COST MANAGEMENT & TESTING PRECAUTIONS

### 🚨 EXPENSIVE SERVICES - USE CAREFULLY
- **Amazon Textract**: $0.065 per page - 477 TSDs = ~38,000 pages = ~$2,470 if all new
  - **Deduplication critical**: Saves $20+ per duplicate document
  - **Test with small batches**: Use `--limit 1` flag for single document tests
  - **Page count estimation**: Use `estimate_page_counts.py` before bulk processing
- **Bedrock Titan Embeddings**: $0.0001 per 1K tokens - can add up with large queries
  - **Cache embeddings**: Avoid regenerating for same queries
  - **Limit test queries**: Use filter-only searches when testing non-search functionality
- **Amazon Comprehend**: NLP processing costs - monitor usage in development
- **OpenSearch**: Instance hours and storage - use appropriate instance sizes
  - **Current**: Single node for development, will need cluster for production
- **Neptune**: Graph database instance costs - optimize SPARQL queries
  - **Temporary upgrade**: db.r5.2xlarge for bulk loading week (~$235 cost)

### Testing Best Practices
- **Limit query frequency** during development to avoid embedding costs
- **Use small document sets** for Textract testing (1-3 documents)
- **Monitor CloudWatch costs** regularly during development
- **Use `--dry-run` flag** before running batch processing
- **Check deduplication** before processing to avoid duplicate costs
- **Batch processing**: 5 documents per batch with 120s delays for stability

## COST ESTIMATES (Current Session)
- **TSD Processing**: 477 documents, 38,006 pages
  - Textract: $2,470 (if all new), $1,235 (if 50% duplicates)
  - Bedrock embeddings: ~$50-100 for all chunks
  - Total estimated: ~$2,520-2,570 for full batch
- **Neptune Upgrade**: db.r5.2xlarge for bulk loading week = $235
- **Related Documents**: Minimal cost, uses existing search infrastructure

## KEY REFERENCE DOCUMENTS
- **Architecture**: `/docs/infrastructure/INFRASTRUCTURE_STACKS_GUIDE.md`
- **API Spec**: `/docs/api/solve-global-gaip-kr-api-DRAFT-v1.yaml`
- **Production Readiness**: `/docs/status/PRODUCTION_READINESS_IMPROVEMENTS_2025-09-24.md`
- **Search Enhancements**: `/docs/SEARCH_ENHANCEMENTS_DATA_2025-11-13T21-34-47Z.md`
- **Related Documents Plan**: `/docs/RELATED_DOCUMENTS_IMPLEMENTATION_PLAN_2025-11-15.md`
- **Database Queries**: `/docs/DATABASE_QUERIES_REFERENCE.md`
- **Scripts Inventory**: `/SCRIPTS_INVENTORY.md`
- **TODO Data Fixes**: `/solution_ingestion/TODO_DATA_FIXES.md`

## DEVELOPMENT WORKFLOW
1. **Feature branches** from `feature/climate-risk-ontology-filtering`
2. **Specific git adds**: `git add lambda/search test-v2-webapp` (avoid timeouts)
3. **Lambda deployment**: Create zip, update function code via AWS CLI
4. **Testing**: Use webapp at CloudFront distribution URL (E1X7VBE3EV1C5K)
5. **Monitoring**: CloudWatch logs for debugging search pipeline
6. **Database queries**: Use PostgreSQL client or DatabaseManager utility

## CURRENT BRANCH STATUS
- **Branch**: `feature/climate-risk-ontology-filtering`
- **Commits ahead**: 8 commits with hybrid search and related documents implementation
- **Last major commit**: Related documents feature with TSD metadata (2025-11-19)
- **Ready for**: TSD bulk loading or summary generation optimization

## KNOWN ISSUES & LIMITATIONS
1. **OpenSearch Highlights**: Content field highlighting causes 15x performance degradation
   - **Workaround**: Using vector chunk text for summaries instead
   - **Investigation needed**: Check content field mapping and analyzer configuration
2. **TSD Titles**: Some TSDs indexed with "Document {doc_id}" instead of actual title
   - **Cause**: Title not in metadata during indexing
   - **Solution**: Database lookup retrieves actual title from documents table
3. **Content Type Migration**: 228 old TSDs had null content_type, manually updated
   - **Prevention**: Keyword-indexer now sets content_type during indexing
4. **Summary Quality**: First 200 chars or chunk text may not be ideal
   - **Future**: Pre-compute summaries or use LLM generation

## TESTING & VALIDATION
- **TSD Searchability**: Verified 228 TSDs indexed with content_type filter working
- **Related Documents**: Tested with 13 World Bank natural catastrophe TSDs
- **Performance**: BM25 search ~140ms, vector search ~200ms, no highlights
- **Database Integration**: PostgresProcessor successfully retrieves title and source_url
- **Webapp Display**: Source names (World Bank, IMF) and ranks displaying correctly

## NEXT CONVERSATION STARTUP
To continue development:
1. Reference this document for full context
2. Check `/docs/status/NEXT_STEPS_2025-11-19.md` for planned work
3. Review recent commits for implementation details
4. Monitor costs before running extensive tests
5. Use existing search logs to debug any issues
6. Check TODO_DATA_FIXES.md for outstanding data issues

## SESSION SUMMARY (2025-11-19)
- **Focus**: TSD searchability validation and related documents feature completion
- **Key Achievement**: End-to-end related documents working with proper metadata
- **Challenges Overcome**: OpenSearch highlights performance, content_type migration
- **Cost Awareness**: Estimated $2,470 for 477 TSD batch, deduplication critical
- **Next Priority**: TSD bulk loading or summary generation optimization
