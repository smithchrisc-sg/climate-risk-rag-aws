"""
Flair NLP Provider - Implementation of NLP interface for Flair NLP
Currently a placeholder - requires Flair to be included in Lambda layer
"""
from typing import List, Dict, Any
from nlp_interface import NLPProvider
import logging

logger = logging.getLogger(__name__)

# Check if Flair is available
try:
    from flair.data import Sentence
    from flair.models import SequenceTagger
    FLAIR_AVAILABLE = True
    logger.info("Flair NLP library is available")
except ImportError:
    FLAIR_AVAILABLE = False
    logger.warning("Flair NLP library not available - provider will be disabled")

class FlairProvider(NLPProvider):
    """Flair NLP implementation of NLP provider"""
    
    def __init__(self):
        """Initialize Flair NLP models"""
        if not FLAIR_AVAILABLE:
            raise ImportError("Flair NLP not available. Install flair package or include in Lambda layer.")
        
        # Load models (these would be cached in Lambda container)
        try:
            self.ner_tagger = SequenceTagger.load('ner')
            logger.info("Loaded Flair NER model")
        except Exception as e:
            logger.error(f"Failed to load Flair NER model: {str(e)}")
            raise
        
        # Note: Flair doesn't have built-in key phrase extraction
        # Would need custom implementation or integration with spaCy
        logger.warning("Key phrase extraction not implemented for Flair provider")
    
    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect entities using Flair NLP"""
        
        if not FLAIR_AVAILABLE:
            raise RuntimeError("Flair NLP not available")
        
        if not text or not text.strip():
            return []
        
        try:
            sentence = Sentence(text)
            self.ner_tagger.predict(sentence)
            
            entities = []
            for entity in sentence.get_spans('ner'):
                entities.append({
                    'text': entity.text,
                    'type': entity.get_label('ner').value,
                    'confidence': entity.get_label('ner').score,
                    'begin_offset': entity.start_position,
                    'end_offset': entity.end_position
                })
            
            logger.debug(f"Detected {len(entities)} entities using Flair")
            return entities
            
        except Exception as e:
            logger.error(f"Error in Flair entity detection: {str(e)}")
            raise
    
    def extract_key_phrases(self, text: str) -> List[Dict[str, Any]]:
        """Extract key phrases - NOT IMPLEMENTED for Flair"""
        
        logger.warning("Key phrase extraction not implemented for Flair provider")
        
        # Placeholder implementation - would need custom logic
        # Could use spaCy noun phrases or other techniques
        return []
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "flair"
    
    def estimate_cost(self, text: str) -> float:
        """Estimate processing cost - Flair is free but has compute costs"""
        
        # Flair has no API costs, but Lambda compute costs
        # Estimate based on processing time and Lambda pricing
        
        if not text:
            return 0.0
        
        # Rough estimate: longer text = more compute time
        # This is a placeholder - would need actual benchmarking
        estimated_seconds = len(text) / 1000  # Very rough estimate
        lambda_cost_per_second = 0.0000166667  # For 1GB memory Lambda
        
        estimated_cost = estimated_seconds * lambda_cost_per_second
        
        logger.debug(f"Estimated Flair processing cost: ${estimated_cost:.6f}")
        return estimated_cost
    
    def get_text_limits(self) -> Dict[str, int]:
        """Return text processing limits for Flair"""
        
        # Flair can handle longer texts but may be slow
        return {
            'max_text_length': 50000,  # Much higher than Comprehend
            'recommended_chunk_size': 10000  # Larger chunks for efficiency
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Flair model information"""
        
        if not FLAIR_AVAILABLE:
            return {'available': False, 'error': 'Flair not installed'}
        
        return {
            'available': True,
            'models_loaded': ['ner'],
            'features': ['entity_detection'],
            'limitations': ['no_key_phrase_extraction'],
            'advantages': ['no_api_costs', 'offline_processing', 'custom_models']
        }
