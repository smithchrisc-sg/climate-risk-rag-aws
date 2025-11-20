# PROJECT CONTEXT SUMMARY
**Updated:** 2025-11-20T21:46:00Z  
**Branch:** feature/climate-risk-ontology-filtering  
**Status:** API response fields completed, UX enhancements deployed, country filter bug fixed

## PROJECT OVERVIEW
Climate Risk RAG (Retrieval-Augmented Generation) system providing intelligent search over climate risk solutions and trusted source documents (TSDs) using hybrid search combining keyword (BM25), vector (semantic), and knowledge graph filtering with comprehensive API response fields.

## CURRENT ARCHITECTURE

### Core Components
- **Knowledge Graph**: Neptune with climate risk ontology, solution metadata, and organization classifications
- **Search Indices**: OpenSearch with `documents_keyword` (BM25) and `chunks_vector` (semantic) indices
- **Vector Embeddings**: Bedrock Titan (`amazon.titan-embed-text-v1`) for semantic search
- **API Gateway**: RESTful search API with comprehensive solution metadata
- **Frontend**: React webapp with advanced filtering, status indicators, and enhanced UX
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
2. **Text Extraction**: Textract for PDF text extraction with hash-based deduplication
3. **NLP Processing**: Offset mapping and entity extraction
4. **Keyword Indexing**: OpenSearch BM25 index with content_type field
5. **Vector Embeddings**: Bedrock Titan embeddings for semantic search
6. **Knowledge Graph**: Triple extraction and Neptune loading with organization analysis

## DIRECTORY STRUCTURE

### `/cdk/`
- Infrastructure as Code using AWS CDK
- Stacks for Neptune, OpenSearch, Lambda layers, API Gateway
- **Key files**: `app.py`, `stacks/` directory with component stacks
- **Status**: Operational with managed OpenSearch (94% cost savings vs Serverless)

### `/lambda/`
- **`/search/`**: Main search Lambda function with hybrid search and comprehensive API responses
  - `src/search/coordinator.py`: Main search orchestration
  - `src/search/bm25_search_service.py`: Keyword search service
  - `src/search/vector_search_service.py`: Semantic search with Titan
  - `src/search/ranking_engine.py`: RRF fusion implementation
  - `src/search/solution_searcher.py`: Knowledge graph integration with full API fields
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
- **`database-core-layer/`**: v18 - Core database utilities with DatabaseManager
- **`knowledge-graph-layer/`**: v63 - Neptune and SPARQL operations with bulk loading

### `/solution_ingestion/`
- Document processing pipeline for ingesting climate risk solutions and TSDs
- **`process_manifest_pipeline.py`**: Batch document processing with skip flags
- **`TODO_DATA_FIXES.md`**: Data quality issues tracker and implementation status

### `/trusted_source_document_selection/`
- TSD manifest files and processing scripts
- **`wb_natcat_tsd_manifest_lexical.jsonl`**: 477 World Bank natural catastrophe TSDs
- **`estimate_page_counts.py`**: Page count estimation for cost planning
- **`test_tsd_opensearch.sh`**: OpenSearch searchability testing script

### `/test-v2-webapp/`
- React frontend application with enhanced UX
- **`app.js`**: Main application with search interface, status indicators, and comprehensive display
- **`index.html`**: HTML structure and styling
- **`styles.css`**: Enhanced CSS with status indicators and responsive design

### `/docs/`
- **`/status/`**: Project status documents and context summaries
- **`/infrastructure/`**: Architecture and deployment guides
- **`/api/`**: API specifications and system architecture

## CURRENT IMPLEMENTATION STATUS

### ✅ COMPLETED (2025-11-20 Session)
- **Country Filter Bug Fix**: Corrected GeoNames URI format from ontology# to sws.geonames.org format
  - Fixed SPARQL query in solution_searcher.py for proper country filtering
  - Ensures frontend country filters work correctly with knowledge graph
- **PPP Involvement Field**: SPARQL-based detection of Public/International + Private organization partnerships
  - Returns "yes" for 60% of solutions, "no" for 39%, "unknown" for 1%
  - Uses organization type analysis from Neptune knowledge graph
- **Last Update Date Field**: ISO8601 formatted dates from knowledge graph `dcterms:created`
  - Handles DD/MM/YYYY format conversion to YYYY-MM-DD
  - Graceful handling of missing data with null values
- **Key Highlights Field**: Array of individual highlight strings from S3 chunks
  - SPARQL queries find "Key Highlights" sections in document structure
  - Each highlight chunk becomes separate string in array (not concatenated)
  - Handles both main search and individual solution retrieval paths
- **Implementation Status Field**: Boolean determination based on publication date vs current year
  - Uses `sg:implementationYear` field from knowledge graph
  - Returns true if implementation year <= current year
