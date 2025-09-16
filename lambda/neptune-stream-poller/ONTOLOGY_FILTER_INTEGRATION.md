# Ontology Filter Integration Guide

## 🔍 **Current State: Filter NOT Integrated**

The `ontology_filter.py` module exists but is **not yet integrated** into the stream processing pipeline. The Lambda is currently processing **ALL** Neptune data without filtering.

## 🔧 **Integration Points**

### **Primary Integration Point: `filter_records` Method**

The main integration point is in the `ElasticSearchSparqlHandler.filter_records()` method:

**File**: `neptune_to_es/neptune_sparql_es_handler.py`  
**Method**: `filter_records(self, records, client)` (line ~191)

### **Current Filtering Logic**
The existing `filter_records` method already filters records based on:
1. Subject is a Blank Node
2. Object is a Resource for predicates other than rdf:type
3. Predicate name in excluded_properties list
4. Object type in excluded_types list
5. Language literal validation
6. Float/Double literal validation
7. Property type validation

### **Where to Add Ontology Filtering**

#### **Option A: Early Filtering (Recommended)**
Add ontology filtering **before** the existing filters:

```python
# In neptune_to_es/neptune_sparql_es_handler.py
# Around line 191 in filter_records method

def filter_records(self, records, client):
    """
    Filters records to be stored in Elastic Search.
    """
    
    # ADD THIS: Import and apply ontology filtering FIRST
    from ontology_filter import get_ontology_filter
    
    ontology_filter = get_ontology_filter()
    
    # Apply ontology filtering before existing filters
    if ontology_filter.filtering_enabled:
        records = ontology_filter.filter_records(records)
        logger.info(f"Ontology filtering applied: {len(records)} records remaining")
    
    # Continue with existing filtering logic...
    excluded_types = get_excluded_datatypes("sparql")
    excluded_properties = get_excluded_properties()
    
    # ... rest of existing method unchanged
```

#### **Option B: Replace Existing Filtering**
Replace the entire filtering logic with ontology-focused filtering:

```python
def filter_records(self, records, client):
    """
    Filters records to be stored in Elastic Search - Ontology focused.
    """
    
    from ontology_filter import get_ontology_filter
    
    ontology_filter = get_ontology_filter()
    
    # Use ontology filtering instead of default filtering
    filtered_records = ontology_filter.filter_records(records)
    
    logger.info(f"Ontology filtering: {len(records)} → {len(filtered_records)} records")
    
    return filtered_records
```

## 🔄 **Processing Flow**

### **Current Flow (No Ontology Filtering)**
```
Neptune Streams → Lambda Handler → ElasticSearchSparqlHandler
                                          ↓
                                   filter_records() 
                                   (existing filters only)
                                          ↓
                                   OpenSearch Indexing
```

### **Proposed Flow (With Ontology Filtering)**
```
Neptune Streams → Lambda Handler → ElasticSearchSparqlHandler
                                          ↓
                                   filter_records()
                                          ↓
                                   ontology_filter.filter_records()
                                   (graph + predicate filtering)
                                          ↓
                                   existing filters (optional)
                                          ↓
                                   OpenSearch Indexing
```

## 📝 **Step-by-Step Integration**

### **Step 1: Modify the Handler**

Edit `neptune_to_es/neptune_sparql_es_handler.py`:

```python
# Add import at the top of the file
from ontology_filter import get_ontology_filter

# Modify the filter_records method (around line 191)
def filter_records(self, records, client):
    """
    Filters records to be stored in Elastic Search.
    Enhanced with ontology filtering for cost optimization.
    """
    
    # Apply ontology filtering first
    ontology_filter = get_ontology_filter()
    
    if ontology_filter.filtering_enabled:
        original_count = len(records)
        records = ontology_filter.filter_records(records)
        logger.info(f"Ontology filter: {original_count} → {len(records)} records")
        
        # If no records remain after ontology filtering, return early
        if not records:
            logger.info("No records remaining after ontology filtering")
            return []
    
    # Continue with existing filtering logic...
    excluded_types = get_excluded_datatypes("sparql")
    excluded_properties = get_excluded_properties()
    
    # ... rest of existing method unchanged
```

