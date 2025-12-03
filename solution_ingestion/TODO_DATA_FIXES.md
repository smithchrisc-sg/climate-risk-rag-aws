# Data Quality Fixes TODO

## High Priority Issues

### 1. Document Pipeline RDF Structure Alignment
**Issue**: Document processing pipeline uses different chunk traversal than solution processing
**Impact**: Inconsistent RDF structure between solutions and documents
**Status**: Identified 2025-11-11
**Action Required**: Modify document processing pipeline to align with solution RDF structure
**Details**: 
- Solutions use hierarchical Document → Section → Paragraph structure
- Document pipeline may use different chunk organization
- Need consistent reading order traversal in KG for both content types

### ✅ 2. GeoNames Country Mapping Misses
**Issue**: Exact string matching fails for country name variations in dcterms:spatial
**Examples**: 
- "Republic of Fiji" vs "Fiji" 
- "People's Republic of China" vs "China"
**Impact**: Missing country mappings in entity extraction
**Status**: PARTIALLY RESOLVED 2025-11-20 - Country filter bug fixed, but need comprehensive solution
**SPARQL Fix Example**:
```sparql
DELETE { ?doc dcterms:spatial "Republic of Fiji" }
INSERT { ?doc dcterms:spatial gn:2077456 }
WHERE { ?doc dcterms:spatial "Republic of Fiji" }
```
**Remaining Work**: Need comprehensive country name lookup facility using KG and ontology
**Priority**: Medium - current workaround functional but not scalable

### 3. Multi-Country Parsing
**Issue**: EntityMapper treats comma/newline-separated countries as single dcterms:spatial value
**Examples**: "Cambodia, <NL>Lao People's Republic" should create two dcterms:spatial triples
**Impact**: Only first country gets mapped
**Status**: Documented 2025-11-04
**Fix**: Update EntityMapper to split on `,` and `\n`, create separate dcterms:spatial triples for each country

### 4. SPARQL Injection Validation
**Issue**: KnowledgeGraphManager rejects valid RDF content
**Example**: Document 452 has unescaped characters causing validation failure
**Impact**: 1 solution out of 568 fails to load
**Status**: Documented 2025-11-04
**Workaround**: Per-document loading approach implemented

### ✅ 17. Repository Test Functionality Implementation
**Issue**: Need repository metadata endpoints with proper authentication
**Status**: COMPLETED 2025-11-21
**Priority**: High - Required for API delivery
**Implementation**:
- Added `/repository/last-update` and `/repository/solution-count` endpoints
- Implemented proper JWT Bearer token authentication
- Fixed CORS preflight issues with API Gateway OPTIONS methods
- Dynamic document counting from OpenSearch for real-time data
- BM25SearchService initialization in coordinator for metadata queries
**Result**: Both repository test buttons working with authentication and real data

### 18. CDK vs Deployed API Gateway Configuration Mismatch
**Issue**: CDK infrastructure code may not match deployed working API Gateway configuration
**Status**: IDENTIFIED 2025-11-21, STILL PENDING 2025-12-02
**Priority**: High - Critical for infrastructure consistency
**Details**:
- Manual OPTIONS methods added via AWS console for CORS preflight
- CDK may not reflect these manual changes
- Future CDK deployments could break working CORS configuration
**Action Required**: 
- Audit deployed API Gateway vs CDK configuration
- Update CDK to match working deployment
- Test CDK deployment in separate environment first
**Risk**: Infrastructure drift and deployment issues

### ✅ 20. Phase 2 Ontology Migration
**Issue**: Search using old messy harvester predicates instead of clean ontology
**Status**: COMPLETED 2025-12-02
**Priority**: High - Core search functionality
**Implementation**:
- Updated solution_searcher.py to use new ontology predicates
  - `sg:riskType` → `sg:addressesRisk`
  - `sg:solutionType` → `sg:providesMechanism`