- **Enhanced UX**: Comprehensive webapp improvements
  - Status indicators with color-coded checkmarks (✅), X marks (❌), and question marks (❓)
  - Three-column expanded view: Risk Types | Solution Types | Key Highlights
  - Responsive design for mobile devices
  - Last Updated date display in main solution panel

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
- **Related Documents Feature**: Hybrid BM25 + Vector search for TSDs related to solutions
- **TSD Content Type**: Added `content_type` field to differentiate TSDs from solutions
- **TSD Metadata Integration**: Database lookups for title, source_url, and source_name

### 🔄 IN PROGRESS
- **TSD Bulk Loading**: 477 World Bank natural catastrophe documents ready for processing
- **Cost Optimization**: Monitoring and optimization of expensive services

### 📋 PENDING
- **OpenSearch Highlights Optimization**: Investigate why content field highlighting is slow
- **Pre-computed Summaries**: Generate summaries during indexing phase
- **Query Expansion**: Synonym handling and related term expansion
- **Search Analytics**: Track query patterns, success rates, user engagement

## TECHNICAL DETAILS

### Search Indices
- **documents_keyword**: BM25 search with `content_type` field ('solution' or 'trusted_source_document')
- **chunks_vector**: Vector search with 1536-dimension Titan embeddings and `content_type` field
- **Field mappings**: `doc_id` for intersection, `vector` field for KNN search, `text` for chunk content

### Knowledge Graph Schema
- **Solutions**: `sgd:Solution` with comprehensive metadata and organization relationships
- **Organizations**: 1,039 public, 344 private, 270 international organizations with type classifications
- **Risk Types**: Mapped to human-readable labels via `rdfs:label`
- **Countries**: GeoNames integration for country name resolution
- **Solution Types**: Categorized solution approaches with label mapping

### Database Schema
- **documents**: doc_id, source_url, title, file_hash, content_type, timestamps
- **document_processing_status**: Processing stage tracking with metadata
- **document_processing_audit**: Audit trail for all processing events

### API Response Format (Enhanced)
```json
{
  "status": "success",
  "total_results": 150,
  "results": {
    "solutions": [{
      "solution_id": "sol_abc123",
      "title": "Solution Title",
      "relevance_score": 0.8542,
      "implemented": true,
      "ppp_involvement": "yes",
      "last_update_date": "2025-04-22",
      "risk_types_addressed": ["Climate Risk"],
      "solution_types": ["Risk Reduction"],
      "country_regions_covered": ["Thailand"],
      "key_highlights": [
        "Automated payouts within 48 hours",
        "Covers 50,000+ smallholder farmers"
      ],
      "related_documents": [{
        "doc_id": "tsd_456",
        "title": "World Bank Climate Report 2024",
        "summary": "Best matching chunk text...",
        "rank": 1,
        "source_name": "World Bank",
        "content_type": "trusted_source_document"
      }]
    }]
  }
}
```

## 🚨 COST MANAGEMENT & TESTING PRECAUTIONS

### **EXPENSIVE SERVICES - USE CAREFULLY**
- **Amazon Textract**: $0.065 per page - 477 TSDs = ~38,000 pages = ~$2,470 if all new
  - **Deduplication critical**: Hash-based system saves $20+ per duplicate document
  - **Test with small batches**: Use `--limit 1` flag for single document tests
  - **Page count estimation**: Use `estimate_page_counts.py` before bulk processing
  - **Monitor processing status**: Check database before reprocessing documents
- **Bedrock Titan Embeddings**: $0.0001 per 1K tokens - can add up with large queries
  - **Cache embeddings**: Avoid regenerating for same queries
  - **Limit test queries**: Use filter-only searches when testing non-search functionality
  - **Monitor usage**: Track embedding generation costs during development
- **Amazon Comprehend**: NLP processing costs when implemented - monitor usage
- **OpenSearch**: Instance hours and storage - current managed setup ~$170/month (vs $1,500+ serverless)
- **Neptune**: Graph database instance costs - optimize SPARQL queries
  - **Current**: db.r5.large for normal operations
  - **Temporary upgrades**: Use larger instances only for bulk loading operations

### Testing Best Practices
- **Always start small**: Use `--limit 1` for single document tests
- **Use dry-run flags**: Test processing logic before actual execution
- **Monitor CloudWatch costs** regularly during development
- **Check deduplication** before processing to avoid duplicate costs
- **Batch processing**: 5 documents per batch with 120s delays for stability
- **Verify existing data**: Check database and indices before reprocessing
- **Cost estimation**: Run page count estimates before bulk Textract operations

### Cost Monitoring Commands
```bash
# Check document processing status before reprocessing
SELECT COUNT(*) FROM document_processing_status 
WHERE stage = 'textract_complete' AND status = 'completed';

# Estimate Textract costs before processing
python3 estimate_page_counts.py --manifest wb_natcat_tsd_manifest_lexical.jsonl

# Test with minimal documents
python3 process_manifest_pipeline.py --limit 1 --dry-run
```

## CURRENT SYSTEM STATUS

