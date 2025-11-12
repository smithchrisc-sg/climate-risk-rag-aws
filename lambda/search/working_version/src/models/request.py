from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class SearchRequest:
    """GAIP API search request model"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}
        if self.parameters is None:
            self.parameters = {}

@dataclass
class SearchFilters:
    """Search filters model"""
    categories: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    date_range: Optional[Dict[str, str]] = None
    document_types: Optional[List[str]] = None

@dataclass
class SearchParameters:
    """Search parameters model"""
    limit: int = 20
    cursor: Optional[str] = None
    include_facets: bool = False
    search_mode: str = "hybrid"  # hybrid, keyword, vector, graph