- Implemented hierarchical filtering with `rdfs:subClassOf+` UNION pattern
- Fixed country mappings to correct GeoNames format (`https://sws.geonames.org/`)
- Fixed Neptune region member URIs to match GeoNames format
- Deleted old predicates from 557 solutions with new ontology
- Preserved old predicates for 10 solutions without LLM extractions
**Result**: All search filters working with hierarchical ontology-based filtering

### 21. Ontology Concept Labels
**Issue**: Some LLM-extracted concepts may not have rdfs:label properties
**Status**: IDENTIFIED 2025-12-02
**Priority**: Medium - Improves search result quality
**Details**:
- Need to query for concepts without labels
- Add missing concepts to appropriate taxonomy files
- Load updated ontology to Neptune
**Action Required**: Run SPARQL query to find unlabeled concepts and add to ontology

### 19. OpenSearch Content Field Highlighting Performance Issue
**Issue**: Content field highlighting causes 15x performance degradation (182ms → 2678ms)
**Status**: IDENTIFIED 2025-11-19 (updated 2025-11-21)
**Priority**: Medium - Feature works but optimization needed
**Details**:
- BM25 search without highlights: 182ms
- BM25 search with content highlights: 2678ms (14.7x slower)
- Currently using vector chunk text as workaround
**Investigation Needed**:
- Check content field mapping and analyzer configuration
- Test different highlighter types (unified, fvh, plain)
- Consider pre-computed summary field during indexing
**Impact**: Related documents feature working but summaries could be better

#### ✅ 16.1 Solution Categories vs Risk Types vs Solution Types
**Current**: Inconsistent usage across mockups and API
**Status**: RESOLVED 2025-11-20 - Kept solution_categories as empty array, focus on risk_types and solution_types
**Fields in Question**:
- `solution_categories`: Kept as empty array `[]` (not needed)
- `risk_types_addressed`: Working (e.g., "Natural Catastrophe", "Cyber", "Health")
- `solution_types`: Working (e.g., "Risk Reduction", "Risk Financing")
**Resolution**: Clarified that solution_categories field is not needed, existing risk_types and solution_types provide sufficient categorization

#### ✅ 16.2 Implementation Status Field
**Current**: `"implemented": "unknown"` (string default)
**Expected**: Boolean value indicating if solution is active/in-use vs planned/speculative
**Status**: COMPLETED 2025-11-20
**Implementation**: 
- Uses `sg:implementationYear` field from knowledge graph
- Returns true if implementation year <= current year, false otherwise
- Handles missing data gracefully with false default
**Result**: Boolean field working correctly in API responses

#### ✅ 16.3 Last Update Date Field
**Current**: Not present in API response
**Expected**: Show when solution data was last updated
**Status**: COMPLETED 2025-11-20
**Implementation**:
- Uses `dcterms:created` field from knowledge graph (not database due to data loading approach)
- Parses DD/MM/YYYY format and converts to ISO8601 YYYY-MM-DD format
- Handles missing data gracefully with null values
**Result**: ISO8601 formatted dates appearing in API responses

#### ✅ 16.4 Public-Private Partnership (PPP) Involvement
**Current**: `"ppp_involvement": "Unknown"` (string default)
**Expected**: Boolean indicating if solution involves both public and private organizations
**Status**: COMPLETED 2025-11-20
**Implementation**:
- SPARQL query checks for both Public/International AND Private organizations
- Returns "yes" for 60% of solutions, "no" for 39%, "unknown" for 1%
- Uses organization type analysis from Neptune knowledge graph with 1,653 classified organizations
**Result**: Accurate PPP detection based on organization involvement analysis

#### ✅ 16.5 Key Highlights Field
**Current**: `"key_highlights": []` (empty array)
**Expected**: Bullet points or structured highlights from "Key Highlights" section
**Status**: COMPLETED 2025-11-20
**Implementation**:
- SPARQL queries find "Key Highlights" sections in document structure
- Retrieves individual chunks from S3 as separate strings (not concatenated like description)
- Each highlight chunk becomes separate array element
- Handles both main search and individual solution retrieval paths
**Result**: Array of individual highlight strings appearing in API responses

