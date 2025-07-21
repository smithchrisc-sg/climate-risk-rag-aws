"""
AWS Titan embeddings implementation
PRESERVED FROM DEPRECATED VERSION - NO FUNCTIONALITY CHANGES
"""
import json
import boto3
import logging
from typing import List
from embeddings_interface import EmbeddingsInterface

# Conditional numpy import
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)

class TitanEmbeddings(EmbeddingsInterface):
    def __init__(self, bedrock_client=None, model_id="amazon.titan-embed-text-v1", **kwargs):
        self.bedrock_client = bedrock_client or boto3.client('bedrock-runtime')
        self._model_id = model_id
        self.batch_size = 25  # Titan API limit
        self._dimension = 1536  # Titan embedding dimension
        
        logger.info(f"Initialized Titan embeddings with model: {self._model_id}")
        
    @property
    def dimension(self) -> int:
        return self._dimension
    
    @property
    def model_id(self) -> str:
        return self._model_id
        
    def create_embeddings_batch(self, texts):
        """Generate embeddings using Titan API"""
        embeddings = []
        
        # Process in batches to respect API limits
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self._process_batch(batch)
            embeddings.extend(batch_embeddings)
            
        return embeddings
    
    def _process_batch(self, texts):
        """Process a single batch through Titan API"""
        embeddings = []
        
        for text in texts:
            try:
                # Prepare request
                request_body = {
                    "inputText": text
                }
                
                # Call Titan API
                response = self.bedrock_client.invoke_model(
                    modelId=self._model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                embedding = response_body.get('embedding')
                
                if embedding is None:
                    logger.error(f"No embedding returned for text: {text[:100]}...")
                    # Use zero vector as fallback
                    embedding = [0.0] * self._dimension
                
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error generating embedding for text: {str(e)}")
                # Use zero vector as fallback
                embeddings.append([0.0] * self._dimension)
                
        return embeddings
    
    def create_single_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        return self.create_embeddings_batch([text])[0]
