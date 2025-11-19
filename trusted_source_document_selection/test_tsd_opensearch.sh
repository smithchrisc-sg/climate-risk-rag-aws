#!/bin/bash
# Run this script from an EC2 instance in the VPC
# Tests TSD searchability in OpenSearch

OPENSEARCH_ENDPOINT="vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
AUTH="admin:veqpat-kegba2-zapbyZ"

echo "=========================================="
echo "TSD SEARCHABILITY TEST"
echo "=========================================="

# Test 1: Count TSDs in keyword index
echo -e "\n1. Counting TSDs in documents_keyword index..."
curl -s -u "${AUTH}" "https://${OPENSEARCH_ENDPOINT}/documents_keyword/_count" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"content_type":"trusted_source_document"}}}' | jq .

# Test 2: Count TSD chunks in vector index
echo -e "\n2. Counting TSD chunks in chunks_vector index..."
curl -s -u "${AUTH}" "https://${OPENSEARCH_ENDPOINT}/chunks_vector/_count" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"content_type":"trusted_source_document"}}}' | jq .

# Test 3: BM25 search for TSDs
echo -e "\n3. Testing BM25 search (related documents query)..."
curl -s -u "${AUTH}" "https://${OPENSEARCH_ENDPOINT}/documents_keyword/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": {
          "multi_match": {
            "query": "natural disaster risk management",
            "fields": ["title^3", "summary^2", "content"]
          }
        },
        "filter": {"term": {"content_type": "trusted_source_document"}}
      }
    },
    "size": 3
  }' | jq '{total: .hits.total.value, results: [.hits.hits[] | {doc_id: ._source.doc_id, title: ._source.title, score: ._score}]}'

# Test 4: Sample TSD chunks from vector index
echo -e "\n4. Testing vector index TSD chunk retrieval..."
curl -s -u "${AUTH}" "https://${OPENSEARCH_ENDPOINT}/chunks_vector/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "filter": {"term": {"content_type": "trusted_source_document"}}
      }
    },
    "size": 2
  }' | jq '{total: .hits.total.value, sample: [.hits.hits[] | {doc_id: ._source.doc_id, chunk_id: ._source.chunk_id, content_type: ._source.content_type}]}'

echo -e "\n=========================================="
echo "TEST COMPLETE"
echo "=========================================="
