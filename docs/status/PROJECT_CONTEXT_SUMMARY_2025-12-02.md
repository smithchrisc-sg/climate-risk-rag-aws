# PROJECT CONTEXT SUMMARY
**Updated:** 2025-12-02T17:10:00Z  
**Branch:** feature/climate-risk-ontology-filtering  
**Status:** Phase 2 Ontology Migration Complete - Search using new predicates

## PROJECT OVERVIEW
Climate Risk RAG (Retrieval-Augmented Generation) system providing intelligent search over climate risk solutions and trusted source documents (TSDs) using hybrid search combining keyword (BM25), vector (semantic), and knowledge graph filtering with hierarchical ontology-based filtering.

## CURRENT ARCHITECTURE

### Core Components
- **Knowledge Graph**: Neptune with NEW ontology predicates (`sg:addressesRisk`, `sg:providesMechanism`, `sg:hasImpact`)
- **Search Indices**: OpenSearch with `documents_keyword` (BM25) and `chunks_vector` (semantic) indices
- **Vector Embeddings**: Bedrock Titan (`amazon.titan-embed-text-v1`) for semantic search
- **API Gateway**: RESTful search API with comprehensive solution metadata and repository endpoints
- **Frontend**: React webapp with advanced filtering, status indicators, enhanced UX, and repository testing
- **Database**: PostgreSQL for document metadata, processing status, and audit trails

### Search Pipeline (Hybrid)
1. **Query Processing**: Tokenization, stop word filtering, strategy routing
2. **Knowledge Graph Filtering**: SPARQL queries with hierarchical filtering using `rdfs:subClassOf+`
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
- **⚠️ IMPORTANT**: CDK may not match deployed API Gateway configuration (manual OPTIONS methods added)

### `/lambda/`
- **`/search/`**: Main search Lambda function with NEW ontology predicates
  - `handler.py`: Main entry point with repository endpoints and CORS OPTIONS handling
  - `src/search/coordinator.py`: Main search orchestration with BM25SearchService initialization
  - `src/search/solution_searcher.py`: **UPDATED** - Uses new ontology predicates with hierarchical filtering
  - `src/search/bm25_search_service.py`: Keyword search service
  - `src/search/vector_search_service.py`: Semantic search with Titan
  - `src/search/ranking_engine.py`: RRF fusion implementation
  - `src/search/session_manager.py`: S3-based result caching
  - `src/search/related_documents_service.py`: TSD retrieval for solutions
  - `src/search/postgres.py`: Database access utility
  - `ONTOLOGY_MIGRATION_CHANGES.md`: Complete migration documentation
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
- **Ontology alignment batch processing**: LLM-based extraction of risks, mechanisms, impacts

### `/trusted_source_document_selection/`
- TSD manifest files and processing scripts
- **`wb_natcat_tsd_manifest_lexical.jsonl`**: 477 World Bank natural catastrophe TSDs
- **`estimate_page_counts.py`**: Page count estimation for cost planning
- **`test_tsd_opensearch.sh`**: OpenSearch searchability testing script

### `/test-v2-webapp/`
- React frontend application with enhanced UX and repository testing
- **`app.js`**: Main application with search interface, status indicators, comprehensive display, and repository test functions
- **`index.html`**: HTML structure and styling with repository test buttons
- **`styles.css`**: Enhanced CSS with status indicators and responsive design

### `/docs/`
- **`/status/`**: Project status documents and context summaries
- **`/infrastructure/`**: Architecture and deployment guides
- **`/api/`**: API specifications and system architecture

## MAJOR MILESTONE: PHASE 2 ONTOLOGY MIGRATION (2025-12-02)

### What Changed
**OLD Predicates** (Messy harvester data):
- `sg:riskType` with values like `sg:RiskType_natural_catastrophe`, `sg:RiskType_earthquakes_typhoons`
- `sg:solutionType` with values like `sg:SolutionType_risk_reduction`

**NEW Predicates** (Clean ontology):
- `sg:addressesRisk` → `sg:NaturalCatastropheRisk`, `sg:FloodRisk`, `sg:EarthquakeRisk`
- `sg:providesMechanism` → `sg:RiskReduction`, `sg:ParametricInsurance`
- `sg:hasImpact` → `sg:IncreasedResilience`, `sg:ImprovedCapacity`

### Hierarchical Filtering
Search now supports hierarchical queries using `rdfs:subClassOf+`:
- Filter for `sg:NaturalCatastropheRisk` returns solutions addressing `sg:FloodRisk`, `sg:EarthquakeRisk`, etc.
- Filter for `sg:FloodRisk` returns only flood-specific solutions
- UNION pattern handles both exact and hierarchical matches

### Implementation Details
1. **Lambda Updated**: `solution_searcher.py` uses new predicates with UNION pattern for hierarchical filtering
2. **Filter Mappings**: Updated to map UI values to new ontology URIs
3. **Country Mappings**: Fixed to use correct GeoNames format (`https://sws.geonames.org/`)
4. **Region Data**: Fixed Neptune region member URIs to match GeoNames format
5. **Neptune Cleanup**: Deleted old predicates from 557 solutions, preserved for 10 without LLM extractions

