#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test script to verify ontology filter integration
"""

import os
import sys

# Set up environment for testing
os.environ['ONTOLOGY_FILTERING_ENABLED'] = 'true'
os.environ['LOG_FILTERED_RECORDS'] = 'true'

# Import our filter
from ontology_filter import get_ontology_filter

def test_basic_filtering():
    """Test basic filtering functionality"""
    
    print("Testing Ontology Filter Integration")
    print("=" * 40)
    
    # Sample geonames record
    geonames_record = {
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
    }
    
    # Sample document record (should be filtered out)
    document_record = {
        'data': {
            'eventData': {
                'stmt': {
                    'graph': 'http://document-data',
                    'subject': 'http://example.org/doc1',
                    'predicate': 'http://example.org/document#content',
                    'object': {'type': 'literal', 'value': 'Document content...'}
                }
            }
        }
    }
    
    # Test filtering
    filter_instance = get_ontology_filter()
    
    print("Filter enabled: {}".format(filter_instance.filtering_enabled))
    print("Number of filtering rules: {}".format(len(filter_instance.filtering_rules)))
    
    # Test individual records
    geonames_result = filter_instance.should_index_record(geonames_record)
    document_result = filter_instance.should_index_record(document_record)
    
    print("Geonames name record: {}".format('INCLUDE' if geonames_result else 'EXCLUDE'))
    print("Document content record: {}".format('INCLUDE' if document_result else 'EXCLUDE'))
    
    # Test batch filtering
    test_records = [geonames_record, document_record]
    filtered_records = filter_instance.filter_records(test_records)
    
    print("Original records: {}".format(len(test_records)))
    print("Filtered records: {}".format(len(filtered_records)))
    
    # Should include geonames name, exclude document content
    success = (geonames_result == True and 
               document_result == False and 
               len(filtered_records) == 1)
    
    print("Test result: {}".format('PASS' if success else 'FAIL'))
    
    return success

if __name__ == "__main__":
    try:
        success = test_basic_filtering()
        sys.exit(0 if success else 1)
    except Exception as e:
        print("Test failed with error: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
