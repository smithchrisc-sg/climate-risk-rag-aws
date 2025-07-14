"""
Climate Risk RAG Cleanup Service
Centralized cleanup of test artifacts across PostgreSQL, OpenSearch, Neptune, and S3
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

from database_cleanup import DatabaseCleanup
from opensearch_cleanup import OpenSearchCleanup
from neptune_cleanup import NeptuneCleanup
from s3_cleanup import S3Cleanup
from safety_validator import SafetyValidator

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class CleanupService:
    """Main cleanup service orchestrator"""
    
    def __init__(self):
        self.database_cleanup = DatabaseCleanup()
        self.opensearch_cleanup = OpenSearchCleanup()
        self.neptune_cleanup = NeptuneCleanup()
        self.s3_cleanup = S3Cleanup()
        self.safety_validator = SafetyValidator()
        
    def execute_cleanup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute cleanup operations based on payload configuration
        
        Args:
            payload: Cleanup configuration payload
            
        Returns:
            Dict containing cleanup results and status
        """
        logger.info(f"Starting cleanup operation with payload: {json.dumps(payload, indent=2)}")
        
        # Validate payload and safety checks
        validation_result = self.safety_validator.validate_payload(payload)
        if not validation_result['valid']:
            return {
                'success': False,
                'error': f"Payload validation failed: {validation_result['errors']}",
                'results': {}
            }
        
        cleanup_scope = payload.get('cleanup_scope', {})
        safety_checks = payload.get('safety_checks', {})
        
        # Check if this is a dry run
        dry_run = safety_checks.get('dry_run', False)
        if dry_run:
            logger.info("DRY RUN MODE - No actual deletions will be performed")
        
        results = {
            'dry_run': dry_run,
            'databases': {},
            's3_data_lake': {},
            'summary': {
                'total_operations': 0,
                'successful_operations': 0,
                'failed_operations': 0,
                'errors': []
            }
        }
        
        try:
            # Execute database cleanups
            if cleanup_scope.get('databases', {}).get('postgresql', {}).get('enabled', False):
                logger.info("Starting PostgreSQL cleanup")
                results['databases']['postgresql'] = self._execute_postgresql_cleanup(
                    cleanup_scope['databases']['postgresql'], dry_run
                )
                results['summary']['total_operations'] += 1
                if results['databases']['postgresql']['success']:
                    results['summary']['successful_operations'] += 1
                else:
                    results['summary']['failed_operations'] += 1
                    results['summary']['errors'].extend(results['databases']['postgresql'].get('errors', []))
            
            if cleanup_scope.get('databases', {}).get('opensearch', {}).get('enabled', False):
                logger.info("Starting OpenSearch cleanup")
                results['databases']['opensearch'] = self._execute_opensearch_cleanup(
                    cleanup_scope['databases']['opensearch'], dry_run
                )
                results['summary']['total_operations'] += 1
                if results['databases']['opensearch']['success']:
                    results['summary']['successful_operations'] += 1
                else:
                    results['summary']['failed_operations'] += 1
                    results['summary']['errors'].extend(results['databases']['opensearch'].get('errors', []))
            
            if cleanup_scope.get('databases', {}).get('neptune', {}).get('enabled', False):
                logger.info("Starting Neptune cleanup")
                results['databases']['neptune'] = self._execute_neptune_cleanup(
                    cleanup_scope['databases']['neptune'], dry_run
                )
                results['summary']['total_operations'] += 1
                if results['databases']['neptune']['success']:
                    results['summary']['successful_operations'] += 1
                else:
                    results['summary']['failed_operations'] += 1
                    results['summary']['errors'].extend(results['databases']['neptune'].get('errors', []))
            
            # Execute S3 cleanup
            if cleanup_scope.get('s3_data_lake', {}).get('enabled', False):
                logger.info("Starting S3 data lake cleanup")
                results['s3_data_lake'] = self._execute_s3_cleanup(
                    cleanup_scope['s3_data_lake'], dry_run
                )
                results['summary']['total_operations'] += 1
                if results['s3_data_lake']['success']:
                    results['summary']['successful_operations'] += 1
                else:
                    results['summary']['failed_operations'] += 1
                    results['summary']['errors'].extend(results['s3_data_lake'].get('errors', []))
            
            # Determine overall success
            overall_success = results['summary']['failed_operations'] == 0
            
            logger.info(f"Cleanup operation completed. Success: {overall_success}")
            logger.info(f"Summary: {results['summary']}")
            
            return {
                'success': overall_success,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'results': results
            }
    
    def _execute_postgresql_cleanup(self, config: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        """Execute PostgreSQL cleanup operations"""
        try:
            return self.database_cleanup.cleanup_postgresql(config, dry_run)
        except Exception as e:
            logger.error(f"PostgreSQL cleanup failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'operations_performed': [],
                'errors': [str(e)]
            }
    
    def _execute_opensearch_cleanup(self, config: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        """Execute OpenSearch cleanup operations"""
        try:
            return self.opensearch_cleanup.cleanup_opensearch(config, dry_run)
        except Exception as e:
            logger.error(f"OpenSearch cleanup failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'operations_performed': [],
                'errors': [str(e)]
            }
    
    def _execute_neptune_cleanup(self, config: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        """Execute Neptune cleanup operations"""
        try:
            return self.neptune_cleanup.cleanup_neptune(config, dry_run)
        except Exception as e:
            logger.error(f"Neptune cleanup failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'operations_performed': [],
                'errors': [str(e)]
            }
    
    def _execute_s3_cleanup(self, config: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        """Execute S3 data lake cleanup operations"""
        try:
            return self.s3_cleanup.cleanup_s3_data_lake(config, dry_run)
        except Exception as e:
            logger.error(f"S3 cleanup failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'operations_performed': [],
                'errors': [str(e)]
            }


def lambda_handler(event, context):
    """
    AWS Lambda handler for cleanup service
    
    Args:
        event: Lambda event containing cleanup payload
        context: Lambda context
        
    Returns:
        Dict containing cleanup results
    """
    logger.info(f"Cleanup service invoked with event: {json.dumps(event, indent=2)}")
    
    try:
        # Initialize cleanup service
        cleanup_service = CleanupService()
        
        # Execute cleanup
        result = cleanup_service.execute_cleanup(event)
        
        # Return result
        return {
            'statusCode': 200 if result['success'] else 500,
            'body': json.dumps(result, indent=2)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f"Lambda handler error: {str(e)}"
            }, indent=2)
        }
