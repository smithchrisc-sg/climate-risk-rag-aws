"""
OpenSearch Cleanup Module
Handles cleanup of vector embeddings and keyword indices
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
    from requests_aws4auth import AWS4Auth
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)

class OpenSearchCleanup:
    """Handles OpenSearch cleanup operations"""
    
    def __init__(self):
        if not OPENSEARCH_AVAILABLE:
            logger.warning("OpenSearch dependencies not available - OpenSearch cleanup will be skipped")
            self.region = None
            self.vector_endpoint = None
            self.keyword_endpoint = None
            self.awsauth = None
            return
            
        self.region = boto3.Session().region_name or 'us-east-1'
        self.vector_endpoint = os.environ.get('OPENSEARCH_VECTOR_ENDPOINT')
        self.keyword_endpoint = os.environ.get('OPENSEARCH_KEYWORD_ENDPOINT')
        
        # Set up AWS authentication for OpenSearch Serverless
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'aoss',  # Use 'aoss' for OpenSearch Serverless
            session_token=credentials.token
        )
    
    def _get_opensearch_client(self, endpoint: str) -> OpenSearch:
        """
        Create OpenSearch client for the given endpoint
        
        Args:
            endpoint: OpenSearch endpoint URL
            
        Returns:
            OpenSearch client instance
        """
        if not OPENSEARCH_AVAILABLE:
            raise Exception("OpenSearch dependencies not available")
            
        # Extract host from endpoint URL
        host = endpoint.replace('https://', '').replace('http://', '')
        logger.info(f"Creating OpenSearch client for host: {host}")
        
        try:
            # Create client for OpenSearch Serverless
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=self.awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            logger.info(f"Successfully created OpenSearch client for {host}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch client for {host}: {str(e)}", exc_info=True)
            raise Exception(f"OpenSearch client creation failed for {host}: {str(e)}")
    
    def cleanup_opensearch(self, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up OpenSearch collections
        
        Args:
            config: OpenSearch cleanup configuration
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dict containing cleanup results
        """
        logger.info(f"Starting OpenSearch cleanup. Dry run: {dry_run}")
        
        if not OPENSEARCH_AVAILABLE:
            return {
                'success': False,
                'operations_performed': [],
                'documents_affected': {},
                'errors': ['OpenSearch dependencies not available - install opensearch-py and requests-aws4auth']
            }
        
        results = {
            'success': True,
            'operations_performed': [],
            'documents_affected': {},
            'errors': []
        }
        
        try:
            collections = config.get('collections', ['climate-risk-vectorsearch', 'climate-risk-keyword-index'])
            document_ids = config.get('document_ids', [])
            
            for collection in collections:
                try:
                    if 'vectorsearch' in collection.lower():
                        collection_result = self._cleanup_vector_collection(
                            collection, document_ids, dry_run
                        )
                    elif 'keyword' in collection.lower():
                        collection_result = self._cleanup_keyword_collection(
                            collection, document_ids, dry_run
                        )
                    else:
                        # Generic cleanup approach
                        collection_result = self._cleanup_generic_collection(
                            collection, document_ids, dry_run
                        )
                    
                    results['documents_affected'][collection] = collection_result['documents_affected']
                    results['operations_performed'].extend(collection_result['operations_performed'])
                    
                    if not collection_result['success']:
                        results['success'] = False
                        results['errors'].extend(collection_result['errors'])
                    
                    logger.info(f"Collection {collection}: {collection_result['documents_affected']} documents {'would be' if dry_run else ''} deleted")
                    
                except Exception as e:
                    error_msg = f"Failed to clean collection {collection}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['success'] = False
        
        except Exception as e:
            error_msg = f"OpenSearch cleanup failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _cleanup_vector_collection(self, collection: str, document_ids: List[str], dry_run: bool) -> Dict[str, Any]:
        """Clean up vector search collection"""
        if not self.vector_endpoint:
            return {
                'success': False,
                'documents_affected': 0,
                'operations_performed': [],
                'errors': ['Vector endpoint not configured']
            }
        
        return self._cleanup_collection_by_endpoint(
            self.vector_endpoint, collection, document_ids, dry_run, 'vector'
        )
    
    def _cleanup_keyword_collection(self, collection: str, document_ids: List[str], dry_run: bool) -> Dict[str, Any]:
        """Clean up keyword search collection"""
        if not self.keyword_endpoint:
            return {
                'success': False,
                'documents_affected': 0,
                'operations_performed': [],
                'errors': ['Keyword endpoint not configured']
            }
        
        return self._cleanup_collection_by_endpoint(
            self.keyword_endpoint, collection, document_ids, dry_run, 'keyword'
        )
    
    def _cleanup_generic_collection(self, collection: str, document_ids: List[str], dry_run: bool) -> Dict[str, Any]:
        """Generic collection cleanup - maps collection names to correct endpoints"""
        # Map known collection names to their correct endpoints
        collection_endpoint_map = {
            'solve-global-kr-vectors-v2': (self.vector_endpoint, 'vector'),
            'solve-global-kr-search-v2': (self.keyword_endpoint, 'keyword')
        }
        
        # Check if we have a specific mapping for this collection
        if collection in collection_endpoint_map:
            endpoint, endpoint_type = collection_endpoint_map[collection]
            if endpoint:
                try:
                    return self._cleanup_collection_by_endpoint(
                        endpoint, collection, document_ids, dry_run, endpoint_type
                    )
                except Exception as e:
                    logger.error(f"Failed to clean {collection} via {endpoint_type} endpoint: {str(e)}")
                    return {
                        'success': False,
                        'documents_affected': 0,
                        'operations_performed': [],
                        'errors': [f'Failed to connect to {endpoint_type} endpoint for collection {collection}: {str(e)}']
                    }
        
        # Fallback: Try both endpoints for unknown collections
        for endpoint, endpoint_type in [(self.vector_endpoint, 'vector'), (self.keyword_endpoint, 'keyword')]:
            if endpoint:
                try:
                    result = self._cleanup_collection_by_endpoint(
                        endpoint, collection, document_ids, dry_run, endpoint_type
                    )
                    if result['success'] or result['documents_affected'] > 0:
                        return result
                except Exception as e:
                    logger.warning(f"Failed to clean {collection} via {endpoint_type} endpoint: {str(e)}")
        
        return {
            'success': False,
            'documents_affected': 0,
            'operations_performed': [],
            'errors': [f'No valid endpoint found for collection {collection}']
        }
    
    def _cleanup_collection_by_endpoint(self, endpoint: str, collection: str, document_ids: List[str], 
                                      dry_run: bool, endpoint_type: str) -> Dict[str, Any]:
        """Clean up collection using specific endpoint"""
        logger.info(f"Starting cleanup for collection {collection} via {endpoint_type} endpoint: {endpoint}")
        
        results = {
            'success': True,
            'documents_affected': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            # Get OpenSearch client
            logger.info(f"Creating OpenSearch client for {endpoint_type} endpoint")
            client = self._get_opensearch_client(endpoint)
            logger.info(f"Successfully created OpenSearch client for {endpoint_type}")
            
            # Try to discover what indices actually exist in the collection
            logger.info(f"Attempting to discover indices in collection {collection}")
            
            # Try different approaches to find indices
            possible_indices = [
                collection,  # Same as collection name
                f"{collection}-index",  # Collection name with -index suffix
                "documents",  # Generic documents index
                "vectors",  # Generic vectors index
                "embeddings",  # Generic embeddings index
                "*"  # Wildcard to match any index
            ]
            
            documents_found = 0
            indices_found = []
            
            for index_name in possible_indices:
                try:
                    logger.info(f"Trying index name: {index_name}")
                    
                    if index_name == "*":
                        # Try to list all indices
                        try:
                            indices_response = client.cat.indices(format='json')
                            logger.info(f"Found indices via cat.indices: {indices_response}")
                            if indices_response:
                                for idx in indices_response:
                                    index_name = idx.get('index', idx.get('i', 'unknown'))
                                    doc_count = int(idx.get('docs.count', '0'))
                                    indices_found.append(index_name)
                                    documents_found += doc_count
                                    logger.info(f"Index {index_name} has {doc_count} documents")
                        except Exception as cat_error:
                            logger.info(f"cat.indices failed: {cat_error}")
                    else:
                        # Try to search this specific index
                        response = client.search(
                            index=index_name,
                            body={
                                "query": {"match_all": {}},
                                "size": 0
                            }
                        )
                        doc_count = response['hits']['total']['value']
                        if doc_count > 0:
                            logger.info(f"Found {doc_count} documents in index {index_name}")
                            documents_found += doc_count
                            indices_found.append(index_name)
                        else:
                            logger.info(f"Index {index_name} exists but is empty")
                            indices_found.append(index_name)
                            
                except Exception as e:
                    error_str = str(e).lower()
                    if 'index_not_found' in error_str or '404' in error_str:
                        logger.info(f"Index {index_name} does not exist")
                    else:
                        logger.warning(f"Error checking index {index_name}: {e}")
            
            logger.info(f"Discovery complete. Found indices: {indices_found}, Total documents: {documents_found}")
            
            if documents_found > 0 or indices_found:
                results['documents_affected'] = documents_found
                results['operations_performed'].append({
                    'operation': 'discovery_successful',
                    'collection': collection,
                    'endpoint_type': endpoint_type,
                    'indices_found': indices_found,
                    'documents_found': documents_found,
                    'dry_run': dry_run
                })
                
                if not dry_run and documents_found > 0:
                    # Actually delete documents from found indices
                    for index_name in indices_found:
                        try:
                            logger.info(f"Attempting to delete all documents from index {index_name}")
                            
                            # OpenSearch Serverless doesn't support delete_by_query
                            # So we need to get all document IDs first, then delete individually
                            
                            # First, get all document IDs
                            search_response = client.search(
                                index=index_name,
                                body={
                                    "query": {"match_all": {}},
                                    "size": 1000,  # Get up to 1000 docs
                                    "_source": False  # We only need IDs
                                }
                            )
                            
                            hits = search_response.get('hits', {}).get('hits', [])
                            deleted_count = 0
                            
                            logger.info(f"Found {len(hits)} documents to delete from {index_name}")
                            
                            # Delete each document individually
                            for hit in hits:
                                doc_id = hit['_id']
                                try:
                                    client.delete(index=index_name, id=doc_id)
                                    deleted_count += 1
                                    logger.debug(f"Deleted document {doc_id} from {index_name}")
                                except Exception as doc_delete_error:
                                    logger.warning(f"Failed to delete document {doc_id}: {doc_delete_error}")
                            
                            logger.info(f"Successfully deleted {deleted_count} documents from index {index_name}")
                            
                            # Update the operation result
                            for op in results['operations_performed']:
                                if op.get('operation') == 'discovery_successful' and op.get('collection') == collection:
                                    op['documents_actually_deleted'] = deleted_count
                                    op['deletion_method'] = 'individual_document_deletion'
                                    break
                            
                        except Exception as delete_error:
                            logger.error(f"Failed to delete from index {index_name}: {delete_error}")
                            results['errors'].append(f"Failed to delete from index {index_name}: {str(delete_error)}")
                            results['success'] = False
            else:
                # No indices found
                results['operations_performed'].append({
                    'operation': 'collection_empty_or_not_found',
                    'collection': collection,
                    'endpoint_type': endpoint_type,
                    'dry_run': dry_run
                })
        
        except Exception as e:
            error_msg = f"OpenSearch client error for {collection} on {endpoint_type}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        logger.info(f"Cleanup completed for {collection} via {endpoint_type}: {results}")
        return results
    
    def get_opensearch_status(self) -> Dict[str, Any]:
        """
        Get current OpenSearch status for reporting
        
        Returns:
            Dict containing OpenSearch status information
        """
        status = {
            'vector_endpoint': {
                'endpoint': self.vector_endpoint,
                'status': 'unknown',
                'collections': {}
            },
            'keyword_endpoint': {
                'endpoint': self.keyword_endpoint,
                'status': 'unknown',
                'collections': {}
            },
            'errors': []
        }
        
        # Check vector endpoint
        if self.vector_endpoint:
            try:
                client = OpenSearch(
                    hosts=[{'host': self.vector_endpoint.replace('https://', ''), 'port': 443}],
                    http_auth=self.awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection
                )
                
                # Get cluster health
                health = client.cluster.health()
                status['vector_endpoint']['status'] = health['status']
                
                # Get indices
                indices = client.indices.get_alias(index="*")
                for index_name in indices:
                    try:
                        count_response = client.count(index=index_name)
                        status['vector_endpoint']['collections'][index_name] = count_response['count']
                    except Exception as e:
                        status['vector_endpoint']['collections'][index_name] = f"Error: {str(e)}"
                        
            except Exception as e:
                status['vector_endpoint']['status'] = 'failed'
                status['errors'].append(f"Vector endpoint error: {str(e)}")
        
        # Check keyword endpoint
        if self.keyword_endpoint:
            try:
                client = OpenSearch(
                    hosts=[{'host': self.keyword_endpoint.replace('https://', ''), 'port': 443}],
                    http_auth=self.awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection
                )
                
                # Get cluster health
                health = client.cluster.health()
                status['keyword_endpoint']['status'] = health['status']
                
                # Get indices
                indices = client.indices.get_alias(index="*")
                for index_name in indices:
                    try:
                        count_response = client.count(index=index_name)
                        status['keyword_endpoint']['collections'][index_name] = count_response['count']
                    except Exception as e:
                        status['keyword_endpoint']['collections'][index_name] = f"Error: {str(e)}"
                        
            except Exception as e:
                status['keyword_endpoint']['status'] = 'failed'
                status['errors'].append(f"Keyword endpoint error: {str(e)}")
        
        return status