### Testing Results
- ✅ Solution category filters (hierarchical)
- ✅ Solution type filters (hierarchical)
- ✅ Country filters (single and multi-select)
- ✅ Region filters (ASEAN, ASEAN+3)
- ✅ Combined filters working correctly

## CURRENT IMPLEMENTATION STATUS

### ✅ COMPLETED (2025-12-02 Session)
- **Phase 2 Ontology Migration**: Complete migration to new predicates
- **Hierarchical Filtering**: UNION pattern for exact + subclass matching
- **Country Mapping Fix**: Corrected GeoNames URI format
- **Region Data Fix**: Updated Neptune region member URIs
- **Neptune Cleanup**: Removed old predicates from 557 solutions
- **Search Testing**: All filters validated and working

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
- **Complete API Fields**: PPP involvement, last update date, key highlights, implementation status
- **Enhanced UX**: Status indicators, responsive design, 3-column layout
- **Country Filter Bug Fix**: Corrected GeoNames URI format for proper filtering
- **Repository Test Functionality**: Complete implementation with authentication
- **Phase 1 Ontology Alignment**: LLM-based extraction of 567 solutions with 99% coverage

### 🔄 IN PROGRESS
- **TSD Bulk Loading**: 477 World Bank natural catastrophe documents ready for processing
- **Cost Optimization**: Monitoring and optimization of expensive services

### 📋 PENDING
- **CDK Synchronization**: Verify CDK matches deployed API Gateway configuration
- **OpenSearch Highlights Optimization**: Investigate why content field highlighting is slow
- **Pre-computed Summaries**: Generate summaries during indexing phase
- **Query Expansion**: Synonym handling and related term expansion
- **Search Analytics**: Track query patterns, success rates, user engagement

## TECHNICAL DETAILS

### Search Indices
- **documents_keyword**: BM25 search with `content_type` field ('solution' or 'trusted_source_document')
- **chunks_vector**: Vector search with 1536-dimension Titan embeddings and `content_type` field
- **Field mappings**: `doc_id` for intersection, `vector` field for KNN search, `text` for chunk content

### Knowledge Graph Schema (NEW ONTOLOGY)
- **Solutions**: `sgd:Solution` with new predicates:
  - `sg:addressesRisk` → Risk concepts (e.g., `sg:FloodRisk`)
  - `sg:providesMechanism` → Mechanism concepts (e.g., `sg:ParametricInsurance`)
  - `sg:hasImpact` → Impact concepts (e.g., `sg:IncreasedResilience`)
- **Organizations**: 1,039 public, 344 private, 270 international organizations with type classifications
- **Risk Taxonomy**: Hierarchical risk concepts with `rdfs:subClassOf` relationships
- **Mechanism Taxonomy**: Hierarchical mechanism concepts with `rdfs:subClassOf` relationships
- **Countries**: GeoNames integration with correct URI format (`https://sws.geonames.org/`)
- **Regions**: Regional organizations with member countries

### Hierarchical Filtering Pattern
```sparql
# Matches EITHER exact OR subclass
?solution sg:addressesRisk ?risk .
{
  FILTER(?risk IN (sg:NaturalCatastropheRisk))
}
UNION
{
  ?risk rdfs:subClassOf+ sg:NaturalCatastropheRisk .
}
```

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
      "risk_types_addressed": ["Flood Risk", "Climate Risk"],
      "solution_types": ["Risk Reduction", "Parametric Insurance"],
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

