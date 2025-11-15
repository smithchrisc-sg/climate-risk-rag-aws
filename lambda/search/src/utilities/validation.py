from typing import Dict, Any
from models.request import SearchRequest
import json
import base64

def validate_request(request_body: Dict[str, Any]) -> SearchRequest:
    """Validate API v2 request format with cursor support"""
    
    # Required: query
    if 'query' not in request_body:
        raise ValueError("Missing required field: query")
    
    query = request_body['query'].strip()
    
    # Allow empty query for filter-only searches
    # if not query:
    #     raise ValueError("Query cannot be empty")
    
    # Optional: parameters (with defaults)
    parameters = request_body.get('parameters', {})
    max_results = parameters.get('max_results', 20)
    cursor = parameters.get('cursor')
    
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")
    
    # Validate cursor if present
    if cursor is not None:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode('utf-8'))
            if not isinstance(cursor_data, dict) or 'query_id' not in cursor_data or 'page' not in cursor_data:
                raise ValueError("Invalid cursor format")
        except Exception:
            raise ValueError("Invalid cursor encoding")
    
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