| **Component** | **Status** | **Version/Config** | **Notes** |
|---------------|------------|-------------------|-----------|
| **API Response Fields** | ✅ Complete | All 4 TODO fields | PPP, Last Update, Key Highlights, Implementation Status |
| **UX Enhancements** | ✅ Deployed | Enhanced webapp | Status indicators, 3-column layout, responsive design |
| **Knowledge Graph Layer** | ✅ Operational | v63 (bulk loading) | Fixed rdflib imports, organization analysis |
| **OpenSearch** | ✅ Operational | Managed 2.19.0 | 94% cost savings vs Serverless |
| **Neptune** | ✅ Operational | Organization data loaded | 1,653 organizations with type classifications |
| **Pipeline** | ✅ Operational | End-to-end tested | Deduplication working, content type differentiation |
| **Related Documents** | ✅ Operational | Hybrid search | TSD retrieval with metadata integration |

### Total Resource Count (Current)
- **Lambda Functions**: 15+ active with enhanced functionality
- **S3 Buckets**: 7 core buckets for processing pipeline
- **Databases**: 3 (OpenSearch, Neptune, RDS)
- **Lambda Layers**: 4 (KG, Database, OpenSearch, Database Dependencies)
- **Security Groups**: 4 with proper VPC configuration
- **API Endpoints**: Enhanced search with comprehensive response fields

## KEY REFERENCE DOCUMENTS
- **Architecture**: `/docs/infrastructure/INFRASTRUCTURE_STACKS_GUIDE.md`
- **API Spec**: `/docs/api/solve-global-gaip-kr-api-DRAFT-v1.yaml`
- **Production Readiness**: `/docs/status/PRODUCTION_READINESS_IMPROVEMENTS_2025-09-24.md`
- **Database Queries**: `/docs/DATABASE_QUERIES_REFERENCE.md`
- **TODO Data Fixes**: `/solution_ingestion/TODO_DATA_FIXES.md`
- **SPARQL Reference**: `/docs/status/SPARQL_QUERIES_REFERENCE_2025-09-15.md`
- **Codebase Reference**: `/docs/CODEBASE_REFERENCE.md`

## DEVELOPMENT WORKFLOW
1. **Feature branches** from `feature/climate-risk-ontology-filtering`
2. **Specific git adds**: `git add lambda/search test-v2-webapp` (avoid timeouts)
3. **Lambda deployment**: Create zip, update function code via AWS CLI
4. **Testing**: Use webapp at CloudFront distribution URL (E1X7VBE3EV1C5K)
5. **Monitoring**: CloudWatch logs for debugging search pipeline
6. **Database queries**: Use PostgreSQL client or DatabaseManager utility
7. **Cost awareness**: Always estimate costs before bulk operations

## CURRENT BRANCH STATUS
- **Branch**: `feature/climate-risk-ontology-filtering`
- **Commits ahead**: 10+ commits with complete API field implementation and UX enhancements
- **Last major commits**: 
  - PPP involvement and last update date fields (2025-11-20)
  - Key highlights field extraction (2025-11-20)
  - Enhanced webapp UX with status indicators (2025-11-20)
- **Ready for**: TSD bulk loading, production deployment preparation, or additional feature development

## KNOWN ISSUES & LIMITATIONS
1. **OpenSearch Highlights**: Content field highlighting causes 15x performance degradation
   - **Workaround**: Using vector chunk text for summaries instead
   - **Investigation needed**: Check content field mapping and analyzer configuration
2. **TSD Processing**: 477 World Bank documents ready for bulk loading
   - **Cost consideration**: ~$2,470 for Textract processing
   - **Deduplication**: Critical to avoid reprocessing costs
3. **Database Integration**: Solutions not fully integrated with PostgreSQL documents table
   - **Current**: Using knowledge graph for metadata
   - **Future**: Full database integration for production

## TESTING & VALIDATION
- **API Fields**: All 4 TODO fields working correctly with proper data types
- **UX Enhancement**: Status indicators and responsive design validated
- **TSD Searchability**: Verified with content_type filter working
- **Related Documents**: Tested with World Bank natural catastrophe TSDs
- **Performance**: Search latency maintained with enhanced functionality
- **Cost Management**: Deduplication system preventing duplicate processing costs

## NEXT CONVERSATION STARTUP
To continue development:
1. Reference this document for full context
2. Check `/docs/status/NEXT_STEPS_2025-11-20.md` for planned work
3. Review recent commits for implementation details
4. **Monitor costs** before running extensive tests (especially Textract)
5. Use existing search logs to debug any issues
6. Check TODO_DATA_FIXES.md for outstanding data issues
7. Consider production readiness checklist items

## SESSION SUMMARY (2025-11-20)
- **Focus**: Complete API response field implementation and UX enhancements
- **Key Achievements**: 
  - PPP involvement detection using SPARQL organization analysis
  - Last update date formatting from knowledge graph
  - Key highlights extraction as individual strings
  - Comprehensive UX with status indicators and responsive design
  - Country filter bug fix for proper GeoNames URI format
- **Technical Debt Addressed**: All 4 TODO API fields now complete
- **Cost Awareness**: Maintained throughout session with careful testing approaches
- **Next Priority**: TSD bulk loading or production deployment preparation
