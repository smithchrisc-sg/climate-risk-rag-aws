#!/usr/bin/env python3
"""
Comparison Testing Framework for Climate Risk RAG System
Compares POC vs AWS implementations across multiple dimensions:
- Text Extraction: Your parsing vs AWS Textract
- NER: Flair vs AWS Comprehend  
- Embeddings: Your vectors vs AWS Titan
- Chunking: 5-sentence vs AWS structured
- End-to-end RAG performance
"""

import json
import boto3
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import classification_report
import concurrent.futures
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComparisonFramework:
    """Framework for comparing POC vs AWS implementations"""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        self.aws_region = aws_region
        self.s3 = boto3.client('s3', region_name=aws_region)
        self.textract = boto3.client('textract', region_name=aws_region)
        self.comprehend = boto3.client('comprehend', region_name=aws_region)
        self.bedrock = boto3.client('bedrock-runtime', region_name=aws_region)
        
        # Results storage
        self.comparison_results = {
            'text_extraction': {},
            'ner_comparison': {},
            'embedding_comparison': {},
            'chunking_comparison': {},
            'rag_performance': {},
            'summary': {}
        }
    
    def run_comprehensive_comparison(self, 
                                   documents_bucket: str,
                                   artifacts_bucket: str,
                                   sample_size: int = 100) -> Dict[str, Any]:
        """Run comprehensive comparison across all dimensions"""
        
        logger.info("Starting comprehensive POC vs AWS comparison")
        logger.info(f"Sample size: {sample_size} documents")
        
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Load sample documents for comparison
            sample_docs = self._select_comparison_sample(documents_bucket, sample_size)
            logger.info(f"Selected {len(sample_docs)} documents for comparison")
            
            # Step 2: Text Extraction Comparison
            logger.info("Comparing text extraction methods...")
            self.comparison_results['text_extraction'] = self._compare_text_extraction(
                sample_docs, documents_bucket, artifacts_bucket
            )
            
            # Step 3: NER Comparison
            logger.info("Comparing NER methods...")
            self.comparison_results['ner_comparison'] = self._compare_ner_methods(
                sample_docs, artifacts_bucket
            )
            
            # Step 4: Embedding Comparison
            logger.info("Comparing embedding methods...")
            self.comparison_results['embedding_comparison'] = self._compare_embeddings(
                sample_docs, artifacts_bucket
            )
            
            # Step 5: Chunking Comparison
            logger.info("Comparing chunking methods...")
            self.comparison_results['chunking_comparison'] = self._compare_chunking_methods(
                sample_docs, artifacts_bucket
            )
            
            # Step 6: End-to-end RAG Performance
            logger.info("Comparing RAG performance...")
            self.comparison_results['rag_performance'] = self._compare_rag_performance(
                sample_docs, documents_bucket, artifacts_bucket
            )
            
            # Step 7: Generate Summary
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.comparison_results['summary'] = {
                'comparison_completed': end_time.isoformat(),
                'duration_seconds': duration,
                'sample_size': len(sample_docs),
                'comparison_dimensions': list(self.comparison_results.keys())[:-1],  # Exclude summary
                'recommendations': self._generate_recommendations()
            }
            
            # Save results
            self._save_comparison_results(artifacts_bucket)
            
            # Generate visualizations
            self._create_comparison_visualizations()
            
            logger.info(f"Comprehensive comparison completed in {duration:.2f} seconds")
            return self.comparison_results
            
        except Exception as e:
            logger.error(f"Comparison failed: {str(e)}")
            raise
    
    def _select_comparison_sample(self, documents_bucket: str, sample_size: int) -> List[Dict]:
        """Select representative sample of documents for comparison"""
        
        # Get list of all documents
        paginator = self.s3.get_paginator('list_objects_v2')
        all_docs = []
        
        for page in paginator.paginate(Bucket=documents_bucket, Prefix='documents/'):
            for obj in page.get('Contents', []):
                if obj['Key'].endswith('.pdf'):
                    doc_id = obj['Key'].split('/')[-1].replace('.pdf', '')
                    all_docs.append({
                        'doc_id': doc_id,
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
        
        # Sample documents (stratified by size if possible)
        if len(all_docs) <= sample_size:
            return all_docs
        
        # Sort by size and take representative sample
        all_docs.sort(key=lambda x: x['size'])
        step = len(all_docs) // sample_size
        sample_docs = [all_docs[i] for i in range(0, len(all_docs), step)][:sample_size]
        
        logger.info(f"Selected {len(sample_docs)} documents from {len(all_docs)} total")
        return sample_docs
    
    def _compare_text_extraction(self, sample_docs: List[Dict], 
                               documents_bucket: str, artifacts_bucket: str) -> Dict[str, Any]:
        """Compare POC text extraction vs AWS Textract"""
        
        comparison_results = {
            'method': 'text_extraction_comparison',
            'sample_size': len(sample_docs),
            'comparisons': [],
            'metrics': {}
        }
        
        # Process sample of documents
        sample_subset = sample_docs[:10]  # Limit for detailed comparison
        
        for doc in tqdm(sample_subset, desc="Comparing text extraction"):
            try:
                doc_id = doc['doc_id']
                
                # Get POC extracted text
                poc_text = self._get_poc_extracted_text(doc_id, artifacts_bucket)
                
                # Get AWS Textract text
                aws_text = self._get_textract_text(doc['key'], documents_bucket)
                
                if poc_text and aws_text:
                    # Compare texts
                    comparison = self._compare_text_quality(poc_text, aws_text, doc_id)
                    comparison_results['comparisons'].append(comparison)
                    
            except Exception as e:
                logger.error(f"Error comparing text extraction for {doc['doc_id']}: {str(e)}")
        
        # Calculate aggregate metrics
        if comparison_results['comparisons']:
            comparison_results['metrics'] = self._calculate_text_metrics(
                comparison_results['comparisons']
            )
        
        return comparison_results
    
    def _compare_ner_methods(self, sample_docs: List[Dict], artifacts_bucket: str) -> Dict[str, Any]:
        """Compare Flair NER vs AWS Comprehend"""
        
        comparison_results = {
            'method': 'ner_comparison',
            'sample_size': len(sample_docs),
            'comparisons': [],
            'metrics': {}
        }
        
        # Process sample of documents
        sample_subset = sample_docs[:20]  # Limit for detailed comparison
        
        for doc in tqdm(sample_subset, desc="Comparing NER methods"):
            try:
                doc_id = doc['doc_id']
                
                # Get Flair NER results
                flair_entities = self._get_flair_ner_results(doc_id, artifacts_bucket)
                
                # Get text for Comprehend processing
                text = self._get_poc_extracted_text(doc_id, artifacts_bucket)
                
                if text and flair_entities:
                    # Get AWS Comprehend results
                    comprehend_entities = self._get_comprehend_entities(text)
                    
                    # Compare NER results
                    comparison = self._compare_ner_results(
                        flair_entities, comprehend_entities, doc_id
                    )
                    comparison_results['comparisons'].append(comparison)
                    
            except Exception as e:
                logger.error(f"Error comparing NER for {doc['doc_id']}: {str(e)}")
        
        # Calculate aggregate metrics
        if comparison_results['comparisons']:
            comparison_results['metrics'] = self._calculate_ner_metrics(
                comparison_results['comparisons']
            )
        
        return comparison_results
