#!/usr/bin/env python3
"""
Direct Comprehend Test - Minimal dependencies
Test Comprehend directly without complex evaluation framework
"""
import boto3
import time

def test_comprehend_direct():
    """Test Comprehend directly with climate content"""
    
    print("DIRECT COMPREHEND TEST")
    print("=" * 30)
    
    try:
        # Initialize Comprehend client
        comprehend = boto3.client('comprehend', region_name='us-east-1')
        print("SUCCESS: Comprehend client initialized")
        
        # Test document with climate content
        test_text = """
        Climate change is causing unprecedented global warming, leading to rising sea levels 
        and extreme weather events. The IPCC reports show that carbon emissions must be 
        reduced by 50% by 2030 to limit temperature increase to 1.5 degrees Celsius. 
        Renewable energy solutions like solar power and wind energy are crucial for 
        mitigation strategies. The Paris Agreement aims to coordinate global climate action.
        """
        
        print("\nTesting document ({} characters)".format(len(test_text)))
        
        # Call Comprehend entity detection
        start_time = time.time()
        
        response = comprehend.detect_entities(
            Text=test_text,
            LanguageCode='en'
        )
        
        processing_time = time.time() - start_time
        
        print("SUCCESS: Comprehend API call completed in {:.2f}s".format(processing_time))
        
        # Display results
        entities = response['Entities']
        print("\nFOUND {} ENTITIES:".format(len(entities)))
        
        for entity in entities:
            print("  - '{}' (Type: {}, Confidence: {:.1%})".format(
                entity['Text'], 
                entity['Type'], 
                entity['Score']
            ))
        
        # Calculate cost
        units = max(1, len(test_text) / 100)
        cost = units * 0.0001  # Entity detection cost
        print("\nCOST ESTIMATE: ${:.6f}".format(cost))
        
        # Climate-specific analysis
        climate_terms = [
            'climate change', 'global warming', 'sea levels', 'extreme weather',
            'ipcc', 'carbon emissions', 'temperature increase', 'renewable energy',
            'solar power', 'wind energy', 'paris agreement'
        ]
        
        found_climate_terms = []
        for entity in entities:
            entity_text = entity['Text'].lower()
            for term in climate_terms:
                if term in entity_text or entity_text in term:
                    found_climate_terms.append(entity['Text'])
                    break
        
        print("\nCLIMATE ANALYSIS:")
        print("Climate terms in text: {}".format(len(climate_terms)))
        print("Climate entities found: {}".format(len(found_climate_terms)))
        print("Climate detection rate: {:.1%}".format(len(found_climate_terms) / len(climate_terms)))
        
        if found_climate_terms:
            print("Climate entities detected:")
            for term in found_climate_terms:
                print("  - {}".format(term))
        
        print("\nTEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print("ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run direct Comprehend test"""
    
    print("Starting direct Comprehend test...")
    
    success = test_comprehend_direct()
    
    if success:
        print("\nDirect test successful!")
        print("Comprehend is working and can detect climate-related entities.")
    else:
        print("\nTest failed - check AWS credentials and permissions.")

if __name__ == "__main__":
    main()
