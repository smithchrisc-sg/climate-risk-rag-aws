"""
AWS Titan embeddings implementation
"""
import json
import boto3
import logging
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
        self.model_id = model_id
        self.batch_size = 25  # Titan API limit
        self.dimension = 1536  # Titan embedding dimension
        
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
                    modelId=self.model_id,
                    body=json.dumps(request_body),
                    contentType='application/json',
                    accept='application/json'
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                embedding_vector = response_body['embedding']
                
                # Convert to numpy array if available, otherwise keep as list
                if NUMPY_AVAILABLE:
                    embedding = np.array(embedding_vector)
                else:
                    embedding = embedding_vector
                    
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error("Error generating Titan embedding: {}".format(str(e)))
                # Return zero vector as fallback
                if NUMPY_AVAILABLE:
                    embeddings.append(np.zeros(self.dimension))
                else:
                    embeddings.append([0.0] * self.dimension)
                
        return embeddings
    
    def get_embedding_dimension(self):
        return self.dimension
    
    def get_model_info(self):
        return {
            "model_type": "titan",
            "model_id": self.model_id,
            "dimension": self.dimension,
            "batch_size": self.batch_size
        }
    
    def estimate_cost(self, texts):
        """Estimate cost based on token count"""
        # Rough estimate: ~4 characters per token
        total_chars = sum(len(text) for text in texts)
        estimated_tokens = total_chars / 4
        
        # Titan cost: $0.0004 per 1K tokens
        cost = (estimated_tokens / 1000) * 0.0004
        return cost
