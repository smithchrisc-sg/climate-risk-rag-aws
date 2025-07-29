"""
OpenSearch Cleanup Module
Handles cleanup of vector embeddings and keyword indices for AWS Managed OpenSearch
Updated from OpenSearch Serverless to Managed OpenSearch cluster
"""

import logging
import os
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import json

# Try to import OpenSearch dependencies, handle gracefully if not available
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

class OpenSearchCleanup:
    """Handles OpenSearch cleanup operations for AWS Managed OpenSearch cluster"""
    
    def __init__(self):
        if not OPENSEARCH_AVAILABLE:
            logger.warning("OpenSearch dependencies not available - OpenSearch cleanup will be skipped")
            self.opensearch_endpoint = None
            self.opensearch_username = None
            self.opensearch_password = None
            return
            
        # Use single managed cluster endpoint (same as vector-embeddings-worker and keyword-indexer)
        self.opensearch_endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        self.opensearch_username = os.environ.get('OPENSEARCH_USERNAME', 'admin')
        self.opensearch_password = os.environ.get('OPENSEARCH_PASSWORD')
        
        logger.info(f"OpenSearch cleanup initialized for managed cluster: {self.opensearch_endpoint}")
    
    def _get_opensearch_client(self) -> OpenSearch:
        """
        Create OpenSearch client for managed cluster with basic authentication
        
        Returns:
            OpenSearch client instance
        """
        if not OPENSEARCH_AVAILABLE:
            raise Exception("OpenSearch dependencies not available")
            
        if not self.opensearch_endpoint:
            raise Exception("OPENSEARCH_ENDPOINT environment variable not set")
            
        if not self.opensearch_password:
            raise Exception("OPENSEARCH_PASSWORD environment variable not set")
        
        # Extract host from endpoint URL
        host = self.opensearch_endpoint.replace('https://', '').replace('http://', '')
        logger.info(f"Creating OpenSearch client for managed cluster host: {host}")
        
        try:
            # Create client for AWS Managed OpenSearch with basic auth
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(self.opensearch_username, self.opensearch_password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = client.info()
            logger.info(f"Connected to OpenSearch cluster: {info.get('cluster_name', 'unknown')}")
            logger.info(f"OpenSearch version: {info.get('version', {}).get('number', 'unknown')}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client for managed cluster: {str(e)}", exc_info=True)
            raise Exception(f"OpenSearch client creation failed: {str(e)}")
    
    def cleanup_opensearch(self, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up OpenSearch indices in managed cluster
        
        Args:
            config: OpenSearch cleanup configuration
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dict containing cleanup results
        """
        logger.info(f"Starting OpenSearch cleanup for managed cluster. Dry run: {dry_run}")
        
        if not OPENSEARCH_AVAILABLE:
            return {
                'success': False,
                'operations_performed': [],
                'documents_affected': {},
                'errors': ['OpenSearch dependencies not available - install opensearch-py']
            }
        
        results = {
            'success': True,
            'operations_performed': [],
            'documents_affected': {},
            'errors': []
        }
        
        try:
            # Map old collection names to actual index names used in managed cluster
            collections = config.get('collections', [])
            document_ids = config.get('document_ids', [])
            
            # Convert collection names to actual index names
            index_mapping = {
                'climate-risk-vectorsearch': 'chunks_vector',  # From vector-embeddings-worker
                'climate-risk-keyword-index': 'documents',     # From keyword-indexer
                'solve-global-kr-vectors-v2': 'chunks_vector', # Legacy mapping
                'solve-global-kr-search-v2': 'documents'       # Legacy mapping
            }
            
            # Get actual indices to clean
            indices_to_clean = []
            for collection in collections:
                if collection in index_mapping:
                    indices_to_clean.append(index_mapping[collection])
                else:
                    # Try the collection name as-is (might be an actual index name)
                    indices_to_clean.append(collection)
            
            # If no specific collections specified, clean the known indices
            if not indices_to_clean:
                indices_to_clean = ['chunks_vector', 'documents']
            
            logger.info(f"Will clean indices: {indices_to_clean}")
            
            # Get single OpenSearch client for managed cluster
            client = self._get_opensearch_client()
            
            for index_name in indices_to_clean:
                try:
                    index_result = self._cleanup_index(client, index_name, document_ids, dry_run)
                    
                    results['documents_affected'][index_name] = index_result['documents_affected']
                    results['operations_performed'].extend(index_result['operations_performed'])
                    
                    if not index_result['success']:
                        results['success'] = False
                        results['errors'].extend(index_result['errors'])
                    
                    logger.info(f"Index {index_name}: {index_result['documents_affected']} documents {'would be' if dry_run else ''} deleted")
                    
                except Exception as e:
                    error_msg = f"Failed to clean index {index_name}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['success'] = False
        
        except Exception as e:
            error_msg = f"OpenSearch cleanup failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _cleanup_index(self, client: OpenSearch, index_name: str, document_ids: List[str], 
                      dry_run: bool) -> Dict[str, Any]:
        """Clean up specific index in managed OpenSearch cluster"""
        logger.info(f"Starting cleanup for index {index_name}")
        
        results = {
            'success': True,
            'documents_affected': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            # Check if index exists
            if not client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} does not exist")
                results['operations_performed'].append({
                    'operation': 'index_not_found',
                    'index': index_name,
                    'dry_run': dry_run
                })
                return results
            
            # Get document count
            try:
                count_response = client.count(index=index_name)
                doc_count = count_response['count']
                logger.info(f"Index {index_name} contains {doc_count} documents")
                
                results['documents_affected'] = doc_count
                results['operations_performed'].append({
                    'operation': 'index_discovered',
                    'index': index_name,
                    'documents_found': doc_count,
                    'dry_run': dry_run
                })
                
                if doc_count == 0:
                    logger.info(f"Index {index_name} is already empty")
                    return results
                
            except Exception as e:
                logger.error(f"Failed to count documents in index {index_name}: {e}")
                results['errors'].append(f"Failed to count documents: {str(e)}")
                results['success'] = False
                return results
            
            if not dry_run and doc_count > 0:
                # Delete documents from index
                try:
                    if document_ids:
                        # Delete specific documents
                        deleted_count = self._delete_specific_documents(client, index_name, document_ids)
                    else:
                        # Delete all documents
                        deleted_count = self._delete_all_documents(client, index_name)
                    
                    results['operations_performed'].append({
                        'operation': 'documents_deleted',
                        'index': index_name,
                        'documents_deleted': deleted_count,
                        'deletion_method': 'specific_documents' if document_ids else 'all_documents',
                        'dry_run': dry_run
                    })
                    
                    logger.info(f"Successfully deleted {deleted_count} documents from index {index_name}")
                    
                except Exception as delete_error:
                    logger.error(f"Failed to delete from index {index_name}: {delete_error}")
                    results['errors'].append(f"Failed to delete from index {index_name}: {str(delete_error)}")
                    results['success'] = False
        
        except Exception as e:
            error_msg = f"OpenSearch index cleanup error for {index_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        logger.info(f"Cleanup completed for index {index_name}: {results}")
        return results
    
    def _delete_all_documents(self, client: OpenSearch, index_name: str) -> int:
        """Delete all documents from an index"""
        try:
            # Use delete_by_query to delete all documents
            response = client.delete_by_query(
                index=index_name,
                body={
                    "query": {
                        "match_all": {}
                    }
                },
                wait_for_completion=True,
                refresh=True
            )
            
            deleted_count = response.get('deleted', 0)
            logger.info(f"Deleted {deleted_count} documents using delete_by_query")
            return deleted_count
            
        except Exception as e:
            logger.warning(f"delete_by_query failed, falling back to individual deletion: {e}")
            # Fallback to individual document deletion
            return self._delete_documents_individually(client, index_name)
    
    def _delete_specific_documents(self, client: OpenSearch, index_name: str, document_ids: List[str]) -> int:
        """Delete specific documents by ID"""
        deleted_count = 0
        
        for doc_id in document_ids:
            try:
                client.delete(index=index_name, id=doc_id)
                deleted_count += 1
                logger.debug(f"Deleted document {doc_id} from {index_name}")
            except Exception as e:
                if '404' not in str(e):  # Ignore not found errors
                    logger.warning(f"Failed to delete document {doc_id}: {e}")
        
        # Refresh index after deletions
        client.indices.refresh(index=index_name)
        
        logger.info(f"Deleted {deleted_count} specific documents from {index_name}")
        return deleted_count
    
    def _delete_documents_individually(self, client: OpenSearch, index_name: str) -> int:
        """Delete all documents individually (fallback method)"""
        deleted_count = 0
        
        try:
            # Get all document IDs in batches
            scroll_response = client.search(
                index=index_name,
                body={
                    "query": {"match_all": {}},
                    "size": 1000,
                    "_source": False
                },
                scroll='5m'
            )
            
            scroll_id = scroll_response['_scroll_id']
            hits = scroll_response['hits']['hits']
            
            while hits:
                # Delete this batch of documents
                for hit in hits:
                    try:
                        client.delete(index=index_name, id=hit['_id'])
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete document {hit['_id']}: {e}")
                
                # Get next batch
                scroll_response = client.scroll(scroll_id=scroll_id, scroll='5m')
                hits = scroll_response['hits']['hits']
            
            # Clear scroll
            client.clear_scroll(scroll_id=scroll_id)
            
            # Refresh index
            client.indices.refresh(index=index_name)
            
        except Exception as e:
            logger.error(f"Individual deletion failed: {e}")
            raise
        
        logger.info(f"Individually deleted {deleted_count} documents from {index_name}")
        return deleted_count
    
    def get_opensearch_status(self) -> Dict[str, Any]:
        """
        Get current OpenSearch status for managed cluster
        
        Returns:
            Dict containing OpenSearch status information
        """
        status = {
            'managed_cluster': {
                'endpoint': self.opensearch_endpoint,
                'status': 'unknown',
                'indices': {}
            },
            'errors': []
        }
        
        if not OPENSEARCH_AVAILABLE:
            status['errors'].append("OpenSearch dependencies not available")
            return status
        
        # Check managed cluster
        if self.opensearch_endpoint:
            try:
                client = self._get_opensearch_client()
                
                # Get cluster health
                health = client.cluster.health()
                status['managed_cluster']['status'] = health['status']
                
                # Get indices information
                try:
                    indices_response = client.cat.indices(format='json')
                    for idx in indices_response:
                        index_name = idx.get('index', idx.get('i', 'unknown'))
                        doc_count = idx.get('docs.count', '0')
                        status['managed_cluster']['indices'][index_name] = {
                            'document_count': int(doc_count) if doc_count.isdigit() else 0,
                            'health': idx.get('health', 'unknown'),
                            'status': idx.get('status', 'unknown')
                        }
                except Exception as indices_error:
                    logger.warning(f"Failed to get indices info: {indices_error}")
                    # Fallback: try to get info for known indices
                    known_indices = ['chunks_vector', 'documents']
                    for index_name in known_indices:
                        try:
                            if client.indices.exists(index=index_name):
                                count_response = client.count(index=index_name)
                                status['managed_cluster']['indices'][index_name] = {
                                    'document_count': count_response['count'],
                                    'health': 'unknown',
                                    'status': 'exists'
                                }
                            else:
                                status['managed_cluster']['indices'][index_name] = {
                                    'document_count': 0,
                                    'health': 'unknown',
                                    'status': 'not_found'
                                }
                        except Exception as e:
                            status['managed_cluster']['indices'][index_name] = {
                                'document_count': 0,
                                'health': 'error',
                                'status': f"Error: {str(e)}"
                            }
                        
            except Exception as e:
                status['managed_cluster']['status'] = 'failed'
                status['errors'].append(f"Managed cluster error: {str(e)}")
        else:
            status['errors'].append("OPENSEARCH_ENDPOINT not configured")
        
        return status