### **Step 2: Enable Filtering via Environment Variable**

```bash
aws lambda update-function-configuration \
    --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" \
    --environment Variables='{
        "ONTOLOGY_FILTERING_ENABLED": "true",
        "ONTOLOGY_GRAPHS": "http://climate-risk-ontology,http://geonames-ontology",
        "LOG_FILTERED_RECORDS": "true"
    }'
```

### **Step 3: Deploy Modified Code**

```bash
cd /Users/chris/climate-risk-rag-aws/lambda/neptune-stream-poller
./deploy.sh
```

### **Step 4: Monitor Integration**

```bash
# Watch Lambda logs for filtering activity
aws logs tail /aws/lambda/NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3 --follow

# Look for log messages like:
# "Ontology filter: 1000 → 150 records"
# "Filtered 1000 records → 150 ontology records (85.0% filtered out)"
```

## 🧪 **Testing the Integration**

### **Test 1: Verify Filtering is Active**
```python
# Check filter status via Lambda environment
import os
print(f"Filtering enabled: {os.getenv('ONTOLOGY_FILTERING_ENABLED')}")
print(f"Ontology graphs: {os.getenv('ONTOLOGY_GRAPHS')}")
```

### **Test 2: Monitor Record Counts**
```bash
# Before integration - check DynamoDB operations
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name ConsumedReadCapacityUnits \
    --dimensions Name=TableName,Value=NeptuneOntologyFTS-LeaseTable \
    --start-time 2025-08-07T19:00:00Z \
    --end-time 2025-08-07T20:00:00Z \
    --period 300 \
    --statistics Sum

# After integration - should see reduced operations
```

### **Test 3: Verify OpenSearch Index Size**
```bash
# Check index size before and after filtering
curl -X GET "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/_cat/indices/amazon_neptune?v" \
    -u admin:veqpat-kegba2-zapbyZ
```

## ⚠️ **Important Considerations**

### **Backup Strategy**
```bash
# Create backup of original handler before modification
cp neptune_to_es/neptune_sparql_es_handler.py neptune_to_es/neptune_sparql_es_handler.py.backup
```

### **Gradual Rollout**
1. **Deploy with filtering disabled** (`ONTOLOGY_FILTERING_ENABLED=false`)
2. **Test deployment** works without issues
3. **Enable filtering** via environment variable
4. **Monitor for 24-48 hours**
5. **Adjust configuration** based on results

### **Rollback Plan**
```bash
# Disable filtering immediately if issues occur
aws lambda update-function-configuration \
    --function-name "NeptuneQuickStart-Neptune-NeptuneStreamPollerLambd-Hgt4k9V4WZw3" \
    --environment Variables='{"ONTOLOGY_FILTERING_ENABLED": "false"}'

# Or restore original code
cp neptune_to_es/neptune_sparql_es_handler.py.backup neptune_to_es/neptune_sparql_es_handler.py
./deploy.sh
```

## 📊 **Expected Results**

### **Cost Reduction**
- **60-80% fewer records** processed
- **Reduced DynamoDB operations** (fewer lease table updates)
- **Smaller OpenSearch indices** (faster queries)
- **Reduced Lambda execution time**

### **Performance Improvement**
- **Faster FTS queries** (smaller search space)
- **More relevant results** (ontology-focused)
- **Reduced noise** in search results

### **Log Output Examples**
```
INFO: Ontology filter: 1000 → 150 records
INFO: Filtered 1000 records → 150 ontology records (85.0% filtered out)
DEBUG: Including: http://climate-risk-ontology | rdfs:label | Climate Change Impact
DEBUG: Filtering: http://document-data | document:content | Reason: graph=False
```

## 🎯 **Success Criteria**

- ✅ Lambda logs show ontology filtering activity
- ✅ Reduced DynamoDB read/write operations
- ✅ Smaller OpenSearch index size
- ✅ FTS queries return only ontology results
- ✅ No errors in stream processing
- ✅ Cost reduction visible in CloudWatch metrics

---

**Status**: Ready for integration - requires manual code modification and deployment