#### ✅ 16.6 Enhanced UX Implementation
**Status**: COMPLETED 2025-11-20
**Implementation**:
- Status indicators with color-coded checkmarks (✅), X marks (❌), and question marks (❓)
- Three-column expanded view: Risk Types | Solution Types | Key Highlights
- Responsive design for mobile devices (3→2→1 columns)
- Last Updated date display in main solution panel
- Enhanced CSS with proper styling and mobile responsiveness
**Result**: Comprehensive UX showing all new API fields with clear visual indicators

**Related Code Locations**:
- API response formatting: `/lambda/search/src/search/solution_searcher.py`
- KG queries: `/lambda/search/src/search/solution_searcher.py` (get_solution_content method)
- Document structure traversal: Knowledge graph layer

#### 16.6 Region vs Country Field Clarification and Hierarchy
**Current**: Inconsistent usage of regions and countries across API response
**Status**: Identified 2025-11-19
**Priority**: Medium

**Current State**:
1. **Frontend (app.js)**: Hardcoded `const region = 'ASEAN'` for demo
2. **API Response - metadata.regions**: Currently contains country name (e.g., "South Korea")
3. **API Response - country_regions_covered**: Contains country name (e.g., "South Korea")

**Issues**:
- `metadata.regions` should contain actual regions (ASEAN, ASEAN+3, etc.), not countries
- Unclear if `country_regions_covered` should include regions or just countries
- Need region hierarchy: Country → Sub-region → Region (e.g., South Korea → East Asia → ASEAN+3)
- Frontend needs dynamic region selection, not hardcoded value

**Knowledge Graph Status**:
- Some region definitions exist in KG (ASEAN, ASEAN+3)
- May need additional region definitions and country-to-region mappings
- GeoNames integration provides country data but region groupings may be incomplete

**Proposed Solution**:
1. **Enhance KG with Region Hierarchy**:
   - Define all relevant regions (ASEAN, ASEAN+3, Asia-Pacific, etc.)
   - Create country-to-region mappings in Neptune
   - Support multiple regions per country (e.g., Thailand → ASEAN, ASEAN+3, Asia-Pacific)

2. **Update API Response Structure**:
   ```json
   {
     "country_regions_covered": ["South Korea"],  // Keep as countries only
     "metadata": {
       "regions": ["ASEAN+3", "Asia-Pacific"],  // Actual regions, ordered narrow→broad
       "countries": ["South Korea"],  // Explicit country list
       "region_hierarchy": {
         "South Korea": ["East Asia", "ASEAN+3", "Asia-Pacific"]
       }
     }
   }
   ```

3. **SPARQL Query Enhancement**:
   - Query country-to-region mappings during solution retrieval
   - Order regions from most specific to most general
   - Include all applicable regions for each country

4. **Frontend Update**:
   - Remove hardcoded `region = 'ASEAN'`
   - Use `metadata.regions[0]` or allow user to select from available regions
   - Display region hierarchy in UI if needed

**Implementation Steps**:
1. Define region taxonomy and country mappings (data modeling)
2. Add region definitions to Neptune knowledge graph
3. Update solution_searcher.py to query region hierarchy
4. Modify API response formatting to include regions array
5. Update frontend to use dynamic regions from API

**Questions to Resolve**:
- Should `country_regions_covered` include regions or stay country-only?
- What is the complete list of regions to support? (ASEAN, ASEAN+3, Asia-Pacific, others?)
- Should regions be filterable in search? (already have region filters in UI)
- How to handle countries in multiple regions?

**Related Code Locations**:
- Frontend: `/test-v2-webapp/app.js` (line with `const region = 'ASEAN'`)
- API response: `/lambda/search/src/search/solution_searcher.py`
- KG queries: `/lambda/search/src/search/solution_searcher.py`
- Region filters: Already implemented in search coordinator

