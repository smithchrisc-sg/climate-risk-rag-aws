#!/usr/bin/env python3
"""
NLP Cost Analyzer - Helps choose between Comprehend and Flair based on cost/performance
Provides detailed cost breakdowns and recommendations
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class NLPCostAnalyzer:
    """Analyzes costs and performance trade-offs between NLP providers"""
    
    # Current pricing (2025)
    COMPREHEND_ENTITY_COST_PER_UNIT = 0.0001  # $0.0001 per 100 chars
    COMPREHEND_PHRASES_COST_PER_UNIT = 0.0001  # $0.0001 per 100 chars
    LAMBDA_COST_PER_GB_SECOND = 0.0000166667
    
    # Performance estimates (would be refined with actual benchmarking)
    COMPREHEND_PROCESSING_TIME = 2.0  # seconds average
    COMPREHEND_MEMORY_MB = 1024
    
    FLAIR_PROCESSING_TIME_PER_1K_CHARS = 0.5  # seconds per 1000 chars
    FLAIR_BASE_TIME = 3.0  # model initialization overhead
    FLAIR_MEMORY_MB = 3008  # max memory for model loading
    
    def __init__(self):
        """Initialize cost analyzer"""
        logger.info("Initialized NLP Cost Analyzer")
    
    def analyze_document_cost(self, text_length: int, document_count: int = 1) -> Dict[str, Any]:
        """
        Analyze cost for processing documents of given length
        
        Args:
            text_length: Length of text in characters
            document_count: Number of documents to process
        """
        
        # Comprehend cost analysis
        comprehend_analysis = self._analyze_comprehend_cost(text_length, document_count)
        
        # Flair cost analysis  
        flair_analysis = self._analyze_flair_cost(text_length, document_count)
        
        # Comparison and recommendation
        recommendation = self._generate_recommendation(comprehend_analysis, flair_analysis)
        
        return {
            'analysis_parameters': {
                'text_length_per_document': text_length,
                'document_count': document_count,
                'total_characters': text_length * document_count
            },
            'comprehend': comprehend_analysis,
            'flair': flair_analysis,
            'comparison': recommendation
        }
    
    def _analyze_comprehend_cost(self, text_length: int, document_count: int) -> Dict[str, Any]:
        """Analyze Amazon Comprehend costs"""
        
        # API costs
        units_per_doc = max(1, text_length / 100)
        entity_cost_per_doc = units_per_doc * self.COMPREHEND_ENTITY_COST_PER_UNIT
        phrases_cost_per_doc = units_per_doc * self.COMPREHEND_PHRASES_COST_PER_UNIT
        api_cost_per_doc = entity_cost_per_doc + phrases_cost_per_doc
        
        # Lambda costs
        lambda_cost_per_doc = (
            self.COMPREHEND_PROCESSING_TIME * 
            (self.COMPREHEND_MEMORY_MB / 1024) * 
            self.LAMBDA_COST_PER_GB_SECOND
        )
        
        total_cost_per_doc = api_cost_per_doc + lambda_cost_per_doc
        total_cost = total_cost_per_doc * document_count
        
        return {
            'provider': 'comprehend',
            'cost_breakdown': {
                'api_cost_per_document': api_cost_per_doc,
                'lambda_cost_per_document': lambda_cost_per_doc,
                'total_cost_per_document': total_cost_per_doc,
                'total_cost_all_documents': total_cost
            },
            'performance': {
                'processing_time_per_document': self.COMPREHEND_PROCESSING_TIME,
                'total_processing_time': self.COMPREHEND_PROCESSING_TIME * document_count,
                'memory_requirement_mb': self.COMPREHEND_MEMORY_MB
            },
            'scaling': {
                'cost_scales_with': 'text_length_and_document_count',
                'processing_time_scales_with': 'document_count_only',
                'parallel_processing': 'excellent'
            }
        }
    
    def _analyze_flair_cost(self, text_length: int, document_count: int) -> Dict[str, Any]:
        """Analyze Flair NLP costs"""
        
        # Processing time estimation
        processing_time_per_doc = self.FLAIR_BASE_TIME + (text_length / 1000 * self.FLAIR_PROCESSING_TIME_PER_1K_CHARS)
        
        # Lambda costs (no API costs)
        lambda_cost_per_doc = (
            processing_time_per_doc * 
            (self.FLAIR_MEMORY_MB / 1024) * 
            self.LAMBDA_COST_PER_GB_SECOND
        )
        
        total_cost = lambda_cost_per_doc * document_count
        
        return {
            'provider': 'flair',
            'cost_breakdown': {
                'api_cost_per_document': 0.0,
                'lambda_cost_per_document': lambda_cost_per_doc,
                'total_cost_per_document': lambda_cost_per_doc,
                'total_cost_all_documents': total_cost
            },
            'performance': {
                'processing_time_per_document': processing_time_per_doc,
                'total_processing_time': processing_time_per_doc * document_count,
                'memory_requirement_mb': self.FLAIR_MEMORY_MB
            },
            'scaling': {
                'cost_scales_with': 'text_length_and_processing_time',
                'processing_time_scales_with': 'text_length_and_document_count',
                'parallel_processing': 'limited_by_memory'
            }
        }
    
    def _generate_recommendation(self, comprehend: Dict, flair: Dict) -> Dict[str, Any]:
        """Generate recommendation based on cost analysis"""
        
        comprehend_cost = comprehend['cost_breakdown']['total_cost_all_documents']
        flair_cost = flair['cost_breakdown']['total_cost_all_documents']
        
        comprehend_time = comprehend['performance']['total_processing_time']
        flair_time = flair['performance']['total_processing_time']
        
        cost_difference = abs(comprehend_cost - flair_cost)
        cost_savings_pct = (cost_difference / max(comprehend_cost, flair_cost)) * 100
        
        time_difference = abs(comprehend_time - flair_time)
        
        # Determine recommendation
        if comprehend_cost < flair_cost:
            if cost_savings_pct > 20:
                recommendation = 'comprehend'
                reason = f'Comprehend is {cost_savings_pct:.1f}% cheaper'
            else:
                recommendation = 'comprehend'
                reason = 'Comprehend is slightly cheaper and much faster'
        else:
            if cost_savings_pct > 30:
                recommendation = 'flair'
                reason = f'Flair is {cost_savings_pct:.1f}% cheaper for this volume'
            else:
                recommendation = 'comprehend'
                reason = 'Cost difference is small, Comprehend is much faster'
        
        return {
            'recommended_provider': recommendation,
            'reason': reason,
            'cost_comparison': {
                'comprehend_total': comprehend_cost,
                'flair_total': flair_cost,
                'difference': cost_difference,
                'savings_percentage': cost_savings_pct,
                'cheaper_provider': 'comprehend' if comprehend_cost < flair_cost else 'flair'
            },
            'performance_comparison': {
                'comprehend_time': comprehend_time,
                'flair_time': flair_time,
                'time_difference': time_difference,
                'faster_provider': 'comprehend' if comprehend_time < flair_time else 'flair'
            },
            'considerations': self._get_additional_considerations()
        }
    
    def _get_additional_considerations(self) -> List[str]:
        """Get additional factors to consider beyond cost"""
        
        return [
            'Flair may have higher accuracy for domain-specific entities',
            'Comprehend has built-in key phrase extraction',
            'Flair requires larger Lambda memory allocation',
            'Comprehend has API rate limits, Flair does not',
            'Flair supports custom models and offline processing',
            'Comprehend provides consistent performance, Flair varies by text complexity'
        ]
    
    def analyze_monthly_volume(self, docs_per_day: int, avg_chars_per_doc: int) -> Dict[str, Any]:
        """Analyze costs for monthly processing volume"""
        
        monthly_docs = docs_per_day * 30
        total_chars = monthly_docs * avg_chars_per_doc
        
        analysis = self.analyze_document_cost(avg_chars_per_doc, monthly_docs)
        
        # Add monthly context
        analysis['monthly_volume'] = {
            'documents_per_day': docs_per_day,
            'documents_per_month': monthly_docs,
            'average_characters_per_document': avg_chars_per_doc,
            'total_characters_per_month': total_chars,
            'comprehend_monthly_cost': analysis['comprehend']['cost_breakdown']['total_cost_all_documents'],
            'flair_monthly_cost': analysis['flair']['cost_breakdown']['total_cost_all_documents']
        }
        
        return analysis
    
    def get_break_even_analysis(self, text_length: int) -> Dict[str, Any]:
        """Find break-even point where Flair becomes more cost-effective"""
        
        # Calculate costs for different document volumes
        volumes = [10, 50, 100, 500, 1000, 5000, 10000]
        break_even_data = []
        
        for volume in volumes:
            analysis = self.analyze_document_cost(text_length, volume)
            break_even_data.append({
                'document_count': volume,
                'comprehend_cost': analysis['comprehend']['cost_breakdown']['total_cost_all_documents'],
                'flair_cost': analysis['flair']['cost_breakdown']['total_cost_all_documents'],
                'cheaper_provider': analysis['comparison']['cost_comparison']['cheaper_provider']
            })
        
        # Find break-even point
        break_even_point = None
        for i, data in enumerate(break_even_data):
            if data['cheaper_provider'] == 'flair':
                break_even_point = data['document_count']
                break
        
        return {
            'text_length': text_length,
            'break_even_point': break_even_point,
            'volume_analysis': break_even_data,
            'summary': f"Flair becomes cost-effective at {break_even_point} documents" if break_even_point else "Comprehend is always cheaper for this text length"
        }

def main():
    """Example usage of cost analyzer"""
    
    analyzer = NLPCostAnalyzer()
    
    # Example 1: Single document analysis
    print("=== SINGLE DOCUMENT ANALYSIS ===")
    analysis = analyzer.analyze_document_cost(text_length=5000, document_count=1)
    
    print(f"Text length: {analysis['analysis_parameters']['text_length_per_document']} characters")
    print(f"Comprehend cost: ${analysis['comprehend']['cost_breakdown']['total_cost_per_document']:.6f}")
    print(f"Flair cost: ${analysis['flair']['cost_breakdown']['total_cost_per_document']:.6f}")
    print(f"Recommendation: {analysis['comparison']['recommended_provider']}")
    print(f"Reason: {analysis['comparison']['reason']}")
    
    # Example 2: Monthly volume analysis
    print("\n=== MONTHLY VOLUME ANALYSIS ===")
    monthly_analysis = analyzer.analyze_monthly_volume(docs_per_day=100, avg_chars_per_doc=3000)
    
    print(f"Monthly volume: {monthly_analysis['monthly_volume']['documents_per_month']} documents")
    print(f"Comprehend monthly cost: ${monthly_analysis['monthly_volume']['comprehend_monthly_cost']:.2f}")
    print(f"Flair monthly cost: ${monthly_analysis['monthly_volume']['flair_monthly_cost']:.2f}")
    print(f"Recommendation: {monthly_analysis['comparison']['recommended_provider']}")
    
    # Example 3: Break-even analysis
    print("\n=== BREAK-EVEN ANALYSIS ===")
    break_even = analyzer.get_break_even_analysis(text_length=2000)
    print(f"Break-even analysis for 2000-character documents:")
    print(f"Result: {break_even['summary']}")

if __name__ == "__main__":
    main()
