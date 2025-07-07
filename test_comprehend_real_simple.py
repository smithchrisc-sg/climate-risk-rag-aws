#!/usr/bin/env python3
"""
REAL Comprehend Test - Actual API Calls with Documented Test Documents
Clear documentation of what is being tested for manual review
"""
import boto3
import json
import time
from datetime import datetime

# DOCUMENTED TEST DOCUMENTS - FOR MANUAL REVIEW
TEST_DOCUMENTS = [
    {
        'doc_id': 'climate_policy_test_001',
        'title': 'Climate Policy Test Document',
        'description': 'Tests detection of policy terms, organizations, and agreements',
        'source': 'Created specifically for testing - contains known climate policy vocabulary',
        'text': """The Paris Agreement represents a landmark international climate accord adopted in 2015 that aims to limit global warming to well below 2 degrees Celsius above pre-industrial levels. The agreement requires countries to submit nationally determined contributions (NDCs) to reduce greenhouse gas emissions. The IPCC Sixth Assessment Report indicates that rapid decarbonization is essential to avoid catastrophic climate impacts. Carbon pricing mechanisms and renewable energy deployment are key strategies for achieving emission reduction targets set by the UNFCCC framework.""",
        'expected_climate_terms': [
            'Paris Agreement', 'IPCC', 'UNFCCC', 'climate accord', 'global warming',
            'greenhouse gas emissions', 'carbon pricing', 'renewable energy', 
            'decarbonization', 'climate impacts', 'NDCs'
        ]
    },
    {
        'doc_id': 'climate_impacts_test_002', 
        'title': 'Climate Impacts Test Document',
        'description': 'Tests detection of physical climate impacts and phenomena',
        'source': 'Created specifically for testing - contains known climate impact vocabulary',
        'text': """Sea level rise poses significant risks to coastal communities worldwide, with projections showing increases of 0.5 to 2 meters by 2100. Rising ocean temperatures contribute to coral bleaching events, threatening marine biodiversity across tropical regions. Extreme weather events including hurricanes, droughts, heat waves, and flooding are becoming more frequent and intense due to climate change. Arctic ice melt and permafrost thaw are accelerating, creating feedback loops that amplify global warming effects.""",
        'expected_climate_terms': [
            'sea level rise', 'coastal communities', 'ocean temperatures', 'coral bleaching',
            'marine biodiversity', 'extreme weather', 'hurricanes', 'droughts', 'heat waves',
            'flooding', 'Arctic ice melt', 'permafrost thaw', 'climate change', 'global warming'
        ]
    }
]

