#!/usr/bin/env python3
"""
OpenSearch Keyword Indexer for Solution Ingestion
Handles keyword indexing of solution documents in OpenSearch.
"""

import logging
import json
from typing import List
from datetime import datetime

from opensearchpy import OpenSearch, RequestsHttpConnection
from models.solution import Solution
from generators.integrated_rdf_chunk_generator import IntegratedChunk

logger = logging.getLogger(__name__)

class OpenSearchKeywordIndexer:
    """Handles OpenSearch keyword indexing operations for documents."""
    
    def __init__(self, env):
        self.env = env
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize OpenSearch client."""
        try:
            # Extract host from endpoint URL
            endpoint = self.env.opensearch_endpoint
            if endpoint.startswith('https://'):
                host = endpoint[8:]  # Remove https://
            else:
                host = endpoint
            
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(self.env.opensearch_username, self.env.opensearch_password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = self.client.info()
            logger.info(f"Connected to OpenSearch: {info.get('cluster_name')}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test OpenSearch connection."""
        try:
            info = self.client.info()
            logger.info(f"OpenSearch connection successful: {info.get('version', {}).get('number', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"OpenSearch connection failed: {e}")
            return False
    
    def index_document(self, solution: Solution, pseudo_doc: str) -> bool:
        """Index a single document."""
        try:
            doc_body = self._prepare_document_body(solution)
            doc_body['full_text'] = pseudo_doc  # Add the pseudo-document text
            
            response = self.client.index(
                index='documents_keyword',
                id=solution.doc_id,
                body=doc_body
            )
            
            logger.info(f"Indexed document {solution.doc_id}: {response.get('result', 'unknown')}")
            return response.get('result') in ['created', 'updated']
            
        except Exception as e:
            logger.error(f"Failed to index document {solution.doc_id}: {e}")
            return False
    
    def search(self, query: str, limit: int = 10) -> List[dict]:
        """Search documents by keyword."""
        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "full_text", "description", "content"]
                    }
                },
                "size": limit
            }
            
            response = self.client.search(
                index='documents_keyword',
                body=search_body
            )
            
            results = []
            for hit in response.get('hits', {}).get('hits', []):
                result = hit.get('_source', {})
                result['score'] = hit.get('_score', 0)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def index_documents(self, solutions: List[Solution]):
        """Index solutions in documents_keyword index."""
        logger.info(f"Indexing {len(solutions)} documents in OpenSearch")
        
        indexed_count = 0
        for solution in solutions:
            try:
                # Prepare document for keyword index
                doc_body = self._prepare_document_body(solution)
                
                # Index document
                response = self.client.index(
                    index='documents_keyword',
                    id=solution.doc_id,
                    body=doc_body
                )
                
                if response.get('result') in ['created', 'updated']:
                    indexed_count += 1
                else:
                    logger.warning(f"Unexpected response for {solution.doc_id}: {response}")
                
            except Exception as e:
                logger.error(f"Failed to index document {solution.doc_id}: {e}")
                continue
        
        logger.info(f"Successfully indexed {indexed_count}/{len(solutions)} documents")
    
    def _prepare_document_body(self, solution: Solution) -> dict:
        """Prepare document body for keyword indexing."""
        
        # Get document text
        if hasattr(solution, 'pseudo_document_text') and solution.pseudo_document_text:
            content = solution.pseudo_document_text
        else:
            content = solution.get_full_text()
        
        # Extract keywords from solution metadata
        keywords = []
        if solution.type_of_risk:
            keywords.append(solution.type_of_risk)
        if solution.type_of_solution:
            keywords.append(solution.type_of_solution)
        if solution.theme:
            keywords.append(solution.theme)
        if solution.country:
            keywords.append(solution.country)
        
        return {
            'doc_id': solution.doc_id,
            'content_type': 'solution',  # Tag as solution document
            'title': solution.name,
            'content': content,
            'document_keywords': keywords,
            'structure_info': {
                'chunk_count': 3,  # Always 3 chunks for solutions
                'has_sections': True
            },
            'metadata': {
                'source_file': solution.source_file,
                'country': solution.country,
                'type_of_risk': solution.type_of_risk,
                'type_of_solution': solution.type_of_solution,
                'theme': solution.theme,
                'year_of_implementation': solution.year_of_implementation,
                'source_url': solution.source_url
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _prepare_chunk_body(self, chunk: IntegratedChunk) -> dict:
        """Prepare chunk body for vector indexing."""
        
        return {
            'chunk_id': chunk.chunk_id,
            'doc_id': chunk.doc_id,
            'chunk_index': self._get_chunk_index(chunk.chunk_type),
            'text': chunk.text,
            'chunk_metadata': {
                'character_count': chunk.character_count,
                'chunk_type': chunk.chunk_type,
                'section_name': chunk.metadata.get('section_name', ''),
                'solution_name': chunk.metadata.get('solution_name', ''),
                'country': chunk.metadata.get('country', ''),
                'type_of_risk': chunk.metadata.get('type_of_risk', ''),
                'type_of_solution': chunk.metadata.get('type_of_solution', '')
            },
            'embedding_metadata': {
                'model': 'amazon.titan-embed-text-v1',
                'status': 'pending'  # Will be updated when vectors are generated
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_chunk_index(self, chunk_type: str) -> int:
        """Get numeric index for chunk type."""
        type_mapping = {
            'desc': 1,
            'highlights': 2,
            'results': 3
        }
        return type_mapping.get(chunk_type, 1)
    
    def check_indices_exist(self) -> dict:
        """Check if required indices exist."""
        indices = ['documents_keyword', 'chunks_vector']
        status = {}
        
        for index in indices:
            try:
                exists = self.client.indices.exists(index=index)
                status[index] = exists
                if exists:
                    count = self.client.count(index=index)['count']
                    status[f"{index}_count"] = count
                else:
                    status[f"{index}_count"] = 0
            except Exception as e:
                logger.error(f"Error checking index {index}: {e}")
                status[index] = False
                status[f"{index}_count"] = 0
        
        return status
    
    def get_indexing_stats(self) -> dict:
        """Get indexing statistics."""
        try:
            stats = self.check_indices_exist()
            return {
                'documents_indexed': stats.get('documents_keyword_count', 0),
                'chunks_indexed': stats.get('chunks_vector_count', 0),
                'indices_exist': {
                    'documents_keyword': stats.get('documents_keyword', False),
                    'chunks_vector': stats.get('chunks_vector', False)
                }
            }
        except Exception as e:
            logger.error(f"Failed to get indexing stats: {e}")
            return {
                'documents_indexed': 0,
                'chunks_indexed': 0,
                'indices_exist': {
                    'documents_keyword': False,
                    'chunks_vector': False
                }
            }