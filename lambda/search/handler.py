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
from models.response import SearchResponse
from utilities.formatting import format_gaip_response
from utilities.validation import validate_request

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for GAIP search API"""

    logger = logging.getLogger("search_handler")
    logger.setLevel(logging.INFO)
    
    start_time = time.time()
    
    try:
        # Parse request
        request_body = json.loads(event['body'])
        user_context = event.get('requestContext', {}).get('authorizer', {})

        logger.info(f"Request body: {request_body}")
        logger.info(f"User context: {user_context}")
        
        # Validate request
        search_request = validate_request(request_body)
        
        # Initialize search coordinator
        coordinator = SearchCoordinator()
        
        # Execute search
        results = asyncio.run(coordinator.search(
            query=search_request.query,
            filters=search_request.filters,
            parameters=search_request.parameters,
            user_context=user_context
        ))
        
        # Format response
        execution_time = time.time() - start_time
        response = format_gaip_response(results, search_request, execution_time)
        
        logger.info(f"Final response: {json.dumps(response, indent=2)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return error_response(400, 'INVALID_REQUEST', str(e))
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return error_response(500, 'INTERNAL_ERROR', 'Search processing failed')

def error_response(status_code: int, error_code: str, message: str) -> Dict[str, Any]:
    """Generate error response"""
    logger = logging.getLogger("search_handler")
    logger.setLevel(logging.INFO)
    logger.error(f"Error response: {error_code} - {message}")
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': {
                'code': error_code,
                'message': message
            }
        })
    }
