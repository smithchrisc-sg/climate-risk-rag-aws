"""
Response Builder

Builds standardized Lambda responses for different scenarios.
"""

import json
from typing import Any, Dict


class ResponseBuilder:
    """
    Builds standardized Lambda responses.
    """
    
    def success_response(self, body: Any) -> Dict[str, Any]:
        """
        Create a successful Lambda response.
        
        Args:
            body: Response body content
            
        Returns:
            Standardized success response
        """
        return self._create_response(200, body)
    
    def error_response(self, error_message: str, status_code: int = 500) -> Dict[str, Any]:
        """
        Create an error Lambda response.
        
        Args:
            error_message: Error message to include
            status_code: HTTP status code (default: 500)
            
        Returns:
            Standardized error response
        """
        return self._create_response(status_code, {
            'error': error_message,
            'status': 'failed'
        })
    
    def _create_response(self, status_code: int, body: Any) -> Dict[str, Any]:
        """
        Create standardized Lambda response.
        
        Args:
            status_code: HTTP status code
            body: Response body
            
        Returns:
            Lambda response dictionary
        """
        return {
            'statusCode': status_code,
            'body': json.dumps(body) if not isinstance(body, str) else body
        }
