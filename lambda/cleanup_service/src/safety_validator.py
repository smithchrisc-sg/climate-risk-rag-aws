"""
Safety Validator Module
Validates cleanup payloads and enforces safety checks
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SafetyValidator:
    """Validates cleanup operations and enforces safety limits"""
    
    def __init__(self):
        # Default safety limits
        self.default_limits = {
            'max_documents_to_delete': 100,
            'require_confirmation': True,
            'allow_full_cleanup': False,
            'max_s3_objects_per_operation': 10000
        }
    
    def validate_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate cleanup payload for safety and correctness
        
        Args:
            payload: Cleanup configuration payload
            
        Returns:
            Dict containing validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'safety_checks_passed': True
        }
        
        try:
            # Check required structure
            if 'cleanup_scope' not in payload:
                validation_result['valid'] = False
                validation_result['errors'].append("Missing 'cleanup_scope' in payload")
                return validation_result
            
            cleanup_scope = payload['cleanup_scope']
            safety_checks = payload.get('safety_checks', {})
            
            # Validate safety checks
            safety_validation = self._validate_safety_checks(safety_checks)
            validation_result['errors'].extend(safety_validation['errors'])
            validation_result['warnings'].extend(safety_validation['warnings'])
            
            if not safety_validation['valid']:
                validation_result['valid'] = False
                validation_result['safety_checks_passed'] = False
            
            # Validate database cleanup configuration
            if 'databases' in cleanup_scope:
                db_validation = self._validate_database_config(cleanup_scope['databases'])
                validation_result['errors'].extend(db_validation['errors'])
                validation_result['warnings'].extend(db_validation['warnings'])
                
                if not db_validation['valid']:
                    validation_result['valid'] = False
            
            # Validate S3 cleanup configuration
            if 's3_data_lake' in cleanup_scope:
                s3_validation = self._validate_s3_config(cleanup_scope['s3_data_lake'])
                validation_result['errors'].extend(s3_validation['errors'])
                validation_result['warnings'].extend(s3_validation['warnings'])
                
                if not s3_validation['valid']:
                    validation_result['valid'] = False
            
            # Check for dangerous operations
            danger_check = self._check_dangerous_operations(cleanup_scope, safety_checks)
            validation_result['warnings'].extend(danger_check['warnings'])
            
            if danger_check['requires_confirmation'] and not safety_checks.get('confirmation_provided', False):
                validation_result['valid'] = False
                validation_result['errors'].append("Dangerous operation requires explicit confirmation")
            
        except Exception as e:
            logger.error(f"Payload validation failed: {str(e)}", exc_info=True)
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _validate_safety_checks(self, safety_checks: Dict[str, Any]) -> Dict[str, Any]:
        """Validate safety check configuration"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check max documents limit
        max_docs = safety_checks.get('max_documents_to_delete', self.default_limits['max_documents_to_delete'])
        if not isinstance(max_docs, int) or max_docs < 0:
            result['valid'] = False
            result['errors'].append("max_documents_to_delete must be a non-negative integer")
        elif max_docs > 1000:
            result['warnings'].append(f"max_documents_to_delete is very high ({max_docs})")
        
        # Check dry run flag
        dry_run = safety_checks.get('dry_run', False)
        if not isinstance(dry_run, bool):
            result['valid'] = False
            result['errors'].append("dry_run must be a boolean")
        
        # Check confirmation requirement
        require_confirmation = safety_checks.get('require_confirmation', self.default_limits['require_confirmation'])
        if not isinstance(require_confirmation, bool):
            result['valid'] = False
            result['errors'].append("require_confirmation must be a boolean")
        
        return result
    
    def _validate_database_config(self, databases_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate database cleanup configuration"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validate PostgreSQL config
        if 'postgresql' in databases_config:
            pg_config = databases_config['postgresql']
            
            if not isinstance(pg_config.get('enabled', False), bool):
                result['errors'].append("postgresql.enabled must be a boolean")
                result['valid'] = False
            
            if pg_config.get('enabled', False):
                # Check tables list
                tables = pg_config.get('tables', [])
                if not isinstance(tables, list):
                    result['errors'].append("postgresql.tables must be a list")
                    result['valid'] = False
                else:
                    allowed_tables = [
                        'document_processing_status',
                        'nlp_processing_status',
                        'vector_processing_status',
                        'keyword_processing_status',
                        'kg_processing_status'
                    ]
                    
                    for table in tables:
                        if table not in allowed_tables:
                            result['warnings'].append(f"Table '{table}' is not in the standard list")
                
                # Check document IDs
                doc_ids = pg_config.get('document_ids', [])
                if not isinstance(doc_ids, list):
                    result['errors'].append("postgresql.document_ids must be a list")
                    result['valid'] = False
                elif len(doc_ids) == 0:
                    result['warnings'].append("No document_ids specified - will clean ALL records")
        
        # Validate OpenSearch config
        if 'opensearch' in databases_config:
            os_config = databases_config['opensearch']
            
            if not isinstance(os_config.get('enabled', False), bool):
                result['errors'].append("opensearch.enabled must be a boolean")
                result['valid'] = False
            
            if os_config.get('enabled', False):
                collections = os_config.get('collections', [])
                if not isinstance(collections, list):
                    result['errors'].append("opensearch.collections must be a list")
                    result['valid'] = False
                
                doc_ids = os_config.get('document_ids', [])
                if not isinstance(doc_ids, list):
                    result['errors'].append("opensearch.document_ids must be a list")
                    result['valid'] = False
                elif len(doc_ids) == 0:
                    result['warnings'].append("No document_ids specified - will clean ALL documents from collections")
        
        # Validate Neptune config
        if 'neptune' in databases_config:
            neptune_config = databases_config['neptune']
            
            if not isinstance(neptune_config.get('enabled', False), bool):
                result['errors'].append("neptune.enabled must be a boolean")
                result['valid'] = False
            
            if neptune_config.get('enabled', False):
                clear_all = neptune_config.get('clear_all_triples', False)
                if not isinstance(clear_all, bool):
                    result['errors'].append("neptune.clear_all_triples must be a boolean")
                    result['valid'] = False
                elif clear_all:
                    result['warnings'].append("clear_all_triples=true will delete ALL document-related triples")
                
                doc_ids = neptune_config.get('document_ids', [])
                if not isinstance(doc_ids, list):
                    result['errors'].append("neptune.document_ids must be a list")
                    result['valid'] = False
        
        return result
    
    def _validate_s3_config(self, s3_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate S3 cleanup configuration"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not isinstance(s3_config.get('enabled', False), bool):
            result['errors'].append("s3_data_lake.enabled must be a boolean")
            result['valid'] = False
        
        if s3_config.get('enabled', False):
            # Check buckets list
            buckets = s3_config.get('buckets', [])
            if not isinstance(buckets, list):
                result['errors'].append("s3_data_lake.buckets must be a list")
                result['valid'] = False
            elif len(buckets) == 0:
                result['warnings'].append("No buckets specified for S3 cleanup")
            
            # Check document IDs
            doc_ids = s3_config.get('document_ids', [])
            if not isinstance(doc_ids, list):
                result['errors'].append("s3_data_lake.document_ids must be a list")
                result['valid'] = False
            elif len(doc_ids) == 0:
                result['warnings'].append("No document_ids specified - will clean ALL objects from buckets")
            
            # Check preserve structure flag
            preserve_structure = s3_config.get('preserve_structure', True)
            if not isinstance(preserve_structure, bool):
                result['errors'].append("s3_data_lake.preserve_structure must be a boolean")
                result['valid'] = False
        
        return result
    
    def _check_dangerous_operations(self, cleanup_scope: Dict[str, Any], 
                                  safety_checks: Dict[str, Any]) -> Dict[str, Any]:
        """Check for potentially dangerous operations"""
        result = {
            'requires_confirmation': False,
            'warnings': []
        }
        
        # Check for full cleanup operations (no document IDs specified)
        dangerous_operations = []
        
        # PostgreSQL full cleanup
        pg_config = cleanup_scope.get('databases', {}).get('postgresql', {})
        if pg_config.get('enabled', False) and len(pg_config.get('document_ids', [])) == 0:
            dangerous_operations.append("PostgreSQL: All records will be deleted")
        
        # OpenSearch full cleanup
        os_config = cleanup_scope.get('databases', {}).get('opensearch', {})
        if os_config.get('enabled', False) and len(os_config.get('document_ids', [])) == 0:
            dangerous_operations.append("OpenSearch: All documents will be deleted from collections")
        
        # Neptune full cleanup
        neptune_config = cleanup_scope.get('databases', {}).get('neptune', {})
        if neptune_config.get('enabled', False):
            if neptune_config.get('clear_all_triples', False):
                dangerous_operations.append("Neptune: ALL document-related triples will be deleted")
            elif len(neptune_config.get('document_ids', [])) == 0:
                dangerous_operations.append("Neptune: All document triples will be deleted")
        
        # S3 full cleanup
        s3_config = cleanup_scope.get('s3_data_lake', {})
        if s3_config.get('enabled', False) and len(s3_config.get('document_ids', [])) == 0:
            dangerous_operations.append("S3: All objects will be deleted from data lake buckets")
        
        if dangerous_operations:
            result['requires_confirmation'] = safety_checks.get('require_confirmation', True)
            result['warnings'].extend([
                "DANGEROUS OPERATIONS DETECTED:",
                *dangerous_operations,
                "These operations will delete large amounts of data!"
            ])
        
        # Check for dry run bypass
        if not safety_checks.get('dry_run', False) and dangerous_operations:
            result['warnings'].append("Consider running with dry_run=true first to preview changes")
        
        return result
    
    def generate_confirmation_summary(self, payload: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of what will be deleted
        
        Args:
            payload: Cleanup configuration payload
            
        Returns:
            String summary of operations
        """
        summary_lines = ["CLEANUP OPERATION SUMMARY:", ""]
        
        cleanup_scope = payload.get('cleanup_scope', {})
        safety_checks = payload.get('safety_checks', {})
        
        dry_run = safety_checks.get('dry_run', False)
        if dry_run:
            summary_lines.append("🔍 DRY RUN MODE - No actual deletions will be performed")
        else:
            summary_lines.append("⚠️  LIVE MODE - Actual deletions will be performed")
        
        summary_lines.append("")
        
        # Database operations
        databases = cleanup_scope.get('databases', {})
        
        if databases.get('postgresql', {}).get('enabled', False):
            pg_config = databases['postgresql']
            doc_ids = pg_config.get('document_ids', [])
            tables = pg_config.get('tables', [])
            
            if doc_ids:
                summary_lines.append(f"📊 PostgreSQL: Delete records for {len(doc_ids)} documents from {len(tables)} tables")
            else:
                summary_lines.append(f"📊 PostgreSQL: Delete ALL records from {len(tables)} tables")
        
        if databases.get('opensearch', {}).get('enabled', False):
            os_config = databases['opensearch']
            doc_ids = os_config.get('document_ids', [])
            collections = os_config.get('collections', [])
            
            if doc_ids:
                summary_lines.append(f"🔍 OpenSearch: Delete documents for {len(doc_ids)} documents from {len(collections)} collections")
            else:
                summary_lines.append(f"🔍 OpenSearch: Delete ALL documents from {len(collections)} collections")
        
        if databases.get('neptune', {}).get('enabled', False):
            neptune_config = databases['neptune']
            doc_ids = neptune_config.get('document_ids', [])
            clear_all = neptune_config.get('clear_all_triples', False)
            
            if clear_all:
                summary_lines.append("🕸️  Neptune: Delete ALL document-related triples")
            elif doc_ids:
                summary_lines.append(f"🕸️  Neptune: Delete triples for {len(doc_ids)} documents")
            else:
                summary_lines.append("🕸️  Neptune: Delete all document triples")
        
        # S3 operations
        s3_config = cleanup_scope.get('s3_data_lake', {})
        if s3_config.get('enabled', False):
            doc_ids = s3_config.get('document_ids', [])
            buckets = s3_config.get('buckets', [])
            
            if doc_ids:
                summary_lines.append(f"🗂️  S3: Delete objects for {len(doc_ids)} documents from {len(buckets)} buckets")
            else:
                summary_lines.append(f"🗂️  S3: Delete ALL objects from {len(buckets)} buckets")
        
        summary_lines.extend(["", "Please review carefully before proceeding!"])
        
        return "\n".join(summary_lines)
