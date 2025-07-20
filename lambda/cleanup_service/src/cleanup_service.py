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
            
            # Generate comprehensive cleanup summary
            cleanup_summary = self._generate_cleanup_summary(results)
            
            logger.info(f"Cleanup operation completed. Success: {overall_success}")
            logger.info(f"Summary: {results['summary']}")
            
            return {
                'success': overall_success,
                'results': results,
                'cleanup_summary': cleanup_summary
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
    
    def _generate_cleanup_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive, readable cleanup summary"""
        summary = {
            'overview': {
                'dry_run': results.get('dry_run', False),
                'total_items_to_clean': 0,
                'operations_count': 0,
                'estimated_impact': 'LOW'
            },
            'detailed_operations': {
                'postgresql': [],
                'opensearch': [],
                'neptune': [],
                's3': []
            },
            'commands_to_execute': {
                'sql_statements': [],
                'sparql_statements': [],
                'opensearch_operations': [],
                's3_operations': []
            }
        }
        
        # Process PostgreSQL operations
        if 'databases' in results and 'postgresql' in results['databases']:
            pg_data = results['databases']['postgresql']
            total_pg_records = 0
            
            for op in pg_data.get('operations_performed', []):
                if op.get('operation') == 'delete_records':
                    table = op.get('table')
                    count = op.get('records_affected', 0)
                    total_pg_records += count
                    
                    summary['detailed_operations']['postgresql'].append({
                        'table': table,
                        'records_to_delete': count,
                        'operation': 'DELETE ALL RECORDS'
                    })
                    
                    # Add SQL command
                    sql_cmd = f"DELETE FROM {table};"
                    summary['commands_to_execute']['sql_statements'].append({
                        'table': table,
                        'command': sql_cmd,
                        'estimated_rows_affected': count
                    })
            
            summary['overview']['total_items_to_clean'] += total_pg_records
        
        # Process OpenSearch operations
        if 'databases' in results and 'opensearch' in results['databases']:
            os_data = results['databases']['opensearch']
            total_os_docs = 0
            
            for op in os_data.get('operations_performed', []):
                if op.get('operation') == 'discovery_successful':
                    collection = op.get('collection')
                    indices = op.get('indices_found', [])
                    doc_count = op.get('documents_found', 0)
                    total_os_docs += doc_count
                    
                    summary['detailed_operations']['opensearch'].append({
                        'collection': collection,
                        'indices': indices,
                        'documents_to_delete': doc_count,
                        'operation': 'DELETE BY QUERY'
                    })
                    
                    # Add OpenSearch commands
                    for index in indices:
                        os_cmd = {
                            'index': index,
                            'method': 'POST',
                            'endpoint': f"/{index}/_delete_by_query",
                            'body': '{"query": {"match_all": {}}}',
                            'estimated_docs_affected': doc_count
                        }
                        summary['commands_to_execute']['opensearch_operations'].append(os_cmd)
            
            summary['overview']['total_items_to_clean'] += total_os_docs
        
        # Process Neptune operations
        if 'databases' in results and 'neptune' in results['databases']:
            neptune_data = results['databases']['neptune']
            total_triples = 0
            
            for op in neptune_data.get('operations_performed', []):
                if op.get('operation') == 'neptune_discovery':
                    discovery = op.get('discovery_results', {})
                    total_triples = op.get('total_triples', 0)
                    
                    summary['detailed_operations']['neptune'].append({
                        'total_triples': total_triples,
                        'documents': discovery.get('documents', 0),
                        'document_chunks': discovery.get('document_chunks', 0),
                        'entities': discovery.get('entities', 0),
                        'relationships': discovery.get('relationships', 0),
                        'operation': 'DELETE ALL DOCUMENT TRIPLES'
                    })
                    
                    # Add SPARQL commands (using correct namespace)
                    sparql_commands = [
                        {
                            'description': 'Delete all document instances and related triples',
                            'query': 'DELETE WHERE { ?s ?p ?o . ?s a <http://solve.global/knowledge-commons/schema#Document> }',
                            'estimated_triples_affected': 'Unknown (Neptune limitation)'
                        },
                        {
                            'description': 'Delete all document chunk instances and related triples', 
                            'query': 'DELETE WHERE { ?s ?p ?o . ?s a <http://solve.global/knowledge-commons/schema#DocumentChunk> }',
                            'estimated_triples_affected': 'Unknown (Neptune limitation)'
                        },
                        {
                            'description': 'Delete all document section instances and related triples',
                            'query': 'DELETE WHERE { ?s ?p ?o . ?s a <http://solve.global/knowledge-commons/schema#DocumentSection> }',
                            'estimated_triples_affected': 'Unknown (Neptune limitation)'
                        }
                    ]
                    summary['commands_to_execute']['sparql_statements'] = sparql_commands
            
            summary['overview']['total_items_to_clean'] += total_triples
        
        # Process S3 operations
        if 's3_data_lake' in results:
            s3_data = results['s3_data_lake']
            total_s3_objects = 0
            
            for op in s3_data.get('operations_performed', []):
                if op.get('operation') == 'count_all_objects':
                    bucket = op.get('bucket')
                    count = op.get('objects_found', 0)
                    size = op.get('total_size', 0)
                    total_s3_objects += count
                    
                    summary['detailed_operations']['s3'].append({
                        'bucket': bucket,
                        'objects_to_delete': count,
                        'total_size_bytes': size,
                        'total_size_mb': round(size / 1024 / 1024, 2),
                        'operation': 'DELETE ALL OBJECTS'
                    })
                    
                    # Add S3 command
                    s3_cmd = {
                        'bucket': bucket,
                        'operation': 'delete_all_objects',
                        'aws_cli_equivalent': f'aws s3 rm s3://{bucket}/ --recursive',
                        'estimated_objects_affected': count
                    }
                    summary['commands_to_execute']['s3_operations'].append(s3_cmd)
            
            summary['overview']['total_items_to_clean'] += total_s3_objects
        
        # Calculate impact level
        total_items = summary['overview']['total_items_to_clean']
        if total_items == 0:
            summary['overview']['estimated_impact'] = 'NONE'
        elif total_items < 100:
            summary['overview']['estimated_impact'] = 'LOW'
        elif total_items < 1000:
            summary['overview']['estimated_impact'] = 'MEDIUM'
        else:
            summary['overview']['estimated_impact'] = 'HIGH'
        
        summary['overview']['operations_count'] = (
            len(summary['commands_to_execute']['sql_statements']) +
            len(summary['commands_to_execute']['sparql_statements']) +
            len(summary['commands_to_execute']['opensearch_operations']) +
            len(summary['commands_to_execute']['s3_operations'])
        )
        
        return summary


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
