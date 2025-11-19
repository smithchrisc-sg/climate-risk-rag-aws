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

### 2. GeoNames Country Mapping Misses
**Issue**: Exact string matching fails for country name variations in dcterms:spatial
**Examples**: 
- "Republic of Fiji" vs "Fiji" 
- "People's Republic of China" vs "China"
**Impact**: Missing country mappings in entity extraction
**Status**: Documented 2025-11-04
**SPARQL Fix Example**:
```sparql
DELETE { ?doc dcterms:spatial "Republic of Fiji" }
INSERT { ?doc dcterms:spatial gn:2077456 }
WHERE { ?doc dcterms:spatial "Republic of Fiji" }
```

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

### 16. API Response Field Enhancements
**Issue**: Four fields in API response are currently defaulted/empty
**Status**: Identified 2025-11-19
**Priority**: Medium

#### 16.1 Solution Categories vs Risk Types vs Solution Types
**Current**: Inconsistent usage across mockups and API
**Status**: Needs clarification 2025-11-19
**Fields in Question**:
- `solution_categories`: Currently empty array `[]`
- `risk_types_addressed`: Working (e.g., "Natural Catastrophe", "Cyber", "Health")
- `solution_types`: Working (e.g., "Risk Reduction", "Risk Financing")
**Issue**: Mockups show inconsistent usage - appears to be made up examples
**Questions**:
- Are solution_categories the same as risk_types_addressed?
- Is there a three-tier taxonomy: category → risk type → solution type?
- Should solution_categories be removed from API response?
**Action Required**: Clarify taxonomy structure with stakeholders before implementation
**Priority**: Medium - affects API contract and frontend display

#### 16.2 Implementation Status Field
**Current**: `"implemented": "unknown"` (string default)
**Expected**: Boolean value indicating if solution is active/in-use vs planned/speculative
**Data Source**: Year of Implementation field (currently used for publication_date)
**Proposed Logic**: 
```python
# If publication_date (Year of Implementation) <= current year, then implemented = true
implemented = publication_date <= datetime.now().year if publication_date else False
```
**Implementation**:
- Update solution_searcher.py get_solution_content() method
- Add logic to compare publication_date with current year
- Return boolean instead of "unknown" string
**Complexity**: Low (simple date comparison)
**Priority**: High - clear logic defined

#### 16.3 Last Update Date Field
**Current**: Not present in API response
**Expected**: Show when solution data was last updated
**Data Source**: Database `documents` table has `created_at` and `updated_at` columns
**Proposed Implementation**:
- Add `last_update_date` to solution metadata in API response
- Retrieve from database during solution content assembly
- Format: ISO 8601 timestamp (e.g., "2025-11-19T15:48:00Z")
**Location in Response**: Add to metadata object or top-level field
```json
{
  "solution_id": "sol_abc123",
  "title": "...",
  "last_update_date": "2025-11-19T15:48:00Z",
  "metadata": {
    "last_update_date": "2025-11-19T15:48:00Z",
    // ... other metadata
  }
}
```
**Implementation**:
- Query documents table for updated_at during solution retrieval
- Add to response formatting in solution_searcher.py
- API response structure is flexible, can add new fields
**Complexity**: Low (database query + formatting)
**Priority**: Medium - useful for users to know data freshness

#### 16.4 Public-Private Partnership (PPP) Involvement
**Current**: `"ppp_involvement": "Unknown"` (string default)
**Expected**: Boolean indicating if solution involves both public and private organizations
**Proposed Solution**: Derive from Knowledge Graph using SPARQL
```sparql
# Check if solution has both public and private organizations
SELECT ?solution 
  (COUNT(DISTINCT ?publicOrg) as ?publicCount)
  (COUNT(DISTINCT ?privateOrg) as ?privateCount)
WHERE {
  ?solution a sgd:Solution .
  OPTIONAL { ?solution sgd:hasPublicOrganization ?publicOrg }
  OPTIONAL { ?solution sgd:hasPrivateOrganization ?privateOrg }
}
GROUP BY ?solution
HAVING (?publicCount > 0 && ?privateCount > 0)
```
**Implementation**:
- Add SPARQL query to solution_searcher.py
- Execute during solution content retrieval
- Set `ppp_involvement: true` if both org types present, `false` otherwise
**Complexity**: Low (SPARQL query + boolean logic)

#### 16.5 Key Highlights Field
**Current**: `"key_highlights": []` (empty array)
**Expected**: Bullet points or structured highlights from "Key Highlights" section
**Proposed Solution**: Extract from document structure similar to description
**Implementation Approach**:
1. Identify "Key Highlights" section in document structure (KG traversal)
2. Extract chunks under that section
3. Format as bullet points or structured list
4. May need text manipulation to clean up formatting
**Considerations**:
- Some solutions may not have Key Highlights section
- Format: array of strings vs structured objects?
- Length limits per highlight?
- Should highlights be ranked/ordered?
**Complexity**: Medium (similar to description extraction but with formatting)

**Related Code Locations**:
- API response formatting: `/lambda/search/src/search/solution_searcher.py`
- KG queries: `/lambda/search/src/search/solution_searcher.py` (get_solution_content method)
- Document structure traversal: Knowledge graph layer

## Medium Priority Issues

### 5. Organization Name Standardization
**Issue**: Inconsistent organization name formats
**Impact**: Reduced entity linking accuracy
**Status**: Identified during ingestion

### 6. Vocabulary Concept Mapping
**Issue**: Some solution types/themes don't map to controlled vocabulary
**Impact**: Missing semantic relationships
**Status**: Ongoing refinement needed

### 7. Error Handling Enhancement
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
