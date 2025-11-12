import time
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class SolutionResponseFormatter:
    
    def format_solution_results(self, solutions: List[Dict], request: Dict, execution_time: float) -> Dict:
        """Format solutions for API v2 hierarchical response"""
        
        formatted_solutions = []
        
        for solution in solutions:
            try:
                formatted_solution = self._format_single_solution(solution)
                formatted_solutions.append(formatted_solution)
            except Exception as e:
                logger.warning(f"Failed to format solution {solution.get('doc_id', 'unknown')}: {e}")
                continue
        
        return {
            'status': 'success',
            'query_id': f"search_{int(time.time())}_{hash(request.get('query', ''))}",
            'execution_time_ms': int(execution_time * 1000),
            'total_results': len(formatted_solutions),
            'returned_results': len(formatted_solutions),
            'results': {
                'solutions': formatted_solutions
            }
        }
    
    def _format_single_solution(self, solution: Dict) -> Dict:
        """Format single solution to API v2 spec"""
        
        content = solution['content']
        metadata = content['chunk_metadata']
        
        # Parse solution categories and types
        solution_categories = self._parse_categories(metadata.get('type_of_solution', ''))
        solution_types = self._parse_types(metadata.get('type_of_solution', ''))
        
        # Parse countries
        countries = self._parse_countries(metadata.get('country', ''))
        
        return {
            'document_id': solution['doc_id'],
            'content_type': 'solution',
            'solution_name': metadata.get('solution_name', 'Unnamed Solution'),
            'title': metadata.get('solution_name', 'Unnamed Solution'),
            'relevance_score': solution.get('relevance_score', 0.0),
            'publication_date': self._format_date(metadata.get('year_of_implementation')),
            'country_regions_covered': countries,
            'risk_types_addressed': [metadata.get('type_of_risk')] if metadata.get('type_of_risk') else [],
            'solution_categories': solution_categories,
            'solution_types': solution_types,
            'implemented': 'yes' if metadata.get('ppp') == 'Yes' else 'unknown',
            'ppp_involvement': 'yes' if metadata.get('ppp') == 'Yes' else 'no',
            'summary_description': content['assembled_description'],
            'key_highlights': self._extract_highlights(content['assembled_description']),
            'source': metadata.get('source_url', ''),
            'related_documents': [],  # Phase 2 implementation
            'snippets': self._create_snippets(content['assembled_description']),
            'metadata': {
                'document_type': 'solution',
                'categories': self._parse_themes(metadata.get('theme', '')),
                'regions': countries,
                'publication_year': self._parse_year(metadata.get('year_of_implementation')),
                'source': metadata.get('source_url', ''),
                'processing_timestamp': metadata.get('processing_timestamp')
            }
        }
    
    def _parse_categories(self, type_of_solution: str) -> List[str]:
        """Parse solution categories from type_of_solution field"""
        if not type_of_solution:
            return []
        
        # Map common solution types to categories
        categories = []
        solution_lower = type_of_solution.lower()
        
        if any(term in solution_lower for term in ['risk reduction', 'prevention', 'mitigation']):
            categories.append('risk reduction')
        if any(term in solution_lower for term in ['penetration', 'insurance', 'coverage']):
            categories.append('insurance penetration')
        if any(term in solution_lower for term in ['financing', 'funding', 'capital']):
            categories.append('risk financing')
        
        return categories if categories else ['risk reduction']  # Default category
    
    def _parse_types(self, type_of_solution: str) -> List[str]:
        """Parse solution types from type_of_solution field"""
        if not type_of_solution:
            return []
        
        # Split on common delimiters and clean up
        types = []
        for part in type_of_solution.replace('\n', ',').split(','):
            cleaned = part.strip()
            if cleaned:
                types.append(cleaned)
        
        return types
    
    def _parse_countries(self, country: str) -> List[str]:
        """Parse countries from country field"""
        if not country:
            return []
        
        # Split on common delimiters and clean up
        countries = []
        for part in country.replace('\n', ',').split(','):
            cleaned = part.strip()
            if cleaned:
                countries.append(cleaned)
        
        return countries
    
    def _parse_themes(self, theme: str) -> List[str]:
        """Parse themes from theme field"""
        if not theme:
            return []
        
        # Split on common delimiters and clean up
        themes = []
        for part in theme.replace('\n', ',').split(','):
            cleaned = part.strip()
            if cleaned:
                themes.append(cleaned)
        
        return themes
    
    def _format_date(self, year: str) -> str:
        """Format year to date string"""
        if not year:
            return None
        
        try:
            # If it's just a year, format as YYYY-01-01
            year_int = int(year)
            return f"{year_int}-01-01"
        except (ValueError, TypeError):
            return None
    
    def _parse_year(self, year: str) -> int:
        """Parse year as integer"""
        if not year:
            return None
        
        try:
            return int(year)
        except (ValueError, TypeError):
            return None
    
    def _extract_highlights(self, description: str) -> List[str]:
        """Extract key highlights from description"""
        if not description:
            return []
        
        # Simple extraction: take first sentence as highlight
        sentences = description.split('.')
        if sentences and len(sentences[0].strip()) > 20:
            return [sentences[0].strip() + '.']
        
        return []
    
    def _create_snippets(self, description: str) -> List[Dict]:
        """Create text snippets from description"""
        if not description:
            return []
        
        # Simple snippet: first 200 characters
        snippet_text = description[:200]
        if len(description) > 200:
            snippet_text += '...'
        
        return [{
            'text': snippet_text,
            'page_number': 1,
            'section': 'Description'
        }]
