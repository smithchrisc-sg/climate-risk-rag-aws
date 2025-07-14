"""
Neptune Cleanup Module
Handles cleanup of knowledge graph triples and entities
"""

import logging
import os
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import json
import requests
from requests.auth import HTTPBasicAuth
import urllib.parse

logger = logging.getLogger(__name__)

class NeptuneCleanup:
    """Handles Neptune knowledge graph cleanup operations"""
    
    def __init__(self):
        self.neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT')
        self.neptune_port = os.environ.get('NEPTUNE_PORT', '8182')
        
        if not self.neptune_endpoint:
            logger.warning("NEPTUNE_ENDPOINT not configured - Neptune cleanup will be skipped")
        
        # Construct SPARQL endpoint URL
        if self.neptune_endpoint:
            self.sparql_endpoint = f"https://{self.neptune_endpoint}:{self.neptune_port}/sparql"
        else:
            self.sparql_endpoint = None
    
    def cleanup_neptune(self, config: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up Neptune knowledge graph
        
        Args:
            config: Neptune cleanup configuration
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dict containing cleanup results
        """
        logger.info(f"Starting Neptune cleanup. Dry run: {dry_run}")
        
        results = {
            'success': True,
            'operations_performed': [],
            'triples_affected': 0,
            'errors': []
        }
        
        if not self.sparql_endpoint:
            results['success'] = False
            results['errors'].append("Neptune endpoint not configured")
            return results
        
        try:
            document_ids = config.get('document_ids', [])
            clear_all_triples = config.get('clear_all_triples', False)
            
            if clear_all_triples and not document_ids:
                # Clear all document-related triples (preserve ontology)
                result = self._clear_all_document_triples(dry_run)
                results['triples_affected'] = result['triples_affected']
                results['operations_performed'].extend(result['operations_performed'])
                if not result['success']:
                    results['success'] = False
                    results['errors'].extend(result['errors'])
            
            elif document_ids:
                # Clear specific document triples
                for doc_id in document_ids:
                    try:
                        result = self._clear_document_triples(doc_id, dry_run)
                        results['triples_affected'] += result['triples_affected']
                        results['operations_performed'].extend(result['operations_performed'])
                        
                        if not result['success']:
                            results['success'] = False
                            results['errors'].extend(result['errors'])
                        
                        logger.info(f"Document {doc_id}: {result['triples_affected']} triples {'would be' if dry_run else ''} deleted")
                        
                    except Exception as e:
                        error_msg = f"Failed to clean document {doc_id}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['success'] = False
            
            else:
                logger.info("No cleanup operations specified for Neptune")
        
        except Exception as e:
            error_msg = f"Neptune cleanup failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _clear_document_triples(self, document_id: str, dry_run: bool) -> Dict[str, Any]:
        """
        Clear triples related to a specific document
        
        Args:
            document_id: Document ID to clean
            dry_run: If True, only count triples
            
        Returns:
            Dict containing operation results
        """
        results = {
            'success': True,
            'triples_affected': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            # SPARQL queries to find and delete document-related triples
            document_uri = f"<http://climate-risk.org/document/{document_id}>"
            
            if dry_run:
                # Count triples that would be deleted
                count_queries = [
                    # Triples where document is subject
                    f"SELECT (COUNT(*) as ?count) WHERE {{ {document_uri} ?p ?o }}",
                    # Triples where document is object
                    f"SELECT (COUNT(*) as ?count) WHERE {{ ?s ?p {document_uri} }}",
                    # Triples related to document chunks
                    f"SELECT (COUNT(*) as ?count) WHERE {{ ?s <http://climate-risk.org/hasDocument> {document_uri} . ?s ?p ?o }}",
                    # Triples related to document entities
                    f"SELECT (COUNT(*) as ?count) WHERE {{ ?s <http://climate-risk.org/extractedFrom> {document_uri} . ?s ?p ?o }}"
                ]
                
                total_count = 0
                for query in count_queries:
                    try:
                        response = self._execute_sparql_query(query)
                        if response and 'results' in response and 'bindings' in response['results']:
                            bindings = response['results']['bindings']
                            if bindings and 'count' in bindings[0]:
                                count = int(bindings[0]['count']['value'])
                                total_count += count
                    except Exception as e:
                        logger.warning(f"Failed to execute count query: {str(e)}")
                
                results['triples_affected'] = total_count
                results['operations_performed'].append({
                    'operation': 'count_document_triples',
                    'document_id': document_id,
                    'triples_found': total_count,
                    'dry_run': True
                })
            
            else:
                # Delete triples
                delete_queries = [
                    # Delete triples where document is subject
                    f"DELETE WHERE {{ {document_uri} ?p ?o }}",
                    # Delete triples where document is object
                    f"DELETE WHERE {{ ?s ?p {document_uri} }}",
                    # Delete triples related to document chunks
                    f"DELETE WHERE {{ ?s <http://climate-risk.org/hasDocument> {document_uri} . ?s ?p ?o }}",
                    # Delete triples related to document entities
                    f"DELETE WHERE {{ ?s <http://climate-risk.org/extractedFrom> {document_uri} . ?s ?p ?o }}"
                ]
                
                total_deleted = 0
                for i, query in enumerate(delete_queries):
                    try:
                        response = self._execute_sparql_update(query)
                        # Neptune doesn't return count of deleted triples, so we estimate
                        # This is a limitation we'll note in the results
                        results['operations_performed'].append({
                            'operation': f'delete_document_triples_query_{i+1}',
                            'document_id': document_id,
                            'query_executed': True,
                            'dry_run': False
                        })
                    except Exception as e:
                        error_msg = f"Failed to execute delete query {i+1}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['success'] = False
                
                # Note: Neptune doesn't provide exact count of deleted triples
                results['triples_affected'] = "unknown (Neptune limitation)"
        
        except Exception as e:
            error_msg = f"Failed to clear document triples for {document_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _clear_all_document_triples(self, dry_run: bool) -> Dict[str, Any]:
        """
        Clear all document-related triples while preserving ontology
        
        Args:
            dry_run: If True, only count triples
            
        Returns:
            Dict containing operation results
        """
        results = {
            'success': True,
            'triples_affected': 0,
            'operations_performed': [],
            'errors': []
        }
        
        try:
            if dry_run:
                # Count all document-related triples
                count_queries = [
                    # All document instances
                    "SELECT (COUNT(*) as ?count) WHERE { ?s a <http://climate-risk.org/Document> . ?s ?p ?o }",
                    # All chunk instances
                    "SELECT (COUNT(*) as ?count) WHERE { ?s a <http://climate-risk.org/DocumentChunk> . ?s ?p ?o }",
                    # All entity instances
                    "SELECT (COUNT(*) as ?count) WHERE { ?s a <http://climate-risk.org/Entity> . ?s ?p ?o }"
                ]
                
                total_count = 0
                for query in count_queries:
                    try:
                        response = self._execute_sparql_query(query)
                        if response and 'results' in response and 'bindings' in response['results']:
                            bindings = response['results']['bindings']
                            if bindings and 'count' in bindings[0]:
                                count = int(bindings[0]['count']['value'])
                                total_count += count
                    except Exception as e:
                        logger.warning(f"Failed to execute count query: {str(e)}")
                
                results['triples_affected'] = total_count
                results['operations_performed'].append({
                    'operation': 'count_all_document_triples',
                    'triples_found': total_count,
                    'dry_run': True
                })
            
            else:
                # Delete all document-related triples
                delete_queries = [
                    # Delete all document instances and their properties
                    "DELETE WHERE { ?s a <http://climate-risk.org/Document> . ?s ?p ?o }",
                    # Delete all chunk instances and their properties
                    "DELETE WHERE { ?s a <http://climate-risk.org/DocumentChunk> . ?s ?p ?o }",
                    # Delete all entity instances and their properties
                    "DELETE WHERE { ?s a <http://climate-risk.org/Entity> . ?s ?p ?o }"
                ]
                
                for i, query in enumerate(delete_queries):
                    try:
                        response = self._execute_sparql_update(query)
                        results['operations_performed'].append({
                            'operation': f'delete_all_document_triples_query_{i+1}',
                            'query_executed': True,
                            'dry_run': False
                        })
                    except Exception as e:
                        error_msg = f"Failed to execute delete query {i+1}: {str(e)}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        results['success'] = False
                
                # Note: Neptune doesn't provide exact count of deleted triples
                results['triples_affected'] = "unknown (Neptune limitation)"
        
        except Exception as e:
            error_msg = f"Failed to clear all document triples: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['success'] = False
            results['errors'].append(error_msg)
        
        return results
    
    def _execute_sparql_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Execute SPARQL SELECT query"""
        try:
            headers = {
                'Accept': 'application/sparql-results+json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'query': query}
            
            response = requests.post(
                self.sparql_endpoint,
                headers=headers,
                data=data,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"SPARQL query failed: {str(e)}")
            raise
    
    def _execute_sparql_update(self, query: str) -> bool:
        """Execute SPARQL UPDATE query"""
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'update': query}
            
            response = requests.post(
                self.sparql_endpoint,
                headers=headers,
                data=data,
                timeout=30
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"SPARQL update failed: {str(e)}")
            raise
    
    def get_neptune_status(self) -> Dict[str, Any]:
        """
        Get current Neptune status for reporting
        
        Returns:
            Dict containing Neptune status information
        """
        status = {
            'endpoint': self.neptune_endpoint,
            'sparql_endpoint': self.sparql_endpoint,
            'status': 'unknown',
            'triple_counts': {},
            'errors': []
        }
        
        if not self.sparql_endpoint:
            status['status'] = 'not_configured'
            status['errors'].append("Neptune endpoint not configured")
            return status
        
        try:
            # Test connection with a simple query
            test_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
            response = self._execute_sparql_query(test_query)
            
            if response and 'results' in response:
                status['status'] = 'connected'
                
                # Get counts for different types of triples
                count_queries = {
                    'total_triples': "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }",
                    'documents': "SELECT (COUNT(*) as ?count) WHERE { ?s a <http://climate-risk.org/Document> }",
                    'chunks': "SELECT (COUNT(*) as ?count) WHERE { ?s a <http://climate-risk.org/DocumentChunk> }",
                    'entities': "SELECT (COUNT(*) as ?count) WHERE { ?s a <http://climate-risk.org/Entity> }"
                }
                
                for count_type, query in count_queries.items():
                    try:
                        response = self._execute_sparql_query(query)
                        if response and 'results' in response and 'bindings' in response['results']:
                            bindings = response['results']['bindings']
                            if bindings and 'count' in bindings[0]:
                                count = int(bindings[0]['count']['value'])
                                status['triple_counts'][count_type] = count
                    except Exception as e:
                        status['triple_counts'][count_type] = f"Error: {str(e)}"
            else:
                status['status'] = 'query_failed'
                
        except Exception as e:
            status['status'] = 'connection_failed'
            status['errors'].append(f"Neptune connection failed: {str(e)}")
        
        return status
