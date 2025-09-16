# Neptune Stream Record Structure & Integration Analysis

## 🔍 **Record Structure**

Based on analysis of the Neptune Stream Poller code, here's the record structure:

### **Raw Stream Record**
```python
record = {
    DATA_STR: {
        # Raw stream data from Neptune
        # Contains SPARQL statement information
        # Gets parsed by parse_sparql_statement()
    },
    # Other metadata fields...
}
```

### **After Parsing (Enhanced Record)**
```python
record = {
    DATA_STR: {
        # Original raw data
        ELEMENTS_STR: {
            SUBJECT: <rdflib.term.URIRef or BNode>,
            PREDICATE: <rdflib.term.URIRef>,
            OBJECT: <rdflib.term.Literal or URIRef>,
            # Additional parsed elements...
        }
    }
}
```

### **Parsed Elements Structure**
```python
statement_elements = {
    SUBJECT: URIRef("http://example.org/subject"),
    PREDICATE: URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
    OBJECT: Literal("Climate Change Impact", datatype=XSD.string, lang="en")
}
```

## 🔧 **Missing Dependencies**

The following are imported from Lambda layer modules not in our download:

### **From `commons`:**
- `parse_sparql_statement(record_data)` - Parses raw stream data into RDF elements
- `DATA_STR` - Constant for accessing record data
- `ELEMENTS_STR` - Constant for accessing parsed elements
- `SUBJECT`, `PREDICATE`, `OBJECT` - Constants for RDF triple elements
- `RDF_TYPE` - Constant for rdf:type predicate

### **From `config_provider`:**
- `config_provider.logging_level` - Logging configuration
- `config_provider.get_handler_additional_param()` - Configuration access

## 📋 **Two Filter Methods Explained**

### **1. `neptune_sparql_es_handler.py` - Full Filtering**
```python
def filter_records(self, records, client):
    """
    Comprehensive filtering for all data types:
    - Blank nodes
    - Non-literal objects (except rdf:type)
    - Excluded properties
    - Excluded datatypes
    - Language validation
    - Numeric validation
    - Type mapping validation
    """
```

### **2. `neptune_sparql_es_string_indexing_handler.py` - String-Only Filtering**
```python
def filter_records(self, records, client):
    """
    Simplified filtering for string-only indexing:
    - Blank nodes
    - Non-string literals only
    - Much simpler logic
    """
```

**Which one is used?** Determined by environment variable `EnableNonStringIndexing`:
- `true` → Uses full handler (neptune_sparql_es_handler.py)
- `false` → Uses string-only handler (neptune_sparql_es_string_indexing_handler.py)

## 🎯 **Integration Strategy**

### **Option A: Create Missing Dependencies (Recommended)**

Create stub implementations of missing dependencies:

```python
# File: neptune_commons.py (new file)

import logging
from rdflib import URIRef
from rdflib.namespace import RDF

# Constants (best guess based on usage)
DATA_STR = "data"
ELEMENTS_STR = "elements"
SUBJECT = "subject"
PREDICATE = "predicate"
OBJECT = "object"
RDF_TYPE = RDF.type

def parse_sparql_statement(record_data):
    """
    Stub implementation - parse SPARQL statement from stream record
    This would normally be in the Lambda layer
    """
    # This is a simplified version - the real implementation
    # would parse the actual Neptune stream format
    
    # For now, assume record_data has the structure we need
    # In reality, this parses Neptune's stream format
    
    if 'stmt' in record_data:
        stmt = record_data['stmt']
        return {
            SUBJECT: URIRef(stmt.get('subject', '')),
            PREDICATE: URIRef(stmt.get('predicate', '')),
            OBJECT: parse_object(stmt.get('object', {}))
        }
    
    # Fallback - return empty structure
    return {SUBJECT: None, PREDICATE: None, OBJECT: None}

def parse_object(obj_data):
    """Parse object from Neptune stream format"""
    from rdflib.term import Literal, URIRef
    
    if obj_data.get('type') == 'literal':
        return Literal(
            obj_data.get('value', ''),
            datatype=URIRef(obj_data.get('datatype', '')) if obj_data.get('datatype') else None,
            lang=obj_data.get('language')
        )
    else:
        return URIRef(obj_data.get('value', ''))
```

### **Option B: Work with Raw Stream Data**

Modify our ontology filter to work with the raw stream format:

```python
# Modified ontology_filter.py

def should_index_record(self, record: Dict[str, Any]) -> bool:
    """
    Work with raw Neptune stream record format
    """
    try:
        # Access raw stream data
        record_data = record.get(DATA_STR, record)  # Fallback to record itself
        
        # Handle different possible formats
        if 'eventData' in record_data:
            # Format from our test data
            stmt = record_data['eventData']['stmt']
        elif 'stmt' in record_data:
            # Direct statement format
            stmt = record_data['stmt']
        else:
            # Unknown format
            return False
        
        graph_uri = stmt.get('graph', '')
        predicate_uri = stmt.get('predicate', '')
        obj_data = stmt.get('object', {})
        
        # Apply filtering logic
        is_ontology_graph = self._is_ontology_graph(graph_uri)
        is_included_predicate = self._is_included_predicate(predicate_uri)
        is_literal = obj_data.get('type') == 'literal'
        
        return is_ontology_graph and is_included_predicate and is_literal
        
    except Exception as e:
        logger.error(f"Error filtering record: {e}")
        return False
```

