#!/usr/bin/env python3
"""
NER-Based Sample Validation Script
Validates the quality and representativeness of NER-based document samples.

This script validates samples generated from documents that have completed
NER processing, ensuring data consistency across all processing stages.
"""

import os
import json
import pandas as pd
import numpy as np
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import Counter
# import matplotlib.pyplot as plt  # Optional for plotting
# import seaborn as sns  # Optional for plotting

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NERSampleValidator:
    """Validates NER-based document samples for quality and representativeness"""
    
    def __init__(self, local_path: str):
        self.local_path = Path(local_path)
        self.ner_results_path = self.local_path / "data" / "ner_results"
        self.raw_docs_path = self.local_path / "data" / "raw"
        self.text_path = self.local_path / "data" / "processed" / "text"
        self.chunks_path = self.local_path / "data" / "chunks"
        self.embeddings_path = self.local_path / "data" / "embeddings"
    
    def load_sample(self, sample_file: str) -> Dict:
        """Load sample selection from JSON file"""
        logger.info(f"Loading sample from: {sample_file}")
        
        with open(sample_file, 'r') as f:
            sample_data = json.load(f)
        
        return sample_data
    
    def validate_sample_structure(self, sample_data: Dict) -> Dict:
        """Validate the structure of the sample data"""
        logger.info("Validating sample structure...")
        
        validation_results = {
            'structure_valid': True,
            'issues': [],
            'metadata_present': False,
            'folder_structure_present': False,
            'sample_documents_present': False
        }
        
        # Check required top-level keys
        required_keys = ['metadata', 'sample_documents', 'folder_structure']
        for key in required_keys:
            if key in sample_data:
                validation_results[f"{key}_present"] = True
            else:
                validation_results['structure_valid'] = False
                validation_results['issues'].append(f"Missing required key: {key}")
        
        # Validate sample documents structure
        if 'sample_documents' in sample_data:
            sample_docs = sample_data['sample_documents']
            if not isinstance(sample_docs, list):
                validation_results['structure_valid'] = False
                validation_results['issues'].append("sample_documents should be a list")
            elif len(sample_docs) == 0:
                validation_results['structure_valid'] = False
                validation_results['issues'].append("sample_documents is empty")
            else:
                # Check first document structure
                first_doc = sample_docs[0]
                required_doc_fields = ['doc_id', 'has_pdf', 'has_text', 'has_chunks', 'has_ner']
                for field in required_doc_fields:
                    if field not in first_doc:
                        validation_results['issues'].append(f"Missing field in documents: {field}")
        
        return validation_results
    
    def validate_sample_distribution(self, sample_data: Dict) -> Dict:
        """Validate the distribution and representativeness of the sample"""
        logger.info("Validating sample distribution...")
        
        sample_docs = sample_data.get('sample_documents', [])
        df = pd.DataFrame(sample_docs)
        
        validation_results = {
            'distribution_valid': True,
            'issues': [],
            'sample_size': len(sample_docs),
            'completeness_distribution': {},
            'size_distribution': {},
            'type_distribution': {},
            'balance_score': 0.0
        }
        
        if len(sample_docs) == 0:
            validation_results['distribution_valid'] = False
            validation_results['issues'].append("No sample documents to validate")
            return validation_results
        
        # Analyze completeness distribution
        if 'completeness_score' in df.columns:
            completeness_dist = df['completeness_score'].describe()
            validation_results['completeness_distribution'] = {
                'mean': float(completeness_dist['mean']),
                'std': float(completeness_dist['std']),
                'min': float(completeness_dist['min']),
                'max': float(completeness_dist['max'])
            }
            
            # Check if sample is biased toward complete documents
            if completeness_dist['mean'] < 0.7:
                validation_results['issues'].append("Sample has low average completeness score")
        
        # Analyze size distribution
        if 'size_category' in df.columns:
            size_dist = df['size_category'].value_counts()
            validation_results['size_distribution'] = size_dist.to_dict()
            
            # Check for reasonable size distribution
            if len(size_dist) < 2:
                validation_results['issues'].append("Sample lacks size diversity")
        
        # Analyze document type distribution
        if 'doc_type' in df.columns:
            type_dist = df['doc_type'].value_counts()
            validation_results['type_distribution'] = type_dist.to_dict()
            
            # Check for type diversity
            if len(type_dist) < 2:
                validation_results['issues'].append("Sample lacks document type diversity")
        
        # Calculate balance score
        balance_scores = []
        for column in ['size_category', 'doc_type', 'chunk_complexity']:
            if column in df.columns:
                dist = df[column].value_counts(normalize=True)
                # Calculate entropy as a measure of balance
                entropy = -sum(p * np.log2(p) for p in dist if p > 0)
                max_entropy = np.log2(len(dist))
                balance_score = entropy / max_entropy if max_entropy > 0 else 0
                balance_scores.append(balance_score)
        
        if balance_scores:
            validation_results['balance_score'] = np.mean(balance_scores)
        
        return validation_results
    
    def validate_sample_coverage(self, sample_data: Dict) -> Dict:
        """Validate that sample covers key dimensions adequately"""
        logger.info("Validating sample coverage...")
        
        sample_docs = sample_data.get('sample_documents', [])
        df = pd.DataFrame(sample_docs)
        
        validation_results = {
            'coverage_valid': True,
            'issues': [],
            'file_availability': {},
            'processing_stage_coverage': {},
            'missing_files_count': 0
        }
        
        if len(sample_docs) == 0:
            validation_results['coverage_valid'] = False
            validation_results['issues'].append("No sample documents to validate coverage")
            return validation_results
        
        # Check file availability across processing stages
        stages = ['has_pdf', 'has_text', 'has_chunks', 'has_embeddings', 'has_ner']
        for stage in stages:
            if stage in df.columns:
                available_count = df[stage].sum()
                total_count = len(df)
                coverage_pct = (available_count / total_count) * 100
                
                validation_results['file_availability'][stage] = {
                    'available': int(available_count),
                    'total': total_count,
                    'coverage_percent': float(coverage_pct)
                }
                
                if coverage_pct < 80:
                    validation_results['issues'].append(f"Low coverage for {stage}: {coverage_pct:.1f}%")
        
        # Count documents with missing files
        missing_files = df[
            (df.get('has_pdf', True) == False) |
            (df.get('has_text', True) == False) |
            (df.get('has_chunks', True) == False) |
            (df.get('has_ner', True) == False)
        ]
        validation_results['missing_files_count'] = len(missing_files)
        
        if len(missing_files) > len(df) * 0.1:  # More than 10% missing files
            validation_results['coverage_valid'] = False
            validation_results['issues'].append(f"Too many documents with missing files: {len(missing_files)}")
        
        return validation_results
    
    def validate_sample_quality(self, sample_data: Dict) -> Dict:
        """Validate overall sample quality"""
        logger.info("Validating sample quality...")
        
        sample_docs = sample_data.get('sample_documents', [])
        
        validation_results = {
            'quality_valid': True,
            'issues': [],
            'quality_score': 0.0,
            'recommendations': []
        }
        
        if len(sample_docs) == 0:
            validation_results['quality_valid'] = False
            validation_results['issues'].append("No sample documents for quality validation")
            return validation_results
        
        df = pd.DataFrame(sample_docs)
        
        # Quality metrics
        quality_scores = []
        
        # 1. Completeness quality
        if 'completeness_score' in df.columns:
            avg_completeness = df['completeness_score'].mean()
            quality_scores.append(avg_completeness)
            
            if avg_completeness < 0.8:
                validation_results['recommendations'].append("Consider filtering for higher completeness documents")
        
        # 2. Size diversity quality
        if 'size_category' in df.columns:
            size_diversity = len(df['size_category'].unique()) / 3.0  # Assuming 3 size categories
            quality_scores.append(size_diversity)
            
            if size_diversity < 0.67:
                validation_results['recommendations'].append("Improve size category representation")
        
        # 3. Type diversity quality
        if 'doc_type' in df.columns:
            type_diversity = min(len(df['doc_type'].unique()) / 5.0, 1.0)  # Cap at 1.0
            quality_scores.append(type_diversity)
            
            if type_diversity < 0.5:
                validation_results['recommendations'].append("Increase document type diversity")
        
        # 4. File availability quality
        file_availability_scores = []
        for stage in ['has_pdf', 'has_text', 'has_chunks', 'has_ner']:
            if stage in df.columns:
                availability = df[stage].mean()
                file_availability_scores.append(availability)
        
        if file_availability_scores:
            avg_availability = np.mean(file_availability_scores)
            quality_scores.append(avg_availability)
            
            if avg_availability < 0.9:
                validation_results['recommendations'].append("Ensure higher file availability across processing stages")
        
        # Calculate overall quality score
        if quality_scores:
            validation_results['quality_score'] = np.mean(quality_scores)
        
        # Determine quality level
        quality_score = validation_results['quality_score']
        if quality_score >= 0.9:
            quality_level = "Excellent"
        elif quality_score >= 0.8:
            quality_level = "Good"
        elif quality_score >= 0.7:
            quality_level = "Acceptable"
        else:
            quality_level = "Poor"
            validation_results['quality_valid'] = False
        
        validation_results['quality_level'] = quality_level
        
        return validation_results
    
    def run_comprehensive_validation(self, sample_file: str) -> Dict:
        """Run comprehensive validation of the sample"""
        logger.info("Running comprehensive sample validation...")
        
        try:
            # Load sample
            sample_data = self.load_sample(sample_file)
            
            # Run all validation checks
            structure_results = self.validate_sample_structure(sample_data)
            distribution_results = self.validate_sample_distribution(sample_data)
            coverage_results = self.validate_sample_coverage(sample_data)
            quality_results = self.validate_sample_quality(sample_data)
            
            # Combine results
            overall_results = {
                'validation_timestamp': datetime.utcnow().isoformat(),
                'sample_file': sample_file,
                'overall_valid': (
                    structure_results['structure_valid'] and
                    distribution_results['distribution_valid'] and
                    coverage_results['coverage_valid'] and
                    quality_results['quality_valid']
                ),
                'structure_validation': structure_results,
                'distribution_validation': distribution_results,
                'coverage_validation': coverage_results,
                'quality_validation': quality_results
            }
            
            # Calculate overall score
            scores = []
            if 'balance_score' in distribution_results:
                scores.append(distribution_results['balance_score'])
            if 'quality_score' in quality_results:
                scores.append(quality_results['quality_score'])
            
            overall_results['overall_score'] = np.mean(scores) if scores else 0.0
            
            # Collect all issues
            all_issues = []
            for result_type in ['structure_validation', 'distribution_validation', 
                              'coverage_validation', 'quality_validation']:
                if 'issues' in overall_results[result_type]:
                    all_issues.extend(overall_results[result_type]['issues'])
            
            overall_results['total_issues'] = len(all_issues)
            overall_results['all_issues'] = all_issues
            
            # Collect all recommendations
            all_recommendations = []
            for result_type in ['quality_validation']:
                if 'recommendations' in overall_results[result_type]:
                    all_recommendations.extend(overall_results[result_type]['recommendations'])
            
            overall_results['recommendations'] = all_recommendations
            
            return overall_results
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return {
                'validation_timestamp': datetime.utcnow().isoformat(),
                'sample_file': sample_file,
                'overall_valid': False,
                'error': str(e)
            }
    
    def save_validation_report(self, validation_results: Dict, output_file: str):
        """Save validation results to JSON file"""
        logger.info(f"Saving validation report to: {output_file}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        logger.info("Validation report saved successfully")
    
    def print_validation_summary(self, validation_results: Dict):
        """Print a human-readable validation summary"""
        print("\n" + "="*60)
        print("SAMPLE VALIDATION RESULTS")
        print("="*60)
        
        overall_score = validation_results.get('overall_score', 0)
        print(f"Overall Score: {overall_score:.2f}")
        
        if 'quality_validation' in validation_results:
            quality_level = validation_results['quality_validation'].get('quality_level', 'Unknown')
            print(f"Grade: {quality_level}")
        
        validation_passed = validation_results.get('overall_valid', False)
        print(f"Validation Passed: {'✅ YES' if validation_passed else '❌ NO'}")
        
        total_issues = validation_results.get('total_issues', 0)
        print(f"Total Issues: {total_issues}")
        
        # Print critical issues
        all_issues = validation_results.get('all_issues', [])
        if all_issues:
            print(f"\nCritical Issues:")
            for issue in all_issues[:5]:  # Show first 5 issues
                print(f"  ❌ {issue}")
            if len(all_issues) > 5:
                print(f"  ... and {len(all_issues) - 5} more issues")
        
        # Print recommendations
        recommendations = validation_results.get('recommendations', [])
        if recommendations:
            print(f"\nRecommendations:")
            for rec in recommendations:
                print(f"  💡 {rec}")
        
        print(f"\nDetailed report saved to: {validation_results.get('sample_file', 'N/A').replace('.json', '_validation.json')}")

def main():
    parser = argparse.ArgumentParser(description='Validate NER-based document sample')
    parser.add_argument('--local-path', help='Path to local climate risk data')
    parser.add_argument('--sample-file', required=True, help='Sample selection JSON file to validate')
    parser.add_argument('--report', help='Output validation report file')
    
    args = parser.parse_args()
    
    try:
        # Use local path from sample file if not provided
        local_path = args.local_path
        if not local_path:
            # Try to extract from sample file
            with open(args.sample_file, 'r') as f:
                sample_data = json.load(f)
            local_path = sample_data.get('metadata', {}).get('local_path')
        
        if not local_path:
            logger.error("Local path not provided and not found in sample file")
            return 1
        
        validator = NERSampleValidator(local_path)
        results = validator.run_comprehensive_validation(args.sample_file)
        
        # Print summary
        validator.print_validation_summary(results)
        
        # Save detailed report
        if args.report:
            validator.save_validation_report(results, args.report)
        else:
            # Default report name
            default_report = args.sample_file.replace('.json', '_validation.json')
            validator.save_validation_report(results, default_report)
        
        return 0 if results.get('overall_valid', False) else 1
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
