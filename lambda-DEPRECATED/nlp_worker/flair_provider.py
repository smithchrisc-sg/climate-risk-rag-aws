"""
Flair NLP Provider - Implementation of NLP interface for Flair NLP
Provides offline NLP processing with higher accuracy but longer processing times
Cost structure: Lambda compute costs (GB-seconds) vs API costs
"""
from typing import List, Dict, Any
from nlp_interface import NLPProvider
import logging
import time

logger = logging.getLogger(__name__)

# Flair availability check - will be True once included in Lambda layer
try:
    from flair.data import Sentence
    from flair.models import SequenceTagger
    FLAIR_AVAILABLE = True
    logger.info("Flair NLP library is available")
except ImportError:
    FLAIR_AVAILABLE = False
    logger.info("Flair NLP library not available - include in Lambda layer to enable")

class FlairProvider(NLPProvider):
    """
    Flair NLP implementation of NLP provider
    
    Trade-offs:
    - Higher accuracy, especially for domain-specific entities
    - Offline processing (no API dependencies)
    - Higher Lambda compute costs (GB-seconds)
    - Longer processing times (10-30 seconds vs 1-2 seconds)
    """
    
    # Lambda cost estimation (3008MB memory allocation)
    LAMBDA_MEMORY_GB = 3.008  # 3008MB in GB
    LAMBDA_COST_PER_GB_SECOND = 0.0000166667
    
    def __init__(self):
        """Initialize Flair NLP models"""
        if not FLAIR_AVAILABLE:
            raise ImportError(
                "Flair NLP not available. Include flair in Lambda layer to enable this provider. "
                "This is not a runtime fallback - Flair must be deployed with the function."
            )
        
        # Load models (cached in Lambda container after cold start)
        start_time = time.time()
        try:
            self.ner_tagger = SequenceTagger.load('ner')
            load_time = time.time() - start_time
            logger.info(f"Loaded Flair NER model in {load_time:.2f}s")
        except Exception as e:
            logger.error(f"Failed to load Flair NER model: {str(e)}")
            raise
        
        # Note: Key phrase extraction would need custom implementation
        # Could integrate with spaCy or implement rule-based extraction
        logger.info("Flair provider initialized - entity detection ready")
    
    def detect_entities(self, text: str) -> List[Dict[str, Any]]:
        """Detect entities using Flair NLP"""
        
        if not text or not text.strip():
            return []
        
        start_time = time.time()
        
        try:
            # Process text with Flair
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
            
            processing_time = time.time() - start_time
            logger.info(f"Flair detected {len(entities)} entities in {processing_time:.2f}s")
            
            return entities
            
        except Exception as e:
            logger.error(f"Error in Flair entity detection: {str(e)}")
            raise
    
    def extract_key_phrases(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract key phrases - Custom implementation needed for Flair
        
        Options:
        1. Integrate with spaCy for noun phrase extraction
        2. Rule-based extraction using POS tagging
        3. Use Flair's own sequence labeling for custom phrase detection
        """
        
        if not text or not text.strip():
            return []
        
        logger.info("Key phrase extraction for Flair not yet implemented")
        
        # Placeholder - could implement noun phrase extraction
        # This would require additional models or spaCy integration
        return []
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "flair"
    
    def estimate_cost(self, text: str) -> float:
        """
        Estimate Lambda compute cost for Flair processing
        
        Cost factors:
        - Memory allocation (3008MB for model loading)
        - Processing time (varies by text length)
        - No API costs (offline processing)
        """
        
        if not text:
            return 0.0
        
        # Estimate processing time based on text length
        # These are rough estimates - would need benchmarking for accuracy
        base_time = 2.0  # Model initialization overhead
        processing_time_per_char = 0.001  # Rough estimate
        
        estimated_seconds = base_time + (len(text) * processing_time_per_char)
        
        # Calculate Lambda cost
        lambda_cost = estimated_seconds * self.LAMBDA_MEMORY_GB * self.LAMBDA_COST_PER_GB_SECOND
        
        logger.debug(f"Estimated Flair cost: ${lambda_cost:.6f} for {len(text)} chars ({estimated_seconds:.1f}s)")
        return lambda_cost
    
    def get_text_limits(self) -> Dict[str, int]:
        """Return text processing limits for Flair"""
        
        # Flair can handle much longer texts than Comprehend
        # Limited mainly by Lambda timeout (15 minutes) and memory
        return {
            'max_text_length': 100000,  # Much higher than Comprehend's 5000
            'recommended_chunk_size': 50000  # Process larger chunks for efficiency
        }
    
    def get_performance_profile(self) -> Dict[str, Any]:
        """Get detailed performance and cost profile"""
        
        return {
            'provider': 'flair',
            'processing_type': 'offline_local',
            'advantages': [
                'Higher accuracy for domain-specific entities',
                'No API dependencies or rate limits',
                'Offline processing',
                'Custom model support',
                'No per-request API costs'
            ],
            'disadvantages': [
                'Higher Lambda compute costs',
                'Longer processing times (10-30s vs 1-2s)',
                'Larger memory requirements (3008MB)',
                'Cold start overhead for model loading',
                'Key phrase extraction not built-in'
            ],
            'cost_structure': {
                'type': 'lambda_compute',
                'memory_allocation_mb': 3008,
                'estimated_cost_per_1000_chars': self.estimate_cost('a' * 1000),
                'break_even_vs_comprehend': 'Depends on volume and accuracy requirements'
            },
            'use_cases': [
                'High accuracy requirements',
                'Domain-specific entity types',
                'Offline processing needs',
                'Custom model requirements',
                'Cost optimization for high-volume processing'
            ]
        }
    
    def benchmark_processing_time(self, sample_text: str) -> Dict[str, float]:
        """Benchmark actual processing time for cost estimation refinement"""
        
        if not FLAIR_AVAILABLE:
            return {'error': 'Flair not available'}
        
        start_time = time.time()
        
        try:
            entities = self.detect_entities(sample_text)
            processing_time = time.time() - start_time
            
            # Calculate actual cost
            actual_cost = processing_time * self.LAMBDA_MEMORY_GB * self.LAMBDA_COST_PER_GB_SECOND
            
            return {
                'text_length': len(sample_text),
                'processing_time_seconds': processing_time,
                'entities_found': len(entities),
                'actual_lambda_cost': actual_cost,
                'cost_per_character': actual_cost / len(sample_text) if sample_text else 0,
                'characters_per_second': len(sample_text) / processing_time if processing_time > 0 else 0
            }
            
        except Exception as e:
            return {'error': str(e)}

# Cost comparison utility
def compare_providers_cost(text_length: int) -> Dict[str, Any]:
    """Compare cost estimates between Flair and Comprehend"""
    
    # Comprehend costs (API-based)
    comprehend_units = max(1, text_length / 100)
    comprehend_api_cost = comprehend_units * 0.0002  # Entity + Key phrases
    comprehend_lambda_cost = 3 * 0.001024 * 0.0000166667  # 3s, 1024MB
    comprehend_total = comprehend_api_cost + comprehend_lambda_cost
    
    # Flair costs (compute-based)
    flair_provider = FlairProvider() if FLAIR_AVAILABLE else None
    flair_cost = flair_provider.estimate_cost('a' * text_length) if flair_provider else 0
    
    return {
        'text_length': text_length,
        'comprehend': {
            'api_cost': comprehend_api_cost,
            'lambda_cost': comprehend_lambda_cost,
            'total_cost': comprehend_total,
            'processing_time_estimate': '1-3 seconds'
        },
        'flair': {
            'api_cost': 0.0,
            'lambda_cost': flair_cost,
            'total_cost': flair_cost,
            'processing_time_estimate': '10-30 seconds'
        },
        'recommendation': 'comprehend' if comprehend_total < flair_cost else 'flair',
        'cost_difference': abs(comprehend_total - flair_cost),
        'flair_break_even_volume': 'High volume where accuracy gains justify compute costs'
    }
