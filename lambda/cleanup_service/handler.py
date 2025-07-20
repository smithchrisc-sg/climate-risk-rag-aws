"""
Climate Risk RAG Cleanup Service - Lambda Handler
Main entry point for the cleanup service Lambda function
"""

import json
import logging
import sys
import os
from typing import Dict, Any

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import from src directory
from cleanup_service import CleanupService

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for cleanup service
    
    Args:
        event: Lambda event containing cleanup configuration
        context: Lambda context object
        
    Returns:
        Dict containing cleanup results and status
    """
    try:
        logger.info(f"Cleanup service invoked with event: {json.dumps(event, indent=2)}")
        
        # Initialize cleanup service
        cleanup_service = CleanupService()
        
        # Execute cleanup based on event payload
        result = cleanup_service.execute_cleanup(event)
        
        logger.info(f"Cleanup completed with result: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup service failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f"Cleanup service failed: {str(e)}",
            'results': {}
        }
