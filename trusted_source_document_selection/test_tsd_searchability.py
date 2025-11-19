#!/usr/bin/env python3
"""
Test if TSDs are searchable in OpenSearch keyword and vector indices
"""
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

OPENSEARCH_ENDPOINT = "vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com"
REGION = "us-east-1"
KEYWORD_INDEX = "documents_keyword"
VECTOR_INDEX = "chunks_vector"

def get_opensearch_client():
    """Create OpenSearch client with AWS auth"""
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'es',
        session_token=credentials.token
    )
    
    return OpenSearch(
        hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

def test_tsd_count(client):
    """Count TSDs in both indices"""
    print("=" * 80)
    print("TSD COUNT TEST")
    print("=" * 80)
    
    # Count in keyword index
    keyword_query = {
        "query": {
            "term": {"content_type": "trusted_source_document"}
        }
    }
    keyword_result = client.count(index=KEYWORD_INDEX, body=keyword_query)
    print(f"TSDs in {KEYWORD_INDEX}: {keyword_result['count']}")
    
    # Count in vector index
    vector_result = client.count(index=VECTOR_INDEX, body=keyword_query)
    print(f"TSD chunks in {VECTOR_INDEX}: {vector_result['count']}")
    
    # Count solutions for comparison
    solution_query = {
        "query": {
            "term": {"content_type": "solution"}
        }
    }
    solution_result = client.count(index=KEYWORD_INDEX, body=solution_query)
    print(f"Solutions in {KEYWORD_INDEX}: {solution_result['count']}")
    
    return keyword_result['count'], vector_result['count']

def test_sample_tsd_retrieval(client, manifest_path):
    """Test if specific TSDs from manifest are retrievable"""
    print("\n" + "=" * 80)
    print("SAMPLE TSD RETRIEVAL TEST")
    print("=" * 80)
    
    # Get first 5 doc_ids from manifest
    doc_ids = []
    with open(manifest_path, 'r') as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            doc = json.loads(line.strip())
            if not doc.get('skip', False):
                doc_ids.append(doc['doc_id'])
    
    print(f"\nTesting retrieval of {len(doc_ids)} sample TSDs...")
    
    for doc_id in doc_ids:
        # Check keyword index
        keyword_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"doc_id": doc_id}},
                        {"term": {"content_type": "trusted_source_document"}}
                    ]
                }
            }
        }
        keyword_result = client.search(index=KEYWORD_INDEX, body=keyword_query)
        keyword_found = keyword_result['hits']['total']['value'] > 0
        
        # Check vector index
        vector_result = client.search(index=VECTOR_INDEX, body=keyword_query)
        vector_chunks = vector_result['hits']['total']['value']
        
        status = "✓" if (keyword_found and vector_chunks > 0) else "✗"
        print(f"{status} {doc_id}: keyword={keyword_found}, vector_chunks={vector_chunks}")

def test_bm25_search(client):
    """Test BM25 search for TSDs with sample query"""
    print("\n" + "=" * 80)
    print("BM25 SEARCH TEST (Related Documents Query)")
    print("=" * 80)
    
    query_text = "natural disaster risk management climate resilience"
    
    search_query = {
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query_text,
                        "fields": ["title^3", "summary^2", "content"]
                    }
                },
                "filter": {
                    "term": {"content_type": "trusted_source_document"}
                }
            }
        },
        "size": 10
    }
    
    result = client.search(index=KEYWORD_INDEX, body=search_query)
    hits = result['hits']['hits']
    
    print(f"Query: '{query_text}'")
    print(f"Results: {len(hits)} TSDs found\n")
    
    for i, hit in enumerate(hits[:5], 1):
        doc_id = hit['_source'].get('doc_id', 'N/A')
        title = hit['_source'].get('title', 'N/A')[:80]
        score = hit['_score']
        print(f"{i}. [{doc_id}] {title}... (score: {score:.2f})")
    
    return len(hits) > 0

def test_vector_search(client):
    """Test vector search for TSD chunks"""
    print("\n" + "=" * 80)
    print("VECTOR SEARCH TEST (Chunk Retrieval)")
    print("=" * 80)
    
    # Just check if we can retrieve TSD chunks with filter
    search_query = {
        "query": {
            "bool": {
                "filter": {
                    "term": {"content_type": "trusted_source_document"}
                }
            }
        },
        "size": 5
    }
    
    result = client.search(index=VECTOR_INDEX, body=search_query)
    hits = result['hits']['hits']
    
    print(f"Sample TSD chunks retrieved: {len(hits)}")
    
    if hits:
        sample = hits[0]['_source']
        print(f"\nSample chunk:")
        print(f"  doc_id: {sample.get('doc_id', 'N/A')}")
        print(f"  chunk_id: {sample.get('chunk_id', 'N/A')}")
        print(f"  content_type: {sample.get('content_type', 'N/A')}")
        print(f"  text preview: {sample.get('text', '')[:100]}...")
    
    return len(hits) > 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test TSD searchability in OpenSearch')
    parser.add_argument('--manifest', default='wb_natcat_tsd_manifest_lexical.jsonl', 
                       help='Path to manifest file')
    
    args = parser.parse_args()
    
    try:
        client = get_opensearch_client()
        
        # Run tests
        keyword_count, vector_count = test_tsd_count(client)
        test_sample_tsd_retrieval(client, args.manifest)
        bm25_works = test_bm25_search(client)
        vector_works = test_vector_search(client)
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"TSDs indexed in keyword index: {keyword_count}")
        print(f"TSD chunks indexed in vector index: {vector_count}")
        print(f"BM25 search working: {'✓ YES' if bm25_works else '✗ NO'}")
        print(f"Vector search working: {'✓ YES' if vector_works else '✗ NO'}")
        
        if keyword_count > 0 and vector_count > 0 and bm25_works and vector_works:
            print("\n✓ TSDs are searchable - safe to proceed with bulk processing")
        else:
            print("\n✗ Issues detected - investigate before bulk processing")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
