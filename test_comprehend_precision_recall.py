#!/usr/bin/env python3
"""
Simple Comprehend Precision/Recall Test
Quick evaluation of Comprehend performance on climate risk content
"""
import sys
import os

# Add lambda worker path for imports
sys.path.append('lambda/nlp_worker')

try:
    from comprehend_evaluator import ComprehendEvaluator
    print("Successfully imported ComprehendEvaluator")
except ImportError as e:
    print("Import error: {}".format(str(e)))
    print("Make sure you're running from the project root directory")
    sys.exit(1)

def test_comprehend_evaluation():
    """Test Comprehend evaluation with sample climate risk documents"""
    
    print("TESTING COMPREHEND PRECISION/RECALL")
    print("=" * 50)
    
    # Sample climate risk documents
    test_documents = [
        {
            'doc_id': 'climate_policy_001',
            'text': """
            The Paris Agreement represents a landmark international climate accord that aims to limit 
            global warming to well below 2 degrees Celsius above pre-industrial levels. The agreement 
            requires countries to submit nationally determined contributions (NDCs) to reduce greenhouse 
            gas emissions. Carbon pricing mechanisms and renewable energy deployment are key strategies 
            for achieving these emission reduction targets. The IPCC reports indicate that rapid 
            decarbonization is essential to avoid catastrophic climate impacts.
            """
        },
        {
            'doc_id': 'climate_impacts_002', 
            'text': """
            Sea level rise poses significant risks to coastal communities worldwide. Rising ocean 
            temperatures contribute to coral bleaching events, threatening marine biodiversity. 
            Extreme weather events including hurricanes, droughts, and heat waves are becoming 
            more frequent and intense due to climate change. Arctic ice melt and permafrost thaw 
            are accelerating, creating feedback loops that amplify global warming effects.
            """
        },
        {
            'doc_id': 'climate_solutions_003',
            'text': """
            Renewable energy technologies such as solar power and wind energy are experiencing 
            rapid cost reductions and deployment growth. Energy efficiency improvements in buildings 
            and transportation can significantly reduce carbon emissions. Nature-based solutions 
            including reforestation and wetland restoration provide both mitigation and adaptation 
            benefits. Carbon capture and storage technologies offer potential for removing CO2 
            from the atmosphere at scale.
            """
        }
    ]
    
    try:
        # Initialize evaluator
        evaluator = ComprehendEvaluator()
        print("Initialized evaluator with climate ontology")
        
        # Test individual documents
        print("\nINDIVIDUAL DOCUMENT RESULTS:")
        print("-" * 40)
        
        individual_results = []
        
        for doc in test_documents:
            print(f"\nEvaluating: {doc['doc_id']}")
            
            result = evaluator.evaluate_document(doc['text'], doc['doc_id'])
            individual_results.append(result)
            
            metrics = result['evaluation_metrics']
            print(f"  Precision: {metrics['precision']:.1%}")
            print(f"  Recall: {metrics['recall']:.1%}")
            print(f"  F1 Score: {metrics['f1_score']:.1%}")
            print(f"  True Positives: {metrics['true_positives']}")
            print(f"  False Positives: {metrics['false_positives']}")
            print(f"  False Negatives: {metrics['false_negatives']}")
            
            if result['recommendations']:
                print(f"  Recommendations: {result['recommendations'][0]}")
        
        # Test corpus evaluation
        print(f"\n📈 CORPUS-LEVEL EVALUATION:")
        print("-" * 40)
        
        corpus_result = evaluator.evaluate_corpus(test_documents)
        corpus_metrics = corpus_result['corpus_metrics']
        
        print(f"Average Precision: {corpus_metrics['average_precision']:.1%}")
        print(f"Average Recall: {corpus_metrics['average_recall']:.1%}")
        print(f"Average F1 Score: {corpus_metrics['average_f1_score']:.1%}")
        
        print(f"\nCorpus Totals:")
        print(f"  True Positives: {corpus_metrics['total_true_positives']}")
        print(f"  False Positives: {corpus_metrics['total_false_positives']}")
        print(f"  False Negatives: {corpus_metrics['total_false_negatives']}")
        
        print(f"\n💡 CORPUS RECOMMENDATIONS:")
        for rec in corpus_result['summary_recommendations']:
            print(f"  • {rec}")
        
        # Show some specific examples
        print(f"\n🔍 DETAILED ANALYSIS EXAMPLES:")
        print("-" * 40)
        
        first_result = individual_results[0]
        metrics = first_result['evaluation_metrics']
        
        if metrics['true_positive_entities']:
            print(f"✅ Entities correctly found by Comprehend:")
            for entity in metrics['true_positive_entities'][:5]:  # Show first 5
                print(f"    • {entity}")
        
        if metrics['false_negative_entities']:
            print(f"❌ Climate entities missed by Comprehend:")
            for entity in metrics['false_negative_entities'][:5]:  # Show first 5
                print(f"    • {entity}")
        
        if metrics['false_positive_entities']:
            print(f"⚠️  Non-climate entities found by Comprehend:")
            for entity in metrics['false_positive_entities'][:5]:  # Show first 5
                print(f"    • {entity}")
        
        print(f"\n💾 Results saved to comprehend_test_results.json")
        
        # Save results for analysis
        import json
        with open('comprehend_test_results.json', 'w') as f:
            json.dump({
                'individual_results': individual_results,
                'corpus_result': corpus_result
            }, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during evaluation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run Comprehend precision/recall test"""
    
    print("Starting Comprehend Evaluation Test...")
    
    # Check if we can run the test
    if not os.path.exists('lambda/nlp_worker/comprehend_evaluator.py'):
        print("❌ ComprehendEvaluator not found. Make sure you're in the project root directory.")
        return
    
    success = test_comprehend_evaluation()
    
    if success:
        print("\n🎉 COMPREHEND EVALUATION COMPLETED SUCCESSFULLY!")
        print("\nNext steps:")
        print("1. Review precision/recall metrics")
        print("2. Analyze false positives/negatives")
        print("3. Consider ontology refinements")
        print("4. Test with larger document corpus")
    else:
        print("\n❌ EVALUATION FAILED - Check error messages above")

if __name__ == "__main__":
    main()
