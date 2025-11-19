"""
Add this to handler.py to test TSD searchability from within Lambda
"""
import json
from src.search.bm25_search_service import BM25SearchService
from src.search.vector_search_service import VectorSearchService

def test_tsd_searchability(event, context):
    """Test if TSDs are searchable in OpenSearch"""
    results = {}
    
    try:
        bm25_service = BM25SearchService()
        vector_service = VectorSearchService()
        
        # Test 1: Count TSDs in keyword index
        keyword_query = {
            "query": {"term": {"content_type": "trusted_source_document"}},
            "size": 0
        }
        keyword_result = bm25_service.client.search(index="documents_keyword", body=keyword_query)
        results['tsd_count_keyword'] = keyword_result['hits']['total']['value']
        
        # Test 2: Count TSD chunks in vector index
        vector_result = vector_service.client.search(index="chunks_vector", body=keyword_query)
        results['tsd_chunks_vector'] = vector_result['hits']['total']['value']
        
        # Test 3: BM25 search for TSDs
        bm25_query = {
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
            "size": 5
        }
        bm25_result = bm25_service.client.search(index="documents_keyword", body=bm25_query)
        results['bm25_search_hits'] = bm25_result['hits']['total']['value']
        results['bm25_sample'] = [
            {
                'doc_id': hit['_source'].get('doc_id'),
                'title': hit['_source'].get('title', '')[:80],
                'score': hit['_score']
            }
            for hit in bm25_result['hits']['hits'][:3]
        ]
        
        # Test 4: Vector search for TSD chunks
        vector_query = {
            "query": {
                "bool": {
                    "filter": {"term": {"content_type": "trusted_source_document"}}
                }
            },
            "size": 5
        }
        vector_result = vector_service.client.search(index="chunks_vector", body=vector_query)
        results['vector_search_hits'] = vector_result['hits']['total']['value']
        
        results['status'] = 'success'
        results['searchable'] = (
            results['tsd_count_keyword'] > 0 and 
            results['tsd_chunks_vector'] > 0 and
            results['bm25_search_hits'] > 0
        )
        
    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
        import traceback
        results['traceback'] = traceback.format_exc()
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, indent=2)
    }
