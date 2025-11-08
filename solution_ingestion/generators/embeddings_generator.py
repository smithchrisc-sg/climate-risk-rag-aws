#!/usr/bin/env python3
"""
Embeddings Generator for Solution Ingestion
Generates vector embeddings using AWS Bedrock Titan for text chunks.
Adapted from vector-embeddings-worker Lambda function.
"""

import json
import boto3
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class TitanEmbeddings:
    """Titan embeddings implementation adapted from Lambda function."""
    
    def __init__(self, bedrock_client=None, model_id="amazon.titan-embed-text-v1", region="us-east-1"):
        self.bedrock_client = bedrock_client or boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        self.batch_size = 25  # Titan API limit
        self.dimension = 1536  # Titan embedding dimension
        self.rate_limit_delay = 0.1  # 100ms between requests for cost control
        
        logger.info(f"Initialized Titan embeddings with model: {self.model_id}")
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts with rate limiting."""
        embeddings = []
        
        # Process in batches to respect API limits
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1}")
            
            batch_embeddings = self._process_batch(batch)
            embeddings.extend(batch_embeddings)
            
            # Rate limiting to control costs
            if i + self.batch_size < len(texts):
                time.sleep(self.rate_limit_delay)
        
        return embeddings
    
    def _process_batch(self, texts: List[str]) -> List[List[float]]:
        """Process a single batch through Titan API."""
        embeddings = []
        
        for text in texts:
            try:
                # Prepare request
                request_body = {
                    "inputText": text[:8000]  # Titan input limit
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
                embedding = response_body.get('embedding')
                
                if embedding is None:
                    logger.error(f"No embedding returned for text: {text[:100]}...")
                    embedding = [0.0] * self.dimension
                
                embeddings.append(embedding)
                
                # Rate limiting between individual requests
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error generating embedding for text: {str(e)}")
                embeddings.append([0.0] * self.dimension)
        
        return embeddings

class EmbeddingsGenerator:
    """Generates vector embeddings for text chunks using Bedrock Titan."""
    
    def __init__(self, region="us-east-1", model_id="amazon.titan-embed-text-v1"):
        self.region = region
        self.model_id = model_id
        self.titan = TitanEmbeddings(region=region, model_id=model_id)
        
        # Cost tracking
        self.total_tokens_processed = 0
        self.total_api_calls = 0
        
        logger.info("EmbeddingsGenerator initialized")
    
    def process_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process chunks and add embeddings.
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
            
        Returns:
            List of chunks with added 'embedding' field
        """
        logger.info(f"Processing {len(chunks)} chunks for embeddings")
        
        # Extract texts for batch processing
        texts = [chunk.get('text', '') for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.titan.create_embeddings_batch(texts)
        
        # Add embeddings to chunks
        enriched_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            enriched_chunk = chunk.copy()
            enriched_chunk['embedding'] = embedding
            enriched_chunk['embedding_model'] = self.model_id
            enriched_chunk['embedding_dimension'] = self.titan.dimension
            enriched_chunks.append(enriched_chunk)
        
        # Update cost tracking
        self.total_tokens_processed += sum(len(text.split()) for text in texts)
        self.total_api_calls += len(texts)
        
        logger.info(f"Generated embeddings for {len(chunks)} chunks")
        logger.info(f"Total tokens processed: {self.total_tokens_processed}")
        logger.info(f"Total API calls: {self.total_api_calls}")
        logger.info(f"Estimated cost: ${self.estimate_cost():.4f}")
        
        return enriched_chunks
    
    def process_solutions_chunks(self, solutions_with_chunks: List[tuple]) -> List[tuple]:
        """
        Process solutions with their chunks and add embeddings.
        
        Args:
            solutions_with_chunks: List of (solution, chunks) tuples
            
        Returns:
            List of (solution, enriched_chunks) tuples
        """
        logger.info(f"Processing embeddings for {len(solutions_with_chunks)} solutions")
        
        enriched_solutions = []
        
        for solution, chunks in solutions_with_chunks:
            logger.info(f"Processing embeddings for solution: {solution.name}")
            
            # Convert chunk objects to dictionaries if needed
            chunk_dicts = []
            for chunk in chunks:
                if hasattr(chunk, '__dict__'):
                    chunk_dict = chunk.__dict__.copy()
                else:
                    chunk_dict = chunk
                chunk_dicts.append(chunk_dict)
            
            # Generate embeddings
            enriched_chunks = self.process_chunks(chunk_dicts)
            
            enriched_solutions.append((solution, enriched_chunks))
        
        return enriched_solutions
    
    def estimate_cost(self) -> float:
        """Estimate cost based on tokens processed."""
        # Titan pricing: ~$0.0008 per 1K tokens
        cost_per_1k_tokens = 0.0008
        return (self.total_tokens_processed / 1000) * cost_per_1k_tokens
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get detailed cost summary."""
        return {
            'total_tokens_processed': self.total_tokens_processed,
            'total_api_calls': self.total_api_calls,
            'estimated_cost_usd': self.estimate_cost(),
            'model_id': self.model_id,
            'cost_per_1k_tokens': 0.0008
        }
