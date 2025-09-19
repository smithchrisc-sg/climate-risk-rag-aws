"""
Structured data models for search results and responses.
Replaces plain dictionaries with typed data classes for better type safety and consistency.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

class ResultType(Enum):
    """Type of search results returned by processor."""
    KEYWORD = "keyword"
    VECTOR = "vector"
    GRAPH = "graph"

@dataclass
class SearchResult:
    """Standardized search result format."""
    document_id: str
    title: str
    score: float
    content: str
    content_highlights: List[str] = field(default_factory=list)
    title_highlights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Optional[ResultType] = None
    
    # Additional fields from current AWS system
    search_type: Optional[str] = None
    search_types: List[str] = field(default_factory=list)
    final_score: Optional[float] = None
    normalized_score: Optional[float] = None
    
    def __post_init__(self):
        """Set final_score to score if not provided"""
        if self.final_score is None:
            self.final_score = self.score
        if self.normalized_score is None:
            self.normalized_score = self.score

@dataclass
class SearchResponse:
    """Container for complete search response."""
    search_type: str
    total_results: int
    results: List[SearchResult]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_result(self, result: SearchResult):
        """Add a result to the response"""
        self.results.append(result)
        self.total_results = len(self.results)
    
    def sort_by_score(self, reverse: bool = True):
        """Sort results by score"""
        self.results.sort(key=lambda x: x.final_score or x.score, reverse=reverse)

def dict_to_search_result(data: Dict[str, Any]) -> SearchResult:
    """Convert dictionary to SearchResult object"""
    return SearchResult(
        document_id=data.get('document_id', ''),
        title=data.get('title', ''),
        score=data.get('score', 0.0),
        content=data.get('content', ''),
        content_highlights=data.get('content_highlights', []),
        title_highlights=data.get('title_highlights', []),
        metadata=data.get('metadata', {}),
        source=ResultType(data['search_type']) if 'search_type' in data else None,
        search_type=data.get('search_type'),
        search_types=data.get('search_types', []),
        final_score=data.get('final_score'),
        normalized_score=data.get('normalized_score')
    )

def search_result_to_dict(result: SearchResult) -> Dict[str, Any]:
    """Convert SearchResult object to dictionary"""
    # Get search_type from multiple possible sources
    search_type_value = (
        result.search_type or 
        (result.metadata.get('source') if result.metadata else None) or
        (result.source.value if result.source else None) or
        'unknown'
    )
    
    # Get search_types - use the merged list if available, otherwise create from single type
    search_types_list = []
    if hasattr(result, 'search_types') and result.search_types:
        search_types_list = result.search_types
    elif result.metadata and 'sources' in result.metadata:
        search_types_list = result.metadata['sources']
    else:
        search_types_list = [search_type_value]
    
    return {
        'document_id': result.document_id,
        'title': result.title,
        'score': result.score,
        'content': result.content,
        'content_highlights': result.content_highlights,
        'title_highlights': result.title_highlights,
        'metadata': {
            **result.metadata,
            'search_types': search_types_list  # Override the empty search_types
        },
        'search_type': search_type_value,
        'search_types': search_types_list,
        'final_score': result.final_score,
        'normalized_score': result.normalized_score
    }

def dict_to_search_response(data: Dict[str, Any]) -> SearchResponse:
    """Convert dictionary to SearchResponse object"""
    results = []
    for result_data in data.get('results', []):
        if isinstance(result_data, dict):
            results.append(dict_to_search_result(result_data))
        elif isinstance(result_data, SearchResult):
            results.append(result_data)
    
    return SearchResponse(
        search_type=data.get('search_type', 'unknown'),
        total_results=data.get('total_results', len(results)),
        results=results,
        metadata=data.get('metadata', {})
    )

def search_response_to_dict(response: SearchResponse) -> Dict[str, Any]:
    """Convert SearchResponse object to dictionary"""
    return {
        'search_type': response.search_type,
        'total_results': response.total_results,
        'results': [search_result_to_dict(result) for result in response.results],
        'metadata': response.metadata
    }
