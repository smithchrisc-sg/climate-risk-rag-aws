#!/usr/bin/env python3
"""
Simple Comprehend Test - No special characters
Quick test of Comprehend with climate content
"""
import sys
import os

# Add lambda worker path for imports
sys.path.append('lambda/nlp_worker')

def test_comprehend_basic():
    """Basic test of Comprehend functionality"""
    
    print("TESTING COMPREHEND WITH CLIMATE CONTENT")
    print("=" * 50)
    
    try:
        # Test import
        from comprehend_evaluator import ComprehendEvaluator
        print("SUCCESS: ComprehendEvaluator imported")
        
        # Initialize evaluator
        evaluator = ComprehendEvaluator()
        print("SUCCESS: Evaluator initialized")
        
        # Test document
        test_text = """
        Climate change is causing unprecedented global warming, leading to rising sea levels 
        and extreme weather events. The IPCC reports show that carbon emissions must be 
        reduced by 50% by 2030 to limit temperature increase to 1.5 degrees Celsius. 
        Renewable energy solutions like solar power and wind energy are crucial for 
        mitigation strategies. The Paris Agreement aims to coordinate global climate action.
        """
        
        print("\nTesting with sample climate document...")
        print("Document length: {} characters".format(len(test_text)))
        
        # Run evaluation
        result = evaluator.evaluate_document(test_text, "test_doc")
        
        # Display results
        metrics = result['evaluation_metrics']
        print("\nRESULTS:")
        print("Precision: {:.1%}".format(metrics['precision']))
        print("Recall: {:.1%}".format(metrics['recall']))
        print("F1 Score: {:.1%}".format(metrics['f1_score']))
        print("True Positives: {}".format(metrics['true_positives']))
        print("False Positives: {}".format(metrics['false_positives']))
        print("False Negatives: {}".format(metrics['false_negatives']))
        
        # Show some examples
        if metrics['true_positive_entities']:
            print("\nEntities correctly found:")
            for entity in metrics['true_positive_entities'][:5]:
                print("  - {}".format(entity))
        
        if metrics['false_negative_entities']:
            print("\nClimate entities missed:")
            for entity in metrics['false_negative_entities'][:5]:
                print("  - {}".format(entity))
        
        if metrics['false_positive_entities']:
            print("\nNon-climate entities found:")
            for entity in metrics['false_positive_entities'][:5]:
                print("  - {}".format(entity))
        
        # Show recommendations
        if result['recommendations']:
            print("\nRecommendations:")
            for rec in result['recommendations']:
                print("  - {}".format(rec))
        
        print("\nTEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print("ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    
    print("Starting Comprehend validation test...")
    
    success = test_comprehend_basic()
    
    if success:
        print("\nTest completed successfully!")
        print("Review the precision/recall metrics above.")
    else:
        print("\nTest failed - check error messages.")

if __name__ == "__main__":
    main()
