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

### 9. Trusted Documents Integration
**Issue**: Need World Bank documents related to solutions we have ingested
**Status**: Not started
**Fix**: Build a utility to use data from the solutions to search for and retrieve documents from the World Bank repository via the search API

### 10. Non-Asia Programs (GAIP Request)
**Issue**: Include specific programs outside Asia-Pacific region
**Examples from Sprint 3 review**:
- Caribbean risk pool
- Africa risk pool
- Additional programs (list needed from GAIP)
**Status**: Awaiting specific program list from GAIP
**Note**: Web scraping was targeting Asia to control costs and validation complexity

## Completed Fixes

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
