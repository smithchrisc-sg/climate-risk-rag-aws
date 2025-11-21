import json
import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from search.coordinator import SearchCoordinator
from models.request import SearchRequest
from utilities.validation import validate_request

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for GAIP search API v2"""

    logger = logging.getLogger("search_handler")
    logger.setLevel(logging.INFO)
    
    start_time = time.time()
    
    try:
        # Determine endpoint from path
        path = event.get('path', '/search')
        http_method = event.get('httpMethod', 'POST')
        
        logger.info(f"Request path: {path}, method: {http_method}")
        
        # Handle CORS preflight requests
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': ''
            }
        
        # Handle repository metadata endpoints
        if path == '/repository/last-update' and http_method == 'GET':
            return handle_repository_metadata('last-update')
        elif path == '/repository/solution-count' and http_method == 'GET':
            return handle_repository_metadata('solution-count')
        elif path == '/search' and http_method == 'POST':
            return handle_search_request(event, context, start_time)
        else:
            return error_response(404, 'NOT_FOUND', f'Endpoint not found: {http_method} {path}')
            
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return error_response(500, 'INTERNAL_ERROR', 'Request processing failed')

def handle_search_request(event: Dict[str, Any], context: Any, start_time: float) -> Dict[str, Any]:
    """Handle API v2 search requests"""
    logger = logging.getLogger("search_handler")
    
    try:
        # Parse request
        request_body = json.loads(event['body'])
        user_context = event.get('requestContext', {}).get('authorizer', {})

        logger.info(f"Request body: {request_body}")
        logger.info(f"User context: {user_context}")
        
        # Validate request (API v2 format only)
        search_request = validate_request(request_body)
        logger.info(f"Search request: {search_request}")

        
        # Initialize search coordinator
        coordinator = SearchCoordinator()
        logger.info(f"Search coordinator: {coordinator}")

        # Execute Phase 1 search (solutions)
        logger.info(f"Executing search for query: {search_request.query}")
        results = asyncio.run(coordinator.search(
            query=search_request.query,
            filters=search_request.filters,
            parameters=search_request.parameters,
            user_context=user_context
        ))
        
        logger.info(f"Search results: {results}")
        
        # Add final execution time
        execution_time = time.time() - start_time
        results['execution_time_ms'] = int(execution_time * 1000)
        
        logger.info(f"Search completed: {results.get('total_results', 0)} solutions in {execution_time:.2f}s")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(results)
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return error_response(400, 'VALIDATION_ERROR', str(e))
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return error_response(500, 'INTERNAL_ERROR', 'Search processing failed')

def handle_repository_metadata(metadata_type: str) -> Dict[str, Any]:
    """Handle repository metadata requests"""
    logger = logging.getLogger("search_handler")
    
    try:
        # Initialize search coordinator
        coordinator = SearchCoordinator()
        
        # Get repository metadata
        metadata = asyncio.run(coordinator.get_repository_metadata(metadata_type))
        
        logger.info(f"Repository metadata ({metadata_type}): {metadata}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(metadata)
        }
        
    except Exception as e:
        logger.error(f"Repository metadata error: {str(e)}")
        return error_response(500, 'INTERNAL_ERROR', 'Repository metadata request failed')

def error_response(status_code: int, error_code: str, message: str) -> Dict[str, Any]:
    """Generate API v2 error response"""
    logger = logging.getLogger("search_handler")
    logger.error(f"Error response: {error_code} - {message}")
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'error',
            'error': {
                'code': error_code,
                'message': message
            },
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        })
    }
