#!/usr/bin/env python3
"""
Main Comparison Runner
Executes comprehensive comparison between POC and AWS implementations
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add the comparison framework to path
sys.path.append(str(Path(__file__).parent))

from comparison_framework import ComparisonFramework

def main():
    parser = argparse.ArgumentParser(description='Run comprehensive POC vs AWS comparison')
    parser.add_argument('--documents-bucket', required=True,
                       help='S3 bucket containing documents')
    parser.add_argument('--artifacts-bucket', required=True,
                       help='S3 bucket containing artifacts')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--sample-size', type=int, default=100,
                       help='Number of documents to sample for comparison')
    parser.add_argument('--output-dir', default='comparison_results',
                       help='Directory to save results')
    parser.add_argument('--quick-test', action='store_true',
                       help='Run quick test with smaller sample')
    
    args = parser.parse_args()
    
    # Adjust sample size for quick test
    if args.quick_test:
        args.sample_size = min(args.sample_size, 20)
        print(f"🚀 Running quick test with {args.sample_size} documents")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print("🔬 Climate Risk RAG - Comprehensive Comparison")
    print("=" * 50)
    print(f"Documents bucket: {args.documents_bucket}")
    print(f"Artifacts bucket: {args.artifacts_bucket}")
    print(f"Sample size: {args.sample_size}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Initialize comparison framework
    framework = ComparisonFramework(args.region)
    
    try:
        # Run comprehensive comparison
        results = framework.run_comprehensive_comparison(
            args.documents_bucket,
            args.artifacts_bucket,
            args.sample_size
        )
        
        # Save results locally
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        results_file = output_dir / f'comparison_results_{timestamp}.json'
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        print_comparison_summary(results)
        
        print(f"\n📊 Detailed results saved to: {results_file}")
        print(f"📈 Visualizations saved to: {output_dir}")
        
    except Exception as e:
        print(f"❌ Comparison failed: {str(e)}")
        sys.exit(1)

def print_comparison_summary(results: dict):
    """Print a human-readable summary of comparison results"""
    
    print("\n" + "=" * 60)
    print("📊 COMPARISON SUMMARY")
    print("=" * 60)
    
    summary = results.get('summary', {})
    print(f"Comparison completed: {summary.get('comparison_completed', 'Unknown')}")
    print(f"Duration: {summary.get('duration_seconds', 0):.2f} seconds")
    print(f"Sample size: {summary.get('sample_size', 0)} documents")
    
    # Text Extraction Results
    if 'text_extraction' in results:
        text_metrics = results['text_extraction'].get('metrics', {})
        print(f"\n📝 TEXT EXTRACTION:")
        print(f"  Average quality score: {text_metrics.get('avg_quality_score', 0):.3f}")
        print(f"  Jaccard similarity: {text_metrics.get('avg_jaccard_similarity', 0):.3f}")
        print(f"  Recommendation: {text_metrics.get('recommendation', 'N/A')}")
    
    # NER Results
    if 'ner_comparison' in results:
        ner_metrics = results['ner_comparison'].get('metrics', {})
        print(f"\n🏷️  NAMED ENTITY RECOGNITION:")
        print(f"  Average F1 score: {ner_metrics.get('avg_f1_score', 0):.3f}")
        print(f"  Average precision: {ner_metrics.get('avg_precision', 0):.3f}")
        print(f"  Average recall: {ner_metrics.get('avg_recall', 0):.3f}")
        print(f"  Recommendation: {ner_metrics.get('recommendation', 'N/A')}")
    
    # Embedding Results
    if 'embedding_comparison' in results:
        emb_comparisons = results['embedding_comparison'].get('comparisons', [])
        if emb_comparisons:
            avg_similarity = sum(c.get('similarity_analysis', {}).get('mean_similarity', 0) 
                               for c in emb_comparisons) / len(emb_comparisons)
            print(f"\n🔢 EMBEDDINGS:")
            print(f"  Average cosine similarity: {avg_similarity:.3f}")
            print(f"  Documents compared: {len(emb_comparisons)}")
    
    # Chunking Results
    if 'chunking_comparison' in results:
        chunk_comparisons = results['chunking_comparison'].get('comparisons', [])
        if chunk_comparisons:
            avg_overlap = sum(c.get('content_overlap', 0) for c in chunk_comparisons) / len(chunk_comparisons)
            print(f"\n✂️  CHUNKING:")
            print(f"  Average content overlap: {avg_overlap:.3f}")
            print(f"  Documents compared: {len(chunk_comparisons)}")
    
    # RAG Performance
    if 'rag_performance' in results:
        rag_queries = results['rag_performance'].get('test_queries', [])
        print(f"\n🤖 RAG PERFORMANCE:")
        print(f"  Test queries: {len(rag_queries)}")
        if rag_queries:
            # Add specific RAG metrics here when implemented
            print(f"  Performance analysis available in detailed results")
    
    # Recommendations
    recommendations = summary.get('recommendations', [])
    if recommendations:
        print(f"\n💡 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec}")
        
        if len(recommendations) > 5:
            print(f"  ... and {len(recommendations) - 5} more recommendations")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
