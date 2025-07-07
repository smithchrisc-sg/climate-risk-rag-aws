#!/usr/bin/env python3
"""
Generate Sample Selection for Selective Migration
Implements stratified sampling to ensure representative document selection
"""

import os
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from collections import defaultdict
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentSampleGenerator:
    """Generates representative document samples using stratified sampling"""
    
    def __init__(self, local_path: str):
        self.local_path = Path(local_path)
        self.documents_df = None
        self.metadata_cache = {}
        
        # Document classification patterns
        self.document_patterns = {
            'climate_reports': [
                'ipcc', 'climate', 'assessment', 'report', 'global', 'warming',
                'temperature', 'carbon', 'emission', 'greenhouse'
            ],
            'regulatory_docs': [
                'regulation', 'policy', 'compliance', 'standard', 'framework',
                'guideline', 'requirement', 'mandate', 'law', 'act'
            ],
            'technical_studies': [
                'study', 'analysis', 'research', 'technical', 'methodology',
                'model', 'simulation', 'data', 'measurement', 'observation'
            ],
            'financial_analysis': [
                'economic', 'financial', 'cost', 'benefit', 'investment',
                'market', 'price', 'revenue', 'budget', 'funding'
            ]
        }
        
        # Size categories (in pages, estimated from file size)
        self.size_categories = {
            'small': (0, 50),      # <50 pages
            'medium': (50, 200),   # 50-200 pages  
            'large': (200, 1000)   # >200 pages
        }
    
    def load_document_metadata(self) -> pd.DataFrame:
        """Load and analyze document metadata from various sources"""
        logger.info("Loading document metadata...")
        
        documents = []
        
        # Load from SQLite database if available
        db_path = self.local_path / "db" / "corpus_document_ids.db"
        if db_path.exists():
            documents.extend(self._load_from_database(db_path))
        
        # Load from provenance file if available
        provenance_path = self.local_path / "data" / "provenance.jsonl"
        if provenance_path.exists():
            documents.extend(self._load_from_provenance(provenance_path))
        
        # Scan raw documents directory
        raw_docs_path = self.local_path / "data" / "raw"
        if raw_docs_path.exists():
            documents.extend(self._scan_raw_documents(raw_docs_path))
        
        # Create DataFrame
        if not documents:
            raise ValueError("No documents found in any source")
        
        self.documents_df = pd.DataFrame(documents)
        self._enrich_metadata()
        
        logger.info(f"Loaded metadata for {len(self.documents_df)} documents")
        return self.documents_df
    
    def _load_from_database(self, db_path: Path) -> List[Dict]:
        """Load document metadata from SQLite database"""
        documents = []
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Try different possible table structures
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            for table_name, in tables:
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    columns = [description[0] for description in cursor.description]
                    
                    if 'id' in columns or 'document_id' in columns:
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            doc_data = dict(zip(columns, row))
                            documents.append({
                                'doc_id': doc_data.get('id') or doc_data.get('document_id'),
                                'title': doc_data.get('title', ''),
                                'source': doc_data.get('source', 'database'),
                                'date': doc_data.get('date') or doc_data.get('created_date'),
                                'metadata': doc_data
                            })
                        break
                        
                except Exception as e:
                    logger.debug(f"Could not process table {table_name}: {e}")
                    continue
            
            conn.close()
            
        except Exception as e:
            logger.warning(f"Could not load from database: {e}")
        
        return documents
    
    def _load_from_provenance(self, provenance_path: Path) -> List[Dict]:
        """Load document metadata from provenance JSONL file"""
        documents = []
        
        try:
            with open(provenance_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        documents.append({
                            'doc_id': data.get('document_id') or f"prov_{line_num}",
                            'title': data.get('title', ''),
                            'source': data.get('source', 'provenance'),
                            'date': data.get('date'),
                            'metadata': data
                        })
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num}: {e}")
                        continue
                        
        except Exception as e:
            logger.warning(f"Could not load provenance file: {e}")
        
        return documents
    
    def _scan_raw_documents(self, raw_path: Path) -> List[Dict]:
        """Scan raw documents directory for PDF files"""
        documents = []
        
        try:
            pdf_files = list(raw_path.glob("*.pdf"))
            
            for pdf_file in pdf_files:
                # Extract document ID from filename
                doc_id = pdf_file.stem
                
                # Get file stats
                stat = pdf_file.stat()
                
                documents.append({
                    'doc_id': doc_id,
                    'title': doc_id.replace('_', ' ').replace('-', ' ').title(),
                    'source': 'filesystem',
                    'date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_size': stat.st_size,
                    'file_path': str(pdf_file),
                    'metadata': {
                        'file_size': stat.st_size,
                        'modified_time': stat.st_mtime,
                        'file_path': str(pdf_file)
                    }
                })
                
        except Exception as e:
            logger.warning(f"Could not scan raw documents: {e}")
        
        return documents
    
    def _enrich_metadata(self):
        """Enrich document metadata with derived features"""
        logger.info("Enriching document metadata...")
        
        # Classify document types based on title/content
        self.documents_df['document_type'] = self.documents_df.apply(
            self._classify_document_type, axis=1
        )
        
        # Estimate document size category
        self.documents_df['size_category'] = self.documents_df.apply(
            self._estimate_size_category, axis=1
        )
        
        # Extract date features
        self.documents_df['year'] = self.documents_df['date'].apply(self._extract_year)
        self.documents_df['date_category'] = self.documents_df['year'].apply(
            lambda x: 'recent' if x and x >= 2020 else 'historical'
        )
        
        # Estimate processing complexity
        self.documents_df['complexity'] = self.documents_df.apply(
            self._estimate_complexity, axis=1
        )
        
        # Add hash for reproducible sampling
        self.documents_df['sample_hash'] = self.documents_df['doc_id'].apply(
            lambda x: int(hashlib.md5(str(x).encode()).hexdigest()[:8], 16)
        )
    
    def _classify_document_type(self, row) -> str:
        """Classify document type based on title and metadata"""
        title = str(row.get('title', '')).lower()
        doc_id = str(row.get('doc_id', '')).lower()
        text = f"{title} {doc_id}"
        
        scores = {}
        for doc_type, keywords in self.document_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[doc_type] = score
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return 'other'
    
    def _estimate_size_category(self, row) -> str:
        """Estimate document size category"""
        file_size = row.get('file_size', 0)
        
        if file_size == 0:
            return 'unknown'
        
        # Rough estimation: 1 page ≈ 50KB for PDF
        estimated_pages = file_size / (50 * 1024)
        
        for category, (min_pages, max_pages) in self.size_categories.items():
            if min_pages <= estimated_pages < max_pages:
                return category
        
        return 'large'  # Default for very large documents
    
    def _extract_year(self, date_str) -> Optional[int]:
        """Extract year from date string"""
        if not date_str:
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y']:
                try:
                    return datetime.strptime(str(date_str)[:10], fmt[:len(str(date_str)[:10])]).year
                except ValueError:
                    continue
            
            # Try to extract 4-digit year
            import re
            year_match = re.search(r'(19|20)\d{2}', str(date_str))
            if year_match:
                return int(year_match.group())
                
        except Exception:
            pass
        
        return None
    
    def _estimate_complexity(self, row) -> str:
        """Estimate document processing complexity"""
        title = str(row.get('title', '')).lower()
        file_size = row.get('file_size', 0)
        
        # Simple heuristics for complexity
        complex_indicators = ['table', 'chart', 'figure', 'graph', 'diagram', 'appendix']
        has_complex_content = any(indicator in title for indicator in complex_indicators)
        
        if has_complex_content or file_size > 5 * 1024 * 1024:  # >5MB
            return 'complex_layout'
        elif file_size > 1 * 1024 * 1024:  # >1MB
            return 'tables_charts'
        else:
            return 'simple_text'
    
    def generate_stratified_sample(self, sample_size: int, strategy: str = 'stratified') -> List[Dict]:
        """Generate stratified sample of documents"""
        logger.info(f"Generating {strategy} sample of {sample_size} documents...")
        
        if self.documents_df is None:
            self.load_document_metadata()
        
        if strategy == 'random':
            return self._random_sample(sample_size)
        elif strategy == 'stratified':
            return self._stratified_sample(sample_size)
        else:
            raise ValueError(f"Unknown sampling strategy: {strategy}")
    
    def _random_sample(self, sample_size: int) -> List[Dict]:
        """Generate random sample"""
        sample_df = self.documents_df.sample(n=min(sample_size, len(self.documents_df)), 
                                           random_state=42)
        return sample_df.to_dict('records')
    
    def _stratified_sample(self, sample_size: int) -> List[Dict]:
        """Generate stratified sample ensuring representative coverage"""
        
        # Define stratification targets
        stratification_targets = {
            'document_type': {
                'climate_reports': 0.40,      # 40%
                'regulatory_docs': 0.20,      # 20%
                'technical_studies': 0.25,    # 25%
                'financial_analysis': 0.15    # 15%
            },
            'date_category': {
                'recent': 0.40,               # 40% recent (2020+)
                'historical': 0.60            # 60% historical
            },
            'size_category': {
                'small': 0.20,                # 20%
                'medium': 0.50,               # 50%
                'large': 0.30                 # 30%
            },
            'complexity': {
                'simple_text': 0.30,          # 30%
                'tables_charts': 0.40,        # 40%
                'complex_layout': 0.30        # 30%
            }
        }
        
        # Start with document type stratification (primary)
        selected_docs = []
        remaining_docs = self.documents_df.copy()
        
        for doc_type, target_ratio in stratification_targets['document_type'].items():
            target_count = int(sample_size * target_ratio)
            
            # Filter documents of this type
            type_docs = remaining_docs[remaining_docs['document_type'] == doc_type]
            
            if len(type_docs) == 0:
                logger.warning(f"No documents found for type: {doc_type}")
                continue
            
            # Apply secondary stratification within this type
            type_sample = self._apply_secondary_stratification(
                type_docs, target_count, stratification_targets
            )
            
            selected_docs.extend(type_sample)
            
            # Remove selected docs from remaining pool
            selected_ids = [doc['doc_id'] for doc in type_sample]
            remaining_docs = remaining_docs[~remaining_docs['doc_id'].isin(selected_ids)]
        
        # Fill remaining slots with random selection if needed
        current_count = len(selected_docs)
        if current_count < sample_size and len(remaining_docs) > 0:
            additional_needed = sample_size - current_count
            additional_sample = remaining_docs.sample(
                n=min(additional_needed, len(remaining_docs)), 
                random_state=42
            ).to_dict('records')
            selected_docs.extend(additional_sample)
        
        logger.info(f"Generated stratified sample with {len(selected_docs)} documents")
        self._log_sample_distribution(selected_docs)
        
        return selected_docs[:sample_size]  # Ensure exact sample size
    
    def _apply_secondary_stratification(self, docs_df: pd.DataFrame, target_count: int, 
                                      stratification_targets: Dict) -> List[Dict]:
        """Apply secondary stratification within a document type"""
        
        if len(docs_df) <= target_count:
            return docs_df.to_dict('records')
        
        # Try to balance by date category first
        selected = []
        remaining = docs_df.copy()
        
        for date_cat, ratio in stratification_targets['date_category'].items():
            cat_target = max(1, int(target_count * ratio))
            cat_docs = remaining[remaining['date_category'] == date_cat]
            
            if len(cat_docs) > 0:
                sample_count = min(cat_target, len(cat_docs))
                cat_sample = cat_docs.sample(n=sample_count, random_state=42)
                selected.extend(cat_sample.to_dict('records'))
                remaining = remaining[~remaining['doc_id'].isin(cat_sample['doc_id'])]
        
        # Fill remaining slots
        current_count = len(selected)
        if current_count < target_count and len(remaining) > 0:
            additional_needed = target_count - current_count
            additional = remaining.sample(
                n=min(additional_needed, len(remaining)), 
                random_state=42
            )
            selected.extend(additional.to_dict('records'))
        
        return selected[:target_count]
    
    def _log_sample_distribution(self, sample_docs: List[Dict]):
        """Log the distribution of the generated sample"""
        sample_df = pd.DataFrame(sample_docs)
        
        logger.info("Sample distribution:")
        
        for column in ['document_type', 'date_category', 'size_category', 'complexity']:
            if column in sample_df.columns:
                distribution = sample_df[column].value_counts()
                percentages = (distribution / len(sample_df) * 100).round(1)
                
                logger.info(f"  {column}:")
                for value, count in distribution.items():
                    pct = percentages[value]
                    logger.info(f"    {value}: {count} ({pct}%)")
    
    def validate_sample(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Validate the quality of the generated sample"""
        logger.info("Validating sample quality...")
        
        validation_results = {
            'sample_size': len(sample_docs),
            'coverage_analysis': {},
            'representativeness_score': 0.0,
            'quality_issues': []
        }
        
        sample_df = pd.DataFrame(sample_docs)
        
        # Check coverage of different categories
        for column in ['document_type', 'date_category', 'size_category', 'complexity']:
            if column in sample_df.columns:
                unique_values = sample_df[column].nunique()
                total_possible = self.documents_df[column].nunique()
                coverage_ratio = unique_values / total_possible if total_possible > 0 else 0
                
                validation_results['coverage_analysis'][column] = {
                    'unique_in_sample': unique_values,
                    'total_possible': total_possible,
                    'coverage_ratio': coverage_ratio
                }
                
                if coverage_ratio < 0.5:
                    validation_results['quality_issues'].append(
                        f"Low coverage for {column}: {coverage_ratio:.2%}"
                    )
        
        # Calculate overall representativeness score
        coverage_scores = [
            analysis['coverage_ratio'] 
            for analysis in validation_results['coverage_analysis'].values()
        ]
        validation_results['representativeness_score'] = np.mean(coverage_scores) if coverage_scores else 0.0
        
        # Check for duplicate documents
        if len(sample_docs) != len(set(doc['doc_id'] for doc in sample_docs)):
            validation_results['quality_issues'].append("Duplicate documents found in sample")
        
        # Check for missing essential data
        missing_ids = sum(1 for doc in sample_docs if not doc.get('doc_id'))
        if missing_ids > 0:
            validation_results['quality_issues'].append(f"{missing_ids} documents missing doc_id")
        
        logger.info(f"Sample validation completed. Representativeness score: {validation_results['representativeness_score']:.2%}")
        
        return validation_results
    
    def save_sample(self, sample_docs: List[Dict], output_path: str):
        """Save sample selection to JSON file"""
        
        # Prepare sample data with metadata
        sample_data = {
            'metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'sample_size': len(sample_docs),
                'total_documents': len(self.documents_df) if self.documents_df is not None else 0,
                'sampling_strategy': 'stratified',
                'version': '1.0'
            },
            'sample_documents': sample_docs,
            'validation': self.validate_sample(sample_docs)
        }
        
        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(sample_data, f, indent=2, default=str)
        
        logger.info(f"Sample saved to: {output_path}")
        
        return sample_data


def main():
    parser = argparse.ArgumentParser(description='Generate document sample for selective migration')
    parser.add_argument('--local-path', required=True, help='Path to local data lake')
    parser.add_argument('--sample-size', type=int, default=1000, help='Number of documents to sample')
    parser.add_argument('--strategy', choices=['random', 'stratified'], default='stratified', 
                       help='Sampling strategy')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--validate', action='store_true', help='Run additional validation')
    
    args = parser.parse_args()
    
    try:
        # Generate sample
        generator = DocumentSampleGenerator(args.local_path)
        generator.load_document_metadata()
        
        sample_docs = generator.generate_stratified_sample(args.sample_size, args.strategy)
        
        # Save sample
        sample_data = generator.save_sample(sample_docs, args.output)
        
        # Print summary
        print(f"\n✅ Sample generation completed!")
        print(f"📊 Sample size: {len(sample_docs)} documents")
        print(f"📁 Output file: {args.output}")
        print(f"🎯 Representativeness score: {sample_data['validation']['representativeness_score']:.2%}")
        
        if sample_data['validation']['quality_issues']:
            print(f"⚠️  Quality issues found:")
            for issue in sample_data['validation']['quality_issues']:
                print(f"   - {issue}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Sample generation failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
