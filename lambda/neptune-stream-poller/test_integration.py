#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify ontology filter integration
Run this locally to test the filtering logic before deployment
"""

import os
import sys
import json

# Set up environment for testing
os.environ['ONTOLOGY_FILTERING_ENABLED'] = 'true'
os.environ['LOG_FILTERED_RECORDS'] = 'true'

# Import our filter
from ontology_filter import get_ontology_filter

def test_geonames_filtering():
    """Test filtering with geonames example data"""
    
    print("🧪 Testing Geonames Ontology Filtering")
    print("=" * 50)
    
    # Sample records based on your geonames example
    test_records = [
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.geonames.org/ontology#name',
                        'object': {'type': 'literal', 'value': 'Jakarta'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.geonames.org/ontology#alternateName',
                        'object': {'type': 'literal', 'value': 'Djakarta', 'language': 'af'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.w3.org/2000/01/rdf-schema#isDefinedBy',
                        'object': {'type': 'uri', 'value': 'https://sws.geonames.org/1642911/about.rdf'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://www.geonames.org/ontology',
                        'subject': 'https://sws.geonames.org/1642911/',
                        'predicate': 'http://www.geonames.org/ontology#population',
                        'object': {'type': 'literal', 'value': '10000000', 'datatype': 'http://www.w3.org/2001/XMLSchema#integer'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://document-data',
                        'subject': 'http://example.org/doc1',
                        'predicate': 'http://example.org/document#content',
                        'object': {'type': 'literal', 'value': 'Document content about Jakarta...'}
                    }
                }
            }
        }
    ]
    
    # Test filtering
    filter_instance = get_ontology_filter()
    
    print(f"📊 Filter configuration:")
    stats = filter_instance.get_filter_stats()
    print(f"  • Filtering enabled: {stats['filtering_enabled']}")
    print(f"  • Approach: {stats['filtering_approach']}")
    print(f"  • Ontologies: {stats['ontologies_count']}")
    print(f"  • Total predicates: {stats['total_predicates']}")
    print()
    
    print(f"📋 Filtering rules:")
    for ontology, predicates in stats['filtering_rules'].items():
        print(f"  • {ontology}:")
        for pred in predicates:
            print(f"    - {pred}")
    print()
    
    print(f"🔍 Testing with {len(test_records)} sample records:")
    for i, record in enumerate(test_records, 1):
        stmt = record['data']['eventData']['stmt']
        graph = stmt['graph'].split('/')[-1] if '/' in stmt['graph'] else stmt['graph']
        pred = stmt['predicate'].split('#')[-1] if '#' in stmt['predicate'] else stmt['predicate'].split('/')[-1]
        obj_type = stmt['object']['type']
        obj_value = stmt['object']['value'][:30] + '...' if len(stmt['object']['value']) > 30 else stmt['object']['value']
        
        should_index = filter_instance.should_index_record(record)
        status = "✅ INCLUDE" if should_index else "❌ EXCLUDE"
        
        print(f"  {i}. {status} | {graph} | {pred} | {obj_type} | {obj_value}")
    
    print()
    
    # Apply batch filtering
    filtered_records = filter_instance.filter_records(test_records)
    
    print(f"🎯 Filtering Results:")
    print(f"  • Original records: {len(test_records)}")
    print(f"  • Filtered records: {len(filtered_records)}")
    print(f"  • Reduction: {((len(test_records) - len(filtered_records)) / len(test_records) * 100):.1f}%")
    print()
    
    print(f"📝 Expected results:")
    print(f"  • ✅ gn:name 'Jakarta' - should be included")
    print(f"  • ✅ gn:alternateName 'Djakarta' - should be included")
    print(f"  • ❌ rdfs:isDefinedBy - should be excluded (not literal)")
    print(f"  • ❌ gn:population - should be excluded (not in whitelist)")
    print(f"  • ❌ document:content - should be excluded (wrong graph)")
    
    return len(filtered_records) == 2  # Should only include name and alternateName

def test_climate_risk_filtering():
    """Test filtering with climate risk ontology data"""
    
    print("\n🧪 Testing Climate Risk Ontology Filtering")
    print("=" * 50)
    
    test_records = [
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://climate-risk-ontology',
                        'subject': 'http://climate-risk-ontology#ClimateChange',
                        'predicate': 'http://www.w3.org/2000/01/rdf-schema#label',
                        'object': {'type': 'literal', 'value': 'Climate Change'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://climate-risk-ontology',
                        'subject': 'http://climate-risk-ontology#ClimateChange',
                        'predicate': 'http://www.w3.org/2004/02/skos/core#definition',
                        'object': {'type': 'literal', 'value': 'Long-term shifts in global temperatures and weather patterns'}
                    }
                }
            }
        },
        {
            'data': {
                'eventData': {
                    'stmt': {
                        'graph': 'http://climate-risk-ontology',
                        'subject': 'http://climate-risk-ontology#ClimateChange',
                        'predicate': 'http://climate-risk-ontology#hasImpactLevel',
                        'object': {'type': 'literal', 'value': 'high'}
                    }
                }
            }
        }
    ]
    
    filter_instance = get_ontology_filter()
    filtered_records = filter_instance.filter_records(test_records)
    
    print(f"🎯 Climate Risk Filtering Results:")
    print(f"  • Original records: {len(test_records)}")
    print(f"  • Filtered records: {len(filtered_records)}")
    
    return len(filtered_records) == 2  # Should include label and definition, exclude hasImpactLevel

def main():
    """Run all integration tests"""
    
    print("🚀 Neptune Stream Poller - Ontology Filter Integration Test")
    print("=" * 60)
    
    try:
        # Test geonames filtering
        geonames_pass = test_geonames_filtering()
        
        # Test climate risk filtering  
        climate_pass = test_climate_risk_filtering()
        
        print(f"\n📊 Test Results:")
        print(f"  • Geonames filtering: {'✅ PASS' if geonames_pass else '❌ FAIL'}")
        print(f"  • Climate risk filtering: {'✅ PASS' if climate_pass else '❌ FAIL'}")
        
        if geonames_pass and climate_pass:
            print(f"\n🎉 All tests passed! Integration is ready for deployment.")
            return 0
        else:
            print(f"\n❌ Some tests failed. Check the filtering logic.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
