#!/usr/bin/env python3
"""
NER-Based Sample Selection Generator for Climate Risk RAG System
Generates stratified samples based on documents that have completed NER processing.

This script uses NER results as the basis for sampling to ensure all selected
documents have completed the full processing pipeline and have corresponding
files in all processing stages.

Updated approach:
- Base sampling on data/ner_results (5K processed documents)
- Ensure corresponding files exist in all processing stages
- Generate realistic samples for cost-effective AWS vs POC comparison
"""

import os
import json
import pandas as pd
import numpy as np
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import hashlib
import random
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NERBasedSampleGenerator:
    """Generates representative document samples based on NER processing results"""
    
    def __init__(self, local_path: str):
        self.local_path = Path(local_path)
        self.ner_results_path = self.local_path / "data" / "ner_results"
        self.raw_docs_path = self.local_path / "data" / "raw"
        self.text_path = self.local_path / "data" / "processed" / "text"
        self.chunks_path = self.local_path / "data" / "chunks"
        self.embeddings_path = self.local_path / "data" / "embeddings"
        
        self.documents_df = None
        self.available_documents = []
        
    def extract_doc_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract document ID from NER result filename"""
        # NER files have pattern: {doc_id}_ner_results.json
        if filename.endswith('_ner_results.json'):
            return filename.replace('_ner_results.json', '')
        
        # Fallback patterns
        base_name = Path(filename).stem
        patterns = [
            r'^(.+)_ner_results$',  # Remove _ner_results suffix
            r'^(.+)\.pdf$',         # Simple PDF name
            r'^(.+)_\w+$',          # Name with suffix
            r'^(\w+_\d+)$',         # Pattern like prov_1234
            r'^([a-f0-9]{8}_[a-f0-9]{8})$',  # Hash pattern
        ]
        
        for pattern in patterns:
            match = re.match(pattern, base_name)
            if match:
                return match.group(1)
        
        # If no pattern matches, return the base name
        return base_name
    
    def load_ner_processed_documents(self) -> List[Dict]:
        """Load list of documents that have completed NER processing"""
        logger.info(f"Loading NER processed documents from: {self.ner_results_path}")
        
        if not self.ner_results_path.exists():
            raise FileNotFoundError(f"NER results directory not found: {self.ner_results_path}")
        
        ner_files = list(self.ner_results_path.glob("*.json"))
        logger.info(f"Found {len(ner_files)} NER result files")
        
        documents = []
        for ner_file in ner_files:
            doc_id = self.extract_doc_id_from_filename(ner_file.name)
            
            # Get file stats
            stat = ner_file.stat()
            
            doc_info = {
                'doc_id': doc_id,
                'ner_file': ner_file.name,
                'ner_size': stat.st_size,
                'ner_modified': datetime.fromtimestamp(stat.st_mtime),
                'has_ner': True
            }
            
            # Check for corresponding files in other stages
            doc_info.update(self._check_corresponding_files(doc_id))
            documents.append(doc_info)
        
        return documents
    
    def _check_corresponding_files(self, doc_id: str) -> Dict:
        """Check if corresponding files exist in all processing stages"""
        result = {
            'has_pdf': False,
            'has_text': False,
            'has_chunks': False,
            'has_embeddings': False,
            'pdf_size': 0,
            'text_size': 0,
            'chunk_count': 0,
            'embedding_count': 0
        }
        
        # Check for PDF file
        pdf_patterns = [f"{doc_id}.pdf", f"{doc_id}"]
        for pattern in pdf_patterns:
            pdf_path = self.raw_docs_path / pattern
            if pdf_path.exists():
                result['has_pdf'] = True
                result['pdf_size'] = pdf_path.stat().st_size
                break
        
        # Check for extracted text
        text_patterns = [f"{doc_id}.txt", f"{doc_id}"]
        for pattern in text_patterns:
            text_path = self.text_path / pattern
            if text_path.exists():
                result['has_text'] = True
                result['text_size'] = text_path.stat().st_size
                break
        
        # Check for chunks directory
        chunks_dir = self.chunks_path / doc_id
        if chunks_dir.exists() and chunks_dir.is_dir():
            result['has_chunks'] = True
            chunk_files = list(chunks_dir.glob("*.json"))
            result['chunk_count'] = len(chunk_files)
        
        # Check for embeddings directory
        embeddings_dir = self.embeddings_path / doc_id
        if embeddings_dir.exists() and embeddings_dir.is_dir():
            result['has_embeddings'] = True
            embedding_files = list(embeddings_dir.glob("*.json"))
            result['embedding_count'] = len(embedding_files)
        
        return result
    
    def enrich_document_metadata(self, documents: List[Dict]) -> pd.DataFrame:
        """Enrich document metadata with additional features for stratification"""
        logger.info("Enriching document metadata...")
        
        df = pd.DataFrame(documents)
        
        # Calculate completeness score (how many processing stages completed)
        df['completeness_score'] = (
            df['has_pdf'].astype(int) +
            df['has_text'].astype(int) +
            df['has_chunks'].astype(int) +
            df['has_embeddings'].astype(int) +
            df['has_ner'].astype(int)
        ) / 5.0
        
        # Categorize by completeness
        df['completeness_category'] = pd.cut(
            df['completeness_score'],
            bins=[0, 0.6, 0.8, 1.0],
            labels=['incomplete', 'partial', 'complete'],
            include_lowest=True
        )
        
        # Size categories based on PDF size
        df['size_category'] = pd.cut(
            df['pdf_size'],
            bins=[0, 1024*1024, 5*1024*1024, float('inf')],
            labels=['small', 'medium', 'large'],
            include_lowest=True
        )
        
        # Chunk complexity categories
        df['chunk_complexity'] = pd.cut(
            df['chunk_count'],
            bins=[0, 50, 200, float('inf')],
            labels=['simple', 'moderate', 'complex'],
            include_lowest=True
        )
        
        # Date categories based on NER processing date
        median_date = df['ner_modified'].median()
        df['processing_date_category'] = df['ner_modified'].apply(
            lambda x: 'recent' if x >= median_date else 'older'
        )
        
        # Document type inference from doc_id patterns
        df['doc_type'] = df['doc_id'].apply(self._infer_document_type)
        
        return df
    
    def _infer_document_type(self, doc_id: str) -> str:
        """Infer document type from document ID patterns"""
        doc_id_lower = doc_id.lower()
        
        if doc_id_lower.startswith('prov_'):
            return 'provisional'
        elif re.match(r'^[a-f0-9]{8}_[a-f0-9]{8}$', doc_id):
            return 'hash_named'
        elif any(keyword in doc_id_lower for keyword in ['report', 'analysis', 'study']):
            return 'report'
        elif any(keyword in doc_id_lower for keyword in ['policy', 'regulation', 'standard']):
            return 'regulatory'
        else:
            return 'other'
    
    def generate_stratified_sample(self, df: pd.DataFrame, sample_size: int, 
                                 strategy: str = 'balanced') -> pd.DataFrame:
        """Generate stratified sample ensuring representation across key dimensions"""
        logger.info(f"Generating stratified sample of {sample_size} documents...")
        
        # Filter to only complete documents for reliable testing
        complete_docs = df[df['completeness_score'] >= 0.8].copy()
        logger.info(f"Found {len(complete_docs)} documents with high completeness (>=80%)")
        
        if len(complete_docs) < sample_size:
            logger.warning(f"Only {len(complete_docs)} complete documents available, using all")
            return complete_docs
        
        # Stratification columns
        strat_columns = ['completeness_category', 'size_category', 'chunk_complexity', 
                        'processing_date_category', 'doc_type']
        
        # Create stratification groups
        complete_docs['strat_group'] = complete_docs[strat_columns].apply(
            lambda x: '_'.join(x.astype(str)), axis=1
        )
        
        # Calculate target samples per group
        group_counts = complete_docs['strat_group'].value_counts()
        group_proportions = group_counts / len(complete_docs)
        
        sampled_docs = []
        remaining_sample_size = sample_size
        
        for group, proportion in group_proportions.items():
            group_docs = complete_docs[complete_docs['strat_group'] == group]
            target_group_size = max(1, int(proportion * sample_size))
            
            if remaining_sample_size <= 0:
                break
                
            actual_group_size = min(target_group_size, len(group_docs), remaining_sample_size)
            
            if actual_group_size > 0:
                group_sample = group_docs.sample(n=actual_group_size, random_state=42)
                sampled_docs.append(group_sample)
                remaining_sample_size -= actual_group_size
        
        # If we still need more samples, randomly select from remaining
        if remaining_sample_size > 0 and sampled_docs:
            sampled_ids = set()
            for sample_df in sampled_docs:
                sampled_ids.update(sample_df['doc_id'].tolist())
            
            remaining_docs = complete_docs[~complete_docs['doc_id'].isin(sampled_ids)]
            if len(remaining_docs) > 0:
                additional_sample = remaining_docs.sample(
                    n=min(remaining_sample_size, len(remaining_docs)), 
                    random_state=42
                )
                sampled_docs.append(additional_sample)
        
        if sampled_docs:
            final_sample = pd.concat(sampled_docs, ignore_index=True)
        else:
            # Fallback to simple random sampling
            final_sample = complete_docs.sample(n=min(sample_size, len(complete_docs)), random_state=42)
        
        logger.info(f"Generated stratified sample with {len(final_sample)} documents")
        self._log_sample_distribution(final_sample)
        
        return final_sample
    
    def _log_sample_distribution(self, sample_df: pd.DataFrame):
        """Log the distribution of the generated sample"""
        logger.info("Sample distribution:")
        
        for column in ['completeness_category', 'size_category', 'chunk_complexity', 
                      'processing_date_category', 'doc_type']:
            if column in sample_df.columns:
                dist = sample_df[column].value_counts()
                logger.info(f"  {column}:")
                for value, count in dist.items():
                    percentage = (count / len(sample_df)) * 100
                    logger.info(f"    {value}: {count} ({percentage:.1f}%)")
    
    def validate_sample_quality(self, original_df: pd.DataFrame, sample_df: pd.DataFrame) -> Dict:
        """Validate the quality and representativeness of the generated sample"""
        logger.info("Validating sample quality...")
        
        validation_results = {
            'sample_size': len(sample_df),
            'original_size': len(original_df),
            'sample_ratio': len(sample_df) / len(original_df),
            'representativeness_score': 0.0,
            'completeness_check': True,
            'issues': []
        }
        
        # Check that all sampled documents have required files
        missing_files = sample_df[
            (sample_df['has_pdf'] == False) | 
            (sample_df['has_text'] == False) | 
            (sample_df['has_chunks'] == False) |
            (sample_df['has_ner'] == False)
        ]
        
        if len(missing_files) > 0:
            validation_results['completeness_check'] = False
            validation_results['issues'].append(f"{len(missing_files)} documents missing required files")
        
        # Calculate representativeness score
        representativeness_scores = []
        for column in ['size_category', 'chunk_complexity', 'doc_type']:
            if column in original_df.columns and column in sample_df.columns:
                orig_dist = original_df[column].value_counts(normalize=True)
                sample_dist = sample_df[column].value_counts(normalize=True)
                
                # Calculate KL divergence (simplified)
                score = 0
                for category in orig_dist.index:
                    if category in sample_dist.index:
                        score += abs(orig_dist[category] - sample_dist[category])
                
                representativeness_scores.append(1 - (score / 2))  # Normalize to 0-1
        
        if representativeness_scores:
            validation_results['representativeness_score'] = np.mean(representativeness_scores)
        
        logger.info(f"Sample validation completed. Representativeness score: {validation_results['representativeness_score']:.2f}")
        
        return validation_results
    
    def save_sample_selection(self, sample_df: pd.DataFrame, output_file: str, 
                            validation_results: Dict):
        """Save the sample selection to JSON file"""
        
        # Convert sample to list of dictionaries
        sample_documents = []
        for _, row in sample_df.iterrows():
            doc_dict = {
                'doc_id': row['doc_id'],
                'ner_file': row['ner_file'],
                'has_pdf': bool(row['has_pdf']),
                'has_text': bool(row['has_text']),
                'has_chunks': bool(row['has_chunks']),
                'has_embeddings': bool(row['has_embeddings']),
                'has_ner': bool(row['has_ner']),
                'pdf_size': int(row['pdf_size']) if pd.notna(row['pdf_size']) else 0,
                'text_size': int(row['text_size']) if pd.notna(row['text_size']) else 0,
                'chunk_count': int(row['chunk_count']) if pd.notna(row['chunk_count']) else 0,
                'embedding_count': int(row['embedding_count']) if pd.notna(row['embedding_count']) else 0,
                'completeness_score': float(row['completeness_score']),
                'size_category': str(row['size_category']),
                'chunk_complexity': str(row['chunk_complexity']),
                'doc_type': str(row['doc_type'])
            }
            sample_documents.append(doc_dict)
        
        # Create output structure
        output_data = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'generator_version': '2.0_ner_based',
                'sampling_strategy': 'ner_based_stratified',
                'local_path': str(self.local_path),
                'total_ner_documents': len(sample_df),
                'sample_size': len(sample_documents)
            },
            'validation': validation_results,
            'folder_structure': {
                'pdfs': 'data/raw/',
                'extracted_text': 'data/processed/text/',
                'chunks': 'data/chunks/',
                'embeddings': 'data/embeddings/',
                'ner_results': 'data/ner_results/'
            },
            'sample_documents': sample_documents
        }
        
        # Save to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        logger.info(f"Sample saved to: {output_path}")
        
        return output_data

def main():
    parser = argparse.ArgumentParser(description='Generate NER-based sample selection for migration')
    parser.add_argument('--local-path', required=True, help='Path to local climate risk data')
    parser.add_argument('--sample-size', type=int, default=1000, help='Number of documents to sample')
    parser.add_argument('--strategy', choices=['balanced', 'diverse'], default='balanced',
                       help='Sampling strategy')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--min-completeness', type=float, default=0.8,
                       help='Minimum completeness score for inclusion (0.0-1.0)')
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = NERBasedSampleGenerator(args.local_path)
        
        # Load NER processed documents
        documents = generator.load_ner_processed_documents()
        
        if not documents:
            logger.error("No NER processed documents found")
            return 1
        
        # Enrich metadata
        df = generator.enrich_document_metadata(documents)
        logger.info(f"Loaded metadata for {len(df)} documents")
        
        # Generate stratified sample
        sample_df = generator.generate_stratified_sample(df, args.sample_size, args.strategy)
        
        # Validate sample quality
        validation_results = generator.validate_sample_quality(df, sample_df)
        
        # Save sample selection
        generator.save_sample_selection(sample_df, args.output, validation_results)
        
        # Print summary
        print(f"\n✅ Sample generation completed!")
        print(f"📊 Sample size: {len(sample_df)} documents")
        print(f"📁 Output file: {args.output}")
        print(f"🎯 Representativeness score: {validation_results['representativeness_score']:.2f}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Sample generation failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
