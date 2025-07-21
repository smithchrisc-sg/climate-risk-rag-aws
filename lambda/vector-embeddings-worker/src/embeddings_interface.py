"""
Embeddings Interface - Abstract base class for different embedding models
PRESERVED FROM DEPRECATED VERSION - NO FUNCTIONALITY CHANGES
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class EmbeddingsInterface(ABC):
    """Abstract interface for embedding generation"""
    
    @abstractmethod
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension"""
        pass
    
    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model identifier"""
        pass

class EmbeddingsFactory:
    """Factory for creating embedding instances"""
    
    @staticmethod
    def create_embeddings(model_type: str = "titan", **kwargs) -> EmbeddingsInterface:
        """Create embeddings instance based on model type"""
        
        if model_type.lower() == "titan":
            from titan_embeddings import TitanEmbeddings
            return TitanEmbeddings(**kwargs)
        
        elif model_type.lower() == "sentence_transformer":
            from sentence_transformer_embeddings import SentenceTransformerEmbeddings
            return SentenceTransformerEmbeddings(**kwargs)
        
        else:
            raise ValueError(f"Unsupported embedding model type: {model_type}")
    
    @staticmethod
    def get_available_models() -> List[str]:
        """Get list of available embedding models"""
        return ["titan", "sentence_transformer"]