**Complexity**: Medium-High (requires data modeling, KG updates, API changes, frontend updates)

## Medium Priority Issues

### 5. Comprehensive Country Name Lookup Facility
**Issue**: Need robust country name resolution using knowledge graph and ontology
**Status**: Added 2025-11-20 following country filter bug fix
**Priority**: Medium-High - foundational for proper geographic filtering
**Requirements**:
- Leverage GeoNames data in Neptune knowledge graph for fuzzy matching
- Support alternate country names, common variations, and historical names
- Create mapping service that can resolve "Republic of Fiji" → "Fiji" → GeoNames URI
- Integrate with existing SPARQL queries for country filtering
- Support regional organization expansion (ASEAN, ASEAN+3, etc.)
**Implementation Approach**:
- Build country name normalization service using Neptune FTS
- Create comprehensive country-to-region mappings in knowledge graph
- Update EntityMapper to use lookup service instead of exact string matching
- Add fuzzy matching capabilities for country name variations
**Related**: Item #2 (GeoNames Country Mapping) - this is the comprehensive solution

### 6. Regional Organization Expansion
**Issue**: Need more regional organizations beyond current country-level filtering
**Status**: Added 2025-11-20
**Priority**: Medium - enhances geographic search capabilities
**Requirements**:
- Add ASEAN, ASEAN+3, Asia-Pacific, South Asia, East Asia regional definitions
- Create country-to-region mappings in Neptune knowledge graph
- Support hierarchical region filtering (country → sub-region → region)
- Update frontend to support regional filtering options
**Implementation**: Integrate with comprehensive country lookup facility (#5)

### 7. Organization Name Standardization
**Issue**: Inconsistent organization name formats
**Impact**: Reduced entity linking accuracy
**Status**: Identified during ingestion

### 7. Organization Name Standardization
**Issue**: Inconsistent organization name formats
**Impact**: Reduced entity linking accuracy
**Status**: Identified during ingestion

### 8. Vocabulary Concept Mapping
**Issue**: Some solution types/themes don't map to controlled vocabulary
**Impact**: Missing semantic relationships
**Status**: Ongoing refinement needed

### 9. Error Handling Enhancement
**Issue**: Better error reporting and recovery for partial failures
**Fix**: Improve logging and continue processing on individual failures
**Status**: Monitor current run

## Search & Query Enhancements

### 8. Cross-System Search Integration
**Issue**: Need unified search across OpenSearch keyword, vector, and Neptune SPARQL
**Status**: Next phase after data ingestion complete - IN PROGRESS 2025-11-11

### 9. Backend Pagination Result Count Issue
**Issue**: Backend returning inconsistent result counts per page (e.g., page 3 returns 19 results instead of 20)
**Impact**: Frontend pagination displays incorrect result ranges (e.g., "Results 41-59" instead of "Results 41-60")
**Status**: Identified 2025-11-13 during cursor-based pagination testing
**Location**: `/Users/chris/climate-risk-rag-aws/lambda/search/src/search/solution_searcher.py` or coordinator pagination logic
**Expected**: Each page should return exactly `max_results` (20) except final page
**Actual**: Some pages return fewer results than requested
**Investigation Needed**: Check Neptune SPARQL LIMIT/OFFSET calculation and S3 content assembly logic

### 13. OpenSearch Content Field Highlighting Performance
**Issue**: Highlighting content field causes 15x performance degradation (182ms → 2678ms)
**Status**: Identified 2025-11-19 during related documents implementation
**Details**:
- BM25 search without highlights: 182ms
- BM25 search with content highlights: 2678ms (14.7x slower)
- BM25 search with full_text + highlights: 1676ms (9.2x slower)
**Investigation Needed**:
- Check content field mapping and analyzer configuration
- Test with different highlighter types (unified, fvh, plain)
- Consider creating separate summary field during indexing
- Verify term_vector settings for highlighting optimization
**Workaround**: Using best matching vector chunk text for summaries
**Impact**: Related documents feature working but summaries could be better
**Priority**: Medium - feature works but optimization would improve quality

### 14. TSD Title Backfill
**Issue**: Some TSDs indexed with "Document {doc_id}" instead of actual title
**Status**: Identified 2025-11-19
**Cause**: Title not in metadata during keyword indexing
**Current Workaround**: Database lookup retrieves actual title from documents table
**Proper Fix**: Update keyword-indexer to get title from database during indexing
**Impact**: Related documents display correct titles via database lookup
**Priority**: Low - workaround effective but adds database query overhead

### 15. Content Type Migration for Existing TSDs
**Issue**: 228 existing TSDs had null content_type field
**Status**: Completed 2025-11-19 via manual bulk update
**Resolution**: Used OpenSearch _update_by_query to set content_type='trusted_source_document'
**Prevention**: Keyword-indexer now sets content_type during indexing
**Impact**: All TSDs now searchable with content_type filter
**Note**: Future TSDs will have content_type set automatically

## Content Loading & Expansion

### ✅ Trusted Source Document Search Integration
**Issue**: Recently indexed TSDs not appearing in search results
**Status**: RESOLVED 2025-11-19
**Root Cause**: content_type field was null for TSDs
**Resolution**:
- Fixed keyword-indexer to set content_type during indexing
- Manually updated 228 existing TSDs with content_type='trusted_source_document'
- Verified 13 test TSDs searchable with content_type filter
**Impact**: All TSDs now searchable, related documents feature working

### ✅ Related Documents Feature Implementation
**Issue**: Need to show related TSDs for each solution
**Status**: Completed 2025-11-19
**Resolution**:
- Implemented hybrid BM25 + Vector search for TSDs
- Integrated PostgresProcessor for database metadata lookups
- Extract source name (World Bank, IMF) from URLs
- Use best matching vector chunk text for summaries
- Display rank instead of relevance score
**Impact**: Users can see 3-5 relevant TSDs per solution with proper metadata

### 9. Trusted Source Document Search Integration
**Issue**: Recently indexed TSDs not appearing in search results
**Status**: Identified 2025-11-18 during batch loading testing
**Possible Causes**:
- OpenSearch index refresh delay (should be ~1 second with refresh=False)
- content_type filter mismatch in search queries
- Index mapping missing content_type field
- Search query construction not handling TSDs correctly
**Investigation Needed**:
- Check if documents exist in documents_keyword index
- Verify chunks exist in chunks_vector index
- Check content_type field is properly set
- Test search with and without content_type filter
**Location**: `/Users/chris/climate-risk-rag-aws/lambda/search/` search services

### 10. Content Type Determination Enhancement
**Issue**: Simple prefix-based content_type determination (sol_ → solution)
**Status**: Identified 2025-11-18 as technical debt
**Current Implementation**: `content_type = 'solution' if doc_id.startswith('sol_') else 'trusted_source_document'`
**Proposed Fix**:
- Add content_type to document metadata during harvesting
- Store in document_processing_status metadata
- Read from metadata in keyword-indexer and vector-embeddings-worker
- Fallback to prefix check if metadata missing
**Impact**: More robust and explicit content type handling
**Complexity**: Low

### 11. Trusted Documents Integration
**Issue**: Need World Bank documents related to solutions we have ingested
**Status**: In progress - 477 documents ready for batch loading
**Current**: 10 test documents loaded successfully with deduplication working
**Next**: Full batch load of remaining 467 documents
**Fix**: Build a utility to use data from the solutions to search for and retrieve documents from the World Bank repository via the search API

### 12. Non-Asia Programs (GAIP Request)
**Issue**: Include specific programs outside Asia-Pacific region
**Examples from Sprint 3 review**:
- Caribbean risk pool
- Africa risk pool
- Additional programs (list needed from GAIP)
**Status**: Awaiting specific program list from GAIP
**Note**: Web scraping was targeting Asia to control costs and validation complexity


### 11. Scheme to use KG for related documents, etc. 
For example, if we have entities in the Solution text (once we're doing full text for solutions) we can walk the entities from chunks to documents. We can also use those entity values to augment the query. Lots of ways to build this out.

## Completed Fixes

### ✅ Textract Deduplication System
**Issue**: Reprocessing documents with Textract costs $20+ per document
**Resolution**: Implemented hash-based duplicate detection using S3 ETag
**Status**: Completed 2025-11-18
**Details**:
- MD5 hash from S3 ETag for single-part uploads (99.7% of documents)
- SHA-256 hash for multipart uploads
- Database query checks textract_complete for matching hash
- Skips Textract and publishes completion message for duplicates
- Hash preserved from textract_initiate to textract_complete metadata
**Impact**: Saves $20+ per duplicate document, prevents unnecessary costs

### ✅ Keyword Indexer Timeout
**Issue**: Lambda timing out at 300 seconds for large documents
**Resolution**: Increased Lambda memory to optimize CPU allocation
**Status**: Completed 2025-11-18
**Details**: Processing time reduced from 300s timeout to 9 seconds
**Impact**: Reliable keyword indexing for documents with 1000+ chunks

### ✅ KG Triple Loader Authentication
**Issue**: Neptune bulk loader failing with "object has no attribute 'auth'" error
**Resolution**: Added auth property to KnowledgeGraphManager for SigV4 signing
**Status**: Completed 2025-11-18
**Details**:
- Added auth property returning NeptuneSigV4Auth callable
- Fixed parallelism value from "AUTO" to "OVERSUBSCRIBE"
- Deployed knowledge-graph-layer v63
**Impact**: Reliable Neptune bulk loading for document structure triples

### ✅ Content Type Field Addition
**Issue**: No differentiation between solutions and trusted source documents in indices
**Resolution**: Added content_type field to keyword and vector indices
**Status**: Completed 2025-11-18
**Details**:
- Implemented determine_document_type() based on doc_id prefix
- Added to documents_keyword index (keyword-indexer)
- Added to chunks_vector index (vector-embeddings-worker)
**Impact**: Enables separate search filtering for solutions vs TSDs

### ✅ Text Extractor Hash Preservation
**Issue**: textract_complete records missing document_hash for deduplication
**Resolution**: text-extractor-processor now copies hash from textract_initiate
**Status**: Completed 2025-11-18
**Impact**: Deduplication works for all future document processing

### ✅ Manifest Skip Flag Support
**Issue**: No way to exclude already-processed documents from batch runs
**Resolution**: Added skip flag parsing in process_manifest_pipeline.py
**Status**: Completed 2025-11-18
**Details**: Documents marked with "skip": true are automatically excluded
**Impact**: Prevents reprocessing in batch operations

### ✅ Pipeline Continuation After Skip
**Issue**: Duplicate documents not triggering rest of pipeline after Textract skip
**Resolution**: Added TEXT_EXTRACTION_COMPLETE_TOPIC_ARN environment variable
**Status**: Completed 2025-11-18
**Impact**: Deduplication works end-to-end without blocking pipeline

### ✅ Deduplication Strategy
**Issue**: 603 solutions → 568 unique (35 duplicates)
**Resolution**: By design - same source URLs create identical doc_ids
**Status**: Confirmed as feature, not bug

### ✅ Database Processor RDBMS Methods
**Issue**: Non-existent store_chunk_data, store_document_metadata methods
**Resolution**: Replaced with no-op implementations
**Status**: Fixed 2025-11-04

### ✅ Data Integrity Validation
**Issue**: Cross-system count verification needed
**Resolution**: Created comprehensive validation tools
**Status**: Completed 2025-11-04

---

*Add new issues as they're discovered during testing and validation*