## 🔧 **Recommended Integration Approach**

### **Step 1: Create Neptune Commons Module**

```python
# File: neptune_commons.py
# Provides missing dependencies from Lambda layer

import logging
from rdflib import URIRef, Literal
from rdflib.namespace import RDF, XSD

# Constants
DATA_STR = "data"
ELEMENTS_STR = "elements" 
SUBJECT = "subject"
PREDICATE = "predicate"
OBJECT = "object"
RDF_TYPE = RDF.type

class MockConfigProvider:
    """Mock config provider for missing config_provider module"""
    
    @property
    def logging_level(self):
        return logging.INFO
    
    def get_handler_additional_param(self, param, default=None):
        import os
        return os.getenv(param, default)

# Global instance
config_provider = MockConfigProvider()

def parse_sparql_statement(record_data):
    """
    Parse Neptune stream record into RDF elements
    This is a best-effort implementation based on observed usage
    """
    try:
        # Handle different possible record formats
        if 'eventData' in record_data:
            stmt = record_data['eventData']['stmt']
        elif 'stmt' in record_data:
            stmt = record_data['stmt']
        else:
            # Try to extract from record_data directly
            stmt = record_data
        
        # Parse subject
        subject_data = stmt.get('subject', '')
        if isinstance(subject_data, dict):
            subject = URIRef(subject_data.get('value', ''))
        else:
            subject = URIRef(subject_data)
        
        # Parse predicate
        predicate_data = stmt.get('predicate', '')
        if isinstance(predicate_data, dict):
            predicate = URIRef(predicate_data.get('value', ''))
        else:
            predicate = URIRef(predicate_data)
        
        # Parse object
        obj_data = stmt.get('object', {})
        if isinstance(obj_data, dict):
            if obj_data.get('type') == 'literal':
                obj = Literal(
                    obj_data.get('value', ''),
                    datatype=URIRef(obj_data.get('datatype', '')) if obj_data.get('datatype') else None,
                    lang=obj_data.get('language')
                )
            else:
                obj = URIRef(obj_data.get('value', ''))
        else:
            obj = Literal(str(obj_data))
        
        return {
            SUBJECT: subject,
            PREDICATE: predicate,
            OBJECT: obj
        }
        
    except Exception as e:
        logging.error(f"Error parsing SPARQL statement: {e}")
        return {SUBJECT: None, PREDICATE: None, OBJECT: None}
```

### **Step 2: Modify Handler Imports**

```python
# In neptune_to_es/neptune_sparql_es_handler.py
# Replace: from commons import *
# With:
try:
    from commons import *
except ImportError:
    from neptune_commons import *
```

### **Step 3: Integrate Ontology Filter**

```python
# In filter_records method, add at the beginning:
from ontology_filter import get_ontology_filter

def filter_records(self, records, client):
    # Apply ontology filtering first
    ontology_filter = get_ontology_filter()
    if ontology_filter.filtering_enabled:
        original_count = len(records)
        records = ontology_filter.filter_records(records)
        logger.info(f"Ontology filter: {original_count} → {len(records)} records")
    
    # Continue with existing logic...
```

## 🧪 **Testing Strategy**

### **Test 1: Verify Dependencies**
```python
# Test that our stubs work
from neptune_commons import parse_sparql_statement, DATA_STR

test_record = {
    DATA_STR: {
        'eventData': {
            'stmt': {
                'subject': 'http://example.org/subject',
                'predicate': 'http://www.w3.org/2000/01/rdf-schema#label',
                'object': {
                    'type': 'literal',
                    'value': 'Test Label'
                }
            }
        }
    }
}

elements = parse_sparql_statement(test_record[DATA_STR])
print(f"Subject: {elements['subject']}")
print(f"Predicate: {elements['predicate']}")
print(f"Object: {elements['object']}")
```

### **Test 2: Integration Test**
```python
# Test full integration
from ontology_filter import get_ontology_filter

filter_instance = get_ontology_filter()
filtered_records = filter_instance.filter_records([test_record])
print(f"Filtered: {len(filtered_records)} records")
```

## ⚠️ **Important Notes**

1. **Lambda Layer Dependencies**: The real `commons` and `config_provider` are in the Lambda layer, not in our downloaded code
2. **Record Format**: The exact Neptune stream record format may differ from our assumptions
3. **Testing Required**: Integration needs testing with real Neptune stream data
4. **Fallback Strategy**: Our stubs provide fallback functionality if layer modules fail

## 🎯 **Next Steps**

1. **Create `neptune_commons.py`** with stub implementations
2. **Modify handler imports** to use fallbacks
3. **Integrate ontology filter** in both handler files
4. **Test with real stream data**
5. **Refine based on actual record format**

---

**Status**: Ready for implementation with dependency stubs
