# Data Quality Fixes TODO

## Entity Mapping Issues

### 1. GeoNames Country Mapping Misses
- **Issue**: Exact string matching fails for country name variations in dcterms:spatial
- **Examples**: "Republic of Fiji" not mapping to Fiji GeoNames URI
- **Fix**: Find string literals in dcterms:spatial, replace with corresponding GeoNames URIs
- **SPARQL Fix Example**:
  ```sparql
  DELETE { ?doc dcterms:spatial "Republic of Fiji" }
  INSERT { ?doc dcterms:spatial gn:2077456 }
  WHERE { ?doc dcterms:spatial "Republic of Fiji" }
  ```
- **Status**: Pending log analysis

### 2. Multi-Country Parsing
- **Issue**: EntityMapper treats comma/newline-separated countries as single dcterms:spatial value
- **Examples**: "Cambodia, <NL>Lao People's Republic" should create two dcterms:spatial triples
- **Fix**: Update EntityMapper to split on `,` and `\n`, create separate dcterms:spatial triples for each country
- **Status**: Needs code fix

## Pipeline Improvements

### 3. Error Handling
- **Issue**: Better error reporting and recovery for partial failures
- **Fix**: Improve logging and continue processing on individual failures
- **Status**: Monitor current run

## Search & Query Enhancements

### 4. Cross-System Search Integration
- **Issue**: Need unified search across OpenSearch keyword, vector, and Neptune SPARQL
- **Status**: Next phase after data ingestion complete

---

*Add new issues as they're discovered during testing and validation*
