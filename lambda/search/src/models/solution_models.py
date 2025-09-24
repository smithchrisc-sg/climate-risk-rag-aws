"""
Solution-focused data models for the updated GAIP API.
Extends existing search models with solution-specific fields and structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

class SolutionCategory(Enum):
    """Solution categories as defined in requirements."""
    RISK_REDUCTION = "risk reduction"
    INSURANCE_PENETRATION = "insurance penetration"
    RISK_FINANCING = "risk financing"

class ImplementationStatus(Enum):
    """Implementation status options."""
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"

class PPPInvolvement(Enum):
    """Public-Private Partnership involvement options."""
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"

class GeographicScope(Enum):
    """Geographic scope options."""
    ASIA = "Asia"
    ASEAN_PLUS_3 = "ASEAN+3"
    ASEAN = "ASEAN"
    COUNTRY = "country"
    PROVINCE_STATE = "province/state"
    CITY_MUNI = "city/muni"

@dataclass
class SolutionContactInfo:
    """Contact information for a solution."""
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

@dataclass
class SourceLink:
    """Link to source website or document."""
    url: str
    title: str
    type: str  # "website", "document", "report", "presentation"

@dataclass
class SolutionResult:
    """Solution-focused search result format."""
    # Core identification
    document_id: str
    document_url: Optional[str] = None
    
    # Solution-specific fields
    solution_name: Optional[str] = None
    title: Optional[str] = None  # Fallback if solution_name not available
    relevance_score: float = 0.0
    
    # Publication and temporal information
    publication_date: Optional[str] = None  # YYYY-MM-DD format
    last_kr_harvest_date: Optional[str] = None  # ISO 8601 format
    
    # Geographic and risk information
    country_regions_covered: List[str] = field(default_factory=list)
    risk_types_addressed: List[str] = field(default_factory=list)
    
    # Solution categorization
    solution_categories: List[str] = field(default_factory=list)
    solution_types: List[str] = field(default_factory=list)
    
    # Implementation information
    solution_implementation_timeline: Optional[str] = None
    implemented: str = "unknown"  # ImplementationStatus enum values
    ppp_involvement: str = "unknown"  # PPPInvolvement enum values
    
    # Detailed solution information
    summary_description: Optional[str] = None
    key_highlights: List[str] = field(default_factory=list)
    results_outcomes: Optional[str] = None
    
    # Contact and source information
    solution_contact_info: Optional[Dict[str, Any]] = None
    source_links: List[Dict[str, Any]] = field(default_factory=list)
    source: Optional[str] = None
    
    # Legacy fields for compatibility
    snippets: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Search system fields
    search_type: Optional[str] = None
    search_types: List[str] = field(default_factory=list)
    final_score: Optional[float] = None
    normalized_score: Optional[float] = None
    
    def __post_init__(self):
        """Set final_score to relevance_score if not provided"""
        if self.final_score is None:
            self.final_score = self.relevance_score
        if self.normalized_score is None:
            self.normalized_score = self.relevance_score

@dataclass
class SolutionSearchRequest:
    """Solution-focused search request format."""
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    
    def get_solution_category_filter(self) -> List[str]:
        """Get solution category filter values."""
        return self.filters.get('solution_category', [])
    
    def get_risk_type_filter(self) -> List[str]:
        """Get risk type filter values."""
        return self.filters.get('risk_type', [])
    
    def get_geographic_scope_filter(self) -> List[str]:
        """Get geographic scope filter values."""
        return self.filters.get('geographic_scope', [])
    
    def get_ppp_involvement_filter(self) -> Optional[bool]:
        """Get PPP involvement filter value."""
        return self.filters.get('ppp_involvement')

@dataclass
class SolutionSearchResponse:
    """Solution-focused search response format."""
    status: str = "success"
    query_id: Optional[str] = None
    execution_time_ms: Optional[int] = None
    total_results: int = 0
    returned_results: int = 0
    results: List[SolutionResult] = field(default_factory=list)
    facets: Dict[str, Dict[str, int]] = field(default_factory=dict)
    pagination: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

@dataclass
class RepositoryMetadata:
    """Repository metadata response format."""
    status: str = "success"
    last_update: Optional[str] = None
    update_type: Optional[str] = None
    documents_updated: Optional[int] = None
    total_solutions: Optional[int] = None
    total_documents: Optional[int] = None
    last_counted: Optional[str] = None
    breakdown: Dict[str, int] = field(default_factory=dict)

def dict_to_solution_result(data: Dict[str, Any]) -> SolutionResult:
    """Convert dictionary to SolutionResult object."""
    return SolutionResult(
        document_id=data.get('document_id', ''),
        document_url=data.get('document_url'),
        solution_name=data.get('solution_name'),
        title=data.get('title', ''),
        relevance_score=data.get('relevance_score', 0.0),
        publication_date=data.get('publication_date'),
        last_kr_harvest_date=data.get('last_kr_harvest_date'),
        country_regions_covered=data.get('country_regions_covered', []),
        risk_types_addressed=data.get('risk_types_addressed', []),
        solution_categories=data.get('solution_categories', []),
        solution_types=data.get('solution_types', []),
        solution_implementation_timeline=data.get('solution_implementation_timeline'),
        implemented=data.get('implemented', 'unknown'),
        ppp_involvement=data.get('ppp_involvement', 'unknown'),
        summary_description=data.get('summary_description'),
        key_highlights=data.get('key_highlights', []),
        results_outcomes=data.get('results_outcomes'),
        solution_contact_info=data.get('solution_contact_info'),
        source_links=data.get('source_links', []),
        source=data.get('source'),
        snippets=data.get('snippets', []),
        metadata=data.get('metadata', {}),
        search_type=data.get('search_type'),
        search_types=data.get('search_types', []),
        final_score=data.get('final_score'),
        normalized_score=data.get('normalized_score')
    )

def solution_result_to_dict(result: SolutionResult) -> Dict[str, Any]:
    """Convert SolutionResult object to dictionary."""
    return {
        'document_id': result.document_id,
        'document_url': result.document_url,
        'solution_name': result.solution_name,
        'title': result.title,
        'relevance_score': result.relevance_score,
        'publication_date': result.publication_date,
        'last_kr_harvest_date': result.last_kr_harvest_date,
        'country_regions_covered': result.country_regions_covered,
        'risk_types_addressed': result.risk_types_addressed,
        'solution_categories': result.solution_categories,
        'solution_types': result.solution_types,
        'solution_implementation_timeline': result.solution_implementation_timeline,
        'implemented': result.implemented,
        'ppp_involvement': result.ppp_involvement,
        'summary_description': result.summary_description,
        'key_highlights': result.key_highlights,
        'results_outcomes': result.results_outcomes,
        'solution_contact_info': result.solution_contact_info,
        'source_links': result.source_links,
        'source': result.source,
        'snippets': result.snippets,
        'metadata': result.metadata,
        'search_type': result.search_type,
        'search_types': result.search_types,
        'final_score': result.final_score,
        'normalized_score': result.normalized_score
    }
