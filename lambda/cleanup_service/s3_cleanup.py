"""
S3 Data Lake Cleanup Module
Handles cleanup of document artifacts in S3 data lake structure
"""

import logging
import os
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import json

logger = logging.getLogger(__name__)

class S3Cleanup:
    """Handles S3 data lake cleanup operations"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        # Get account ID from environment or Lambda context instead of STS call
        self.account_id = os.environ.get('AWS_ACCOUNT_ID', '861276078413')
        self.region = boto3.Session().region_name or 'us-east-1'
        
        # Standard bucket patterns
        self.bucket_patterns = {
            'source_documents': f'solve-global-kr-dl-source-documents-{self.account_id}-{self.region}',
            'text': f'solve-global-kr-dl-text-{self.account_id}-{self.region}',
            'chunks': f'solve-global-kr-dl-chunks-{self.account_id}-{self.region}',
            'embeddings': f'solve-global-kr-dl-embeddings-{self.account_id}-{self.region}',
            'keywords': f'solve-global-kr-dl-keywords-{self.account_id}-{self.region}',
            'nlp': f'solve-global-kr-dl-nlp-{self.account_id}-{self.region}',
            'neptune_ttl': f'solve-global-kr-dl-neptune-ttl-{self.account_id}-{self.region}',
            'cache': f'solve-global-kr-cache-{self.account_id}-{self.region}'
        }
    
    def cleanup_s3_data_lake(self, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up S3 data lake objects
        
        Args:
            config: S3 cleanup configuration
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dict containing cleanup results
        """
        logger.info(f"Starting S3 data lake cleanup. Dry run: {dry_run}")
        
        results = {
            'success': True,
            'operations_performed': [],
            'objects_affected': {},
            'total_objects_deleted': 0,
            'total_size_deleted': 0,
            'errors': []
        }
        
        try:
            buckets = config.get('buckets', list(self.bucket_patterns.values()))
            document_ids = config.get('document_ids', [])
            preserve_structure = config.get('preserve_structure', True)
            
            # Resolve bucket patterns to actual bucket names
            resolved_buckets = self._resolve_bucket_names(buckets)
            
            for bucket_name in resolved_buckets:
                try:
                    bucket_result = self._cleanup_bucket(
                        bucket_name, document_ids, preserve_structure, dry_run
                    )
                    
                    results['objects_affected'][bucket_name] = bucket_result['objects_affected']
                    results['total_objects_deleted'] += bucket_result['objects_affected']
                    results['total_size_deleted'] += bucket_result['size_deleted']
                    results['operations_performed'].extend(bucket_result['operations_performed'])
                    
                    if not bucket_result['success']:
                        results['success'] = False
                        results['errors'].extend(bucket_result['errors'])
                    
                    logger.info(f"Bucket {bucket_name}: {bucket_result['objects_affected']} objects {'would be' if dry_run else ''} deleted")
                    
                except Exception as e:
                    error_msg = f"Failed to clean bucket {bucket_name}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['success'] = False
        
        except Exception as e:
            error_msg = f"S3 cleanup failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _resolve_bucket_names(self, bucket_patterns: List[str]) -> List[str]:
        """
        Resolve bucket patterns to actual bucket names
        
        Args:
            bucket_patterns: List of bucket names or patterns
            
        Returns:
            List of resolved bucket names
        """
        resolved_buckets = []
        
        for pattern in bucket_patterns:
            if '*' in pattern:
                # Pattern matching - find buckets that match
                try:
                    response = self.s3_client.list_buckets()
                    pattern_prefix = pattern.replace('*', '')
                    
                    for bucket in response['Buckets']:
                        bucket_name = bucket['Name']
                        if bucket_name.startswith(pattern_prefix):
                            resolved_buckets.append(bucket_name)
                            
                except Exception as e:
                    logger.warning(f"Failed to resolve bucket pattern {pattern}: {str(e)}")
            else:
                # Direct bucket name
                resolved_buckets.append(pattern)
        
        return list(set(resolved_buckets))  # Remove duplicates
    
    def _cleanup_bucket(self, bucket_name: str, document_ids: List[str], 
                       preserve_structure: bool, dry_run: bool) -> Dict[str, Any]:
        """
        Clean up objects in a specific bucket
        
        Args:
            bucket_name: Name of bucket to clean
            document_ids: List of specific document IDs to clean (empty = all)
            preserve_structure: If True, keep folder structure
            dry_run: If True, only count objects
            
        Returns:
            Dict containing bucket cleanup results
        """
        results = {
            'success': True,
            'objects_affected': 0,
            'size_deleted': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            # Check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    logger.info(f"Bucket {bucket_name} does not exist - skipping")
                    return results
                else:
                    raise
            
            if document_ids:
                # Clean specific documents
                for doc_id in document_ids:
                    doc_result = self._cleanup_document_objects(
                        bucket_name, doc_id, preserve_structure, dry_run
                    )
                    
                    results['objects_affected'] += doc_result['objects_affected']
                    results['size_deleted'] += doc_result['size_deleted']
                    results['operations_performed'].extend(doc_result['operations_performed'])
                    
                    if not doc_result['success']:
                        results['success'] = False
                        results['errors'].extend(doc_result['errors'])
            else:
                # Clean all objects in bucket
                all_result = self._cleanup_all_objects(
                    bucket_name, preserve_structure, dry_run
                )
                
                results['objects_affected'] = all_result['objects_affected']
                results['size_deleted'] = all_result['size_deleted']
                results['operations_performed'].extend(all_result['operations_performed'])
                
                if not all_result['success']:
                    results['success'] = False
                    results['errors'].extend(all_result['errors'])
        
        except Exception as e:
            error_msg = f"Failed to clean bucket {bucket_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _cleanup_document_objects(self, bucket_name: str, document_id: str, 
                                 preserve_structure: bool, dry_run: bool) -> Dict[str, Any]:
        """Clean up objects for a specific document"""
        results = {
            'success': True,
            'objects_affected': 0,
            'size_deleted': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            # List objects with document ID prefix
            # Data lake structure: /data_lake/{doc_id}/
            prefix = f"data_lake/{document_id}/"
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
            
            objects_to_delete = []
            total_size = 0
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append({'Key': obj['Key']})
                        total_size += obj['Size']
            
            if objects_to_delete:
                results['objects_affected'] = len(objects_to_delete)
                results['size_deleted'] = total_size
                
                if dry_run:
                    results['operations_performed'].append({
                        'operation': 'count_document_objects',
                        'bucket': bucket_name,
                        'document_id': document_id,
                        'objects_found': len(objects_to_delete),
                        'total_size': total_size,
                        'dry_run': True
                    })
                else:
                    # Delete objects in batches
                    batch_size = 1000  # S3 delete limit
                    for i in range(0, len(objects_to_delete), batch_size):
                        batch = objects_to_delete[i:i + batch_size]
                        
                        response = self.s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': batch}
                        )
                        
                        deleted_count = len(response.get('Deleted', []))
                        errors = response.get('Errors', [])
                        
                        results['operations_performed'].append({
                            'operation': 'delete_document_objects_batch',
                            'bucket': bucket_name,
                            'document_id': document_id,
                            'batch_number': i // batch_size + 1,
                            'objects_deleted': deleted_count,
                            'errors': len(errors),
                            'dry_run': False
                        })
                        
                        if errors:
                            for error in errors:
                                error_msg = f"Failed to delete {error['Key']}: {error['Message']}"
                                results['errors'].append(error_msg)
                                results['success'] = False
            
            # If preserve_structure is False, also clean up the folder
            if not preserve_structure and not dry_run and objects_to_delete:
                try:
                    # Try to delete the folder itself (if empty)
                    self.s3_client.delete_object(Bucket=bucket_name, Key=prefix)
                    results['operations_performed'].append({
                        'operation': 'delete_document_folder',
                        'bucket': bucket_name,
                        'document_id': document_id,
                        'folder_key': prefix,
                        'dry_run': False
                    })
                except Exception as e:
                    # Folder deletion failure is not critical
                    logger.warning(f"Failed to delete folder {prefix}: {str(e)}")
        
        except Exception as e:
            error_msg = f"Failed to clean document {document_id} from bucket {bucket_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _cleanup_all_objects(self, bucket_name: str, preserve_structure: bool, dry_run: bool) -> Dict[str, Any]:
        """Clean up all objects in bucket"""
        results = {
            'success': True,
            'objects_affected': 0,
            'size_deleted': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket_name)
            
            objects_to_delete = []
            total_size = 0
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append({'Key': obj['Key']})
                        total_size += obj['Size']
            
            if objects_to_delete:
                results['objects_affected'] = len(objects_to_delete)
                results['size_deleted'] = total_size
                
                if dry_run:
                    results['operations_performed'].append({
                        'operation': 'count_all_objects',
                        'bucket': bucket_name,
                        'objects_found': len(objects_to_delete),
                        'total_size': total_size,
                        'dry_run': True
                    })
                else:
                    # Delete objects in batches
                    batch_size = 1000  # S3 delete limit
                    for i in range(0, len(objects_to_delete), batch_size):
                        batch = objects_to_delete[i:i + batch_size]
                        
                        response = self.s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': batch}
                        )
                        
                        deleted_count = len(response.get('Deleted', []))
                        errors = response.get('Errors', [])
                        
                        results['operations_performed'].append({
                            'operation': 'delete_all_objects_batch',
                            'bucket': bucket_name,
                            'batch_number': i // batch_size + 1,
                            'objects_deleted': deleted_count,
                            'errors': len(errors),
                            'dry_run': False
                        })
                        
                        if errors:
                            for error in errors:
                                error_msg = f"Failed to delete {error['Key']}: {error['Message']}"
                                results['errors'].append(error_msg)
                                results['success'] = False
        
        except Exception as e:
            error_msg = f"Failed to clean all objects from bucket {bucket_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def get_s3_status(self) -> Dict[str, Any]:
        """
        Get current S3 data lake status for reporting
        
        Returns:
            Dict containing S3 status information
        """
        status = {
            'buckets': {},
            'total_objects': 0,
            'total_size': 0,
            'errors': []
        }
        
        for bucket_type, bucket_name in self.bucket_patterns.items():
            try:
                # Check if bucket exists
                self.s3_client.head_bucket(Bucket=bucket_name)
                
                # Get object count and size
                paginator = self.s3_client.get_paginator('list_objects_v2')
                page_iterator = paginator.paginate(Bucket=bucket_name)
                
                object_count = 0
                total_size = 0
                
                for page in page_iterator:
                    if 'Contents' in page:
                        object_count += len(page['Contents'])
                        total_size += sum(obj['Size'] for obj in page['Contents'])
                
                status['buckets'][bucket_type] = {
                    'bucket_name': bucket_name,
                    'exists': True,
                    'object_count': object_count,
                    'total_size': total_size
                }
                
                status['total_objects'] += object_count
                status['total_size'] += total_size
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    status['buckets'][bucket_type] = {
                        'bucket_name': bucket_name,
                        'exists': False,
                        'object_count': 0,
                        'total_size': 0
                    }
                else:
                    status['buckets'][bucket_type] = {
                        'bucket_name': bucket_name,
                        'exists': 'unknown',
                        'error': str(e)
                    }
                    status['errors'].append(f"Error checking bucket {bucket_name}: {str(e)}")
            
            except Exception as e:
                status['buckets'][bucket_type] = {
                    'bucket_name': bucket_name,
                    'exists': 'unknown',
                    'error': str(e)
                }
                status['errors'].append(f"Error checking bucket {bucket_name}: {str(e)}")
        
        return status
