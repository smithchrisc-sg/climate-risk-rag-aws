from typing import Dict, Any
from models.request import SearchRequest

def validate_request(request_body: Dict[str, Any]) -> SearchRequest:
    """Validate and parse search request"""
    
    # Required fields
    if 'query' not in request_body:
        raise ValueError("Missing required field: query")
    
    query = request_body['query'].strip()
    if not query:
        raise ValueError("Query cannot be empty")
    
    # Optional filters
    filters = request_body.get('filters', {})
    if not isinstance(filters, dict):
        raise ValueError("Filters must be an object")
    
    # Validate filter values
    if 'categories' in filters and not isinstance(filters['categories'], list):
        raise ValueError("Categories filter must be an array")
    
    if 'regions' in filters and not isinstance(filters['regions'], list):
        raise ValueError("Regions filter must be an array")
    
    if 'date_range' in filters:
        date_range = filters['date_range']
        if not isinstance(date_range, dict):
            raise ValueError("Date range filter must be an object")
        if 'start' not in date_range and 'end' not in date_range:
            raise ValueError("Date range must specify start or end")
    
    # Optional parameters
    parameters = request_body.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ValueError("Parameters must be an object")
    
    # Validate parameter values
    if 'limit' in parameters:
        limit = parameters['limit']
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("Limit must be an integer between 1 and 100")
    
    if 'search_mode' in parameters:
        valid_modes = ['hybrid', 'keyword', 'vector', 'graph']
        if parameters['search_mode'] not in valid_modes:
            raise ValueError(f"Search mode must be one of: {valid_modes}")
    
    return SearchRequest(
        query=query,
        filters=filters,
        parameters=parameters
    )
