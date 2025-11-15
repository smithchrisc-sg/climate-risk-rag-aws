import re
import logging
from typing import Optional

class QueryProcessor:
    """Handles query preprocessing and validation for hybrid search routing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Query processing configuration
        self.min_query_length = 2
        self.max_query_length = 500
        
        # Stop words that don't warrant hybrid search
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with'
        }
    
    def preprocess_query(self, query: str) -> str:
        """Clean and preprocess the query string"""
        
        if not query:
            return ""
        
        # Basic cleaning
        cleaned = query.strip()
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Truncate if too long
        if len(cleaned) > self.max_query_length:
            cleaned = cleaned[:self.max_query_length].strip()
            self.logger.warning(f"Query truncated to {self.max_query_length} characters")
        
        return cleaned
    
    def should_use_hybrid_search(self, query: str) -> bool:
        """Determine if query warrants hybrid search or should use filter-only"""
        
        if not query or len(query.strip()) == 0:
            return False
        
        # Check minimum length
        if len(query.strip()) < self.min_query_length:
            return False
        
        # Tokenize and check for meaningful content
        tokens = self._tokenize(query)
        meaningful_tokens = [t for t in tokens if t.lower() not in self.stop_words]
        
        # Need at least one meaningful token
        if len(meaningful_tokens) == 0:
            return False
        
        # If we have meaningful content, use hybrid search
        self.logger.info(f"Query has {len(meaningful_tokens)} meaningful tokens: {meaningful_tokens}")
        return True
    
    def _tokenize(self, query: str) -> list:
        """Simple tokenization for query analysis"""
        
        # Split on whitespace and punctuation, keep alphanumeric tokens
        tokens = re.findall(r'\b\w+\b', query.lower())
        
        # Filter out very short tokens
        tokens = [t for t in tokens if len(t) >= 2]
        
        return tokens
    
    def extract_query_terms(self, query: str) -> list:
        """Extract search terms from processed query"""
        
        processed = self.preprocess_query(query)
        if not processed:
            return []
        
        return self._tokenize(processed)
    
    def validate_query(self, query: str) -> dict:
        """Validate query and return validation result"""
        
        result = {
            'valid': True,
            'processed_query': '',
            'issues': []
        }
        
        if not query:
            result['valid'] = True  # Empty queries are valid (filter-only)
            return result
        
        processed = self.preprocess_query(query)
        result['processed_query'] = processed
        
        if len(processed) > self.max_query_length:
            result['issues'].append(f"Query too long (max {self.max_query_length} chars)")
        
        tokens = self._tokenize(processed)
        if len(tokens) == 0:
            result['issues'].append("No valid search terms found")
        
        return result
