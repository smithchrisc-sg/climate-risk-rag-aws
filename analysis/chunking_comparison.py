#!/usr/bin/env python3
"""
Chunking Comparison Utility
Compares different chunking approaches for climate risk documents
"""

import json
import boto3
import logging
from typing import Dict, List, Any, Tuple
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChunkingComparator:
    """Compares different chunking strategies"""
    
    def __init__(self, aws_region: str = 'us-east-1'):
        self.s3 = boto3.client('s3', region_name=aws_region)
        
    def compare_chunking_methods(self, 
                                local_chunks_path: str,
                                aws_artifacts_bucket: str,
                                sample_size: int = 100) -> Dict[str, Any]:
        """Compare local POC chunking vs AWS structured chunking"""
        
        logger.info("Starting chunking comparison analysis")
        
        # Load sample of local chunks
        local_chunks = self._load_local_chunks(local_chunks_path, sample_size)
        
        # Load corresponding AWS chunks
        aws_chunks = self._load_aws_chunks(aws_artifacts_bucket, local_chunks.keys())
        
        # Perform comparison analysis
        comparison_results = {
            'summary': self._compare_chunk_statistics(local_chunks, aws_chunks),
            'quality_metrics': self._analyze_chunk_quality(local_chunks, aws_chunks),
            'structure_analysis': self._analyze_structure_preservation(aws_chunks),
            'recommendations': self._generate_recommendations(local_chunks, aws_chunks)
        }
        
        # Generate visualizations
        self._create_comparison_visualizations(comparison_results)
        
        return comparison_results
    
    def _load_local_chunks(self, chunks_path: str, sample_size: int) -> Dict[str, List[Dict]]:
        """Load sample of local POC chunks"""
        chunks_path = Path(chunks_path)
        local_chunks = {}
        
        # Get sample of document directories
        doc_dirs = list(chunks_path.glob('*'))[:sample_size]
        
        for doc_dir in doc_dirs:
            if doc_dir.is_dir():
                doc_id = doc_dir.name
                doc_chunks = []
                
                # Load all chunks for this document
                for chunk_file in sorted(doc_dir.glob('chunk_*.json')):
                    try:
                        with open(chunk_file, 'r') as f:
                            chunk_data = json.load(f)
                            chunk_data['source'] = 'local_poc'
                            chunk_data['chunking_method'] = '5_sentence_2_overlap'
                            doc_chunks.append(chunk_data)
                    except Exception as e:
                        logger.warning(f"Error loading {chunk_file}: {str(e)}")
                
                if doc_chunks:
                    local_chunks[doc_id] = doc_chunks
        
        logger.info(f"Loaded local chunks for {len(local_chunks)} documents")
        return local_chunks
    
    def _load_aws_chunks(self, bucket: str, doc_ids: List[str]) -> Dict[str, List[Dict]]:
        """Load corresponding AWS structured chunks"""
        aws_chunks = {}
        
        for doc_id in doc_ids:
            try:
                # Try to load AWS chunks for this document
                key = f"structured_chunks/{doc_id}.json"
                
                try:
                    response = self.s3.get_object(Bucket=bucket, Key=key)
                    chunk_data = json.loads(response['Body'].read())
                    
                    # Add metadata
                    for chunk in chunk_data:
                        chunk['source'] = 'aws_structured'
                        chunk['chunking_method'] = 'textract_structured'
                    
                    aws_chunks[doc_id] = chunk_data
                    
                except self.s3.exceptions.NoSuchKey:
                    logger.warning(f"No AWS chunks found for document {doc_id}")
                    
            except Exception as e:
                logger.error(f"Error loading AWS chunks for {doc_id}: {str(e)}")
        
        logger.info(f"Loaded AWS chunks for {len(aws_chunks)} documents")
        return aws_chunks
    
    def _compare_chunk_statistics(self, local_chunks: Dict, aws_chunks: Dict) -> Dict:
        """Compare basic statistics between chunking methods"""
        
        local_stats = self._calculate_chunk_stats(local_chunks, 'Local POC')
        aws_stats = self._calculate_chunk_stats(aws_chunks, 'AWS Structured')
        
        return {
            'local_poc': local_stats,
            'aws_structured': aws_stats,
            'comparison': {
                'avg_chunks_per_doc_ratio': aws_stats['avg_chunks_per_doc'] / local_stats['avg_chunks_per_doc'] if local_stats['avg_chunks_per_doc'] > 0 else 0,
                'avg_chunk_length_ratio': aws_stats['avg_chunk_length'] / local_stats['avg_chunk_length'] if local_stats['avg_chunk_length'] > 0 else 0,
                'chunk_size_variance_ratio': aws_stats['chunk_size_variance'] / local_stats['chunk_size_variance'] if local_stats['chunk_size_variance'] > 0 else 0
            }
        }
    
    def _calculate_chunk_stats(self, chunks_data: Dict, method_name: str) -> Dict:
        """Calculate statistics for a chunking method"""
        all_chunks = []
        doc_chunk_counts = []
        
        for doc_id, doc_chunks in chunks_data.items():
            doc_chunk_counts.append(len(doc_chunks))
            all_chunks.extend(doc_chunks)
        
        if not all_chunks:
            return {'method': method_name, 'total_chunks': 0}
        
        chunk_lengths = []
        sentence_counts = []
        word_counts = []
        
        for chunk in all_chunks:
            text = chunk.get('text', '')
            chunk_lengths.append(len(text))
            
            # Count sentences and words
            sentences = text.count('.') + text.count('!') + text.count('?')
            words = len(text.split())
            
            sentence_counts.append(sentences)
            word_counts.append(words)
        
        return {
            'method': method_name,
            'total_documents': len(chunks_data),
            'total_chunks': len(all_chunks),
            'avg_chunks_per_doc': sum(doc_chunk_counts) / len(doc_chunk_counts) if doc_chunk_counts else 0,
            'avg_chunk_length': sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0,
            'avg_sentences_per_chunk': sum(sentence_counts) / len(sentence_counts) if sentence_counts else 0,
            'avg_words_per_chunk': sum(word_counts) / len(word_counts) if word_counts else 0,
            'chunk_size_variance': pd.Series(chunk_lengths).var() if chunk_lengths else 0,
            'min_chunk_length': min(chunk_lengths) if chunk_lengths else 0,
            'max_chunk_length': max(chunk_lengths) if chunk_lengths else 0
        }
    
    def _analyze_chunk_quality(self, local_chunks: Dict, aws_chunks: Dict) -> Dict:
        """Analyze chunk quality metrics"""
        
        quality_metrics = {
            'coherence_analysis': {},
            'boundary_analysis': {},
            'content_preservation': {}
        }
        
        # Analyze coherence (sentence boundary preservation)
        local_coherence = self._analyze_coherence(local_chunks)
        aws_coherence = self._analyze_coherence(aws_chunks)
        
        quality_metrics['coherence_analysis'] = {
            'local_poc': local_coherence,
            'aws_structured': aws_coherence,
            'coherence_improvement': aws_coherence['avg_coherence_score'] - local_coherence['avg_coherence_score']
        }
        
        # Analyze boundary quality
        aws_boundary_quality = self._analyze_boundary_quality(aws_chunks)
        quality_metrics['boundary_analysis'] = aws_boundary_quality
        
        return quality_metrics
    
    def _analyze_coherence(self, chunks_data: Dict) -> Dict:
        """Analyze chunk coherence (simplified metric)"""
        coherence_scores = []
        
        for doc_id, doc_chunks in chunks_data.items():
            for chunk in doc_chunks:
                text = chunk.get('text', '')
                
                # Simple coherence metric: ratio of complete sentences
                sentences = text.split('.')
                complete_sentences = sum(1 for s in sentences if s.strip() and not s.strip().endswith(('and', 'or', 'but', 'however')))
                total_sentences = len([s for s in sentences if s.strip()])
                
                coherence_score = complete_sentences / total_sentences if total_sentences > 0 else 0
                coherence_scores.append(coherence_score)
        
        return {
            'avg_coherence_score': sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0,
            'coherence_variance': pd.Series(coherence_scores).var() if coherence_scores else 0
        }
    
    def _analyze_boundary_quality(self, aws_chunks: Dict) -> Dict:
        """Analyze AWS structured chunking boundary quality"""
        boundary_types = {}
        structure_preservation = {}
        
        for doc_id, doc_chunks in aws_chunks.items():
            for chunk in doc_chunks:
                chunk_type = chunk.get('chunk_type', 'unknown')
                boundary_types[chunk_type] = boundary_types.get(chunk_type, 0) + 1
                
                # Analyze structure preservation
                hierarchy_level = chunk.get('hierarchy_level', 0)
                section_context = chunk.get('section_context', 'unknown')
                
                if section_context not in structure_preservation:
                    structure_preservation[section_context] = []
                structure_preservation[section_context].append(hierarchy_level)
        
        return {
            'chunk_type_distribution': boundary_types,
            'structure_preservation': {
                context: {
                    'count': len(levels),
                    'avg_hierarchy_level': sum(levels) / len(levels) if levels else 0
                }
                for context, levels in structure_preservation.items()
            }
        }
    
    def _analyze_structure_preservation(self, aws_chunks: Dict) -> Dict:
        """Analyze how well AWS chunking preserves document structure"""
        
        structure_analysis = {
            'hierarchy_distribution': {},
            'section_type_analysis': {},
            'page_distribution': {},
            'table_preservation': 0,
            'header_context_preservation': 0
        }
        
        total_chunks = 0
        
        for doc_id, doc_chunks in aws_chunks.items():
            for chunk in doc_chunks:
                total_chunks += 1
                
                # Hierarchy analysis
                hierarchy_level = chunk.get('hierarchy_level', 0)
                structure_analysis['hierarchy_distribution'][hierarchy_level] = \
                    structure_analysis['hierarchy_distribution'].get(hierarchy_level, 0) + 1
                
                # Section type analysis
                chunk_type = chunk.get('chunk_type', 'unknown')
                structure_analysis['section_type_analysis'][chunk_type] = \
                    structure_analysis['section_type_analysis'].get(chunk_type, 0) + 1
                
                # Page distribution
                page_num = chunk.get('page_number', 1)
                structure_analysis['page_distribution'][page_num] = \
                    structure_analysis['page_distribution'].get(page_num, 0) + 1
                
                # Special structure preservation
                if chunk_type == 'table':
                    structure_analysis['table_preservation'] += 1
                elif chunk_type == 'header_with_context':
                    structure_analysis['header_context_preservation'] += 1
        
        # Convert counts to percentages
        if total_chunks > 0:
            structure_analysis['hierarchy_distribution'] = {
                level: count / total_chunks * 100
                for level, count in structure_analysis['hierarchy_distribution'].items()
            }
            structure_analysis['section_type_analysis'] = {
                stype: count / total_chunks * 100
                for stype, count in structure_analysis['section_type_analysis'].items()
            }
            structure_analysis['table_preservation_percentage'] = \
                structure_analysis['table_preservation'] / total_chunks * 100
            structure_analysis['header_context_percentage'] = \
                structure_analysis['header_context_preservation'] / total_chunks * 100
        
        return structure_analysis
    
    def _generate_recommendations(self, local_chunks: Dict, aws_chunks: Dict) -> List[str]:
        """Generate recommendations based on comparison"""
        recommendations = []
        
        local_stats = self._calculate_chunk_stats(local_chunks, 'Local')
        aws_stats = self._calculate_chunk_stats(aws_chunks, 'AWS')
        
        # Chunk size recommendations
        if aws_stats['avg_chunk_length'] > local_stats['avg_chunk_length'] * 1.5:
            recommendations.append(
                "AWS structured chunking creates larger chunks. Consider adjusting max_chunk_size parameter for more granular chunks."
            )
        elif aws_stats['avg_chunk_length'] < local_stats['avg_chunk_length'] * 0.7:
            recommendations.append(
                "AWS structured chunking creates smaller chunks. This may improve precision but could impact context."
            )
        
        # Chunk count recommendations
        if aws_stats['total_chunks'] > local_stats['total_chunks'] * 1.3:
            recommendations.append(
                "AWS creates significantly more chunks. This provides finer granularity but may increase processing costs."
            )
        
        # Structure-specific recommendations
        recommendations.extend([
            "AWS structured chunking preserves document hierarchy - leverage this for better context in RAG queries.",
            "Consider using chunk_type and hierarchy_level metadata for weighted search results.",
            "Table chunks should be processed differently - consider specialized embedding strategies.",
            "Header chunks with context provide better semantic understanding than isolated headers."
        ])
        
        return recommendations
    
    def _create_comparison_visualizations(self, results: Dict):
        """Create visualizations comparing chunking methods"""
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Chunking Method Comparison: Local POC vs AWS Structured', fontsize=16)
        
        # 1. Chunk statistics comparison
        local_stats = results['summary']['local_poc']
        aws_stats = results['summary']['aws_structured']
        
        metrics = ['avg_chunks_per_doc', 'avg_chunk_length', 'avg_sentences_per_chunk', 'avg_words_per_chunk']
        local_values = [local_stats[metric] for metric in metrics]
        aws_values = [aws_stats[metric] for metric in metrics]
        
        x = range(len(metrics))
        width = 0.35
        
        axes[0, 0].bar([i - width/2 for i in x], local_values, width, label='Local POC', alpha=0.8)
        axes[0, 0].bar([i + width/2 for i in x], aws_values, width, label='AWS Structured', alpha=0.8)
        axes[0, 0].set_xlabel('Metrics')
        axes[0, 0].set_ylabel('Values')
        axes[0, 0].set_title('Chunk Statistics Comparison')
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels([m.replace('_', ' ').title() for m in metrics], rotation=45)
        axes[0, 0].legend()
        
        # 2. Structure analysis (AWS only)
        if 'structure_analysis' in results:
            structure_data = results['structure_analysis']['section_type_analysis']
            
            axes[0, 1].pie(structure_data.values(), labels=structure_data.keys(), autopct='%1.1f%%')
            axes[0, 1].set_title('AWS Chunk Type Distribution')
        
        # 3. Hierarchy distribution (AWS only)
        if 'structure_analysis' in results:
            hierarchy_data = results['structure_analysis']['hierarchy_distribution']
            
            axes[1, 0].bar(hierarchy_data.keys(), hierarchy_data.values())
            axes[1, 0].set_xlabel('Hierarchy Level')
            axes[1, 0].set_ylabel('Percentage of Chunks')
            axes[1, 0].set_title('Document Hierarchy Preservation')
        
        # 4. Quality metrics comparison
        if 'quality_metrics' in results and 'coherence_analysis' in results['quality_metrics']:
            coherence_data = results['quality_metrics']['coherence_analysis']
            
            methods = ['Local POC', 'AWS Structured']
            coherence_scores = [
                coherence_data['local_poc']['avg_coherence_score'],
                coherence_data['aws_structured']['avg_coherence_score']
            ]
            
            axes[1, 1].bar(methods, coherence_scores, color=['skyblue', 'lightcoral'])
            axes[1, 1].set_ylabel('Coherence Score')
            axes[1, 1].set_title('Chunk Coherence Comparison')
            axes[1, 1].set_ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig('chunking_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        logger.info("Comparison visualizations saved as 'chunking_comparison.png'")


def main():
    parser = argparse.ArgumentParser(description='Compare chunking methods')
    parser.add_argument('--local-chunks-path', required=True,
                       help='Path to local POC chunks directory')
    parser.add_argument('--aws-artifacts-bucket', required=True,
                       help='AWS S3 artifacts bucket name')
    parser.add_argument('--sample-size', type=int, default=50,
                       help='Number of documents to sample for comparison')
    parser.add_argument('--output-file', default='chunking_comparison_results.json',
                       help='Output file for detailed results')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    
    args = parser.parse_args()
    
    comparator = ChunkingComparator(args.region)
    
    results = comparator.compare_chunking_methods(
        args.local_chunks_path,
        args.aws_artifacts_bucket,
        args.sample_size
    )
    
    # Save detailed results
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "="*60)
    print("CHUNKING COMPARISON SUMMARY")
    print("="*60)
    
    local_stats = results['summary']['local_poc']
    aws_stats = results['summary']['aws_structured']
    
    print(f"\nLocal POC Method:")
    print(f"  Total chunks: {local_stats['total_chunks']}")
    print(f"  Avg chunks per doc: {local_stats['avg_chunks_per_doc']:.1f}")
    print(f"  Avg chunk length: {local_stats['avg_chunk_length']:.0f} chars")
    print(f"  Avg sentences per chunk: {local_stats['avg_sentences_per_chunk']:.1f}")
    
    print(f"\nAWS Structured Method:")
    print(f"  Total chunks: {aws_stats['total_chunks']}")
    print(f"  Avg chunks per doc: {aws_stats['avg_chunks_per_doc']:.1f}")
    print(f"  Avg chunk length: {aws_stats['avg_chunk_length']:.0f} chars")
    print(f"  Avg sentences per chunk: {aws_stats['avg_sentences_per_chunk']:.1f}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(results['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print(f"\nDetailed results saved to: {args.output_file}")


if __name__ == "__main__":
    main()
