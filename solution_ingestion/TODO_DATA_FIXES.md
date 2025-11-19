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

## Content Loading & Expansion

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
