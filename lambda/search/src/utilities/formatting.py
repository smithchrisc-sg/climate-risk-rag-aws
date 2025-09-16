from typing import Dict, Any
from models.request import SearchRequest

def format_gaip_response(results: Dict[str, Any], request: SearchRequest, 
                        execution_time: float) -> Dict[str, Any]:
    """Format search results according to GAIP API specification"""
    
    formatted_results = []
    for result in results['results']:
        formatted_result = {
            'document_id': result['document_id'],
            'title': result.get('title', ''),
            'summary': result.get('summary', ''),
            'score': result['final_score'],
            'document_type': result.get('document_type', 'unknown'),
            'categories': result.get('categories', []),
            'regions': result.get('regions', []),
            'publication_date': result.get('publication_date'),
            'source_url': result.get('source_url'),
            'highlights': {
                'content': result.get('content_highlights', []),
                'title': result.get('title_highlights', [])
            },
            'metadata': {
                'search_types': result.get('search_types', []),
                'matched_concepts': result.get('matched_concepts', []),
                'file_size': result.get('file_size'),
                'processing_status': result.get('processing_status')
            }
        }
        formatted_results.append(formatted_result)
    
    # Build response
    response = {
        'results': formatted_results,
        'pagination': {
            'cursor': results['pagination'].get('cursor'),
            'next_cursor': results['pagination'].get('next_cursor'),
            'total_results': results['pagination']['total_results'],
            'returned_results': results['pagination']['returned_results'],
            'limit': request.parameters.get('limit', 20)
        },
        'execution_time': execution_time,
        'query': request.query
    }
    
    # Add facets if requested
    if request.parameters.get('include_facets', False):
        response['facets'] = generate_facets(formatted_results)
    
    return response

def generate_facets(results: list) -> Dict[str, Any]:
    """Generate faceted search results"""
    facets = {
        'categories': {},
        'regions': {},
        'document_types': {}
    }
    
    for result in results:
        # Category facets
        for category in result.get('categories', []):
            facets['categories'][category] = facets['categories'].get(category, 0) + 1
        
        # Region facets
        for region in result.get('regions', []):
            facets['regions'][region] = facets['regions'].get(region, 0) + 1
        
        # Document type facets
        doc_type = result.get('document_type', 'unknown')
        facets['document_types'][doc_type] = facets['document_types'].get(doc_type, 0) + 1
    
    return facets
