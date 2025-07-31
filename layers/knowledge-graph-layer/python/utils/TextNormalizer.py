#!/usr/bin/env python3
"""
Text Normalizer - Comprehensive text processing for entity-ontology alignment
Handles stemming, lemmatization, canonicalization, and domain-specific normalization
"""
import logging
import re
import string
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import nltk
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import unicodedata

class TextNormalizer:
    """
    Comprehensive text normalization for NLP-ontology integration
    Handles multiple normalization strategies for improved matching accuracy
    """
    
    def __init__(self, download_nltk_data: bool = True):
        """
        Initialize text normalizer with NLTK components
        
        Args:
            download_nltk_data: Whether to download required NLTK data
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize NLTK components
        if download_nltk_data:
            self._download_nltk_data()
            
        self.stemmer = PorterStemmer()
        self.lemmatizer = WordNetLemmatizer()
        
        # Load stopwords
        try:
            self.stopwords = set(stopwords.words('english'))
        except LookupError:
            self.logger.warning("NLTK stopwords not available, using minimal set")
            self.stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Domain-specific normalization patterns
        self._setup_domain_patterns()
        
        self.logger.debug("TextNormalizer initialized")
    
    def _download_nltk_data(self):
        """Download required NLTK data with error handling"""
        required_data = ['punkt', 'wordnet', 'stopwords', 'averaged_perceptron_tagger']
        
        for data_name in required_data:
            try:
                nltk.download(data_name, quiet=True)
            except Exception as e:
                self.logger.warning(f"Failed to download NLTK data '{data_name}': {e}")
    
    def _setup_domain_patterns(self):
        """Setup domain-specific normalization patterns"""
        
        # Climate and environmental term standardization
        self.climate_synonyms = {
            'global warming': 'climate change',
            'greenhouse gas': 'ghg',
            'carbon dioxide': 'co2',
            'methane': 'ch4',
            'nitrous oxide': 'n2o',
            'sea level rise': 'slr',
            'extreme weather': 'extreme weather events',
            'renewable energy': 'clean energy',
            'fossil fuel': 'fossil fuels',
            'carbon footprint': 'carbon emissions'
        }
        
        # Financial term standardization
        self.financial_synonyms = {
            'financial institution': 'bank',
            'central bank': 'federal reserve',
            'investment bank': 'investment banking',
            'commercial bank': 'retail bank',
            'credit union': 'cooperative bank',
            'asset management': 'investment management',
            'private equity': 'pe',
            'venture capital': 'vc',
            'initial public offering': 'ipo',
            'environmental social governance': 'esg'
        }
        
        # Regulatory term standardization  
        self.regulatory_synonyms = {
            'securities and exchange commission': 'sec',
            'federal reserve': 'fed',
            'office of the comptroller': 'occ',
            'federal deposit insurance corporation': 'fdic',
            'commodity futures trading commission': 'cftc',
            'financial stability oversight council': 'fsoc',
            'basel committee': 'bcbs',
            'international organization of securities commissions': 'iosco'
        }
        
        # Combine all domain synonyms
        self.domain_synonyms = {
            **self.climate_synonyms,
            **self.financial_synonyms, 
            **self.regulatory_synonyms
        }
        
        # Abbreviation expansion patterns
        self.abbreviation_patterns = {
            r'\bco2\b': 'carbon dioxide',
            r'\bghg\b': 'greenhouse gas',
            r'\besg\b': 'environmental social governance',
            r'\bsec\b': 'securities and exchange commission',
            r'\bfed\b': 'federal reserve',
            r'\bipo\b': 'initial public offering',
            r'\bpe\b': 'private equity',
            r'\bvc\b': 'venture capital'
        }
    
    def normalize_entity_text(self, text: str, strategies: List[str] = None) -> Dict[str, str]:
        """
        Apply multiple normalization strategies to entity text
        
        Args:
            text: Input text to normalize
            strategies: List of normalization strategies to apply
                       Options: ['basic', 'stemmed', 'lemmatized', 'domain', 'canonical']
        
        Returns:
            Dictionary with different normalized versions
        """
        if strategies is None:
            strategies = ['basic', 'stemmed', 'lemmatized', 'domain', 'canonical']
        
        results = {'original': text}
        
        if 'basic' in strategies:
            results['basic'] = self._basic_normalization(text)
            
        if 'stemmed' in strategies:
            results['stemmed'] = self._stem_text(text)
            
        if 'lemmatized' in strategies:
            results['lemmatized'] = self._lemmatize_text(text)
            
        if 'domain' in strategies:
            results['domain'] = self._domain_normalization(text)
            
        if 'canonical' in strategies:
            results['canonical'] = self._canonical_normalization(text)
        
        return results
    
    def _basic_normalization(self, text: str) -> str:
        """Basic text normalization - case, punctuation, whitespace"""
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove punctuation except hyphens and apostrophes
        normalized = re.sub(r'[^\w\s\'-]', ' ', normalized)
        
        # Handle contractions
        normalized = re.sub(r"'s\b", '', normalized)  # Remove possessive
        normalized = re.sub(r"'t\b", ' not', normalized)  # can't -> can not
        normalized = re.sub(r"'re\b", ' are', normalized)  # we're -> we are
        normalized = re.sub(r"'ve\b", ' have', normalized)  # I've -> I have
        normalized = re.sub(r"'ll\b", ' will', normalized)  # I'll -> I will
        normalized = re.sub(r"'d\b", ' would', normalized)  # I'd -> I would
        
        # Clean up extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _stem_text(self, text: str) -> str:
        """Apply Porter stemming to text"""
        basic = self._basic_normalization(text)
        
        try:
            tokens = word_tokenize(basic)
            stemmed_tokens = [self.stemmer.stem(token) for token in tokens if token not in self.stopwords]
            return ' '.join(stemmed_tokens)
        except Exception as e:
            self.logger.warning(f"Stemming failed for '{text}': {e}")
            return basic
    
    def _lemmatize_text(self, text: str) -> str:
        """Apply WordNet lemmatization to text"""
        basic = self._basic_normalization(text)
        
        try:
            tokens = word_tokenize(basic)
            lemmatized_tokens = [self.lemmatizer.lemmatize(token) for token in tokens if token not in self.stopwords]
            return ' '.join(lemmatized_tokens)
        except Exception as e:
            self.logger.warning(f"Lemmatization failed for '{text}': {e}")
            return basic
    
    def _domain_normalization(self, text: str) -> str:
        """Apply domain-specific normalization"""
        normalized = self._basic_normalization(text)
        
        # Apply domain synonym replacements
        for synonym, canonical in self.domain_synonyms.items():
            normalized = re.sub(r'\b' + re.escape(synonym) + r'\b', canonical, normalized, flags=re.IGNORECASE)
        
        # Apply abbreviation expansions
        for pattern, expansion in self.abbreviation_patterns.items():
            normalized = re.sub(pattern, expansion, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _canonical_normalization(self, text: str) -> str:
        """Apply comprehensive canonical normalization"""
        if not text:
            return ""
        
        # Start with domain normalization
        normalized = self._domain_normalization(text)
        
        # Unicode normalization
        normalized = unicodedata.normalize('NFKD', normalized)
        
        # Remove accents and diacritics
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        # Standardize number representations
        normalized = re.sub(r'\b(\d+),(\d+)\b', r'\1\2', normalized)  # Remove commas from numbers
        normalized = re.sub(r'\b(\d+)\.0+\b', r'\1', normalized)  # 5.0 -> 5
        
        # Standardize units
        unit_patterns = {
            r'\bpercent\b': '%',
            r'\bdegrees?\s*celsius\b': '°C',
            r'\bdegrees?\s*fahrenheit\b': '°F',
            r'\bkilometers?\b': 'km',
            r'\bmeters?\b': 'm',
            r'\btons?\b': 'tonnes',
            r'\bbillions?\b': 'billion',
            r'\bmillions?\b': 'million'
        }
        
        for pattern, replacement in unit_patterns.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Final cleanup
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def calculate_text_similarity(self, text1: str, text2: str, method: str = 'canonical') -> float:
        """
        Calculate similarity between two texts using specified normalization
        
        Args:
            text1: First text
            text2: Second text  
            method: Normalization method ('basic', 'stemmed', 'lemmatized', 'domain', 'canonical')
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        norm1 = self.normalize_entity_text(text1, [method])[method]
        norm2 = self.normalize_entity_text(text2, [method])[method]
        
        if not norm1 or not norm2:
            return 0.0
        
        if norm1 == norm2:
            return 1.0
        
        # Calculate Jaccard similarity on word sets
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def extract_key_terms(self, text: str, min_length: int = 3, max_terms: int = 10) -> List[str]:
        """
        Extract key terms from text for matching
        
        Args:
            text: Input text
            min_length: Minimum term length
            max_terms: Maximum number of terms to return
        
        Returns:
            List of key terms
        """
        normalized = self._canonical_normalization(text)
        
        try:
            tokens = word_tokenize(normalized)
            
            # Filter tokens
            key_terms = [
                token for token in tokens 
                if (len(token) >= min_length and 
                    token not in self.stopwords and
                    token.isalpha())
            ]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_terms = []
            for term in key_terms:
                if term not in seen:
                    seen.add(term)
                    unique_terms.append(term)
            
            return unique_terms[:max_terms]
            
        except Exception as e:
            self.logger.warning(f"Key term extraction failed for '{text}': {e}")
            return []
    
    def get_normalization_stats(self) -> Dict[str, int]:
        """Get statistics about normalization patterns"""
        return {
            'climate_synonyms': len(self.climate_synonyms),
            'financial_synonyms': len(self.financial_synonyms),
            'regulatory_synonyms': len(self.regulatory_synonyms),
            'total_domain_synonyms': len(self.domain_synonyms),
            'abbreviation_patterns': len(self.abbreviation_patterns),
            'stopwords': len(self.stopwords)
        }

# Example usage and testing
if __name__ == "__main__":
    normalizer = TextNormalizer()
    
    test_texts = [
        "Climate Change and Global Warming",
        "Financial Institution's ESG Policies", 
        "SEC's Environmental Regulations",
        "CO2 Emissions from Fossil Fuels"
    ]
    
    for text in test_texts:
        results = normalizer.normalize_entity_text(text)
        print(f"Original: {text}")
        for method, normalized in results.items():
            if method != 'original':
                print(f"  {method}: {normalized}")
        print()
