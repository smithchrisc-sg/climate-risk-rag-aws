import json
import boto3
import uuid
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

class SearchSessionManager:
    """Manages S3-based search sessions for stable pagination"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'solve-global-kr-search-sessions-861276078413-us-east-1'
        self.logger = logging.getLogger(__name__)
        
    def _get_session_key(self, session_id: str) -> str:
        """Generate S3 key for session storage"""
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        return f"search-sessions/{date_str}/{session_id}.json"
    
    def _create_query_hash(self, query: str, filters: Dict[str, Any]) -> str:
        """Create hash of query and filters for validation"""
        content = json.dumps({'query': query, 'filters': filters}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def create_session_with_minimal_data(self, query: str, filters: Dict[str, Any], 
                                             solution_ranking: List[Dict], solution_lookup: Dict[str, Any],
                                             page_size: int = 20) -> str:
        """Create session with minimal solution data for fast page serving"""
        
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=24)
        
        # Extract solution IDs and scores, store minimal solution data
        solution_ids = [item['solution_id'] for item in solution_ranking]
        scores = {}
        solutions_data = {}
        
        for item in solution_ranking:
            sol_id = item['solution_id']
            scores[sol_id] = {
                'combined_score': item.get('combined_score', 0.0),
                'content_score': item.get('content_score', 0.0),
                'related_documents': item.get('related_documents', [])
            }
            
            # Store minimal solution data for fast retrieval
            if sol_id in solution_lookup:
                solutions_data[sol_id] = self._convert_to_minimal_format(solution_lookup[sol_id])
        
        session_data = {
            'session_id': session_id,
            'created_at': created_at.isoformat() + 'Z',
            'expires_at': expires_at.isoformat() + 'Z',
            'page_size': page_size,
            'total_results': len(solution_ids),
            'query_metadata': {
                'query_hash': self._create_query_hash(query, filters),
                'original_query': query,
                'applied_filters': filters,
                'search_method': 'keyword_ranking',
                'computation_time_ms': 0
            },
            'ranking_data': {
                'solution_ids': solution_ids,
                'scores': scores,
                'solutions_data': solutions_data,
                'max_cached_results': len(solution_ids),
                'truncated': False
            }
        }
        
        # Store in S3
        try:
            key = self._get_session_key(session_id)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(session_data),
                ContentType='application/json',
                Expires=expires_at
            )
            
            self.logger.info(f"Created session {session_id} with {len(solution_ids)} results")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create session {session_id}: {e}")
            raise
    
    async def create_session_lightweight(self, query: str, filters: Dict[str, Any], 
                                       solution_ids: List[str], page_size: int, 
                                       metadata: Dict[str, Any] = None) -> str:
        """Create session with only solution IDs (lightweight)"""
        
        session_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=24)
        
        session_data = {
            "session_id": session_id,
            "created_at": created_at.isoformat() + 'Z',
            "expires_at": expires_at.isoformat() + 'Z',
            "query": query,
            "filters": filters,
            "page_size": page_size,
            "total_results": len(solution_ids),
            "solution_ids": solution_ids,  # Just IDs, no full content
            "metadata": metadata or {},  # Store additional metadata like RRF scores
            "ranking_metadata": {
                "has_query": bool(query and query.strip()),
                "ranking_type": "filter_only" if not query or not query.strip() else "query_based"
            }
        }
        
        # Store in S3
        try:
            key = self._get_session_key(session_id)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(session_data),
                ContentType='application/json',
                Expires=expires_at
            )
            
            self.logger.info(f"Created lightweight session {session_id} with {len(solution_ids)} solution IDs")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create lightweight session {session_id}: {e}")
            raise

    async def load_session_lightweight(self, session_id: str) -> Dict[str, Any]:
        """Load lightweight session data from S3"""
        
        try:
            key = self._get_session_key(session_id)
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            session_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Check if expired
            expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                raise SessionExpiredError(f"Session {session_id} expired")
            
            self.logger.info(f"Loaded lightweight session {session_id}")
            return session_data
            
        except self.s3_client.exceptions.NoSuchKey:
            raise SessionNotFoundError(f"Session {session_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to load lightweight session {session_id}: {e}")
            raise

    def get_page_solution_ids(self, session_data: Dict[str, Any], page: int, 
                            requested_page_size: Optional[int] = None) -> Dict[str, Any]:
        """Extract solution IDs for a specific page from lightweight session"""
        
        # Use session page size if not overridden
        page_size = requested_page_size or session_data['page_size']
        total_results = session_data['total_results']
        total_pages = (total_results + page_size - 1) // page_size
        
        # Validate page bounds
        if page < 1 or page > total_pages:
            raise ValueError(f"Page {page} out of bounds (1-{total_pages})")
        
        # Calculate slice
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_results)
        
        # Get solution IDs for this page
        solution_ids = session_data['solution_ids'][start_idx:end_idx]
        
        return {
            'solution_ids': solution_ids,
            'page_info': {
                'current_page': page,
                'total_pages': total_pages,
                'total_results': total_results,
                'page_size': page_size,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'start_result': start_idx + 1,
                'end_result': end_idx
            }
        }
    
    def _convert_to_minimal_format(self, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert solution to minimal API v2 format for session storage"""
        
        try:
            doc_id = solution_data.get('doc_id', '')
            kg_data = solution_data.get('kg_data', {})
            content = solution_data.get('content', {})
            
            title = kg_data.get('title', '') or content.get('chunk_metadata', {}).get('solution_name', '')
            description = content.get('assembled_description', '')
            
            return {
                'document_id': doc_id,
                'content_type': 'solution',
                'solution_name': title,
                'title': title,
                'relevance_score': 0.0,  # Will be set from ranking
                'publication_date': None,
                'country_regions_covered': [],
                'risk_types_addressed': [kg_data.get('riskType', '')] if kg_data.get('riskType') else [],
                'solution_categories': [],
                'solution_types': kg_data.get('solutionType', '').split(',') if kg_data.get('solutionType') else [],
                'implemented': 'unknown',
                'ppp_involvement': 'unknown',
                'summary_description': description,
                'key_highlights': [],
                'source': '',
                'related_documents': [],
                'snippets': [
                    {
                        'text': description[:200] + '...' if description and len(description) > 200 else description,
                        'page_number': 1,
                        'section': 'Description'
                    }
                ] if description else [],
                'metadata': {
                    'document_type': 'solution',
                    'categories': [],
                    'regions': [],
                    'publication_year': None,
                    'source': 'session_cache',
                    'processing_timestamp': ''
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to convert solution {solution_data.get('doc_id', 'unknown')}: {e}")
            return {
                'document_id': solution_data.get('doc_id', 'unknown'),
                'content_type': 'solution',
                'solution_name': 'Conversion error',
                'title': 'Conversion error',
                'relevance_score': 0.0,
                'summary_description': 'Error converting solution data',
                'metadata': {'source': 'conversion_error'}
            }
    
    def _convert_solution_to_api_format(self, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert solution_searcher format to API v2 format"""
        
        try:
            # Extract data from the complex solution_searcher format
            doc_id = solution_data.get('doc_id', '')
            kg_data = solution_data.get('kg_data', {})
            content = solution_data.get('content', {})
            
            # Handle case where solution_data IS the content
            if not kg_data and not content:
                # This might be a direct solution object, try to extract what we can
                title = solution_data.get('title', solution_data.get('solution_name', ''))
                description = solution_data.get('summary_description', solution_data.get('assembled_description', ''))
            else:
                title = kg_data.get('title', content.get('chunk_metadata', {}).get('solution_name', ''))
                description = content.get('assembled_description', '')
            
            # Build API v2 format solution
            return {
                'document_id': doc_id,
                'content_type': 'solution',
                'solution_name': title,
                'title': title,
                'relevance_score': solution_data.get('relevance_score', 0.0),
                'publication_date': None,
                'country_regions_covered': [],
                'risk_types_addressed': [kg_data.get('riskType', '')] if kg_data.get('riskType') else [],
                'solution_categories': [],
                'solution_types': kg_data.get('solutionType', '').split(',') if kg_data.get('solutionType') else [],
                'implemented': 'unknown',
                'ppp_involvement': 'unknown',
                'summary_description': description,
                'key_highlights': [],
                'source': '',
                'related_documents': [],
                'snippets': [
                    {
                        'text': description[:200] + '...' if description and len(description) > 200 else description,
                        'page_number': 1,
                        'section': 'Description'
                    }
                ] if description else [],
                'metadata': {
                    'document_type': 'solution',
                    'categories': [],
                    'regions': [],
                    'publication_year': None,
                    'source': '',
                    'processing_timestamp': content.get('chunk_metadata', {}).get('processing_timestamp', '') if content else ''
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to format solution {solution_data.get('doc_id', 'unknown')}: {e}")
            # Return a minimal valid solution object
            return {
                'document_id': solution_data.get('doc_id', 'unknown'),
                'content_type': 'solution',
                'solution_name': 'Solution data formatting error',
                'title': 'Solution data formatting error',
                'relevance_score': 0.0,
                'publication_date': None,
                'country_regions_covered': [],
                'risk_types_addressed': [],
                'solution_categories': [],
                'solution_types': [],
                'implemented': 'unknown',
                'ppp_involvement': 'unknown',
                'summary_description': 'Error formatting solution data',
                'key_highlights': [],
                'source': '',
                'related_documents': [],
                'snippets': [],
                'metadata': {
                    'document_type': 'solution',
                    'categories': [],
                    'regions': [],
                    'publication_year': None,
                    'source': 'error_fallback',
                    'processing_timestamp': ''
                }
            }
    
    async def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load session data from S3"""
        
        try:
            key = self._get_session_key(session_id)
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            session_data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Check if expired
            expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
            if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
                raise SessionExpiredError(f"Session {session_id} expired")
            
            self.logger.info(f"Loaded session {session_id}")
            return session_data
            
        except self.s3_client.exceptions.NoSuchKey:
            raise SessionNotFoundError(f"Session {session_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to load session {session_id}: {e}")
            raise
    
    def get_page_data(self, session_data: Dict[str, Any], page: int, 
                     requested_page_size: Optional[int] = None) -> Dict[str, Any]:
        """Extract page data from session"""
        
        # Use session page size if not overridden
        page_size = requested_page_size or session_data['page_size']
        total_results = session_data['total_results']
        total_pages = (total_results + page_size - 1) // page_size
        
        # Validate page bounds
        if page < 1 or page > total_pages:
            raise ValueError(f"Page {page} out of bounds (1-{total_pages})")
        
        # Calculate slice
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_results)
        
        # Get solution IDs for this page
        solution_ids = session_data['solution_ids'][start_idx:end_idx]
        
        return {
            'solution_ids': solution_ids,
            'page_info': {
                'current_page': page,
                'total_pages': total_pages,
                'total_results': total_results,
                'page_size': page_size,
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'start_result': start_idx + 1,
                'end_result': end_idx
            },
            'scores': session_data['ranking_metadata']
        }

class SessionNotFoundError(Exception):
    """Session not found in S3"""
    pass

class SessionExpiredError(Exception):
    """Session has expired"""
    pass
