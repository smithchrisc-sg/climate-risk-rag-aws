# Data Integrity Checks

## Neptune Knowledge Graph Queries

### Solution Count
```sparql
PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>

SELECT (COUNT(?doc) as ?solution_count) WHERE {
    ?doc a sgd:Solution .
}
```

### Chunk Count by Document
```sparql
dat
```

### Country Mapping Status
```sparql
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX gn: <http://www.geonames.org/ontology#>

SELECT ?country (COUNT(?doc) as ?doc_count) WHERE {
    ?doc dcterms:spatial ?country .
} GROUP BY ?country ORDER BY DESC(?doc_count)
```

### Unmapped Countries (String literals instead of GeoNames URIs)
```sparql
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?country WHERE {
    ?doc dcterms:spatial ?country .
    FILTER(isLiteral(?country))
}
```

## OpenSearch Queries

### Document Keyword Index Count
```bash
curl -u admin:veqpat-kegba2-zapbyZ \
  -H "Content-Type: application/json" \
  -X POST \
  "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/documents_keyword/_count" \
  -d '{
    "query": {
      "term": {
        "content_type": "solution"
      }
    }
  }'
```

### Vector Index Chunk Count
```bash
curl -u admin:veqpat-kegba2-zapbyZ \
  -H "Content-Type: application/json" \
  -X POST \
  "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/chunks_vector/_count" \
  -d '{
    "query": {
      "term": {
        "content_type": "solution"
      }
    }
  }'
```

### Unique Documents in Vector Index
```bash
curl -u admin:veqpat-kegba2-zapbyZ \
  -H "Content-Type: application/json" \
  -X POST \
  "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/chunks_vector/_search" \
  -d '{
    "size": 0,
    "query": {
      "term": {
        "content_type": "solution"
      }
    },
    "aggs": {
      "unique_documents": {
        "cardinality": {
          "field": "doc_id"
        }
      }
    }
  }'
```

### Sample Document Structure
```bash
curl -u admin:veqpat-kegba2-zapbyZ \
  "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/documents_keyword/_search?size=1&pretty"
```

### Sample Chunk Structure
```bash
curl -u admin:veqpat-kegba2-zapbyZ \
  "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/chunks_vector/_search?size=1&pretty"
```

## Data Lake File Counts

### Solution Documents
```bash
find output_data/kr-dl-text/data-lake/ -name "*.txt" | wc -l
```

### Chunks
```bash
find output_data/kr-dl-chunks/data-lake/ -name "*.json" | wc -l
```

### Embeddings
```bash
find output_data/kr-dl-embeddings/data-lake/ -name "*.json" | wc -l
```

### TTL Files
```bash
find output_data/kr-dl-neptune-ttl/data-lake/ -name "*.ttl" | wc -l
```

### Unique Documents in Each Data Lake
```bash
echo "Unique docs in text:"
find output_data/kr-dl-text/data-lake/ -name "*.txt" | \
  sed 's/.*\/\([^\/]*\)\.txt/\1/' | sort -u | wc -l

echo "Unique docs in chunks:"
find output_data/kr-dl-chunks/data-lake/ -name "*.json" | \
  sed 's/.*\/\([^_]*\)_.*/\1/' | sort -u | wc -l

echo "Unique docs in embeddings:"
find output_data/kr-dl-embeddings/data-lake/ -name "*.json" | \
  sed 's/.*\/\([^_]*\)_.*/\1/' | sort -u | wc -l

echo "Unique docs in TTL:"
find output_data/kr-dl-neptune-ttl/data-lake/ -name "*.ttl" | \
  sed 's/.*\/\([^\/]*\)\.ttl/\1/' | sort -u | wc -l
```

### Check for Duplicate Processing
```bash
echo "Documents with most chunks:"
find output_data/kr-dl-chunks/data-lake/ -name "*.json" | \
  sed 's/.*\/\([^_]*\)_.*/\1/' | sort | uniq -c | sort -nr | head -10

echo "Documents with most embeddings:"
find output_data/kr-dl-embeddings/data-lake/ -name "*.json" | \
  sed 's/.*\/\([^_]*\)_.*/\1/' | sort | uniq -c | sort -nr | head -10
```

## Cross-System Consistency Checks

### Expected Relationships
- **Neptune solutions** = **OpenSearch keyword documents** = **Data lake text files** = **Data lake TTL files**
- **OpenSearch vector chunks** ≤ **Data lake chunk files** ≤ **Data lake embedding files**
- **Unique docs in vector index** = **Neptune solutions**

### Quick Validation Script
```bash
#!/bin/bash
echo "=== Data Integrity Check ==="
echo "Neptune solutions: [run SPARQL query]"
echo "OpenSearch keyword docs: [run curl count]"
echo "OpenSearch vector chunks: [run curl count]"
echo "OpenSearch unique docs: [run curl aggregation]"
echo "Data lake text files: $(find output_data/kr-dl-text/data-lake/ -name "*.txt" | wc -l)"
echo "Data lake chunk files: $(find output_data/kr-dl-chunks/data-lake/ -name "*.json" | wc -l)"
echo "Data lake embedding files: $(find output_data/kr-dl-embeddings/data-lake/ -name "*.json" | wc -l)"
echo "Data lake TTL files: $(find output_data/kr-dl-neptune-ttl/data-lake/ -name "*.ttl" | wc -l)"
```

## Troubleshooting Queries

### Find Missing Mappings
```sparql
PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?doc ?title ?country WHERE {
    ?doc a sgd:Solution ;
         dcterms:title ?title ;
         dcterms:spatial ?country .
    FILTER(isLiteral(?country) && CONTAINS(?country, ","))
} LIMIT 20
```

### Check RDF Structure
```sparql
PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>

SELECT ?doc ?section ?paragraph WHERE {
    ?doc a sgd:Solution ;
         sgd:hasChild ?section .
    ?section a sgd:Section ;
             sgd:hasChild ?paragraph .
    ?paragraph a sgd:Paragraph .
} LIMIT 10
```
