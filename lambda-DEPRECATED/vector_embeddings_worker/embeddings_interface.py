"""
Abstract embeddings interface for pluggable model support
Supports both AWS Titan and open-source sentence-transformers
"""
# Conditional numpy import - only needed for SentenceTransformers
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Create a dummy numpy for type hints
    class DummyNumpy:
        def array(self, data):
            return data
        def zeros(self, shape):
            return [0.0] * shape
    np = DummyNumpy()

class EmbeddingsInterface(object):
    """Abstract interface for embeddings generation"""
    
    def __init__(self, **kwargs):
        """Initialize the embeddings model"""
        raise NotImplementedError("Subclasses must implement __init__")
    
    def create_embeddings_batch(self, texts):
        """Generate embeddings for a batch of texts"""
        raise NotImplementedError("Subclasses must implement create_embeddings_batch")
    
    def get_embedding_dimension(self):
        """Get the dimension of embeddings produced by this model"""
        raise NotImplementedError("Subclasses must implement get_embedding_dimension")
    
    def get_model_info(self):
        """Get model information for tracking and debugging"""
        raise NotImplementedError("Subclasses must implement get_model_info")
    
    def estimate_cost(self, texts):
        """Estimate cost for processing these texts"""
        raise NotImplementedError("Subclasses must implement estimate_cost")

class EmbeddingsFactory(object):
    """Factory for creating embeddings instances"""
    
    @staticmethod
    def create_embeddings(model_type, **kwargs):
        """Create embeddings instance based on model type"""
        if model_type.lower() == 'titan':
            from titan_embeddings import TitanEmbeddings
            return TitanEmbeddings(**kwargs)
        elif model_type.lower() == 'sentence_transformers':
            from sentence_transformer_embeddings import SentenceTransformerEmbeddings
            return SentenceTransformerEmbeddings(**kwargs)
        else:
            raise ValueError("Unsupported model type: {}".format(model_type))
