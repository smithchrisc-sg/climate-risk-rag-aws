"""
NLP Interface - Abstract base class for pluggable NLP providers
Supports Amazon Comprehend, Flair NLP, and future providers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NLPProvider(ABC):
    """Abstract base class for NLP providers"""
    
    @abstractmethod
    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect entities in text with offsets
        
        Returns:
            List of entities with format:
            {
                'text': str,
                'type': str,
                'confidence': float,
                'begin_offset': int,
                'end_offset': int
            }
        """
        pass
    
    @abstractmethod
    def extract_key_phrases(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract key phrases with offsets
        
        Returns:
            List of key phrases with format:
            {
                'text': str,
                'confidence': float,
                'begin_offset': int,
                'end_offset': int
            }
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name for tracking and logging"""
        pass
    
    @abstractmethod
    def estimate_cost(self, text: str) -> float:
        """Estimate processing cost for given text"""
        pass
    
    @abstractmethod
    def get_text_limits(self) -> Dict[str, int]:
        """
        Return text processing limits for this provider
        
        Returns:
            {
                'max_text_length': int,
                'recommended_chunk_size': int
            }
        """
        pass

class NLPProcessorFactory:
    """Factory for creating NLP processors"""
    
    _providers = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class):
        """Register a new NLP provider"""
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered NLP provider: {name}")
    
    @classmethod
    def create_processor(cls, provider_name: str) -> 'NLPProcessor':
        """Create NLP processor with specified provider"""
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            # Try to import and register known providers
            cls._register_known_providers()
        
        if provider_name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(f"Unknown NLP provider: {provider_name}. Available: {available}")
        
        provider_class = cls._providers[provider_name]
        provider = provider_class()
        
        return NLPProcessor(provider)
    
    @classmethod
    def _register_known_providers(cls):
        """Register known providers on first use"""
        try:
            from comprehend_provider import ComprehendProvider
            cls.register_provider('comprehend', ComprehendProvider)
        except ImportError:
            logger.warning("ComprehendProvider not available")
        
        try:
            from flair_provider import FlairProvider
            cls.register_provider('flair', FlairProvider)
        except ImportError:
            logger.warning("FlairProvider not available")
    
    @classmethod
    def list_available_providers(cls) -> List[str]:
        """List all available providers"""
        cls._register_known_providers()
        return list(cls._providers.keys())

class CostTracker:
    """Track processing costs for different providers"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.total_cost = 0.0
        self.processing_history = []
    
    def add_processing_cost(self, text_length: int, cost: float):
        """Add a processing cost entry"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'text_length': text_length,
            'cost': cost,
            'provider': self.provider_name
        }
        self.processing_history.append(entry)
        self.total_cost += cost
        
        logger.info(f"Processing cost: ${cost:.6f} for {text_length} characters ({self.provider_name})")
    
    def get_total_cost(self) -> float:
        """Get total accumulated cost"""
        return self.total_cost
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary statistics"""
        if not self.processing_history:
            return {'total_cost': 0.0, 'processing_count': 0}
        
        total_chars = sum(entry['text_length'] for entry in self.processing_history)
        avg_cost_per_char = self.total_cost / total_chars if total_chars > 0 else 0
        
        return {
            'total_cost': self.total_cost,
            'processing_count': len(self.processing_history),
            'total_characters': total_chars,
            'avg_cost_per_character': avg_cost_per_char,
            'provider': self.provider_name
        }

class NLPProcessor:
    """Main NLP processing coordinator"""
    
    def __init__(self, provider: NLPProvider):
        self.provider = provider
        self.cost_tracker = CostTracker(provider.get_provider_name())
        self.text_limits = provider.get_text_limits()
        
        logger.info(f"Initialized NLP processor with {provider.get_provider_name()} provider")
    
    def process_document(self, doc_id: str, full_text: str) -> Dict[str, Any]:
        """Process full document text for entities and key phrases"""
        
        start_time = datetime.now()
        
        # Validate text length
        if len(full_text) > self.text_limits['max_text_length']:
            logger.warning(f"Text length {len(full_text)} exceeds limit {self.text_limits['max_text_length']}")
            # Will be handled by provider's internal chunking
        
        results = {
            'doc_id': doc_id,
            'provider': self.provider.get_provider_name(),
            'entities': [],
            'key_phrases': [],
            'processing_cost': 0.0,
            'processed_at': start_time.isoformat(),
            'text_length': len(full_text),
            'processing_duration': 0.0
        }
        
        try:
            # Estimate cost before processing
            estimated_cost = self.provider.estimate_cost(full_text)
            logger.info(f"Estimated NLP cost for {doc_id}: ${estimated_cost:.6f}")
            
            # Entity detection
            logger.info(f"Starting entity detection for {doc_id}")
            entities = self.provider.detect_entities(full_text)
            results['entities'] = entities
            logger.info(f"Detected {len(entities)} entities for {doc_id}")
            
            # Key phrase extraction
            logger.info(f"Starting key phrase extraction for {doc_id}")
            key_phrases = self.provider.extract_key_phrases(full_text)
            results['key_phrases'] = key_phrases
            logger.info(f"Extracted {len(key_phrases)} key phrases for {doc_id}")
            
            # Calculate actual costs
            actual_cost = self.provider.estimate_cost(full_text)  # For now, use estimate as actual
            results['processing_cost'] = actual_cost
            self.cost_tracker.add_processing_cost(len(full_text), actual_cost)
            
            # Calculate processing duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            results['processing_duration'] = duration
            
            logger.info(f"NLP processing completed for {doc_id} in {duration:.2f}s, cost: ${actual_cost:.6f}")
            
        except Exception as e:
            logger.error(f"Error processing document {doc_id}: {str(e)}")
            results['error'] = str(e)
            results['processing_cost'] = 0.0
            raise
        
        return results
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary"""
        return self.cost_tracker.get_cost_summary()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            'name': self.provider.get_provider_name(),
            'text_limits': self.text_limits,
            'cost_summary': self.get_cost_summary()
        }
