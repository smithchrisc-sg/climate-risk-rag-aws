from typing import Dict, Any
from models.request import SearchRequest

def validate_request(request_body: Dict[str, Any]) -> SearchRequest:
    """Validate API v2 request format only"""
    
    # Required: query
    if 'query' not in request_body:
        raise ValueError("Missing required field: query")
    
    query = request_body['query'].strip()
    if not query:
        raise ValueError("Query cannot be empty")
    
    # Optional: parameters (with defaults)
    parameters = request_body.get('parameters', {})
    max_results = parameters.get('max_results', 20)
    
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")
    
    # Optional: filters
    filters = request_body.get('filters', {})
    if not isinstance(filters, dict):
        raise ValueError("Filters must be an object")
    
    # Validate specific filter types if present
    if 'solution_category' in filters and not isinstance(filters['solution_category'], list):
        raise ValueError("solution_category filter must be an array")
    
    if 'risk_type' in filters and not isinstance(filters['risk_type'], list):
        raise ValueError("risk_type filter must be an array")
    
    if 'solution_type' in filters and not isinstance(filters['solution_type'], list):
        raise ValueError("solution_type filter must be an array")
    
    if 'countries' in filters and not isinstance(filters['countries'], list):
        raise ValueError("countries filter must be an array")
    
    return SearchRequest(
        query=query,
        filters=filters,
        parameters=parameters
    )
