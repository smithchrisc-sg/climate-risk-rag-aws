"""
SentenceTransformers embeddings implementation (open source)
"""
import logging
from embeddings_interface import EmbeddingsInterface

# Conditional imports
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)

class SentenceTransformerEmbeddings(EmbeddingsInterface):
    def __init__(self, model_name="all-MiniLM-L6-v2", **kwargs):
        if not NUMPY_AVAILABLE:
            logger.error("NumPy not available - SentenceTransformers requires NumPy")
            self.available = False
            self.model_name = model_name
            self.dimension = 384  # Default dimension for all-MiniLM-L6-v2
            self.batch_size = 32
            return
            
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            self.dimension = self.model.get_sentence_embedding_dimension()
            self.batch_size = 32  # Can handle larger batches
            self.available = True
        except ImportError as e:
            logger.error("sentence-transformers not available: {}".format(str(e)))
            logger.error("Install with: pip install sentence-transformers")
            self.available = False
            self.model_name = model_name
            self.dimension = 384  # Default dimension for all-MiniLM-L6-v2
            self.batch_size = 32
        except Exception as e:
            logger.error("Error initializing SentenceTransformers: {}".format(str(e)))
            self.available = False
            self.model_name = model_name
            self.dimension = 384
            self.batch_size = 32
        
    def create_embeddings_batch(self, texts):
        """Generate embeddings using SentenceTransformers"""
        if not self.available or not NUMPY_AVAILABLE:
            raise RuntimeError("SentenceTransformers not available. NumPy: {}, SentenceTransformers: {}".format(
                NUMPY_AVAILABLE, self.available))
        
        try:
            # SentenceTransformers can handle the full batch efficiently
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # Convert to list of numpy arrays for consistency
            return [np.array(emb) for emb in embeddings]
            
        except Exception as e:
            logger.error("Error generating SentenceTransformer embeddings: {}".format(str(e)))
            # Return zero vectors as fallback
            return [np.zeros(self.dimension) for _ in texts]
    
    def get_embedding_dimension(self):
        return self.dimension
    
    def get_model_info(self):
        return {
            "model_type": "sentence_transformers",
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "available": self.available
        }
    
    def estimate_cost(self, texts):
        """SentenceTransformers is free (only Lambda compute cost)"""
        # Only Lambda compute cost - roughly estimate based on processing time
        # Assume ~1ms per text for embedding generation
        processing_time_seconds = len(texts) * 0.001
        
        # Lambda cost: roughly $0.0000166667 per GB-second
        # Assume 2GB memory usage for embeddings
        lambda_cost = processing_time_seconds * 2 * 0.0000166667
        
        return lambda_cost