def test_comprehend_real():
    """Test Amazon Comprehend with real API calls on documented test documents"""
    
    print("REAL AMAZON COMPREHEND TEST")
    print("=" * 50)
    print("Testing with actual Comprehend API calls")
    print("Test documents documented below for manual review")
    print("=" * 50)
    
    try:
        # Initialize Comprehend client
        session = boto3.Session(profile_name='solve-global')
        comprehend = session.client('comprehend', region_name='us-east-1')
        print("SUCCESS: Connected to Amazon Comprehend")
        
        all_results = []
        
        for i, test_doc in enumerate(TEST_DOCUMENTS):
            print("\n" + "=" * 60)
            print("TEST DOCUMENT {}: {}".format(i+1, test_doc['title']))
            print("=" * 60)
            print("Doc ID: {}".format(test_doc['doc_id']))
            print("Description: {}".format(test_doc['description']))
            print("Source: {}".format(test_doc['source']))
            print("Text Length: {} characters".format(len(test_doc['text'])))
            
            print("\nFULL TEXT FOR MANUAL REVIEW:")
            print("-" * 40)
            print(test_doc['text'])
            print("-" * 40)
            
            print("Expected Climate Terms ({} terms):".format(len(test_doc['expected_climate_terms'])))
            for term in test_doc['expected_climate_terms']:
                print("  - {}".format(term))
            print("-" * 40)
            
            try:
                print("\nCalling Amazon Comprehend...")
                
                start_time = time.time()
                
                # Entity detection
                entity_response = comprehend.detect_entities(
                    Text=test_doc['text'],
                    LanguageCode='en'
                )
                
                # Key phrase detection
                phrase_response = comprehend.detect_key_phrases(
                    Text=test_doc['text'],
                    LanguageCode='en'
                )
                
                processing_time = time.time() - start_time
                
                # Calculate cost
                text_length = len(test_doc['text'])
                units = max(1, text_length / 100.0)
                entity_cost = units * 0.0001
                phrase_cost = units * 0.0001
                total_cost = entity_cost + phrase_cost
                
                print("COMPREHEND API RESULTS:")
                print("Processing Time: {:.2f} seconds".format(processing_time))
                print("Estimated Cost: ${:.6f}".format(total_cost))
                print("Entities Found: {}".format(len(entity_response['Entities'])))
                print("Key Phrases Found: {}".format(len(phrase_response['KeyPhrases'])))
                
                print("\nENTITIES DETECTED BY COMPREHEND:")
                entities_found = []
                for entity in entity_response['Entities']:
                    entity_info = {
                        'text': entity['Text'],
                        'type': entity['Type'],
                        'confidence': entity['Score']
                    }
                    entities_found.append(entity_info)
                    print("  - '{}' (Type: {}, Confidence: {:.1%})".format(
                        entity['Text'], entity['Type'], entity['Score']
                    ))
                
                print("\nKEY PHRASES DETECTED BY COMPREHEND:")
                phrases_found = []
                for phrase in phrase_response['KeyPhrases']:
                    phrase_info = {
                        'text': phrase['Text'],
                        'confidence': phrase['Score']
                    }
                    phrases_found.append(phrase_info)
                    print("  - '{}' (Confidence: {:.1%})".format(
                        phrase['Text'], phrase['Score']
                    ))
                
                # Analysis against expected terms
                found_texts = set(e['text'].lower() for e in entities_found)
                found_texts.update(p['text'].lower() for p in phrases_found)
                expected_texts = set(term.lower() for term in test_doc['expected_climate_terms'])
                
                # Find matches (allowing partial matches)
                true_positives = set()
                for found in found_texts:
                    for expected in expected_texts:
                        if expected in found or found in expected:
                            true_positives.add(expected)
                            break
                
                false_negatives = expected_texts - true_positives
                
                precision_denominator = len(found_texts) if found_texts else 1
                recall_denominator = len(expected_texts) if expected_texts else 1
                
                precision = len(true_positives) / precision_denominator
                recall = len(true_positives) / recall_denominator
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                print("\nPERFORMANCE ANALYSIS:")
                print("Climate Terms Expected: {}".format(len(expected_texts)))
                print("Climate Terms Found: {}".format(len(true_positives)))
                print("Recall: {:.1%} ({}/{})".format(recall, len(true_positives), len(expected_texts)))
                print("F1 Score: {:.1%}".format(f1_score))
                
                if true_positives:
                    print("Climate Terms Successfully Detected:")
                    for term in sorted(true_positives):
                        print("  + {}".format(term))
                
                if false_negatives:
                    print("Climate Terms MISSED by Comprehend:")
                    for term in sorted(false_negatives):
                        print("  - {}".format(term))
                
                # Store results
                result = {
                    'doc_id': test_doc['doc_id'],
                    'title': test_doc['title'],
                    'text_length': text_length,
                    'processing_time': processing_time,
                    'cost': total_cost,
                    'entities_count': len(entities_found),
                    'phrases_count': len(phrases_found),
                    'recall': recall,
                    'f1_score': f1_score,
                    'climate_terms_found': list(true_positives),
                    'climate_terms_missed': list(false_negatives),
                    'comprehend_entities': entities_found,
                    'comprehend_phrases': phrases_found
                }
                
                all_results.append(result)
                
                print("SUCCESS: Test completed for {}".format(test_doc['doc_id']))
                
            except Exception as e:
                print("ERROR testing {}: {}".format(test_doc['doc_id'], str(e)))
                all_results.append({
                    'doc_id': test_doc['doc_id'],
                    'title': test_doc['title'],
                    'error': str(e)
                })
            
            # Rate limiting
            time.sleep(1)
        
        # Summary
        print("\n" + "=" * 60)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        successful_tests = [r for r in all_results if 'error' not in r]
        
        if successful_tests:
            total_cost = sum(r['cost'] for r in successful_tests)
            avg_recall = sum(r['recall'] for r in successful_tests) / len(successful_tests)
            avg_f1 = sum(r['f1_score'] for r in successful_tests) / len(successful_tests)
            
            print("Tests Completed: {}/{}".format(len(successful_tests), len(TEST_DOCUMENTS)))
            print("Total Cost: ${:.6f}".format(total_cost))
            print("Average Climate Term Recall: {:.1%}".format(avg_recall))
            print("Average F1 Score: {:.1%}".format(avg_f1))
            
            print("\nPER-DOCUMENT PERFORMANCE:")
            for result in successful_tests:
                print("  {}: Recall={:.1%}, F1={:.1%}, Cost=${:.6f}".format(
                    result['title'], result['recall'], result['f1_score'], result['cost']
                ))
        
        # Save results with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = 'comprehend_real_test_results_{}.json'.format(timestamp)
        
        with open(results_file, 'w') as f:
            json.dump({
                'test_metadata': {
                    'test_type': 'real_comprehend_api_test',
                    'test_date': datetime.now().isoformat(),
                    'comprehend_region': 'us-east-1',
                    'documents_tested': len(TEST_DOCUMENTS)
                },
                'test_documents': TEST_DOCUMENTS,
                'test_results': all_results
            }, f, indent=2)
        
        print("\nDetailed results saved to: {}".format(results_file))
        print("All test documents are fully documented in the results file")
        print("You can manually review the test documents and Comprehend's performance")
        
        return all_results
        
    except Exception as e:
        print("FATAL ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run real Comprehend test"""
    
    print("Starting REAL Amazon Comprehend Integration Test...")
    print("This will make actual API calls and incur small costs (~$0.001)")
    print("Test documents are clearly documented for your manual review")
    
    results = test_comprehend_real()
    
    if results:
        print("\nREAL COMPREHEND TEST COMPLETED SUCCESSFULLY!")
        print("Review the detailed output above and the saved JSON file.")
        print("All test documents are documented for your manual verification.")
    else:
        print("\nTest failed - check error messages above.")

if __name__ == "__main__":
    main()
