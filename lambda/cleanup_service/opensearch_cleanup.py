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
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)

class OpenSearchCleanup:
    """Handles OpenSearch cleanup operations"""
    
    def __init__(self):
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        self.vector_endpoint = os.environ.get('OPENSEARCH_VECTOR_ENDPOINT')
        self.keyword_endpoint = os.environ.get('OPENSEARCH_KEYWORD_ENDPOINT')
        
        # Set up AWS authentication
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            'es',
            session_token=credentials.token
        )
    
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
        """Generic collection cleanup - tries both endpoints"""
        # Try vector endpoint first, then keyword endpoint
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
        results = {
            'success': True,
            'documents_affected': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            # Create OpenSearch client
            client = OpenSearch(
                hosts=[{'host': endpoint.replace('https://', ''), 'port': 443}],
                http_auth=self.awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection
            )
            
            # Check if collection/index exists
            if not client.indices.exists(index=collection):
                logger.warning(f"Collection {collection} does not exist on {endpoint_type} endpoint")
                return results
            
            if document_ids:
                # Delete specific documents
                for doc_id in document_ids:
                    try:
                        if dry_run:
                            # Check if document exists
                            response = client.search(
                                index=collection,
                                body={
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"document_id": doc_id}},
                                                {"term": {"document_id.keyword": doc_id}},
                                                {"prefix": {"_id": doc_id}}
                                            ]
                                        }
                                    },
                                    "size": 0
                                }
                            )
                            doc_count = response['hits']['total']['value']
                            results['documents_affected'] += doc_count
                        else:
                            # Delete by query
                            response = client.delete_by_query(
                                index=collection,
                                body={
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {"term": {"document_id": doc_id}},
                                                {"term": {"document_id.keyword": doc_id}},
                                                {"prefix": {"_id": doc_id}}
                                            ]
                                        }
                                    }
                                }
                            )
                            results['documents_affected'] += response.get('deleted', 0)
                        
                        results['operations_performed'].append({
                            'operation': 'delete_document',
                            'collection': collection,
                            'document_id': doc_id,
                            'endpoint_type': endpoint_type,
                            'dry_run': dry_run
                        })
                        
                    except Exception as e:
                        error_msg = f"Failed to delete document {doc_id} from {collection}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['success'] = False
            else:
                # Delete all documents in collection
                try:
                    if dry_run:
                        # Count all documents
                        response = client.count(index=collection)
                        results['documents_affected'] = response['count']
                    else:
                        # Delete all documents
                        response = client.delete_by_query(
                            index=collection,
                            body={"query": {"match_all": {}}},
                            wait_for_completion=True
                        )
                        results['documents_affected'] = response.get('deleted', 0)
                    
                    results['operations_performed'].append({
                        'operation': 'delete_all_documents',
                        'collection': collection,
                        'endpoint_type': endpoint_type,
                        'dry_run': dry_run
                    })
                    
                except Exception as e:
                    error_msg = f"Failed to delete all documents from {collection}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['success'] = False
        
        except Exception as e:
            error_msg = f"OpenSearch client error for {collection} on {endpoint_type}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
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
