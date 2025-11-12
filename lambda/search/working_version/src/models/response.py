from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Individual search result"""
    document_id: str
    title: str
    summary: str
    score: float
    document_type: str
    categories: List[str]
    regions: List[str]
    publication_date: Optional[str]
    source_url: Optional[str]
    highlights: Dict[str, List[str]]
    metadata: Dict[str, Any]

@dataclass
class SearchResponse:
    """GAIP API search response model"""
    results: List[SearchResult]
    pagination: Dict[str, Any]
    facets: Optional[Dict[str, Any]]
    execution_time: float
    total_results: int
