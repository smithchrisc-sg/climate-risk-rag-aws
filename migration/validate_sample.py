#!/usr/bin/env python3
"""
Sample Validation Script
Validates the quality and representativeness of generated document samples
"""

import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SampleValidator:
    """Validates document sample quality and representativeness"""
    
    def __init__(self):
        self.validation_results = {}
        
    def load_sample(self, sample_file: str) -> Dict[str, Any]:
        """Load sample data from JSON file"""
        logger.info(f"Loading sample from: {sample_file}")
        
        with open(sample_file, 'r') as f:
            sample_data = json.load(f)
        
        return sample_data
    
    def validate_sample_structure(self, sample_data: Dict) -> Dict[str, Any]:
        """Validate the structure of the sample data"""
        logger.info("Validating sample structure...")
        
        validation = {
            'has_metadata': 'metadata' in sample_data,
            'has_documents': 'sample_documents' in sample_data,
            'has_validation': 'validation' in sample_data,
            'document_count': len(sample_data.get('sample_documents', [])),
            'issues': []
        }
        
        # Check required fields
        if not validation['has_metadata']:
            validation['issues'].append("Missing metadata section")
        
        if not validation['has_documents']:
            validation['issues'].append("Missing sample_documents section")
        
        if validation['document_count'] == 0:
            validation['issues'].append("No documents in sample")
        
        # Validate document structure
        sample_docs = sample_data.get('sample_documents', [])
        required_fields = ['doc_id', 'title', 'document_type']
        
        for i, doc in enumerate(sample_docs[:10]):  # Check first 10
            missing_fields = [field for field in required_fields if field not in doc]
            if missing_fields:
                validation['issues'].append(f"Document {i} missing fields: {missing_fields}")
        
        validation['structure_valid'] = len(validation['issues']) == 0
        
        return validation
    
    def validate_sample_distribution(self, sample_data: Dict) -> Dict[str, Any]:
        """Validate the distribution of the sample across different dimensions"""
        logger.info("Validating sample distribution...")
        
        sample_docs = sample_data.get('sample_documents', [])
        if not sample_docs:
            return {'distribution_valid': False, 'error': 'No sample documents'}
        
        df = pd.DataFrame(sample_docs)
        
        validation = {
            'distribution_analysis': {},
            'balance_scores': {},
            'issues': []
        }
        
        # Expected distributions (targets)
        expected_distributions = {
            'document_type': {
                'climate_reports': 0.40,
                'regulatory_docs': 0.20,
                'technical_studies': 0.25,
                'financial_analysis': 0.15
            },
            'date_category': {
                'recent': 0.40,
                'historical': 0.60
            },
            'size_category': {
                'small': 0.20,
                'medium': 0.50,
                'large': 0.30
            },
            'complexity': {
                'simple_text': 0.30,
                'tables_charts': 0.40,
                'complex_layout': 0.30
            }
        }
        
        # Analyze each dimension
        for dimension, expected_dist in expected_distributions.items():
            if dimension in df.columns:
                actual_dist = df[dimension].value_counts(normalize=True).to_dict()
                
                # Calculate balance score
                balance_score = self._calculate_balance_score(actual_dist, expected_dist)
                
                validation['distribution_analysis'][dimension] = {
                    'expected': expected_dist,
                    'actual': actual_dist,
                    'balance_score': balance_score
                }
                
                validation['balance_scores'][dimension] = balance_score
                
                # Check for significant deviations
                for category, expected_ratio in expected_dist.items():
                    actual_ratio = actual_dist.get(category, 0)
                    deviation = abs(actual_ratio - expected_ratio)
                    
                    if deviation > 0.15:  # More than 15% deviation
                        validation['issues'].append(
                            f"{dimension}.{category}: Expected {expected_ratio:.1%}, "
                            f"got {actual_ratio:.1%} (deviation: {deviation:.1%})"
                        )
            else:
                validation['issues'].append(f"Missing dimension: {dimension}")
                validation['balance_scores'][dimension] = 0.0
        
        # Overall balance score
        balance_scores = list(validation['balance_scores'].values())
        validation['overall_balance_score'] = np.mean(balance_scores) if balance_scores else 0.0
        
        validation['distribution_valid'] = validation['overall_balance_score'] > 0.7
        
        return validation
    
    def validate_sample_coverage(self, sample_data: Dict) -> Dict[str, Any]:
        """Validate coverage of different categories"""
        logger.info("Validating sample coverage...")
        
        sample_docs = sample_data.get('sample_documents', [])
        if not sample_docs:
            return {'coverage_valid': False, 'error': 'No sample documents'}
        
        df = pd.DataFrame(sample_docs)
        
        validation = {
            'coverage_analysis': {},
            'issues': []
        }
        
        # Check coverage for each categorical dimension
        categorical_dimensions = ['document_type', 'date_category', 'size_category', 'complexity']
        
        for dimension in categorical_dimensions:
            if dimension in df.columns:
                unique_values = df[dimension].nunique()
                total_values = df[dimension].count()
                unique_categories = df[dimension].unique().tolist()
                
                validation['coverage_analysis'][dimension] = {
                    'unique_categories': unique_categories,
                    'unique_count': unique_values,
                    'total_count': total_values,
                    'coverage_ratio': unique_values / max(1, total_values)
                }
                
                # Check for minimum coverage
                if unique_values < 2:
                    validation['issues'].append(f"Low diversity in {dimension}: only {unique_values} categories")
            else:
                validation['issues'].append(f"Missing dimension for coverage analysis: {dimension}")
        
        validation['coverage_valid'] = len(validation['issues']) == 0
        
        return validation
    
    def validate_sample_quality(self, sample_data: Dict) -> Dict[str, Any]:
        """Validate overall sample quality"""
        logger.info("Validating sample quality...")
        
        sample_docs = sample_data.get('sample_documents', [])
        
        validation = {
            'quality_metrics': {},
            'issues': []
        }
        
        # Check for duplicates
        doc_ids = [doc.get('doc_id') for doc in sample_docs]
        unique_doc_ids = set(doc_ids)
        
        if len(doc_ids) != len(unique_doc_ids):
            duplicates = len(doc_ids) - len(unique_doc_ids)
            validation['issues'].append(f"Found {duplicates} duplicate documents")
        
        validation['quality_metrics']['duplicate_count'] = len(doc_ids) - len(unique_doc_ids)
        
        # Check for missing essential data
        missing_doc_ids = sum(1 for doc in sample_docs if not doc.get('doc_id'))
        missing_titles = sum(1 for doc in sample_docs if not doc.get('title'))
        
        validation['quality_metrics']['missing_doc_ids'] = missing_doc_ids
        validation['quality_metrics']['missing_titles'] = missing_titles
        
        if missing_doc_ids > 0:
            validation['issues'].append(f"{missing_doc_ids} documents missing doc_id")
        
        if missing_titles > 0:
            validation['issues'].append(f"{missing_titles} documents missing title")
        
        # Check sample size
        expected_size = sample_data.get('metadata', {}).get('sample_size', 1000)
        actual_size = len(sample_docs)
        
        validation['quality_metrics']['expected_size'] = expected_size
        validation['quality_metrics']['actual_size'] = actual_size
        validation['quality_metrics']['size_match'] = expected_size == actual_size
        
        if expected_size != actual_size:
            validation['issues'].append(f"Sample size mismatch: expected {expected_size}, got {actual_size}")
        
        # Overall quality score
        quality_factors = [
            1.0 if validation['quality_metrics']['duplicate_count'] == 0 else 0.5,
            1.0 if validation['quality_metrics']['missing_doc_ids'] == 0 else 0.0,
            1.0 if validation['quality_metrics']['missing_titles'] == 0 else 0.8,
            1.0 if validation['quality_metrics']['size_match'] else 0.9
        ]
        
        validation['quality_score'] = np.mean(quality_factors)
        validation['quality_valid'] = validation['quality_score'] > 0.8
        
        return validation
    
    def _calculate_balance_score(self, actual_dist: Dict, expected_dist: Dict) -> float:
        """Calculate balance score between actual and expected distributions"""
        
        # Calculate weighted deviation
        total_deviation = 0
        total_weight = 0
        
        for category, expected_ratio in expected_dist.items():
            actual_ratio = actual_dist.get(category, 0)
            deviation = abs(actual_ratio - expected_ratio)
            weight = expected_ratio  # Weight by expected importance
            
            total_deviation += deviation * weight
            total_weight += weight
        
        # Convert to balance score (1.0 = perfect balance, 0.0 = completely unbalanced)
        avg_deviation = total_deviation / total_weight if total_weight > 0 else 1.0
        balance_score = max(0.0, 1.0 - (avg_deviation * 2))  # Scale deviation to 0-1
        
        return balance_score
    
    def run_comprehensive_validation(self, sample_file: str) -> Dict[str, Any]:
        """Run comprehensive validation of the sample"""
        logger.info("Running comprehensive sample validation...")
        
        # Load sample
        sample_data = self.load_sample(sample_file)
        
        # Run all validations
        validations = {
            'structure': self.validate_sample_structure(sample_data),
            'distribution': self.validate_sample_distribution(sample_data),
            'coverage': self.validate_sample_coverage(sample_data),
            'quality': self.validate_sample_quality(sample_data)
        }
        
        # Calculate overall validation score
        validation_scores = []
        for validation_type, validation_result in validations.items():
            if validation_type == 'structure':
                score = 1.0 if validation_result.get('structure_valid', False) else 0.0
            elif validation_type == 'distribution':
                score = validation_result.get('overall_balance_score', 0.0)
            elif validation_type == 'coverage':
                score = 1.0 if validation_result.get('coverage_valid', False) else 0.5
            elif validation_type == 'quality':
                score = validation_result.get('quality_score', 0.0)
            else:
                score = 0.5
            
            validation_scores.append(score)
        
        overall_score = np.mean(validation_scores)
        
        # Compile results
        results = {
            'validation_timestamp': datetime.utcnow().isoformat(),
            'sample_file': sample_file,
            'overall_validation_score': overall_score,
            'validation_passed': overall_score > 0.7,
            'validations': validations,
            'summary': self._generate_validation_summary(validations, overall_score)
        }
        
        return results
    
    def _generate_validation_summary(self, validations: Dict, overall_score: float) -> Dict[str, Any]:
        """Generate validation summary"""
        
        all_issues = []
        for validation_result in validations.values():
            all_issues.extend(validation_result.get('issues', []))
        
        summary = {
            'overall_score': overall_score,
            'validation_grade': self._get_validation_grade(overall_score),
            'total_issues': len(all_issues),
            'critical_issues': [issue for issue in all_issues if 'missing' in issue.lower()],
            'recommendations': self._generate_recommendations(validations, all_issues)
        }
        
        return summary
    
    def _get_validation_grade(self, score: float) -> str:
        """Convert validation score to grade"""
        if score >= 0.9:
            return 'Excellent'
        elif score >= 0.8:
            return 'Good'
        elif score >= 0.7:
            return 'Acceptable'
        elif score >= 0.6:
            return 'Needs Improvement'
        else:
            return 'Poor'
    
    def _generate_recommendations(self, validations: Dict, all_issues: List[str]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Structure recommendations
        structure_issues = validations.get('structure', {}).get('issues', [])
        if structure_issues:
            recommendations.append("Fix structural issues before proceeding with migration")
        
        # Distribution recommendations
        distribution_score = validations.get('distribution', {}).get('overall_balance_score', 1.0)
        if distribution_score < 0.7:
            recommendations.append("Consider regenerating sample with better stratification")
        
        # Quality recommendations
        quality_score = validations.get('quality', {}).get('quality_score', 1.0)
        if quality_score < 0.8:
            recommendations.append("Address data quality issues before migration")
        
        # Coverage recommendations
        coverage_valid = validations.get('coverage', {}).get('coverage_valid', True)
        if not coverage_valid:
            recommendations.append("Increase sample diversity to improve coverage")
        
        # General recommendations
        if len(all_issues) > 5:
            recommendations.append("Consider increasing sample size for better representation")
        
        if not recommendations:
            recommendations.append("Sample validation passed - ready for migration")
        
        return recommendations
    
    def save_validation_report(self, results: Dict, output_file: str):
        """Save validation report to file"""
        logger.info(f"Saving validation report to: {output_file}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("Validation report saved successfully")


def main():
    parser = argparse.ArgumentParser(description='Validate document sample quality')
    parser.add_argument('--sample-file', required=True, help='Sample selection JSON file')
    parser.add_argument('--report', help='Output validation report file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        validator = SampleValidator()
        results = validator.run_comprehensive_validation(args.sample_file)
        
        # Print summary
        summary = results['summary']
        print(f"\n{'='*60}")
        print("SAMPLE VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Overall Score: {results['overall_validation_score']:.2f}")
        print(f"Grade: {summary['validation_grade']}")
        print(f"Validation Passed: {'✅ YES' if results['validation_passed'] else '❌ NO'}")
        print(f"Total Issues: {summary['total_issues']}")
        
        if summary['critical_issues']:
            print(f"\nCritical Issues:")
            for issue in summary['critical_issues']:
                print(f"  ❌ {issue}")
        
        print(f"\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  💡 {rec}")
        
        # Save report if requested
        if args.report:
            validator.save_validation_report(results, args.report)
            print(f"\nDetailed report saved to: {args.report}")
        
        return 0 if results['validation_passed'] else 1
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