### Repository Metadata Endpoints
```json
// GET /repository/last-update
{
  "status": "success",
  "last_update": "2025-11-10T08:00:00Z",
  "update_type": "solution_ingestion",
  "documents_updated": 568
}

// GET /repository/solution-count  
{
  "status": "success",
  "total_solutions": 568,
  "total_trusted_documents": 240,
  "total_documents": 808,
  "last_counted": "2025-12-02T22:00:00Z"
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
| **Ontology Migration** | ✅ Complete | Phase 2 deployed | Hierarchical filtering working |
| **Search Lambda** | ✅ Operational | New predicates | All filters tested and working |
| **Knowledge Graph Layer** | ✅ Operational | v63 (bulk loading) | Fixed rdflib imports, organization analysis |
| **OpenSearch** | ✅ Operational | Managed 2.19.0 | 94% cost savings vs Serverless |
| **Neptune** | ✅ Operational | Clean ontology | Old predicates removed, regions fixed |
| **Pipeline** | ✅ Operational | End-to-end tested | Deduplication working, content type differentiation |
| **Related Documents** | ✅ Operational | Hybrid search | TSD retrieval with metadata integration |

### Total Resource Count (Current)
- **Lambda Functions**: 15+ active with enhanced functionality
- **S3 Buckets**: 7 core buckets for processing pipeline
- **Databases**: 3 (OpenSearch, Neptune, RDS)
- **Lambda Layers**: 4 (KG, Database, OpenSearch, Database Dependencies)
- **Security Groups**: 4 with proper VPC configuration
- **API Endpoints**: Enhanced search with comprehensive response fields + repository metadata

## KEY REFERENCE DOCUMENTS
- **Architecture**: `/docs/infrastructure/INFRASTRUCTURE_STACKS_GUIDE.md`
- **API Spec**: `/docs/api/solve-global-gaip-kr-api-DRAFT-v1.yaml`
- **Production Readiness**: `/docs/status/PRODUCTION_READINESS_IMPROVEMENTS_2025-09-24.md`
- **Database Queries**: `/docs/DATABASE_QUERIES_REFERENCE.md`
- **TODO Data Fixes**: `/solution_ingestion/TODO_DATA_FIXES.md`
- **SPARQL Reference**: `/docs/status/SPARQL_QUERIES_REFERENCE_2025-09-15.md`
- **Codebase Reference**: `/docs/CODEBASE_REFERENCE.md`
- **Related Documents Plan**: `/docs/RELATED_DOCUMENTS_IMPLEMENTATION_PLAN_2025-11-15.md`
- **Ontology Migration**: `/lambda/search/ONTOLOGY_MIGRATION_CHANGES.md`

## DEVELOPMENT WORKFLOW
1. **Feature branches** from `feature/climate-risk-ontology-filtering`
2. **Specific git adds**: `git add lambda/search test-v2-webapp` (avoid timeouts)
3. **Lambda deployment**: Create zip, update function code via AWS CLI
4. **Testing**: Use webapp at CloudFront distribution URL (E1X7VBE3EV1C5K)
5. **Monitoring**: CloudWatch logs for debugging search pipeline
6. **Database queries**: Use PostgreSQL client or DatabaseManager utility
7. **Cost awareness**: Always estimate costs before bulk operations
8. **Neptune queries**: Use Jupyter notebook with SigV4 auth for SPARQL

## CURRENT BRANCH STATUS
- **Branch**: `feature/climate-risk-ontology-filtering`
- **Commits ahead**: 12+ commits with complete ontology migration
- **Last major commits**: 
  - Complete ontology migration to new predicates (2025-12-02)
  - Fixed country and region mappings (2025-12-02)
  - Neptune cleanup of old predicates (2025-12-02)
- **Ready for**: TSD bulk loading, production deployment preparation, or additional feature development

## KNOWN ISSUES & LIMITATIONS
1. **CDK vs Deployed Configuration**: CDK may not reflect manual API Gateway OPTIONS methods
   - **Manual changes**: OPTIONS methods added via console for CORS
   - **TODO**: Verify CDK matches deployed working systems
2. **OpenSearch Highlights**: Content field highlighting causes 15x performance degradation
   - **Workaround**: Using vector chunk text for summaries instead
   - **Investigation needed**: Check content field mapping and analyzer configuration
3. **TSD Processing**: 477 World Bank documents ready for bulk loading
   - **Cost consideration**: ~$2,470 for Textract processing
   - **Deduplication**: Critical to avoid reprocessing costs

## TESTING & VALIDATION
- **Ontology Migration**: All filters tested with new predicates
- **Hierarchical Filtering**: Verified with natural-catastrophe → flood/earthquake subclasses
- **Country Filters**: Single and multi-select working correctly
- **Region Filters**: ASEAN and ASEAN+3 working after Neptune fix
- **Search Performance**: Latency maintained with new query patterns
- **Cost Management**: Deduplication system preventing duplicate processing costs

## NEXT CONVERSATION STARTUP
To continue development:
1. Reference this document for full context
2. Check `/docs/status/NEXT_STEPS_2025-12-02.md` for planned work
3. Review recent commits for implementation details
4. **Monitor costs** before running extensive tests (especially Textract)
5. Use existing search logs to debug any issues
6. Check TODO_DATA_FIXES.md for outstanding data issues
7. Consider production readiness checklist items
8. **Verify CDK matches deployed API Gateway configuration**

## SESSION SUMMARY (2025-12-02)
- **Focus**: Complete Phase 2 ontology migration to new predicates
- **Key Achievements**: 
  - Migrated search lambda to use new ontology predicates
  - Implemented hierarchical filtering with rdfs:subClassOf+
  - Fixed country and region mappings to correct GeoNames format
  - Cleaned up old predicates from Neptune (557 solutions)
  - All search filters tested and working
- **Technical Debt Addressed**: Removed messy harvester predicates, using clean ontology
- **Cost Awareness**: Maintained throughout session with careful testing approaches
- **Next Priority**: TSD bulk loading, CDK synchronization, or production deployment preparation

## CRITICAL NOTES
- **Ontology Migration Complete**: Search now uses clean hierarchical ontology predicates
- **Old Predicates Removed**: Cleaned from 557 solutions, preserved for 10 without extractions
- **Hierarchical Filtering**: Enables both broad and specific queries
- **All Filters Working**: Solution category, type, countries, regions all validated
- **Production Ready**: Core search functionality complete with new ontology
